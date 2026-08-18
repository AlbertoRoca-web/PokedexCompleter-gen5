from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path
from typing import cast

from PIL import Image

Direction = str

TILE_SIZE = 16
TILE_ORIGIN_X = 24
TILE_ORIGIN_Y = 40
STAIRS_TILE = (1, 7)

# Conservative first-pass grid for the visible bedroom. This is not the whole game.
# Keep it boring: enough structure to route around bed/table/furniture from screenshots.
# . walkable, # blocked, S target/stairs approach tile near lower-left cyan stair graphic.
BEDROOM_GRID = [
    "############",
    "#....###...#",
    "#..........#",
    "#..####..###",
    "#..####....#",
    "#...###...#",
    "...###....##",
    ".S........##",
]


@dataclass(frozen=True)
class PixelPoint:
    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class TilePoint:
    x: int
    y: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class BedroomNavigationDecision:
    player_pixel: PixelPoint | None
    player_tile: TilePoint | None
    target_tile: TilePoint
    path: list[TilePoint]
    next_action: Direction | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "player_pixel": self.player_pixel.to_dict() if self.player_pixel else None,
            "player_tile": self.player_tile.to_dict() if self.player_tile else None,
            "target_tile": self.target_tile.to_dict(),
            "path": [tile.to_dict() for tile in self.path],
            "next_action": self.next_action,
            "reason": self.reason,
        }


def decide_bedroom_next_action(
    image_path: Path,
    *,
    blocked_tiles: set[tuple[int, int]] | None = None,
    expected_tile: TilePoint | tuple[int, int] | None = None,
) -> BedroomNavigationDecision:
    player_pixel = detect_player_pixel(image_path, expected_tile=expected_tile)
    target = TilePoint(*STAIRS_TILE)
    if player_pixel is None:
        return BedroomNavigationDecision(None, None, target, [], None, "player sprite was not detected")
    raw_player_tile = pixel_to_bedroom_tile(player_pixel)
    player_tile = nearest_walkable_tile(raw_player_tile, blocked_tiles=blocked_tiles)
    path = astar_path(BEDROOM_GRID, player_tile.to_tuple(), target.to_tuple(), blocked_tiles=blocked_tiles)
    if not path:
        return BedroomNavigationDecision(player_pixel, player_tile, target, [], None, "no A* path to bedroom target")
    if len(path) == 1:
        return BedroomNavigationDecision(
            player_pixel, player_tile, target, [player_tile], None, "already at target tile"
        )
    next_action = _direction_between(path[0], path[1])
    return BedroomNavigationDecision(
        player_pixel,
        player_tile,
        target,
        [TilePoint(x, y) for x, y in path],
        next_action,
        "next A* step toward bedroom target",
    )


