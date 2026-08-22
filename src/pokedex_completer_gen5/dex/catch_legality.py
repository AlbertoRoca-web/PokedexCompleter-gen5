from __future__ import annotations

from dataclasses import dataclass

ALWAYS_FORBIDDEN_BALLS = frozenset({"master-ball"})
CONTEXT_RESTRICTED_BALLS = frozenset({"safari-ball"})
DEFAULT_PRIORITY = (
    "quick-ball",
    "dusk-ball",
    "net-ball",
    "ultra-ball",
    "great-ball",
    "poke-ball",
    "premier-ball",
    "timer-ball",
    "repeat-ball",
    "nest-ball",
    "luxury-ball",
    "heal-ball",
    "dive-ball",
)


@dataclass(frozen=True)
class CatchContext:
    game: str = "white"
    turn: int = 1
    is_cave_or_night: bool = False
    is_water_or_bug: bool = False
    is_safari_zone: bool = False


def normalize_ball_name(name: str) -> str:
    return name.casefold().strip().replace("é", "e").replace(" ", "-")


def ball_is_legal(ball: str, context: CatchContext) -> bool:
    normalized = normalize_ball_name(ball)
    if normalized in ALWAYS_FORBIDDEN_BALLS:
        return False
    if normalized in CONTEXT_RESTRICTED_BALLS:
        return context.is_safari_zone and context.game.casefold() != "white"
    return normalized in DEFAULT_PRIORITY


def choose_legal_ball(available_balls: list[str], context: CatchContext) -> str:
    available = {normalize_ball_name(ball): ball for ball in available_balls}
    priority = list(DEFAULT_PRIORITY)
    if context.turn != 1:
        priority.remove("quick-ball")
        priority.append("quick-ball")
    if not context.is_cave_or_night:
        priority.remove("dusk-ball")
        priority.append("dusk-ball")
    if not context.is_water_or_bug:
        priority.remove("net-ball")
        priority.append("net-ball")
    for normalized in priority:
        if normalized in available and ball_is_legal(normalized, context):
            return available[normalized]
    raise ValueError("No PKHeX/HOME-compatible non-Master, non-Safari ball is available.")
