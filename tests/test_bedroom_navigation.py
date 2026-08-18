from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pokedex_completer_gen5.emulator.bedroom_navigation import (
    BEDROOM_GRID,
    PixelPoint,
    TilePoint,
    astar_path,
    bedroom_tile_to_pixel,
    decide_bedroom_next_action,
    detect_player_pixel,
    nearest_walkable_tile,
    pixel_to_bedroom_tile,
    tile_after_action,
)


def test_pixel_to_bedroom_tile_uses_calibrated_grid() -> None:
    assert pixel_to_bedroom_tile(PixelPoint(120, 137)) == TilePoint(6, 6)


def test_bedroom_tile_to_pixel_uses_calibrated_grid() -> None:
    assert bedroom_tile_to_pixel(TilePoint(6, 6)) == PixelPoint(120, 136)


def test_nearest_walkable_tile_snaps_blocked_detection() -> None:
    assert nearest_walkable_tile(TilePoint(5, 6)) == TilePoint(5, 5)


def test_astar_path_routes_to_stairs() -> None:
    path = astar_path(BEDROOM_GRID, (3, 5), (10, 5))

    assert path[0] == (3, 5)
    assert path[-1] == (10, 5)
    assert len(path) > 1


def test_tile_after_action_returns_attempted_neighbor() -> None:
    assert tile_after_action(TilePoint(6, 6), "Left") == (5, 6)
    assert tile_after_action((6, 6), "Down") == (6, 7)


def test_astar_path_respects_dynamic_blocked_tiles() -> None:
    path = astar_path(BEDROOM_GRID, (6, 7), (10, 5), blocked_tiles={(5, 7)})

    assert (5, 7) not in path


def test_detect_player_pixel_from_synthetic_sprite(tmp_path: Path) -> None:
    path = tmp_path / "sprite.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((111, 120, 130, 138), fill=(60, 44, 60))
    draw.rectangle((116, 116, 125, 124), fill=(239, 109, 109))
    image.save(path)

    assert detect_player_pixel(path) == PixelPoint(120, 138)


def test_detect_player_pixel_handles_white_cap_back_sprite(tmp_path: Path) -> None:
    path = tmp_path / "white-cap-sprite.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((163, 106, 184, 132), fill=(60, 44, 60))
    draw.rectangle((168, 102, 179, 112), fill=(239, 239, 247))
    image.save(path)

    assert detect_player_pixel(path, expected_tile=TilePoint(9, 5)) == PixelPoint(168, 132)


def test_detect_player_pixel_uses_expected_tile_cap_anchor_in_clutter(tmp_path: Path) -> None:
    path = tmp_path / "sprite-in-clutter.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 130, 110, 180), fill=(60, 44, 60))
    draw.rectangle((70, 74, 79, 79), fill=(239, 109, 109))
    image.save(path)

    assert detect_player_pixel(path, expected_tile=TilePoint(1, 4)) == PixelPoint(74, 115)


def test_detect_player_pixel_prefers_expected_tile_over_distractor(tmp_path: Path) -> None:
    path = tmp_path / "sprite-with-distractor.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((111, 120, 130, 138), fill=(60, 44, 60))
    draw.rectangle((116, 116, 125, 124), fill=(239, 109, 109))
    draw.rectangle((26, 105, 43, 116), fill=(60, 44, 60))
    image.save(path)

    assert detect_player_pixel(path, expected_tile=TilePoint(6, 6)) == PixelPoint(120, 138)


def test_decide_bedroom_next_action_from_synthetic_sprite(tmp_path: Path) -> None:
    path = tmp_path / "sprite.png"
    image = Image.new("RGB", (256, 384), (239, 207, 150))
    draw = ImageDraw.Draw(image)
    draw.rectangle((111, 120, 130, 138), fill=(60, 44, 60))
    draw.rectangle((116, 116, 125, 124), fill=(239, 109, 109))
    image.save(path)

    decision = decide_bedroom_next_action(path)

    assert decision.player_tile == TilePoint(6, 5)
    assert decision.next_action == "Right"
