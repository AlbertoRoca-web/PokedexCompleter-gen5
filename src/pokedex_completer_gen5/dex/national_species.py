from __future__ import annotations

from pokedex_completer_gen5.dex.bw_unova import UNOVA_DEX
from pokedex_completer_gen5.dex.gen1_to_gen4_species import SPECIES_NAMES as GEN1_TO_GEN4_NAMES

NATIONAL_SPECIES_NAMES: dict[int, str] = dict(GEN1_TO_GEN4_NAMES)
NATIONAL_SPECIES_NAMES.update({pokemon.national: pokemon.name for pokemon in UNOVA_DEX})


def national_species_name(species_id: int) -> str:
    return NATIONAL_SPECIES_NAMES.get(species_id, f"National #{species_id}")