def detect_player_pixel(
    image_path: Path, *, expected_tile: TilePoint | tuple[int, int] | None = None
) -> PixelPoint | None:
    with Image.open(image_path) as raw_image:
        image = raw_image.convert("RGB")
        width, height = image.size
        top_height = min(192, height)
        mask = _sprite_mask(image, width=width, height=top_height)
    components = _connected_components(mask)
    candidates = []
    for component in components:
        xs = [x for x, _y in component]
        ys = [y for _x, y in component]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        box_width = x2 - x1 + 1
        box_height = y2 - y1 + 1
        if expected_tile is None:
            if not (8 <= box_width <= 38 and 8 <= box_height <= 42):
                continue
        elif not (5 <= box_width <= 80 and 5 <= box_height <= 90):
            continue
        if y2 < 100:
            continue
        candidates.append((y2, len(component), x1, x2, y1, y2))
    if not candidates:
        return None
    if expected_tile is not None:
        expected_pixel = bedroom_tile_to_pixel(expected_tile)
        _score, _bottom, _size, x1, x2, _y1, y2 = min(
            (
                _pixel_distance_squared(PixelPoint(_clamp(expected_pixel.x, x1, x2), y2), expected_pixel),
                y2,
                size,
                x1,
                x2,
                y1,
                y2,
            )
            for y2, size, x1, x2, y1, _component_bottom in candidates
        )
        return PixelPoint(_clamp(expected_pixel.x, x1, x2), y2)
    _bottom, _size, x1, x2, _y1, y2 = max(candidates)
    return PixelPoint((x1 + x2) // 2, y2)


def bedroom_tile_to_pixel(tile: TilePoint | tuple[int, int]) -> PixelPoint:
    x, y = tile.to_tuple() if isinstance(tile, TilePoint) else tile
    return PixelPoint(TILE_ORIGIN_X + x * TILE_SIZE, TILE_ORIGIN_Y + y * TILE_SIZE)


def pixel_to_bedroom_tile(pixel: PixelPoint) -> TilePoint:
    tile_x = round((pixel.x - TILE_ORIGIN_X) / TILE_SIZE)
    tile_y = round((pixel.y - TILE_ORIGIN_Y) / TILE_SIZE)
    max_y = len(BEDROOM_GRID) - 1
    max_x = len(BEDROOM_GRID[0]) - 1
    return TilePoint(_clamp(tile_x, 0, max_x), _clamp(tile_y, 0, max_y))


def nearest_walkable_tile(
    tile: TilePoint,
    *,
    blocked_tiles: set[tuple[int, int]] | None = None,
) -> TilePoint:
    blocked = blocked_tiles or set()
    if _is_walkable(BEDROOM_GRID, tile.to_tuple(), blocked_tiles=blocked):
        return tile
    queue = deque([tile.to_tuple()])
    seen = {tile.to_tuple()}
    while queue:
        current = queue.popleft()
        for neighbor in _neighbors_for_search(current):
            if neighbor in seen:
                continue
            if _is_walkable(BEDROOM_GRID, neighbor, blocked_tiles=blocked):
                return TilePoint(*neighbor)
            seen.add(neighbor)
            queue.append(neighbor)
    return tile


def astar_path(
    grid: list[str],
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    blocked_tiles: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    blocked = blocked_tiles or set()
    if not _is_walkable(grid, start, blocked_tiles=blocked) or not _is_walkable(grid, goal, blocked_tiles=blocked):
        return []
    frontier: list[tuple[int, tuple[int, int]]] = []
    heappush(frontier, (0, start))
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    cost_so_far: dict[tuple[int, int], int] = {start: 0}
    while frontier:
        _priority, current = heappop(frontier)
        if current == goal:
            return _reconstruct_path(came_from, current)
        for next_tile in _neighbors(grid, current, blocked_tiles=blocked):
            new_cost = cost_so_far[current] + 1
            if next_tile in cost_so_far and new_cost >= cost_so_far[next_tile]:
                continue
            cost_so_far[next_tile] = new_cost
            priority = new_cost + _manhattan(next_tile, goal)
            heappush(frontier, (priority, next_tile))
            came_from[next_tile] = current
    return []


def _sprite_mask(image: Image.Image, *, width: int, height: int) -> set[tuple[int, int]]:
    mask: set[tuple[int, int]] = set()
    for y in range(70, height):
        for x in range(width):
            r, g, b = cast(tuple[int, int, int], image.getpixel((x, y)))
            if _is_spriteish_pixel(r, g, b):
                mask.add((x, y))
    return mask


def _is_spriteish_pixel(r: int, g: int, b: int) -> bool:
    if r <= 5 and g <= 5 and b <= 5:
        return False
    dark_outline = r < 145 and g < 145 and b < 170
    red_hat = r >= 180 and g <= 145 and b <= 145
    white_cap = r >= 185 and g >= 185 and b >= 230
    blue_shadow = b > r + 20 and b > g + 10 and b >= 90
    floor_or_wall = r > 180 and g > 160 and 100 < b < 230
    return (dark_outline or red_hat or white_cap or blue_shadow) and not floor_or_wall


def _connected_components(mask: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for point in list(mask):
        if point in seen:
            continue
        queue = deque([point])
        seen.add(point)
        component: list[tuple[int, int]] = []
        while queue:
            x, y = queue.popleft()
            component.append((x, y))
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in mask and neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        if len(component) >= 8:
            components.append(component)
    return components


def tile_after_action(tile: TilePoint | tuple[int, int], action: Direction) -> tuple[int, int]:
    x, y = tile.to_tuple() if isinstance(tile, TilePoint) else tile
    if action == "Up":
        return (x, y - 1)
    if action == "Down":
        return (x, y + 1)
    if action == "Left":
        return (x - 1, y)
    if action == "Right":
        return (x + 1, y)
    raise ValueError(f"Unsupported movement action: {action}")


def _neighbors(
    grid: list[str], tile: tuple[int, int], *, blocked_tiles: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    return [
        candidate
        for candidate in _neighbors_for_search(tile)
        if _is_walkable(grid, candidate, blocked_tiles=blocked_tiles)
    ]


def _neighbors_for_search(tile: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = tile
    return [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]


def _is_walkable(
    grid: list[str], tile: tuple[int, int], *, blocked_tiles: set[tuple[int, int]] | None = None
) -> bool:
    x, y = tile
    blocked = blocked_tiles or set()
    return 0 <= y < len(grid) and 0 <= x < len(grid[y]) and tile not in blocked and grid[y][x] in {".", "S"}


def _reconstruct_path(
    came_from: dict[tuple[int, int], tuple[int, int] | None], current: tuple[int, int]
) -> list[tuple[int, int]]:
    path = [current]
    while came_from[current] is not None:
        previous = came_from[current]
        if previous is None:
            break
        current = previous
        path.append(current)
    path.reverse()
    return path


def _direction_between(start: tuple[int, int], end: tuple[int, int]) -> Direction:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 1:
        return "Right"
    if dx == -1:
        return "Left"
    if dy == 1:
        return "Down"
    if dy == -1:
        return "Up"
    raise ValueError(f"Tiles are not adjacent: {start} -> {end}")


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _pixel_distance_squared(a: PixelPoint, b: PixelPoint) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
