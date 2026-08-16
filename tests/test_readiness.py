from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from pokedex_completer_gen5.emulator.readiness import ensure_emulator_ready
from pokedex_completer_gen5.persistence.database import init_database, reset_database_engine_for_tests
from pokedex_completer_gen5.settings import get_settings


def configure_runtime(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("POKEDEX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("POKEDEX_DB_PATH", str(tmp_path / "runtime" / "run.sqlite3"))
    get_settings.cache_clear()
    reset_database_engine_for_tests()
    init_database()


class FakeBridge:
    def start(self) -> None:
        pass

    def status(self) -> dict[str, Any]:
        return {"connected": True}

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "bridge.info":
            return {"ok": True, "method": method, "turbo": True}
        if method == "get_state":
            return {"ok": True, "method": method}
        if method == "screenshot":
            path = Path(str(params["path"]))  # type: ignore[index]
            Image.new("RGB", (8, 8), "white").save(path)
            return {"ok": True, "method": method}
        raise AssertionError(method)


def test_ensure_emulator_ready_uses_existing_good_bridge(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr("pokedex_completer_gen5.emulator.readiness.native_bridge", lambda: FakeBridge())

    result = ensure_emulator_ready(relaunch_if_needed=False).to_dict()

    assert result["ok"] is True
    assert [probe["name"] for probe in result["probes"]] == ["bridge.info", "get_state", "screenshot"]


def test_ensure_emulator_ready_can_relaunch_after_failed_probe(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    calls = {"bridge": 0}

    class FailingThenGoodBridge(FakeBridge):
        def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            if calls["bridge"] == 0:
                calls["bridge"] += 1
                from pokedex_completer_gen5.emulator.native_bridge import NativeBridgeError

                raise NativeBridgeError("nope")
            return super().request(method, params)

    bridge = FailingThenGoodBridge()
    monkeypatch.setattr("pokedex_completer_gen5.emulator.readiness.native_bridge", lambda: bridge)
    monkeypatch.setattr(
        "pokedex_completer_gen5.emulator.readiness.launch_bizhawk",
        lambda *args, **kwargs: {"ok": True, "pid": 123},
    )
    monkeypatch.setattr(
        "pokedex_completer_gen5.emulator.readiness.wait_for_native_bridge",
        lambda timeout_seconds=25: {"ok": True},
    )

    result = ensure_emulator_ready(relaunch_if_needed=True).to_dict()

    assert result["ok"] is True
    assert result["retried_launch"] is True
