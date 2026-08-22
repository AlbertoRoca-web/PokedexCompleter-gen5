from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeError
from pokedex_completer_gen5.server.rest import app


def test_dashboard_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "PC Living Dex Dashboard" in response.text


def test_local_connection_discovery_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/local/discover")
    assert response.status_code == 200
    assert response.json()["services"]["mcp_stdio"]["command"] == "uv run rld-mcp"


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_provider_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health/providers")
    assert response.status_code == 200
    assert "providers" in response.json()


def test_ui_event_endpoint_records_telemetry() -> None:
    client = TestClient(app)
    response = client.post("/api/ui/events", json={"event_type": "clicked_thing", "payload": {"ok": True}})

    assert response.status_code == 200
    assert response.json()["event_type"] == "ui.clicked_thing"
    telemetry = client.get("/api/telemetry").json()["events"]
    assert any(event["event_type"] == "ui.clicked_thing" for event in telemetry)


def test_pc_living_dex_empty_save_returns_json_error() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/pc-living-dex",
        json={
            "save_path": "",
            "game": "white",
            "scope": "regional",
            "target_policy": "game-regional",
            "include_party": True,
        },
    )

    assert response.status_code == 400
    assert "Save path is empty" in response.json()["detail"]


def test_pc_living_dex_missing_save_returns_json_error() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/pc-living-dex",
        json={
            "save_path": "D:/definitely/not/a/real/save.sav",
            "game": "white",
            "scope": "regional",
            "target_policy": "game-regional",
            "include_party": True,
        },
    )

    assert response.status_code == 404
    assert "Save file not found" in response.json()["detail"]


def test_voice_config_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/voice/config?mode=rubberduck")
    assert response.status_code == 200
    assert response.json()["mode"] == "rubberduck"


def test_voice_realtime_session_requires_non_off_mode() -> None:
    client = TestClient(app)
    response = client.post("/api/voice/realtime-session?mode=off")
    assert response.status_code == 400


def test_validator_event_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/validator/events",
        json={
            "event_type": "voice_commentary",
            "message": "Testing rubberduck event.",
            "payload": {"source": "test"},
        },
    )

    assert response.status_code == 200
    assert response.json()["event_type"] == "voice_commentary"
    assert client.get("/api/validator/events").json()["events"]


def test_emulator_macro_open_menu_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        calls.append((method, params))
        return {"ok": True, "method": method}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.post("/api/emulator/macro/open-menu", json={"wait_frames": 7})

    assert response.status_code == 200
    assert response.json()["macro_name"] == "open_menu"
    assert response.json()["status"] == "executed-needs-human-confirmation"
    assert ("press", {"button": "X", "frames": 1}) in calls
    assert ("frame_advance", {"frames": 7}) in calls
    assert response.json()["verification"]["mode"] == "visual-macro-v1"
    assert response.json()["validator_event"]["event_type"] == "macro_visual_verification"


def test_emulator_speed_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        assert method == "emulator.set_speed"
        assert params == {"percent": 400}
        return {"ok": True, "method": method, "percent": 400}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.post("/api/emulator/speed", json={"percent": 400})

    assert response.status_code == 200
    assert response.json()["percent"] == 400


def test_emulator_semantic_state_endpoint_uses_memory_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if method == "bridge.info":
            return {"ok": True, "method": method, "frame_count": 7}
        if method == "memory.read_bytes":
            return {"ok": True, "method": method, "values_csv": "6", "hex": "06"}
        raise AssertionError(method)

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.get("/api/emulator/semantic-state")

    assert response.status_code == 200
    assert response.json()["mode"] == "unknown"
    assert response.json()["state"]["menu_open"] is False
    assert "battle_state" in response.json()["missing_profile_fields"]
    assert response.json()["profile"]["profile_id"] == "white_us_eu"


