from __future__ import annotations

from pokedex_completer_gen5.dex.game_profiles import normalize_game
from pokedex_completer_gen5.dex.national_species import national_species_name


def test_black2_alias_is_recognized() -> None:
    profile = normalize_game("b2")
    assert profile.key == "black2"
    assert profile.planner_supported is False


def test_bw_planner_is_supported() -> None:
    assert normalize_game("black").planner_supported is True
    assert normalize_game("white").planner_supported is True


def test_national_species_name_uses_gen1_to_gen4_and_unova() -> None:
    assert national_species_name(21) == "Spearow"
    assert national_species_name(506) == "Lillipup"
    assert national_species_name(649) == "Genesect"
