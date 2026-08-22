from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

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


def test_tile_tuple_parses_tile_payload() -> None:
    assert continuous_play._tile_tuple({"x": 2, "y": 5}) == (2, 5)


def test_tile_tuple_rejects_malformed_payload() -> None:
    assert continuous_play._tile_tuple({"x": "2", "y": 5}) is None
    assert continuous_play._tile_tuple(None) is None


def test_screenshot_path_prefers_artifact_path() -> None:
    assert continuous_play._screenshot_path({"screenshot": {"artifact_path": "a.png", "path": "b.png"}}) == "a.png"


def test_screenshot_path_falls_back_to_path() -> None:
    assert continuous_play._screenshot_path({"screenshot": {"path": "b.png"}}) == "b.png"


def test_screenshot_path_returns_none_when_missing() -> None:
    assert continuous_play._screenshot_path({"screenshot": {}}) is None


def test_battle_lane_detector_finds_red_battle_ui(tmp_path: Path) -> None:
    path = tmp_path / "battle.png"
    image = Image.new("RGB", (256, 384), (0, 20, 24))
    ImageDraw.Draw(image).rectangle((0, 220, 255, 300), fill=(180, 10, 20))
    image.save(path)

    assert continuous_play._is_battle_like_screenshot(path) is True


def test_battle_lane_detector_ignores_dark_overworld_bottom_screen(tmp_path: Path) -> None:
    path = tmp_path / "overworld.png"
    Image.new("RGB", (256, 384), (0, 30, 35)).save(path)

    assert continuous_play._is_battle_like_screenshot(path) is False


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
