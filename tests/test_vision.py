from __future__ import annotations

from pathlib import Path

from PIL import Image

from pokedex_completer_gen5.emulator.vision import analyze_screenshot


def test_analyze_screenshot_detects_blank_white(tmp_path: Path) -> None:
    path = tmp_path / "white.png"
    Image.new("RGB", (16, 16), "white").save(path)

    analysis = analyze_screenshot(path)

    assert analysis["blank_white"] is True
    assert analysis["visually_informative"] is False


def test_analyze_screenshot_detects_informative_image(tmp_path: Path) -> None:
    path = tmp_path / "mixed.png"
    image = Image.new("RGB", (2, 1), "white")
    image.putpixel((0, 0), (0, 0, 0))
    image.save(path)

    analysis = analyze_screenshot(path)

    assert analysis["blank_white"] is False
    assert analysis["visually_informative"] is True
