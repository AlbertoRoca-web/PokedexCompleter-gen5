from __future__ import annotations

import json

from pokedex_completer_gen5.emulator.native_bridge import _frame_for_bizhawk, _strip_bizhawk_frame_prefix


def test_strip_bizhawk_frame_prefix() -> None:
    payload = json.dumps({"id": "abc", "ok": True})
    framed = f"{len(payload)} {payload}"

    assert _strip_bizhawk_frame_prefix(framed) == payload


def test_strip_bizhawk_frame_prefix_allows_length_mismatch() -> None:
    payload = json.dumps({"id": "abc", "ok": True})
    framed = f"999 {payload}"

    assert _strip_bizhawk_frame_prefix(framed) == payload


def test_frame_for_bizhawk_uses_length_prefix() -> None:
    payload = json.dumps({"method": "get_state"})

    assert _frame_for_bizhawk(payload) == f"{len(payload)} {payload}".encode()
