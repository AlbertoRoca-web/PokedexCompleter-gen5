from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pokedex_completer_gen5.dex.bw_unova import UNOVA_DEX
from pokedex_completer_gen5.persistence.living_dex_progress import verified_catches
from pokedex_completer_gen5.saveio.gen5_save import build_save_payload

SpawnRarity = Literal["common", "uncommon", "rare", "super-rare"]


@dataclass(frozen=True)
class EncounterDecision:
    action: Literal["catch", "run"]
    species_id: int
    species_name: str
    rarity: SpawnRarity
    encounter_chance: float
    owned_species_count: int
    family_body_quota: int
    owned_family_bodies: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_spawn_rarity(chance: float) -> SpawnRarity:
    if chance >= 40:
        return "common"
    if chance >= 15:
        return "uncommon"
    if chance >= 5:
        return "rare"
    return "super-rare"


def decide_encounter(
    *,
    save_path: Path,
    species_id: int,
    encounter_chance: float,
    game: str = "white",
    progress_db: Path = Path(".runtime/living-dex-progress.sqlite3"),
) -> EncounterDecision:
    pokemon = next((entry for entry in UNOVA_DEX if entry.national == species_id), None)
    if pokemon is None:
        return EncounterDecision(
            "run",
            species_id,
            f"National #{species_id}",
            classify_spawn_rarity(encounter_chance),
            encounter_chance,
            0,
            0,
            0,
            "Species is outside the configured White regional Living Dex target set.",
        )
    payload = build_save_payload(save_path, game, "auto")
    save_counts = _save_species_counts(payload)
    session_counts = Counter(catch.species_id for catch in verified_catches(progress_db))
    owned_counts = save_counts + session_counts
    family_ids = {
        entry.national
        for entry in UNOVA_DEX
        if entry.name in pokemon.family
    }
    owned_species = owned_counts[species_id]
    owned_family_bodies = sum(owned_counts[national] for national in family_ids)
    family_quota = len(pokemon.family)
    rarity = classify_spawn_rarity(encounter_chance)
    if owned_family_bodies >= family_quota:
        action, reason = "run", "Evolution family physical-body quota is already satisfied."
    elif rarity in {"rare", "super-rare"} and owned_species >= 1:
        action, reason = "run", "Rare wild specimen already secured; use evolution or breeding for family extras."
    else:
        action = "catch"
        reason = (
            f"Family needs {family_quota - owned_family_bodies} more physical body/bodies; "
            f"{rarity} spawn remains within catch quota."
        )
    return EncounterDecision(
        action,
        species_id,
        pokemon.name,
        rarity,
        encounter_chance,
        owned_species,
        family_quota,
        owned_family_bodies,
        reason,
    )


def _save_species_counts(payload: dict[str, Any]) -> Counter[int]:
    counts: Counter[int] = Counter()
    raw_counts = payload.get("selected_species_counts", [])
    if not isinstance(raw_counts, list):
        return counts
    for entry in raw_counts:
        if not isinstance(entry, dict):
            continue
        species_id = entry.get("species_id")
        count = entry.get("count")
        if isinstance(species_id, int) and isinstance(count, int) and count > 0:
            counts[species_id] += count
    return counts
