from __future__ import annotations

from pokedex_completer_gen5.dex.route_transition_planner import choose_travel_mode


def test_adjacent_route_prefers_walking() -> None:
    assert choose_travel_mode(walking_cost=1, fly_available=True) == "walk"
    assert choose_travel_mode(walking_cost=2, fly_available=True) == "walk"


def test_distant_route_prefers_fly_when_available() -> None:
    assert choose_travel_mode(walking_cost=3, fly_available=True) == "fly"


def test_distant_route_walks_without_fly() -> None:
    assert choose_travel_mode(walking_cost=10, fly_available=False) == "walk"
