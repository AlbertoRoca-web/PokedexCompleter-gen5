from __future__ import annotations

from dataclasses import dataclass

# Gen 5-relevant no-eggs / no-breeding species in the Unova regional dex.
# Includes mythicals and legendaries. Also covers Victini/event boys being annoying.
UNBREEDABLE_NATIONAL_IDS: frozenset[int] = frozenset(
    {
        494,  # Victini
        638, 639, 640,  # Swords of Justice
        641, 642, 645,  # Forces of Nature
        643, 644, 646,  # Tao trio
        647, 648, 649,  # Keldeo, Meloetta, Genesect
    }
)

# Breedable but genderless families require Ditto in Gen 5.
DITTO_REQUIRED_NATIONAL_IDS: frozenset[int] = frozenset(
    {
        599, 600, 601,  # Klink line
        615,  # Cryogonal
        622, 623,  # Golett line
    }
)


@dataclass(frozen=True)
class BreedingRule:
    can_breed: bool
    note: str


def breeding_rule_for_family(national_ids: tuple[int, ...]) -> BreedingRule:
    if all(national_id in UNBREEDABLE_NATIONAL_IDS for national_id in national_ids):
        return BreedingRule(False, "cannot breed in Gen 5")
    if any(national_id in DITTO_REQUIRED_NATIONAL_IDS for national_id in national_ids):
        return BreedingRule(True, "breed with Ditto required for this genderless family")
    return BreedingRule(True, "breed base-stage extras with a compatible partner or Ditto")
