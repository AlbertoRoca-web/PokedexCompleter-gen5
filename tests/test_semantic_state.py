from __future__ import annotations

from typing import Any

from pokedex_completer_gen5.emulator.semantic_state import build_semantic_state, load_memory_profile


def test_default_memory_profile_starts_unverified() -> None:
    profile = load_memory_profile("white_us_eu")

    assert profile.profile_id == "white_us_eu"
    assert profile.domain == "ARM9 System Bus"
    assert "menu_state" in profile.missing_fields()
    assert profile.known_fields() == []


def test_semantic_state_reports_missing_profile_fields_without_guessing() -> None:
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, params))
        if method == "bridge.info":
            return {"ok": True, "frame_count": 123, "approx_framerate": 240}
        raise AssertionError(method)

    payload = build_semantic_state(fake_bridge, profile_id="white_us_eu").to_dict()

    assert payload["mode"] == "unknown"
    assert payload["confidence"] == 0.0
    assert "menu_state" in payload["missing_profile_fields"]
    assert calls == [("bridge.info", None)]
