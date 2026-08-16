from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageChops, ImageStat

from pokedex_completer_gen5.emulator.vision import analyze_screenshot


@dataclass(frozen=True)
class ScreenClassification:
    screen_type: str
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_type": self.screen_type,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


@dataclass(frozen=True)
class ScreenDelta:
    before_path: str
    after_path: str
    mean_abs_diff: float
    changed_pixel_ratio: float
    changed_enough: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_path": self.before_path,
            "after_path": self.after_path,
            "mean_abs_diff": self.mean_abs_diff,
            "changed_pixel_ratio": self.changed_pixel_ratio,
            "changed_enough": self.changed_enough,
        }


def classify_screenshot(path: Path) -> ScreenClassification:
    analysis = analyze_screenshot(path)
    if analysis["blank_white"]:
        return ScreenClassification("blank-white", 0.99, ["near-white image with almost no channel range"])
    if analysis["blank_black"]:
        return ScreenClassification("blank-black", 0.99, ["near-black image with almost no channel range"])

    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        dark_ratio = _dark_pixel_ratio(gray)
        top_dark_ratio = _dark_pixel_ratio(gray.crop((0, 0, width, max(1, height // 3))))
        row_density = _text_row_density(gray)
        right_panel_dark_ratio = _dark_pixel_ratio(gray.crop((width * 2 // 3, 0, width, height)))

    reasons: list[str] = []
    if dark_ratio > 0.04 and (row_density > 0.08 or right_panel_dark_ratio > 0.04):
        reasons.append("dark pixel density and row structure look menu-like")
        reasons.append(f"dark_ratio={dark_ratio:.3f}, row_density={row_density:.3f}")
        return ScreenClassification("menu-like", min(0.9, 0.45 + row_density + dark_ratio), reasons)

    if analysis["mean_brightness"] > 210 and 0.001 <= dark_ratio <= 0.18 and top_dark_ratio > 0.001:
        reasons.append("mostly bright screen with sparse dark logo/text pixels")
        return ScreenClassification("boot-or-logo", 0.75, reasons)

    if analysis["visually_informative"]:
        reasons.append("not blank, but no stronger primitive class matched")
        return ScreenClassification("unknown-informative", 0.35, reasons)

    return ScreenClassification("unknown", 0.1, ["fallback classification"])


def compare_screenshots(before_path: Path, after_path: Path, *, pixel_threshold: int = 18) -> ScreenDelta:
    with Image.open(before_path) as before_image, Image.open(after_path) as after_image:
        before = before_image.convert("RGB")
        after = after_image.convert("RGB")
        if before.size != after.size:
            after = after.resize(before.size)
        diff = ImageChops.difference(before, after)
        stat = ImageStat.Stat(diff)
        mean_abs_diff = float(sum(stat.mean) / 3)
        changed_pixels = diff.convert("L").point(lambda value: 255 if cast(int, value) >= pixel_threshold else 0)
        changed_stat = ImageStat.Stat(changed_pixels)
        changed_pixel_ratio = float(changed_stat.mean[0] / 255)
    return ScreenDelta(
        before_path=str(before_path),
        after_path=str(after_path),
        mean_abs_diff=mean_abs_diff,
        changed_pixel_ratio=changed_pixel_ratio,
        changed_enough=mean_abs_diff >= 8.0 or changed_pixel_ratio >= 0.03,
    )


def _dark_pixel_ratio(gray: Image.Image, threshold: int = 96) -> float:
    mask = gray.point(lambda value: 255 if cast(int, value) <= threshold else 0)
    return float(ImageStat.Stat(mask).mean[0] / 255)


def _text_row_density(gray: Image.Image) -> float:
    width, height = gray.size
    if width == 0 or height == 0:
        return 0.0
    row_hits = 0
    for y in range(height):
        row = gray.crop((0, y, width, y + 1))
        if _dark_pixel_ratio(row) >= 0.05:
            row_hits += 1
    return row_hits / height
