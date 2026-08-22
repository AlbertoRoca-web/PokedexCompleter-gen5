from __future__ import annotations

import json
from pathlib import Path

from pokedex_completer_gen5.dex.location_kb import LocationKnowledgeBase

KB = {
    "fly_policy": {"menu_toggle_button": "S"},
    "targets": [
        {
            "national": 504,
            "name": "Patrat",
            "locations": [
                {
                    "location_area": "route-1",
                    "encounters": [{"method": "walk", "min_level": 2, "max_level": 4, "chance": 50}],
                }
            ],
        }
    ],
}


def test_location_kb_loads_target_encounters(tmp_path: Path) -> None:
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(KB), encoding="utf-8")

    knowledge_base = LocationKnowledgeBase.load(path)

    locations = knowledge_base.locations_for(504)
    assert locations[0].location_area == "route-1"
    assert locations[0].method == "walk"


def test_fly_route_contains_explicit_unfezant_protocol(tmp_path: Path) -> None:
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(KB), encoding="utf-8")
    knowledge_base = LocationKnowledgeBase.load(path)

    route = knowledge_base.shortest_route(current_area="nuvema-town", target_national=504, fly_available=True)

    assert [step.operation for step in route] == [
        "toggle-menu",
        "open-party",
        "select-pokemon",
        "select-move",
        "select-destination",
        "verify-location",
    ]
    assert route[0].value == "S"
    assert route[2].value == "Unfezant"
    assert route[3].value == "Fly"


def test_same_area_prefers_walk_without_fly(tmp_path: Path) -> None:
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(KB), encoding="utf-8")
    knowledge_base = LocationKnowledgeBase.load(path)

    route = knowledge_base.shortest_route(current_area="route-1", target_national=504, fly_available=True)

    assert route[0].operation == "walk-to-area"
