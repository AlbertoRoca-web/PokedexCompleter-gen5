from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pokedex_completer_gen5.dex.route_target_planner import build_route_target_plan

DEFAULT_PROGRESS_DB = Path(".runtime/living-dex-progress.sqlite3")


@dataclass(frozen=True)
class VerifiedCatch:
    species_id: int
    species_name: str
    ball: str
    location_area: str
    evidence_path: str
    caught_at: str


def record_verified_catch(
    *,
    species_id: int,
    species_name: str,
    ball: str,
    location_area: str,
    evidence_path: str,
    db_path: Path = DEFAULT_PROGRESS_DB,
) -> VerifiedCatch:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    catch = VerifiedCatch(
        species_id=species_id,
        species_name=species_name,
        ball=ball,
        location_area=location_area,
        evidence_path=evidence_path,
        caught_at=datetime.now(UTC).isoformat(),
    )
    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            """
            INSERT INTO verified_catches
                (species_id, species_name, ball, location_area, evidence_path, caught_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                catch.species_id,
                catch.species_name,
                catch.ball,
                catch.location_area,
                catch.evidence_path,
                catch.caught_at,
            ),
        )
    return catch


def verified_catches(db_path: Path = DEFAULT_PROGRESS_DB) -> tuple[VerifiedCatch, ...]:
    if not db_path.exists():
        return ()
    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        rows = connection.execute(
            "SELECT species_id, species_name, ball, location_area, evidence_path, caught_at "
            "FROM verified_catches ORDER BY caught_at"
        ).fetchall()
    return tuple(VerifiedCatch(*row) for row in rows)


def session_owned_species_ids(db_path: Path = DEFAULT_PROGRESS_DB) -> set[int]:
    return {catch.species_id for catch in verified_catches(db_path)}


def build_master_route_cross_reference(
    *,
    save_path: Path,
    current_area: str,
    fly_available: bool,
    db_path: Path = DEFAULT_PROGRESS_DB,
    limit: int = 20,
) -> dict[str, Any]:
    catches = verified_catches(db_path)
    session_counts: dict[int, int] = {}
    for catch in catches:
        session_counts[catch.species_id] = session_counts.get(catch.species_id, 0) + 1
    route_plan = build_route_target_plan(
        save_path=save_path,
        current_area=current_area,
        fly_available=fly_available,
        limit=limit,
        additional_owned_ids={catch.species_id for catch in catches},
        additional_owned_counts=session_counts,
    )
    return {
        "master_state_sources": ["save-party-pc", "verified-session-catches", "future-live-pc-ram"],
        "verified_session_catches": [asdict(catch) for catch in catches],
        "route_plan": route_plan,
    }


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS verified_catches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            species_id INTEGER NOT NULL,
            species_name TEXT NOT NULL,
            ball TEXT NOT NULL,
            location_area TEXT NOT NULL,
            evidence_path TEXT NOT NULL,
            caught_at TEXT NOT NULL
        )
        """
    )
