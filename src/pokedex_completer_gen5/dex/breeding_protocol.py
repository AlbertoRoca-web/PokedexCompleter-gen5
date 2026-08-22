from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BreedingPlan:
    ready: bool
    parent_species: str
    partner_species: str
    egg_species: str
    eggs_needed: int
    destination: str
    prerequisites: tuple[str, ...]
    legality_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_breeding_plan(
    *,
    parent_species: str,
    base_species: str,
    eggs_needed: int,
    ditto_owned: bool,
    bicycle_owned: bool = True,
) -> BreedingPlan:
    prerequisites = ["Route 3 Day Care unlocked", "Day Care second slot unlocked"]
    if not ditto_owned:
        prerequisites.append("Obtain a legitimate Ditto body")
    if not bicycle_owned:
        prerequisites.append("Obtain Bicycle in Nimbasa City")
    return BreedingPlan(
        ready=ditto_owned and bicycle_owned and eggs_needed > 0,
        parent_species=parent_species,
        partner_species="Ditto",
        egg_species=base_species,
        eggs_needed=max(0, eggs_needed),
        destination="unova-route-3-day-care",
        prerequisites=tuple(prerequisites),
        legality_rules=(
            "Ditto cannot breed with Ditto",
            "Undiscovered Egg Group cannot breed",
            "Generation V eggs hatch in a standard Poke Ball",
            "Preserve original trainer, hatch location, and origin-game metadata",
            "Save and export a validated .sav after collecting each required egg batch",
        ),
    )
