from __future__ import annotations

from pathlib import Path

import pytest

from pokedex_completer_gen5.emulator.launcher import BizHawkLaunchConfig, launch_bizhawk


def test_launch_bizhawk_builds_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = tmp_path / "EmuHawk.exe"
    rom = tmp_path / "white.nds"
    lua = tmp_path / "bridge.lua"
    exe.write_text("fake", encoding="utf-8")
    rom.write_text("fake", encoding="utf-8")
    lua.write_text("fake", encoding="utf-8")
    calls: list[object] = []

    class FakeProcess:
        pid = 1234

    def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr("pokedex_completer_gen5.emulator.launcher.subprocess.Popen", fake_popen)

    result = launch_bizhawk(BizHawkLaunchConfig(exe, rom, lua))

    assert result["ok"] is True
    assert result["pid"] == 1234
    assert calls
    args, kwargs = calls[0]
    command = args[0]
    assert command == [str(exe), "--lua", str(lua), str(rom)]
    assert kwargs["cwd"] == str(exe.parent)


def test_launch_bizhawk_rejects_missing_exe(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="BizHawk executable not found"):
        launch_bizhawk(BizHawkLaunchConfig(tmp_path / "missing.exe", None, tmp_path / "bridge.lua"))


def test_launch_bizhawk_rejects_missing_lua(tmp_path: Path) -> None:
    exe = tmp_path / "EmuHawk.exe"
    exe.write_text("fake", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Lua bridge script not found"):
        launch_bizhawk(BizHawkLaunchConfig(exe, None, tmp_path / "missing.lua"))
