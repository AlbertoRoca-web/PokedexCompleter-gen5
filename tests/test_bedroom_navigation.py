from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pokedex_completer_gen5.emulator.bedroom_navigation import (
    BEDROOM_GRID,
    PixelPoint,
    TilePoint,
    astar_path,
    decide_bedroom_next_action,
    detect_player_pixel,
    pixel_to_bedroom_tile,
)


def test_pixel_to_bedroom_tile_uses_calibrated_grid() -> None:
    assert pixel_to_bedroom_tile(PixelPoint(120, 137)) == TilePoint(6, 6)


def test_astar_path_routes_to_stairs() -> None:
    path = astar_path(BEDROOM_GRID, (6, 6), (0, 6))

    assert path[0] == (6, 6)
    assert path[-1] == (0, 6)
    assert len(path) > 1


def test_detect_player_pixel_from_synthetic_sprite(tmp_path: Path) -> None:
    path = tmp_path / "sprite.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((111, 120, 130, 138), fill=(60, 44, 60))
    draw.rectangle((116, 116, 125, 124), fill=(239, 109, 109))
    image.save(path)

    assert detect_player_pixel(path) == PixelPoint(120, 138)


def test_decide_bedroom_next_action_from_synthetic_sprite(tmp_path: Path) -> None:
    path = tmp_path / "sprite.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((111, 120, 130, 138), fill=(60, 44, 60))
    draw.rectangle((116, 116, 125, 124), fill=(239, 109, 109))
    image.save(path)

    decision = decide_bedroom_next_action(path)

    assert decision.player_tile == TilePoint(6, 6)
    assert decision.next_action == "Left"
