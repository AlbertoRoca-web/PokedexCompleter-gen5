from __future__ import annotations

import json
from pathlib import Path

KNOWLEDGE_PATH = Path("data/knowledge/white-route-1-verified.json")


def test_route_1_super_rod_tables_match_original_pokemon_white() -> None:
    payload = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    encounters = payload["encounters"]

    ordinary = {
        (entry["species"], entry.get("form")): entry["chance"]
        for entry in encounters
        if entry["method"] == "super-rod"
    }
    rippling = {
        (entry["species"], entry.get("form")): entry["chance"]
        for entry in encounters
        if entry["method"] == "rippling-fishing"
    }

    assert ordinary == {("Feebas", None): 5, ("Basculin", "blue-striped"): 95}
    assert rippling == {
        ("Feebas", None): 60,
        ("Milotic", None): 5,
        ("Basculin", "red-striped"): 35,
    }
    assert sum(ordinary.values()) == 100
    assert sum(rippling.values()) == 100
