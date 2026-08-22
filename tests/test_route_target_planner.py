from __future__ import annotations

from pokedex_completer_gen5.dex.location_kb import FlyPolicy
from pokedex_completer_gen5.dex.route_target_planner import _navigation_steps


def test_route_navigation_uses_unfezant_for_distant_area() -> None:
    steps = _navigation_steps("dreamyard-area", 4, True, FlyPolicy())

    assert [(step.operation, step.value) for step in steps] == [
        ("toggle-menu", "S"),
        ("open-party", "Pokemon"),
        ("select-pokemon", "Unfezant"),
        ("select-move", "Fly"),
        ("select-destination", "dreamyard-area"),
        ("verify-location", "dreamyard-area"),
    ]


def test_route_navigation_walks_to_adjacent_area() -> None:
    steps = _navigation_steps("unova-route-1-area", 1, True, FlyPolicy())

    assert steps[0].operation == "walk-to-area"
