from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    profile: str = Field(default="balanced", alias="RLD_AI_PROFILE")
    model_classifier: str = Field(default="gpt-5-nano", alias="AI_MODEL_CLASSIFIER")
    model_bounded_planner: str = Field(default="gpt-5-mini", alias="AI_MODEL_BOUNDED_PLANNER")
    model_planner: str = Field(default="gpt-5.4-mini", alias="AI_MODEL_PLANNER")
    model_recovery: str = Field(default="gpt-5.6-terra", alias="AI_MODEL_RECOVERY")
    model_hard: str = Field(default="gpt-5.5", alias="AI_MODEL_HARD")
    reasoning_classifier: str = Field(default="none", alias="AI_REASONING_CLASSIFIER")
    reasoning_bounded: str = Field(default="low", alias="AI_REASONING_BOUNDED")
    reasoning_planner: str = Field(default="low", alias="AI_REASONING_PLANNER")
    reasoning_recovery: str = Field(default="medium", alias="AI_REASONING_RECOVERY")
    reasoning_hard: str = Field(default="high", alias="AI_REASONING_HARD")


class EmulatorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bizhawk_exe: Path = Field(
        default=Path(r"D:\alroc\codepup\tools\BizHawk-2.11.1\EmuHawk.exe"),
        alias="BIZHAWK_EXE",
    )
    pokemon_white_rom: Path = Field(
        default=Path(
            r"C:\Users\alroc\Downloads\Pokemon - White Version (USA, Europe) (NDSi Enhanced)"
            r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).nds"
        ),
        alias="POKEMON_WHITE_ROM",
    )
    pokemon_white_save: Path = Field(
        default=Path(r"D:\Users\alroc\Downloads\rolplete\POKEMON W.sav"),
        alias="POKEMON_WHITE_SAVE",
    )
    bizhawk_white_saveram: Path = Field(
        default=Path(
            r"D:\alroc\codepup\tools\BizHawk-2.11.1\NDS\SaveRAM"
            r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).SaveRAM"
        ),
        alias="BIZHAWK_WHITE_SAVERAM",
    )
    lua_script: Path = Field(
        default=Path(r"D:\alroc\codepup\PokedexCompleter-gen5\lua\bizhawk_gen5_bridge.lua"),
        alias="BIZHAWK_LUA_SCRIPT",
    )
    legacy_bridge_host: str = Field(default="127.0.0.1", alias="BIZHAWK_BRIDGE_HOST")
    legacy_bridge_port: int = Field(default=8765, alias="BIZHAWK_BRIDGE_PORT")
    legacy_bridge_timeout_seconds: float = Field(default=5.0, alias="BIZHAWK_BRIDGE_TIMEOUT_SECONDS")
    native_bridge_host: str = Field(default="127.0.0.1", alias="BIZHAWK_NATIVE_BRIDGE_HOST")
    native_bridge_port: int = Field(default=8766, alias="BIZHAWK_NATIVE_BRIDGE_PORT")
    native_bridge_timeout_seconds: float = Field(default=5.0, alias="BIZHAWK_NATIVE_BRIDGE_TIMEOUT_SECONDS")


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    runtime_dir: Path = Field(default=Path(".runtime"), alias="POKEDEX_RUNTIME_DIR")
    db_path: Path = Field(default=Path(".runtime") / "pokedex_completer.sqlite3", alias="POKEDEX_DB_PATH")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai: AISettings = Field(default_factory=AISettings)
    emulator: EmulatorSettings = Field(default_factory=EmulatorSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
