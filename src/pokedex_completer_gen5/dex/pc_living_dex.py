from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pokedex_completer_gen5.dex.bw_unova import UNOVA_DEX, Pokemon
from pokedex_completer_gen5.dex.catchable_targets import target_species_for_game
from pokedex_completer_gen5.dex.game_profiles import normalize_game
from pokedex_completer_gen5.dex.national_species import national_species_name


@dataclass(frozen=True)
class LivingDexTarget:
    national: int
    regional: int | None
    name: str
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "national": self.national,
            "regional": self.regional,
            "name": self.name,
            "method": self.method,
        }


@dataclass(frozen=True)
class PcLivingDexReport:
    game_profile: str
    scope: str
    include_party: bool
    target_policy: str
    selected_copy: int
    target_count: int
    pc_owned_target_count: int
    party_owned_target_count: int
    combined_owned_target_count: int
    missing_count: int
    pc_complete: bool
    combined_complete: bool
    missing_targets: tuple[LivingDexTarget, ...]
    extra_owned_species: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_profile": self.game_profile,
            "scope": self.scope,
            "include_party": self.include_party,
            "target_policy": self.target_policy,
            "selected_copy": self.selected_copy,
            "target_count": self.target_count,
            "pc_owned_target_count": self.pc_owned_target_count,
            "party_owned_target_count": self.party_owned_target_count,
            "combined_owned_target_count": self.combined_owned_target_count,
            "missing_count": self.missing_count,
            "pc_complete": self.pc_complete,
            "combined_complete": self.combined_complete,
            "missing_targets": [target.to_dict() for target in self.missing_targets],
            "extra_owned_species": [
                {"national": species_id, "name": national_species_name(species_id)}
                for species_id in self.extra_owned_species
            ],
        }


def build_pc_living_dex_report(
    save_payload: dict[str, Any],
    game: str,
    scope: str = "regional",
    include_party: bool = True,
    target_policy: str = "game-regional",
) -> PcLivingDexReport:
    profile = normalize_game(game)
    targets = living_dex_targets(profile.key, scope=scope, target_policy=target_policy)
    target_ids = {target.national for target in targets}
    selected_copy = _selected_copy(save_payload)
    pc_counts, party_counts = physical_counts_by_source(save_payload, selected_copy)

    combined_counts = pc_counts + party_counts if include_party else pc_counts
    pc_owned_ids = owned_target_ids(pc_counts, target_ids)
    party_owned_ids = owned_target_ids(party_counts, target_ids)
    combined_owned_ids = owned_target_ids(combined_counts, target_ids)
    missing_targets = tuple(target for target in targets if target.national not in combined_owned_ids)
    extra_owned_species = tuple(sorted(set(combined_counts) - target_ids))

    return PcLivingDexReport(
        game_profile=profile.key,
        scope=scope,
        include_party=include_party,
        target_policy=target_policy,
        selected_copy=selected_copy,
        target_count=len(targets),
        pc_owned_target_count=len(pc_owned_ids),
        party_owned_target_count=len(party_owned_ids),
        combined_owned_target_count=len(combined_owned_ids),
        missing_count=len(missing_targets),
        pc_complete=len(pc_owned_ids) == len(targets),
        combined_complete=len(combined_owned_ids) == len(targets),
        missing_targets=missing_targets,
        extra_owned_species=extra_owned_species,
    )


def owned_target_ids(counts: Counter[int], target_ids: set[int]) -> set[int]:
    return {species_id for species_id, count in counts.items() if count > 0 and species_id in target_ids}


def living_dex_targets(
    game: str,
    scope: str = "regional",
    target_policy: str = "game-regional",
) -> tuple[LivingDexTarget, ...]:
    if scope == "national":
        raise NotImplementedError("National living dex scope is intentionally pending.")
    if scope != "regional":
        raise ValueError(f"Unsupported living dex scope: {scope}")

    profile = normalize_game(game)
    if profile.regional_dex_key != "bw_unova":
        return tuple()

    if target_policy == "game-regional":
        pokemon_targets = (pokemon for pokemon in UNOVA_DEX if available_in_game(pokemon, profile.key))
        return tuple(target_from_pokemon(pokemon) for pokemon in pokemon_targets)
    if target_policy == "all-regional":
        return tuple(target_from_pokemon(pokemon) for pokemon in UNOVA_DEX)
    if target_policy == "catchable-only":
        return tuple(
            LivingDexTarget(
                national=target.national,
                regional=target.regional,
                name=target.name,
                method=target.method,
            )
            for target in target_species_for_game(profile.key, mode="direct")
        )
    raise ValueError(f"Unsupported target policy: {target_policy}")


def target_from_pokemon(pokemon: Pokemon) -> LivingDexTarget:
    return LivingDexTarget(
        national=pokemon.national,
        regional=pokemon.regional,
        name=pokemon.name,
        method=pokemon.method,
    )


def available_in_game(pokemon: Pokemon, game: str) -> bool:
    return not ((pokemon.black_only and game != "black") or (pokemon.white_only and game != "white"))


def physical_counts_by_source(save_payload: dict[str, Any], selected_copy: int) -> tuple[Counter[int], Counter[int]]:
    selected = _copy_payload(save_payload, selected_copy)
    pc_counts: Counter[int] = Counter()
    party_counts: Counter[int] = Counter()
    for mon in selected.get("mons", []):
        if not isinstance(mon, dict):
            continue
        species_id = mon.get("species_id")
        source = mon.get("source")
        if not isinstance(species_id, int):
            continue
        if source == "pc":
            pc_counts[species_id] += 1
        elif source == "party":
            party_counts[species_id] += 1
    return pc_counts, party_counts


def _selected_copy(save_payload: dict[str, Any]) -> int:
    selected_copy = save_payload.get("selected_copy")
    return selected_copy if isinstance(selected_copy, int) else 0


def _copy_payload(save_payload: dict[str, Any], selected_copy: int) -> dict[str, Any]:
    copies = save_payload.get("copies")
    if not isinstance(copies, list):
        return {}
    for copy_payload in copies:
        if not isinstance(copy_payload, dict):
            continue
        if copy_payload.get("copy_index") == selected_copy:
            return copy_payload
    return {}
