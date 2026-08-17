from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_action_candidates.py"
_SPEC = importlib.util.spec_from_file_location("validate_action_candidates", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
validate_action_candidates = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_action_candidates)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(self, path: str, *, json: dict[str, Any]) -> _FakeResponse:
        self.requests.append((path, json))
        if path == "/api/emulator/frame-advance":
            return _FakeResponse({"ok": True})
        if path == "/api/emulator/press":
            return _FakeResponse({"ok": True})
        address = int(json["address"])
        length = int(json["length"])
        return _FakeResponse({"ok": True, "values": list(range(address, address + length))})


def test_candidate_addresses_combines_explicit_addresses_and_ranges() -> None:
    addresses = validate_action_candidates._candidate_addresses(["0x1002", "0x1000"], [["0x1000", "0x4"]])

    assert addresses == [0x1000, 0x1001, 0x1002, 0x1003]


def test_candidate_addresses_requires_at_least_one_address() -> None:
    try:
        validate_action_candidates._candidate_addresses([], None)
    except ValueError as exc:
        assert "At least one address" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_group_nearby_addresses_splits_on_max_span() -> None:
    groups = validate_action_candidates._group_nearby_addresses(
        [0x1005, 0x1000, 0x1002, 0x1400, 0x1401],
        max_span=0x400,
    )

    assert groups == [
        (0x1000, [0x1000, 0x1002, 0x1005]),
        (0x1400, [0x1400, 0x1401]),
    ]


def test_with_control_action_prepends_missing_control() -> None:
    assert validate_action_candidates._with_control_action(["Up", "Down", "Up"], "Wait") == ["Wait", "Up", "Down"]


def test_perform_action_wait_only_advances_frames() -> None:
    client = _FakeClient()

    validate_action_candidates._perform_action(client, "Wait", press_frames=7, advance_frames=11)

    assert client.requests == [("/api/emulator/frame-advance", {"frames": 18})]


def test_perform_action_button_presses_then_advances() -> None:
    client = _FakeClient()

    validate_action_candidates._perform_action(client, "Up", press_frames=7, advance_frames=11)

    assert client.requests == [
        ("/api/emulator/press", {"button": "Up", "frames": 7}),
        ("/api/emulator/frame-advance", {"frames": 11}),
    ]


def test_candidate_summary_omits_verbose_observation_values() -> None:
    summary = validate_action_candidates._candidate_summary(
        {
            "hex_address": "0x20",
            "score": 9.0,
            "baseline_stability": 1.0,
            "movement_change_rate": 0.5,
            "control_change_rate": 0.0,
            "movement_specific_change_rate": 0.5,
            "distinct_directional_after_modes": 2,
            "action_modes_different_from_control": 2,
            "action_after_modes": {"Wait": 1, "Up": 2},
            "before_by_action": {"Wait": [1, 1], "Up": [1, 1]},
            "after_by_action": {"Wait": [1, 1], "Up": [2, 2]},
        }
    )

    assert summary == {
        "hex_address": "0x20",
        "score": 9.0,
        "baseline_stability": 1.0,
        "movement_change_rate": 0.5,
        "control_change_rate": 0.0,
        "movement_specific_change_rate": 0.5,
        "distinct_directional_after_modes": 2,
        "action_modes_different_from_control": 2,
        "action_after_modes": {"Wait": 1, "Up": 2},
    }


def test_read_addresses_batches_nearby_addresses() -> None:
    client = _FakeClient()

    values = validate_action_candidates._read_addresses(
        client,
        domain="ARM9 System Bus",
        addresses=[0x1000, 0x1003, 0x1400],
    )

    assert values == {
        "0x1000": 0x1000,
        "0x1003": 0x1003,
        "0x1400": 0x1400,
    }
    assert client.requests == [
        (
            "/api/emulator/memory/read-bytes",
            {"domain": "ARM9 System Bus", "address": 0x1000, "length": 4},
        ),
        (
            "/api/emulator/memory/read-bytes",
            {"domain": "ARM9 System Bus", "address": 0x1400, "length": 1},
        ),
    ]


def test_rank_candidates_prefers_movement_specific_changes_over_stable_bytes() -> None:
    observations = [
        {
            "action": "Wait",
            "before": {"0x10": 7, "0x20": 1},
            "after": {"0x10": 7, "0x20": 1},
        },
        {
            "action": "Up",
            "before": {"0x10": 7, "0x20": 1},
            "after": {"0x10": 7, "0x20": 2},
        },
        {
            "action": "Down",
            "before": {"0x10": 7, "0x20": 1},
            "after": {"0x10": 7, "0x20": 3},
        },
    ]

    ranked = validate_action_candidates._rank_candidates(observations, [0x10, 0x20], control_action="Wait")

    assert ranked[0]["hex_address"] == "0x20"
    assert ranked[0]["movement_specific_change_rate"] == 1.0
    assert ranked[1]["hex_address"] == "0x10"
    assert ranked[1]["movement_specific_change_rate"] == 0.0
