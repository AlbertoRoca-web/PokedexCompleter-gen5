from __future__ import annotations

from pathlib import Path

from pokedex_completer_gen5.autonomy.loop import AutonomyBudget, AutonomyConfig, run_autonomy
from pokedex_completer_gen5.persistence.database import init_database, reset_database_engine_for_tests
from pokedex_completer_gen5.settings import get_settings


def configure_runtime(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("POKEDEX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("POKEDEX_DB_PATH", str(tmp_path / "runtime" / "run.sqlite3"))
    get_settings.cache_clear()
    reset_database_engine_for_tests()
    init_database()


def test_autonomy_dry_run_prioritizes_semantic_state(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)

    result = run_autonomy(AutonomyConfig(budget=AutonomyBudget(max_iterations=3, max_seconds=30))).to_dict()

    assert result["status"] == "stopped-dry-run"
    assert result["steps"][0]["decision"] == "discover-semantic-state"
    assert result["events"][0]["event_type"] == "autonomy.run_started"
    assert (tmp_path / "runtime" / "logs" / "events.jsonl").exists()


def test_autonomy_respects_iteration_budget(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)

    result = run_autonomy(
        AutonomyConfig(
            dry_run=False,
            budget=AutonomyBudget(max_iterations=2, max_seconds=30),
        )
    ).to_dict()

    assert result["status"] == "completed-budget"
    assert len(result["steps"]) == 2
