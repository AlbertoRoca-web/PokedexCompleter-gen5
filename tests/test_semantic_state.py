from __future__ import annotations

from typing import Any

from pokedex_completer_gen5.emulator.semantic_state import build_semantic_state, load_memory_profile


def test_default_memory_profile_has_tentative_menu_state() -> None:
    profile = load_memory_profile("white_us_eu")

    assert profile.profile_id == "white_us_eu"
    assert profile.domain == "ARM9 System Bus"
    assert "menu_state" in profile.known_fields()
    assert "battle_state" in profile.missing_fields()


def test_semantic_state_unknown_mapped_menu_value_does_not_fallback_to_nonzero() -> None:
    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "bridge.info":
            return {"ok": True, "frame_count": 123, "approx_framerate": 240}
        if method == "memory.read_bytes":
            return {"ok": True, "values_csv": "12", "hex": "0C"}
        raise AssertionError(method)

    payload = build_semantic_state(fake_bridge, profile_id="white_us_eu").to_dict()

    assert payload["mode"] == "unknown"
    assert payload["state"]["menu_open"] is None


def test_semantic_state_maps_loaded_overworld_menu_closed_value() -> None:
    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "bridge.info":
            return {"ok": True, "frame_count": 123, "approx_framerate": 240}
        if method == "memory.read_bytes":
            return {"ok": True, "values_csv": "4", "hex": "04"}
        raise AssertionError(method)

    payload = build_semantic_state(fake_bridge, profile_id="white_us_eu").to_dict()

    assert payload["mode"] == "unknown"
    assert payload["state"]["menu_open"] is False


def test_semantic_state_uses_tentative_menu_value_map() -> None:
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, params))
        if method == "bridge.info":
            return {"ok": True, "frame_count": 123, "approx_framerate": 240}
        if method == "memory.read_bytes":
            assert params == {"domain": "ARM9 System Bus", "address": 0x020A84BF, "length": 1}
            return {"ok": True, "values_csv": "7", "hex": "07"}
        raise AssertionError(method)

    payload = build_semantic_state(fake_bridge, profile_id="white_us_eu").to_dict()

    assert payload["mode"] == "menu"
    assert payload["state"]["menu_open"] is True
    assert payload["confidence"] > 0
    assert "battle_state" in payload["missing_profile_fields"]
    assert calls == [
        ("bridge.info", None),
        ("memory.read_bytes", {"domain": "ARM9 System Bus", "address": 0x020A84BF, "length": 1}),
    ]
