from __future__ import annotations

import pytest

from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report, living_dex_targets


def sample_payload() -> dict[str, object]:
    return {
        "selected_copy": 0,
        "copies": [
            {
                "copy_index": 0,
                "mons": [
                    {"species_id": 506, "species_name": "Lillipup", "source": "pc"},
                    {"species_id": 519, "species_name": "Pidove", "source": "party"},
                    {"species_id": 21, "species_name": "Spearow", "source": "party"},
                ],
            }
        ],
    }


def test_regional_living_dex_targets_include_version_available_species() -> None:
    white_targets = {target.name for target in living_dex_targets("white")}
    black_targets = {target.name for target in living_dex_targets("black")}

    assert "Zekrom" in white_targets
    assert "Reshiram" not in white_targets
    assert "Reshiram" in black_targets
    assert "Zekrom" not in black_targets


def test_pc_living_dex_counts_pc_and_party_separately() -> None:
    report = build_pc_living_dex_report(sample_payload(), "white", include_party=True)

    assert report.pc_owned_target_count == 1
    assert report.party_owned_target_count == 1
    assert report.combined_owned_target_count == 2
    assert 21 in report.extra_owned_species
    assert report.combined_complete is False


def test_pc_living_dex_can_ignore_party() -> None:
    report = build_pc_living_dex_report(sample_payload(), "white", include_party=False)

    assert report.pc_owned_target_count == 1
    assert report.party_owned_target_count == 1
    assert report.combined_owned_target_count == 1


def test_national_scope_is_explicitly_pending() -> None:
    with pytest.raises(NotImplementedError):
        living_dex_targets("white", scope="national")
