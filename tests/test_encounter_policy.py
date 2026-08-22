from __future__ import annotations

from pokedex_completer_gen5.dex.encounter_policy import classify_spawn_rarity


def test_spawn_rarity_thresholds() -> None:
    assert classify_spawn_rarity(50) == "common"
    assert classify_spawn_rarity(25) == "uncommon"
    assert classify_spawn_rarity(5) == "rare"
    assert classify_spawn_rarity(1) == "super-rare"
