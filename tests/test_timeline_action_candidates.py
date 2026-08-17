from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "timeline_action_candidates.py"
_SPEC = importlib.util.spec_from_file_location("timeline_action_candidates", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
timeline_action_candidates = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(timeline_action_candidates)


def test_sample_frames_are_sorted_unique_non_negative() -> None:
    assert timeline_action_candidates._sample_frames([20, 0, 10, 10]) == [0, 10, 20]


def test_sample_frames_rejects_negative_values() -> None:
    try:
        timeline_action_candidates._sample_frames([0, -1])
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_rank_timelines_prefers_action_timeline_divergence() -> None:
    observations = [
        {
            "action": "Wait",
            "before": {"0x10": 1, "0x20": 9},
            "timeline": [
                {"frame": 0, "values": {"0x10": 1, "0x20": 9}},
                {"frame": 10, "values": {"0x10": 1, "0x20": 9}},
            ],
        },
        {
            "action": "Up",
            "before": {"0x10": 1, "0x20": 9},
            "timeline": [
                {"frame": 0, "values": {"0x10": 1, "0x20": 9}},
                {"frame": 10, "values": {"0x10": 2, "0x20": 9}},
            ],
        },
    ]

    ranked = timeline_action_candidates._rank_timelines(
        observations,
        [0x10, 0x20],
        sample_frames=[0, 10],
        control_action="Wait",
    )

    assert ranked[0]["hex_address"] == "0x10"
    assert ranked[0]["action_divergence_count"] == 1
    assert ranked[0]["differing_action_frames"] == {"Up": [10]}
    assert ranked[1]["hex_address"] == "0x20"
    assert ranked[1]["score"] < 0


def test_candidate_summary_omits_verbose_observations() -> None:
    summary = timeline_action_candidates._candidate_summary(
        {
            "hex_address": "0x10",
            "score": 1.0,
            "baseline_stability": 1.0,
            "stable_control_timeline": 1.0,
            "action_divergence_rate": 0.5,
            "action_divergence_count": 2,
            "distinct_final_modes": 1,
            "differing_action_frames": {"Up": [10]},
            "modes_by_action": {"Wait": {0: 1}, "Up": {0: 1, 10: 2}},
            "giant_payload": [1, 2, 3],
        }
    )

    assert "giant_payload" not in summary
    assert summary["hex_address"] == "0x10"
    assert summary["differing_action_frames"] == {"Up": [10]}
