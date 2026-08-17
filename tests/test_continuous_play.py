from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "continuous_play.py"
_SPEC = importlib.util.spec_from_file_location("continuous_play", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
continuous_play = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(continuous_play)


def test_action_plan_uses_preset_when_no_override() -> None:
    assert continuous_play._action_plan(None, "wander") == continuous_play.PRESETS["wander"]


def test_action_plan_normalizes_aliases() -> None:
    assert continuous_play._action_plan(["confirm", "cancel", "up", "Right"], "wander") == [
        "A",
        "B",
        "Up",
        "Right",
    ]


def test_action_plan_rejects_unknown_actions() -> None:
    try:
        continuous_play._action_plan(["banana"], "wander")
    except ValueError as exc:
        assert "Unsupported action" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_finish_reports_jsonl_path() -> None:
    result = continuous_play._finish(
        True,
        "run-id",
        Path("events.jsonl"),
        [{"event": "x"}],
        "done",
        completed_steps=3,
    )

    assert result == {
        "ok": True,
        "run_id": "run-id",
        "reason": "done",
        "completed_steps": 3,
        "output_path": "events.jsonl",
        "event_count": 1,
    }
