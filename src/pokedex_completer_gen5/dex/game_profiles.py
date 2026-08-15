from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameProfile:
    key: str
    title: str
    generation: int
    regional_dex_key: str
    planner_supported: bool
    notes: str = ""


GAME_PROFILES: dict[str, GameProfile] = {
    "black": GameProfile(
        key="black",
        title="Pokémon Black",
        generation=5,
        regional_dex_key="bw_unova",
        planner_supported=True,
    ),
    "white": GameProfile(
        key="white",
        title="Pokémon White",
        generation=5,
        regional_dex_key="bw_unova",
        planner_supported=True,
    ),
    "black2": GameProfile(
        key="black2",
        title="Pokémon Black 2",
        generation=5,
        regional_dex_key="b2w2_unova",
        planner_supported=False,
        notes="Save extraction works; B2W2 regional living dex data is not loaded yet.",
    ),
    "white2": GameProfile(
        key="white2",
        title="Pokémon White 2",
        generation=5,
        regional_dex_key="b2w2_unova",
        planner_supported=False,
        notes="Save extraction works; B2W2 regional living dex data is not loaded yet.",
    ),
}

GAME_ALIASES: dict[str, str] = {
    "b": "black",
    "black": "black",
    "pokemon-black": "black",
    "w": "white",
    "white": "white",
    "pokemon-white": "white",
    "b2": "black2",
    "black2": "black2",
    "black-2": "black2",
    "black_2": "black2",
    "pokemon-black-2": "black2",
    "w2": "white2",
    "white2": "white2",
    "white-2": "white2",
    "white_2": "white2",
    "pokemon-white-2": "white2",
}


def normalize_game(value: str) -> GameProfile:
    key = GAME_ALIASES.get(value.strip().casefold())
    if key is None:
        valid = ", ".join(sorted(GAME_PROFILES))
        raise ValueError(f"Unknown Gen 5 game {value!r}. Valid games: {valid}")
    return GAME_PROFILES[key]


def supported_game_keys() -> tuple[str, ...]:
    return tuple(GAME_PROFILES)
