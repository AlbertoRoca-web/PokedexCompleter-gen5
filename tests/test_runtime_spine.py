from __future__ import annotations

from pathlib import Path

from pokedex_completer_gen5.ai.benchmark import dry_run_model_routing
from pokedex_completer_gen5.ai.router import PlanningTask, choose_model
from pokedex_completer_gen5.domain.game_state import semantic_state_from_bridge
from pokedex_completer_gen5.events import event_bus
from pokedex_completer_gen5.persistence.database import init_database, reset_database_engine_for_tests
from pokedex_completer_gen5.persistence.store import (
    get_artifact,
    latest_artifact_path,
    list_artifacts,
    macro_reliability,
    persist_artifact,
    persist_macro_attempt,
    persist_macro_feedback,
)
from pokedex_completer_gen5.runtime import ensure_runtime_dirs
from pokedex_completer_gen5.settings import AISettings, get_settings
from pokedex_completer_gen5.trajectory import read_jsonl_events


def configure_runtime(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("POKEDEX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("POKEDEX_DB_PATH", str(tmp_path / "runtime" / "run.sqlite3"))
    get_settings.cache_clear()
    reset_database_engine_for_tests()


def test_runtime_dirs_are_created(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)

    paths = ensure_runtime_dirs()

    assert paths.root.exists()
    assert paths.logs.exists()
    assert paths.db_path.parent.exists()


def test_event_bus_can_append_jsonl(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    from pokedex_completer_gen5.trajectory import append_jsonl_event

    event_bus().subscribe(append_jsonl_event)
    event_bus().publish("test.event", {"ok": True})

    assert read_jsonl_events(limit=1)[0]["event_type"] == "test.event"


def test_sqlite_macro_feedback_reliability(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    init_database()

    persist_macro_attempt(
        {
            "id": "macro-1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "macro_name": "open_menu",
            "status": "executed-needs-human-confirmation",
            "expected_result": "menu",
        }
    )
    persist_macro_feedback(
        {
            "id": "feedback-1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "macro_run_id": "macro-1",
            "outcome": "success",
            "notes": "woof",
            "payload": {},
        }
    )

    reliability = macro_reliability()
    assert reliability[0]["macro_name"] == "open_menu"
    assert reliability[0]["success_rate"] == 1.0


def test_artifact_store_round_trip(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configure_runtime(monkeypatch, tmp_path)
    init_database()
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"png-ish")

    metadata = persist_artifact("screenshot", screenshot, {"source": "test"})

    assert get_artifact(str(metadata["id"])) is not None
    assert list_artifacts("screenshot", limit=1)[0]["path"] == str(screenshot)
    assert latest_artifact_path("screenshot") == screenshot


def test_semantic_state_is_conservative() -> None:
    state = semantic_state_from_bridge({"ok": True, "result": {"frame": 123}})

    assert state.mode == "unknown"
    assert state.frame == 123
    assert state.bridge_connected is True


def test_model_router_respects_offline_profile() -> None:
    settings = AISettings(RLD_AI_PROFILE="offline")

    assert choose_model(PlanningTask(kind="planning", complexity=5), settings=settings) is None


def test_benchmark_routing_seed_case() -> None:
    cases = dry_run_model_routing(Path("tests/planner_cases"))

    assert cases
    assert cases[0]["selected_model"] == "gpt-5-mini"
