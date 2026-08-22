from __future__ import annotations

import pytest

from pokedex_completer_gen5.dex.catch_legality import CatchContext, ball_is_legal, choose_legal_ball


def test_master_ball_is_always_forbidden() -> None:
    assert ball_is_legal("Master Ball", CatchContext()) is False


def test_safari_ball_is_forbidden_in_pokemon_white() -> None:
    assert ball_is_legal("Safari Ball", CatchContext(game="white", is_safari_zone=True)) is False


def test_selector_ignores_forbidden_large_stacks() -> None:
    selected = choose_legal_ball(
        ["Master Ball", "Safari Ball", "Ultra Ball", "Poke Ball"],
        CatchContext(game="white", turn=2),
    )

    assert selected == "Ultra Ball"


def test_first_turn_prefers_quick_ball() -> None:
    selected = choose_legal_ball(["Ultra Ball", "Quick Ball"], CatchContext(turn=1))

    assert selected == "Quick Ball"


def test_selector_fails_closed_when_only_illegal_balls_exist() -> None:
    with pytest.raises(ValueError, match="No PKHeX/HOME-compatible"):
        choose_legal_ball(["Master Ball", "Safari Ball"], CatchContext(game="white"))
