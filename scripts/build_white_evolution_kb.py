from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact Unova evolution knowledge from PokeAPI.")
    parser.add_argument("--output", type=Path, default=Path("data/knowledge/white-evolutions.jsonl"))
    args = parser.parse_args()
    client = httpx.Client(base_url="https://pokeapi.co/api/v2", timeout=60)
    chain_cache: dict[str, dict[str, Any]] = {}
    records = []
    for national in range(494, 650):
        species = client.get(f"/pokemon-species/{national}").json()
        chain_url = str(species["evolution_chain"]["url"])
        if chain_url not in chain_cache:
            chain_cache[chain_url] = client.get(chain_url).json()
        chain = chain_cache[chain_url]
        records.append(
            {
                "national": national,
                "name": species["name"],
                "is_baby": species["is_baby"],
                "evolution_chain_id": chain["id"],
                "transitions": _transitions(chain["chain"]),
                "source": chain_url,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(record, separators=(",", ":"), sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "output": str(args.output), "species_count": len(records)}, indent=2))
    return 0


def _transitions(root: dict[str, Any]) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []

    def visit(node: dict[str, Any]) -> None:
        source = str(node["species"]["name"])
        for child in node.get("evolves_to", []):
            transitions.append(
                {
                    "from": source,
                    "to": child["species"]["name"],
                    "details": [_compact_detail(detail) for detail in child.get("evolution_details", [])],
                }
            )
            visit(child)

    visit(root)
    return transitions


def _compact_detail(detail: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "min_level",
        "min_happiness",
        "min_beauty",
        "min_affection",
        "time_of_day",
        "needs_overworld_rain",
        "turn_upside_down",
    )
    compact = {key: detail.get(key) for key in keys if detail.get(key) not in (None, "", False)}
    for key in ("trigger", "item", "held_item", "known_move", "location", "trade_species"):
        value = detail.get(key)
        if isinstance(value, dict) and isinstance(value.get("name"), str):
            compact[key] = value["name"]
    if detail.get("gender") is not None:
        compact["gender"] = detail["gender"]
    if detail.get("relative_physical_stats") is not None:
        compact["relative_physical_stats"] = detail["relative_physical_stats"]
    return compact


if __name__ == "__main__":
    raise SystemExit(main())
