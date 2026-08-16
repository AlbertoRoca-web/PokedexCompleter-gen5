from __future__ import annotations

from pathlib import Path

from pokedex_completer_gen5.settings import AISettings, EmulatorSettings, RuntimeSettings, TimingSettings, get_settings


def test_ai_settings_defaults_are_cost_routed() -> None:
    settings = AISettings()

    assert settings.model_classifier == "gpt-5-nano"
    assert settings.model_bounded_planner == "gpt-5-mini"
    assert settings.model_planner == "gpt-5.4-mini"
    assert settings.model_recovery == "gpt-5.6-terra"
    assert settings.model_hard == "gpt-5.5"


def test_emulator_settings_accept_env_aliases(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BIZHAWK_NATIVE_BRIDGE_PORT", "9876")
    monkeypatch.setenv("POKEMON_WHITE_SAVE", r"D:\saves\POKEMON W.sav")

    settings = EmulatorSettings()

    assert settings.native_bridge_port == 9876
    assert settings.pokemon_white_save == Path(r"D:\saves\POKEMON W.sav")
    assert settings.speed_percent == 400


def test_timing_settings_default_to_fast_profile() -> None:
    settings = TimingSettings()

    assert settings.speed_profile == "fast"
    assert settings.title_press_frames == 5
    assert settings.title_change_advance_frames == 120
    assert settings.macro_wait_frames == 12


def test_runtime_settings_defaults_to_local_runtime_dir() -> None:
    settings = RuntimeSettings()

    assert settings.runtime_dir == Path(".runtime")
    assert settings.db_path == Path(".runtime") / "pokedex_completer.sqlite3"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
