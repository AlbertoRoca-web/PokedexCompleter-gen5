from __future__ import annotations

from collections.abc import Iterable

from pokedex_completer_gen5.dex.catchable_targets import (
    CatchableTarget,
    build_catchable_inventory_report,
    target_species_for_game,
)


def names(targets: Iterable[CatchableTarget]) -> set[str]:
    return {target.name for target in targets}


def test_direct_targets_respect_white_version_exclusives() -> None:
    targets = target_species_for_game("white", mode="direct")
    target_names = names(targets)

    assert "Solosis" in target_names
    assert "Thundurus" in target_names
    assert "Zekrom" in target_names
    assert "Gothita" not in target_names
    assert "Tornadus" not in target_names
    assert "Reshiram" not in target_names
    assert "Victini" not in target_names
    assert "Genesect" not in target_names


def test_direct_targets_respect_black_version_exclusives() -> None:
    targets = target_species_for_game("black", mode="direct")
    target_names = names(targets)

    assert "Gothita" in target_names
    assert "Tornadus" in target_names
    assert "Reshiram" in target_names
    assert "Solosis" not in target_names
    assert "Thundurus" not in target_names
    assert "Zekrom" not in target_names


def test_catchable_inventory_report_compares_physical_bodies_not_pokedex_flags() -> None:
    payload = {
        "selected_species_counts": [
            {"species_id": 506, "species_name": "Lillipup", "count": 1},
            {"species_id": 649, "species_name": "Genesect", "count": 1},
        ]
    }

    report = build_catchable_inventory_report(payload, "white", mode="direct")
    missing_names = {target.name for target in report.missing_targets}

    assert 506 in report.owned_target_ids
    assert 649 in report.ignored_owned_ids
    assert "Lillipup" not in missing_names
    assert "Patrat" in missing_names
