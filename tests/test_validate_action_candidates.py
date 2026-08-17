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
        address = int(json["address"])
        length = int(json["length"])
        return _FakeResponse({"ok": True, "values": list(range(address, address + length))})


def test_group_nearby_addresses_splits_on_max_span() -> None:
    groups = validate_action_candidates._group_nearby_addresses(
        [0x1005, 0x1000, 0x1002, 0x1400, 0x1401],
        max_span=0x400,
    )

    assert groups == [
        (0x1000, [0x1000, 0x1002, 0x1005]),
        (0x1400, [0x1400, 0x1401]),
    ]


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
