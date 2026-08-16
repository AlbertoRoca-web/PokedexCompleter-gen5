from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pokedex_completer_gen5.emulator.macro_visual_verifier import verify_macro_visual_change
from pokedex_completer_gen5.emulator.screen_classifier import classify_screenshot, compare_screenshots
from pokedex_completer_gen5.emulator.visual_wait import InformativeScreenshotResult, ScreenshotAttempt


def test_classify_blank_white(tmp_path: Path) -> None:
    path = tmp_path / "blank.png"
    Image.new("RGB", (64, 64), "white").save(path)

    assert classify_screenshot(path).screen_type == "blank-white"


def test_classify_boot_or_logo(tmp_path: Path) -> None:
    path = tmp_path / "boot.png"
    image = Image.new("RGB", (256, 384), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 50), "The Pokemon Company", fill="black")
    draw.rectangle((60, 130, 190, 160), outline="gray", width=3)
    image.save(path)

    assert classify_screenshot(path).screen_type == "boot-or-logo"


def test_classify_menu_like(tmp_path: Path) -> None:
    path = tmp_path / "menu.png"
    image = Image.new("RGB", (256, 384), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((130, 30, 245, 300), outline="black", width=3)
    for y in range(60, 260, 35):
        draw.rectangle((145, y, 230, y + 16), fill="black")
    image.save(path)

    assert classify_screenshot(path).screen_type == "menu-like"


def test_compare_screenshots_detects_change(tmp_path: Path) -> None:
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    Image.new("RGB", (32, 32), "white").save(before)
    Image.new("RGB", (32, 32), "black").save(after)

    delta = compare_screenshots(before, after)

    assert delta.changed_enough is True
    assert delta.changed_pixel_ratio == 1.0


def test_macro_visual_verifier_marks_no_change_failure(tmp_path: Path) -> None:
    path = tmp_path / "same.png"
    image = Image.new("RGB", (32, 32), "white")
    image.putpixel((0, 0), (0, 0, 0))
    image.save(path)
    before = _result(path)
    after = _result(path)

    verification = verify_macro_visual_change("open_menu", before, after)

    assert verification.status == "verified-failure"


def _result(path: Path) -> InformativeScreenshotResult:
    attempt = ScreenshotAttempt(
        attempt=1,
        path=str(path),
        response={"ok": True},
        analysis={"visually_informative": True},
        artifact={},
    )
    return InformativeScreenshotResult(ok=True, reason="informative_screenshot_found", attempts=[attempt])
