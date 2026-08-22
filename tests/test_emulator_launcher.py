from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from pokedex_completer_gen5.emulator.launcher import (
    BizHawkLaunchConfig,
    install_bizhawk_save,
    launch_bizhawk,
    stop_existing_bizhawk,
)


def test_launch_bizhawk_builds_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = tmp_path / "EmuHawk.exe"
    rom = tmp_path / "white.nds"
    lua = tmp_path / "bridge.lua"
    save = tmp_path / "POKEMON W.sav"
    saveram = tmp_path / "NDS" / "SaveRAM" / "Pokemon White.SaveRAM"
    exe.write_text("fake", encoding="utf-8")
    rom.write_text("fake", encoding="utf-8")
    lua.write_text("fake", encoding="utf-8")
    save.write_bytes(b"completed-save")
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    class FakeProcess:
        pid = 1234

    def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr("pokedex_completer_gen5.emulator.launcher.subprocess.Popen", fake_popen)
    monkeypatch.setattr(
        "pokedex_completer_gen5.emulator.launcher.stop_existing_bizhawk",
        lambda config: {"attempted": True, "exit_code": 0},
    )

    result = launch_bizhawk(BizHawkLaunchConfig(exe, rom, lua, save, saveram), install_save=True)

    assert result["ok"] is True
    assert result["pid"] == 1234
    assert calls
    args, kwargs = calls[0]
    command = cast(list[str], args[0])
    assert command == [str(exe), "--socket-ip", "127.0.0.1", "--socket-port", "8766", "--lua", str(lua), str(rom)]
    assert kwargs["cwd"] == str(exe.parent)
    assert saveram.read_bytes() == b"completed-save"
    assert result["installed_save"]["match"] is True
    assert result["stopped_existing"] == {"attempted": True, "exit_code": 0}


def test_stop_existing_bizhawk_normalizes_process_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeCompletedProcess:
        returncode = 128
        stdout = ""
        stderr = 'ERROR: The process "EmuHawk.exe" not found.'

    monkeypatch.setattr("pokedex_completer_gen5.emulator.launcher.os.name", "nt")
    monkeypatch.setattr(
        "pokedex_completer_gen5.emulator.launcher.subprocess.run",
        lambda *args, **kwargs: FakeCompletedProcess(),
    )

    config = BizHawkLaunchConfig(tmp_path / "EmuHawk.exe", None, tmp_path / "bridge.lua", None, None)
    result = stop_existing_bizhawk(config)

    assert result["ok"] is True
    assert result["status"] == "no_existing_process"
    assert result["stderr"] == ""


def test_stop_existing_bizhawk_reports_non_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pokedex_completer_gen5.emulator.launcher.os.name", "posix")
    config = BizHawkLaunchConfig(tmp_path / "EmuHawk.exe", None, tmp_path / "bridge.lua", None, None)
    result = stop_existing_bizhawk(config)
    assert result["attempted"] is False


def test_install_bizhawk_save_can_be_disabled_with_empty_paths(tmp_path: Path) -> None:
    exe = tmp_path / "EmuHawk.exe"
    lua = tmp_path / "bridge.lua"

    assert install_bizhawk_save(BizHawkLaunchConfig(exe, None, lua, None, None)) is None


def test_launch_bizhawk_rejects_missing_exe(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="BizHawk executable not found"):
        launch_bizhawk(BizHawkLaunchConfig(tmp_path / "missing.exe", None, tmp_path / "bridge.lua", None, None))


def test_launch_bizhawk_rejects_missing_lua(tmp_path: Path) -> None:
    exe = tmp_path / "EmuHawk.exe"
    exe.write_text("fake", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Lua bridge script not found"):
        launch_bizhawk(BizHawkLaunchConfig(exe, None, tmp_path / "missing.lua", None, None))
