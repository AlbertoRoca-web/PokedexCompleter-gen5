from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pokedex_completer_gen5.server.rest import app


def test_dashboard_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "PC Living Dex Dashboard" in response.text


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


def test_emulator_press_endpoint_uses_bridge_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, config: object) -> None:
            self.config = config

        def press(self, button: str, frames: int = 1) -> dict[str, object]:
            return {"ok": True, "button": button, "frames": frames}

    monkeypatch.setattr("pokedex_completer_gen5.server.rest.BizHawkClient", FakeClient)
    client = TestClient(app)
    response = client.post("/api/emulator/press", json={"button": "A", "frames": 2})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "button": "A", "frames": 2}