def test_emulator_memory_read_bytes_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        assert method == "memory.read_bytes"
        assert params == {"domain": "Main RAM", "address": 16, "length": 4}
        return {"ok": True, "method": method, "values_csv": "1,2,3,255", "hex": "010203FF"}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.post(
        "/api/emulator/memory/read-bytes",
        json={"domain": "Main RAM", "address": 16, "length": 4},
    )

    assert response.status_code == 200
    assert response.json()["values"] == [1, 2, 3, 255]
    assert response.json()["hex"] == "010203FF"


def test_emulator_memory_read_u8_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        assert method == "memory.read_u8"
        assert params == {"domain": "Main RAM", "address": 32}
        return {"ok": True, "method": method, "value": 42}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.post("/api/emulator/memory/read-u8", json={"domain": "Main RAM", "address": 32})

    assert response.status_code == 200
    assert response.json()["value"] == 42


def test_emulator_memory_diff_after_press_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        assert method == "memory.diff_after_press"
        assert params == {
            "domain": "ARM9 System Bus",
            "address": 16,
            "length": 32,
            "button": "Start",
            "press_frames": 5,
            "advance_frames": 120,
            "max_changes": 10,
        }
        return {
            "ok": True,
            "method": method,
            "changed_count": 2,
            "changes_csv": "20AA4C0:0:1,20AA4C1:7:9",
        }

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    client = TestClient(app)
    response = client.post(
        "/api/emulator/memory/diff-after-press",
        json={
            "domain": "ARM9 System Bus",
            "address": 16,
            "length": 32,
            "button": "start",
            "press_frames": 5,
            "advance_frames": 120,
            "max_changes": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["changes"][0]["hex_address"] == "0x20AA4C0"
    assert response.json()["changes"][1]["after"] == 9


def test_emulator_macro_feedback_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/emulator/macro/feedback",
        json={"macro_run_id": "macro-1", "outcome": "success", "notes": "opened menu"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "success"
    assert client.get("/api/emulator/macro/feedback").json()["feedback"]


def test_emulator_bridge_error_returns_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient:
        def __init__(self, config: object) -> None:
            self.config = config

        def get_state(self) -> dict[str, object]:
            raise BizHawkBridgeError("connection refused")

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.BizHawkClient", FailingClient)
    client = TestClient(app)
    response = client.get("/api/emulator/state")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "connection refused"
    assert "Launch from the website" in response.json()["detail"]["hint"]
    assert "native_bridge" in response.json()["detail"]


def test_emulator_press_endpoint_uses_bridge_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, config: object) -> None:
            self.config = config

        def press(self, button: str, frames: int = 1) -> dict[str, object]:
            return {"ok": True, "button": button, "frames": frames}

        def press_sequence(self, buttons: list[str], frames: int = 1, gap_frames: int = 1) -> dict[str, object]:
            return {"ok": True, "buttons": buttons, "frames": frames, "gap_frames": gap_frames}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.BizHawkClient", FakeClient)
    client = TestClient(app)
    response = client.post("/api/emulator/press", json={"button": "A", "frames": 2})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "button": "A", "frames": 2}

    sequence_response = client.post(
        "/api/emulator/press-sequence",
        json={"buttons": ["A", "B"], "frames": 2, "gap_frames": 3},
    )
    assert sequence_response.status_code == 200
    assert sequence_response.json() == {"ok": True, "buttons": ["A", "B"], "frames": 2, "gap_frames": 3}


def test_emulator_touch_endpoint_uses_bridge_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_bridge_request(method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        calls.append((method, params))
        return {"ok": True, "method": method, **(params or {})}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.bridge_request", fake_bridge_request)
    response = TestClient(app).post("/api/emulator/touch", json={"x": 42, "y": 99, "frames": 2})

    assert response.status_code == 200
    assert calls == [("touch", {"x": 42, "y": 99, "frames": 2})]


def test_emulator_touch_endpoint_validates_ds_coordinates() -> None:
    response = TestClient(app).post("/api/emulator/touch", json={"x": 256, "y": 256})

    assert response.status_code == 422
