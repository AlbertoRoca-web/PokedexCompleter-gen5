from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class B2W2Pokemon:
    regional: int
    national: int
    name: str
    method: str = ""


# Pokémon Black 2 / White 2 use a different, larger regional dex than Black / White.
# Do not import BW_UNOVA as a shortcut. That would be convenient, which is exactly how bugs dress up.
B2W2_UNOVA_DEX: tuple[B2W2Pokemon, ...] = tuple()


def b2w2_planner_available() -> bool:
    return bool(B2W2_UNOVA_DEX)
