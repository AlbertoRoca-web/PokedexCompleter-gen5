from __future__ import annotations

import random
import re

SAFE_NICKNAMES = (
    "Biscuit",
    "Comet",
    "Doodle",
    "Mochi",
    "Maple",
    "Noodle",
    "Pebble",
    "Pip",
    "Sprout",
    "Sunny",
    "Toffee",
    "Waffles",
    "Widget",
    "Zippy",
)
NICKNAME_PATTERN = re.compile(r"^[A-Za-z]{1,10}$")


def generate_safe_nickname(*, seed: int | str | None = None) -> str:
    nickname = random.Random(seed).choice(SAFE_NICKNAMES)
    if not nickname_is_home_safe(nickname):
        raise RuntimeError("Configured nickname list contains an unsafe value.")
    return nickname


def nickname_is_home_safe(nickname: str) -> bool:
    return bool(NICKNAME_PATTERN.fullmatch(nickname))
