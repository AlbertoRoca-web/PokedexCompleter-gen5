from __future__ import annotations

from pokedex_completer_gen5.dex.breeding_protocol import build_breeding_plan
from pokedex_completer_gen5.dex.evolution_kb import evolution_record


def test_breeding_plan_requires_ditto_and_preserves_gen5_ball_legality() -> None:
    plan = build_breeding_plan(
        parent_species="Herdier",
        base_species="Lillipup",
        eggs_needed=1,
        ditto_owned=True,
    )

    assert plan.ready is True
    assert plan.partner_species == "Ditto"
    assert any("standard Poke Ball" in rule for rule in plan.legality_rules)


def test_patrat_evolution_record_comes_from_generated_knowledge_base() -> None:
    record = evolution_record(504)

    transition = next(item for item in record["transitions"] if item["to"] == "watchog")
    assert transition["details"][0]["min_level"] == 20
