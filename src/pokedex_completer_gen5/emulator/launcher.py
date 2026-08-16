from __future__ import annotations

import hashlib
import os
import shutil
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
DEFAULT_WHITE_SAVE = Path(r"D:\Users\alroc\Downloads\rolplete\POKEMON W.sav")
DEFAULT_WHITE_SAVERAM = Path(
    r"D:\alroc\codepup\tools\BizHawk-2.11.1\NDS\SaveRAM"
    r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).SaveRAM"
)


@dataclass(frozen=True)
class BizHawkLaunchConfig:
    bizhawk_exe: Path
    rom_path: Path | None
    lua_script: Path
    save_source: Path | None
    saveram_path: Path | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bizhawk_exe": str(self.bizhawk_exe),
            "rom_path": str(self.rom_path) if self.rom_path else None,
            "lua_script": str(self.lua_script),
            "save_source": str(self.save_source) if self.save_source else None,
            "saveram_path": str(self.saveram_path) if self.saveram_path else None,
        }


def bizhawk_launch_config_from_env(rom_path: Path | None = None) -> BizHawkLaunchConfig:
    configured_rom = rom_path or _optional_path(os.getenv("POKEMON_WHITE_ROM")) or DEFAULT_WHITE_ROM
    return BizHawkLaunchConfig(
        bizhawk_exe=Path(os.getenv("BIZHAWK_EXE", str(DEFAULT_BIZHAWK_EXE))),
        rom_path=configured_rom,
        lua_script=Path(os.getenv("BIZHAWK_LUA_SCRIPT", str(DEFAULT_LUA_SCRIPT))),
        save_source=_optional_path(os.getenv("POKEMON_WHITE_SAVE")) or DEFAULT_WHITE_SAVE,
        saveram_path=_optional_path(os.getenv("BIZHAWK_WHITE_SAVERAM")) or DEFAULT_WHITE_SAVERAM,
    )


def install_bizhawk_save(config: BizHawkLaunchConfig) -> dict[str, Any] | None:
    if config.save_source is None or config.saveram_path is None:
        return None
    if not config.save_source.exists():
        raise FileNotFoundError(f"Configured White save not found: {config.save_source}")
    config.saveram_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config.save_source, config.saveram_path)
    source_hash = _sha256(config.save_source)
    saveram_hash = _sha256(config.saveram_path)
    return {
        "source": str(config.save_source),
        "saveram": str(config.saveram_path),
        "bytes": config.saveram_path.stat().st_size,
        "sha256": saveram_hash,
        "match": source_hash == saveram_hash,
    }


def stop_existing_bizhawk(config: BizHawkLaunchConfig) -> dict[str, Any]:
    if os.name != "nt":
        return {"attempted": False, "reason": "Only Windows taskkill is supported for now."}
    result = subprocess.run(  # noqa: S603 - local emulator process cleanup.
        ["taskkill", "/IM", config.bizhawk_exe.name, "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "attempted": True,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def launch_bizhawk(
    config: BizHawkLaunchConfig,
    *,
    install_save: bool = True,
    restart_existing: bool = True,
) -> dict[str, Any]:
    if not config.bizhawk_exe.exists():
        raise FileNotFoundError(f"BizHawk executable not found: {config.bizhawk_exe}")
    if config.rom_path is not None and not config.rom_path.exists():
        raise FileNotFoundError(f"ROM not found: {config.rom_path}")
    if not config.lua_script.exists():
        raise FileNotFoundError(f"Lua bridge script not found: {config.lua_script}")

    stopped_existing = stop_existing_bizhawk(config) if restart_existing else None
    installed_save = install_bizhawk_save(config) if install_save else None

    args = [str(config.bizhawk_exe), "--lua", str(config.lua_script)]
    if config.rom_path is not None:
        # BizHawk help says the ROM should be passed last. Because of course it does.
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
        "stopped_existing": stopped_existing,
        "installed_save": installed_save,
        "next_step": (
            "BizHawk was launched with --lua. "
            "If controls still fail, check the Lua Console for bridge errors."
        ),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None
