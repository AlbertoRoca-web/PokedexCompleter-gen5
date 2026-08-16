from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from pokedex_completer_gen5.emulator.title_flow import (
    _looks_like_gen5_overworld_frame,
    run_resume_saved_game_from_title,
)
from pokedex_completer_gen5.persistence.database import init_database, reset_database_engine_for_tests
from pokedex_completer_gen5.settings import get_settings


def configure_runtime(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("POKEDEX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("POKEDEX_DB_PATH", str(tmp_path / "runtime" / "run.sqlite3"))
    get_settings.cache_clear()
    reset_database_engine_for_tests()
    init_database()


def test_resume_saved_game_from_title_candidate_overworld(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    screenshots = 0
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal screenshots
        calls.append((method, params))
        if method == "bridge.info":
            return {"ok": True, "method": method, "approx_framerate": 240.0, "turbo": True}
        if method == "screenshot":
            screenshots += 1
            path = Path(str(params["path"]))  # type: ignore[index]
            if screenshots == 1:
                _boot_logo(path)
            elif screenshots == 2:
                _continue_menu_like(path)
            else:
                _overworld_like(path)
            return {"ok": True, "method": method}
        if method == "memory.read_bytes":
            assert params == {"domain": "ARM9 System Bus", "address": 0x020A84BF, "length": 1}
            return {"ok": True, "method": method, "values_csv": "6", "hex": "06"}
        if method in {"press", "frame_advance"}:
            return {"ok": True, "method": method}
        raise AssertionError(method)

    result = run_resume_saved_game_from_title(
        fake_bridge,
        initial_wait_frames=1,
        wait_after_start_frames=2,
        wait_after_continue_frames=3,
        wait_after_cgear_prompt_frames=3,
        wait_after_cgear_confirm_frames=3,
        visual_max_attempts=1,
        press_frames=5,
        change_max_attempts=2,
        change_advance_frames=4,
    )

    payload = result.to_dict()
    assert payload["status"] == "candidate-overworld"
    assert payload["verification"]["screen_delta"]["changed_enough"] is True
    assert payload["verification"]["ram_verified"] is True
    assert payload["verification"]["visual_known_overworld"] is True
    assert ("press", {"button": "Start", "frames": 30}) in calls
    assert ("press", {"button": "A", "frames": 5}) in calls
    assert ("press", {"button": "Down", "frames": 5}) in calls
    assert any(method == "bridge.info" for method, _ in calls)


def test_resume_saved_game_skips_start_when_already_on_continue_menu(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    screenshots = 0
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_bridge(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal screenshots
        calls.append((method, params))
        if method == "bridge.info":
            return {"ok": True, "method": method}
        if method == "screenshot":
            screenshots += 1
            path = Path(str(params["path"]))  # type: ignore[index]
            if screenshots == 1:
                _continue_menu_like(path)
            else:
                _overworld_like(path)
            return {"ok": True, "method": method}
        if method == "memory.read_bytes":
            return {"ok": True, "method": method, "values_csv": "6", "hex": "06"}
        if method in {"press", "frame_advance"}:
            return {"ok": True, "method": method}
        raise AssertionError(method)

    result = run_resume_saved_game_from_title(
        fake_bridge,
        initial_wait_frames=1,
        wait_after_start_frames=2,
        wait_after_continue_frames=3,
        wait_after_cgear_prompt_frames=3,
        wait_after_cgear_confirm_frames=3,
        visual_max_attempts=1,
        press_frames=5,
        change_max_attempts=2,
        change_advance_frames=4,
    )

    payload = result.to_dict()
    assert payload["status"] == "candidate-overworld"
    assert ("press", {"button": "Start", "frames": 5}) not in calls
    assert ("press", {"button": "A", "frames": 5}) in calls


def test_overworld_frame_guard_rejects_dark_cinematic(tmp_path: Path) -> None:
    path = tmp_path / "cinematic.png"
    image = Image.new("RGB", (256, 384), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 256, 192), fill=(70, 50, 30))
    draw.rectangle((120, 30, 220, 90), fill=(200, 170, 100))
    image.save(path)

    assert _looks_like_gen5_overworld_frame(path) is False


def _boot_logo(path: Path) -> None:
    image = Image.new("RGB", (256, 384), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 50), "The Pokemon Company", fill="black")
    image.save(path)


def _continue_menu_like(path: Path) -> None:
    image = Image.new("RGB", (256, 384), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 230, 260), outline="black", width=3)
    draw.rectangle((100, 120, 210, 145), fill="black")
    draw.rectangle((100, 170, 210, 195), fill="black")
    image.save(path)


def _overworld_like(path: Path) -> None:
    image = Image.new("RGB", (256, 384), (140, 180, 120))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 236, 180), fill=(220, 210, 180))
    draw.rectangle((100, 170, 140, 210), fill=(30, 60, 120))
    draw.rectangle((0, 192, 256, 384), fill=(5, 20, 20))
    for x in range(0, 256, 32):
        draw.line((x, 192, x, 384), fill=(20, 60, 55))
    image.save(path)
