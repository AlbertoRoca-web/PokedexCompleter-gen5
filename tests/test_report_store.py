from __future__ import annotations

from pokedex_completer_gen5.backend.report_store import build_dex_report_row, sanitized_report_payload


def sample_payload() -> dict[str, object]:
    return {
        "save": r"D:\alroc\codepup\rolo3\POKEMON W.sav",
        "game_profile": "white",
        "regional_dex_key": "bw_unova",
        "planner_supported": True,
        "selected_copy": 0,
        "dex_status": {
            "unique_species_owned": 2,
            "missing_species_count": 154,
        },
    }


def test_sanitized_report_payload_redacts_save_path() -> None:
    sanitized = sanitized_report_payload(sample_payload())

    assert sanitized["save"] == "POKEMON W.sav"
    assert sanitized["save_path_redacted"] is True


def test_build_dex_report_row_extracts_metadata() -> None:
    row = build_dex_report_row(sample_payload(), save_sha256="abc123")

    assert row.game_profile == "white"
    assert row.regional_dex_key == "bw_unova"
    assert row.planner_supported is True
    assert row.selected_copy == 0
    assert row.unique_species_owned == 2
    assert row.missing_species_count == 154
    assert row.save_sha256 == "abc123"
    assert row.report_json["save"] == "POKEMON W.sav"
