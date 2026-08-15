from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pokedex_completer_gen5.dex.bw_unova import UNOVA_DEX, Pokemon
from pokedex_completer_gen5.dex.game_profiles import normalize_game

DIRECT_CATCH_KEYWORDS = (
    "catch",
    "fish",
    "surf",
    "shaking grass",
    "rippling water",
    "legendary catch",
    "story legendary",
    "roamer",
    "static",
)

OBTAINABLE_KEYWORDS = DIRECT_CATCH_KEYWORDS + (
    "gift",
    "fossil",
    "egg",
)

EXCLUDED_KEYWORDS = (
    "event",
    "transfer",
)


@dataclass(frozen=True)
class CatchableTarget:
    national: int
    regional: int
    name: str
    method: str
    category: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "national": self.national,
            "regional": self.regional,
            "name": self.name,
            "method": self.method,
            "category": self.category,
        }


@dataclass(frozen=True)
class CatchableInventoryReport:
    game_profile: str
    target_mode: str
    targets: tuple[CatchableTarget, ...]
    owned_target_ids: tuple[int, ...]
    missing_targets: tuple[CatchableTarget, ...]
    ignored_owned_ids: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_profile": self.game_profile,
            "target_mode": self.target_mode,
            "target_count": len(self.targets),
            "owned_target_count": len(self.owned_target_ids),
            "missing_target_count": len(self.missing_targets),
            "targets": [target.to_dict() for target in self.targets],
            "owned_target_ids": list(self.owned_target_ids),
            "missing_targets": [target.to_dict() for target in self.missing_targets],
            "ignored_owned_ids": list(self.ignored_owned_ids),
        }


def target_species_for_game(game: str, mode: str = "direct") -> tuple[CatchableTarget, ...]:
    if mode not in ("direct", "obtainable"):
        raise ValueError(f"Unsupported target mode: {mode}")
    profile = normalize_game(game)
    if profile.regional_dex_key != "bw_unova":
        return tuple()

    targets: list[CatchableTarget] = []
    for pokemon in UNOVA_DEX:
        if not available_in_version(pokemon, profile.key):
            continue
        if mode == "direct" and not is_directly_catchable(pokemon):
            continue
        if mode == "obtainable" and not is_obtainable_without_trade_or_event(pokemon):
            continue
        targets.append(
            CatchableTarget(
                national=pokemon.national,
                regional=pokemon.regional,
                name=pokemon.name,
                method=pokemon.method,
                category=target_category(pokemon),
            )
        )
    return tuple(sorted(targets, key=lambda target: target.regional))


def build_catchable_inventory_report(
    save_payload: dict[str, Any],
    game: str,
    mode: str = "direct",
) -> CatchableInventoryReport:
    profile = normalize_game(game)
    targets = target_species_for_game(profile.key, mode=mode)
    target_ids = {target.national for target in targets}
    owned_ids = owned_species_ids_from_payload(save_payload)
    owned_target_ids = tuple(sorted(owned_ids & target_ids))
    missing_targets = tuple(target for target in targets if target.national not in owned_ids)
    ignored_owned_ids = tuple(sorted(owned_ids - target_ids))
    return CatchableInventoryReport(
        game_profile=profile.key,
        target_mode=mode,
        targets=targets,
        owned_target_ids=owned_target_ids,
        missing_targets=missing_targets,
        ignored_owned_ids=ignored_owned_ids,
    )


def owned_species_ids_from_payload(save_payload: dict[str, Any]) -> set[int]:
    counts = save_payload.get("selected_species_counts")
    if not isinstance(counts, list):
        return set()
    owned: set[int] = set()
    for entry in counts:
        if not isinstance(entry, dict):
            continue
        species_id = entry.get("species_id")
        count = entry.get("count")
        if isinstance(species_id, int) and isinstance(count, int) and count > 0:
            owned.add(species_id)
    return owned


def available_in_version(pokemon: Pokemon, game: str) -> bool:
    return not ((pokemon.black_only and game != "black") or (pokemon.white_only and game != "white"))


def is_directly_catchable(pokemon: Pokemon) -> bool:
    method = pokemon.method.casefold()
    if any(keyword in method for keyword in EXCLUDED_KEYWORDS):
        return False
    return any(keyword in method for keyword in DIRECT_CATCH_KEYWORDS)


def is_obtainable_without_trade_or_event(pokemon: Pokemon) -> bool:
    method = pokemon.method.casefold()
    if any(keyword in method for keyword in EXCLUDED_KEYWORDS):
        return False
    return any(keyword in method for keyword in OBTAINABLE_KEYWORDS)


def target_category(pokemon: Pokemon) -> str:
    method = pokemon.method.casefold()
    if "legendary" in method or "roamer" in method:
        return "legendary"
    if "fish" in method or "surf" in method or "rippling water" in method:
        return "water"
    if "shaking grass" in method:
        return "special-encounter"
    if "fossil" in method:
        return "fossil"
    if "gift" in method:
        return "gift"
    return "wild"
