from __future__ import annotations

from pathlib import Path

from pokedex_completer_gen5.persistence.living_dex_progress import (
    record_verified_catch,
    session_owned_species_ids,
    verified_catches,
)


def test_verified_catch_updates_session_master_inventory(tmp_path: Path) -> None:
    db_path = tmp_path / "progress.sqlite3"

    catch = record_verified_catch(
        species_id=504,
        species_name="Patrat",
        ball="Ultra Ball",
        location_area="unova-route-1-area",
        evidence_path="caught.png",
        db_path=db_path,
    )

    assert catch.species_id == 504
    assert session_owned_species_ids(db_path) == {504}
    assert verified_catches(db_path)[0].ball == "Ultra Ball"
