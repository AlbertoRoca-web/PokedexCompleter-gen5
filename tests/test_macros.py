from __future__ import annotations

from typing import Any

from pokedex_completer_gen5.emulator.macros import run_close_menu_macro, run_open_menu_macro


def test_open_menu_macro_presses_menu_action_then_waits() -> None:
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, params))
        return {"ok": True, "method": method}

    macro = run_open_menu_macro(fake_bridge, wait_frames=12)

    assert macro.macro_name == "open_menu"
    assert macro.status == "executed-needs-human-confirmation"
    assert calls == [("press", {"button": "X", "frames": 1}), ("frame_advance", {"frames": 12})]


def test_close_menu_macro_presses_cancel_then_waits() -> None:
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, params))
        return {"ok": True, "method": method}

    macro = run_close_menu_macro(fake_bridge, wait_frames=8)

    assert macro.macro_name == "close_menu"
    assert calls == [("press", {"button": "B", "frames": 1}), ("frame_advance", {"frames": 8})]
