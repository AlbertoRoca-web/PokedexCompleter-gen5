from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BIZHAWK_EXE = Path(r"D:\alroc\codepup\tools\BizHawk-2.11.1\EmuHawk.exe")
DEFAULT_WHITE_ROM = Path(
    r"C:\Users\alroc\Downloads\Pokemon - White Version (USA, Europe) (NDSi Enhanced)"
    r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).nds"
)
DEFAULT_LUA_SCRIPT = Path(r"D:\alroc\codepup\PokedexCompleter-gen5\lua\bizhawk_gen5_bridge.lua")


@dataclass(frozen=True)
class BizHawkLaunchConfig:
    bizhawk_exe: Path
    rom_path: Path | None
    lua_script: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "bizhawk_exe": str(self.bizhawk_exe),
            "rom_path": str(self.rom_path) if self.rom_path else None,
            "lua_script": str(self.lua_script),
        }


def bizhawk_launch_config_from_env(rom_path: Path | None = None) -> BizHawkLaunchConfig:
    configured_rom = rom_path or _optional_path(os.getenv("POKEMON_WHITE_ROM")) or DEFAULT_WHITE_ROM
    return BizHawkLaunchConfig(
        bizhawk_exe=Path(os.getenv("BIZHAWK_EXE", str(DEFAULT_BIZHAWK_EXE))),
        rom_path=configured_rom,
        lua_script=Path(os.getenv("BIZHAWK_LUA_SCRIPT", str(DEFAULT_LUA_SCRIPT))),
    )


def launch_bizhawk(config: BizHawkLaunchConfig) -> dict[str, Any]:
    if not config.bizhawk_exe.exists():
        raise FileNotFoundError(f"BizHawk executable not found: {config.bizhawk_exe}")
    if config.rom_path is not None and not config.rom_path.exists():
        raise FileNotFoundError(f"ROM not found: {config.rom_path}")

    args = [str(config.bizhawk_exe)]
    if config.rom_path is not None:
        args.append(str(config.rom_path))

    process = subprocess.Popen(  # noqa: S603 - local user-configured executable launcher.
        args,
        cwd=str(config.bizhawk_exe.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {
        "ok": True,
        "pid": process.pid,
        "launched": config.to_dict(),
        "next_step": "In BizHawk, open Tools -> Lua Console and load the bridge script if it is not already running.",
    }


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None
