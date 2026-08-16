from __future__ import annotations

import json
from pathlib import Path

import pytest

from pokedex_completer_gen5.dex.b2w2_unova import b2w2_planner_available
from pokedex_completer_gen5.saveio.gen5_save import build_save_output

WHITE_SAVE = Path(r"D:\Users\alroc\Downloads\rolplete\POKEMON W.sav")


def test_b2w2_planner_starts_unavailable() -> None:
    assert b2w2_planner_available() is False


@pytest.mark.skipif(not WHITE_SAVE.exists(), reason="local Pokémon White save fixture is not present")
def test_local_white_json_report_smoke() -> None:
    payload = json.loads(build_save_output(WHITE_SAVE, "white", output_format="json"))
    assert payload["game_profile"] == "white"
    assert payload["planner_supported"] is True
    assert payload["dex_status"]["unique_species_owned"] >= 1
    assert payload["selected_species_counts"]
