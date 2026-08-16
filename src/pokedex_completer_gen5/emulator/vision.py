from __future__ import annotations

from pathlib import Path
from typing import Any, cast


def analyze_screenshot(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageStat
    except ImportError as exc:  # pragma: no cover - optional vision dependency.
        raise RuntimeError("Install vision dependencies with: uv sync --extra vision") from exc

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        means = tuple(float(value) for value in stat.mean)
        extrema = cast(tuple[tuple[int, int], tuple[int, int], tuple[int, int]], rgb.getextrema())
        width, height = rgb.size

    channel_ranges = [high - low for low, high in extrema]
    mean_brightness = sum(means) / 3
    max_range = max(channel_ranges) if channel_ranges else 0
    blank_white = mean_brightness >= 248 and max_range <= 4
    blank_black = mean_brightness <= 4 and max_range <= 4
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "mean_rgb": means,
        "mean_brightness": mean_brightness,
        "channel_ranges": channel_ranges,
        "blank_white": blank_white,
        "blank_black": blank_black,
        "visually_informative": not (blank_white or blank_black),
    }
