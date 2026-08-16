from __future__ import annotations

import json

from pokedex_completer_gen5.emulator.native_bridge import (
    NativeBridgeServer,
    _frame_for_bizhawk,
    _looks_like_complete_json_message,
    _strip_bizhawk_frame_prefix,
)


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


def test_complete_json_message_allows_framed_message_without_newline() -> None:
    payload = json.dumps({"id": "abc", "ok": True})

    assert _looks_like_complete_json_message(f"{len(payload)} {payload}") is True


def test_handle_lines_processes_framed_message_without_newline() -> None:
    payload = json.dumps({"id": "abc", "ok": True})
    server = NativeBridgeServer()

    remainder = server._handle_lines(f"{len(payload)} {payload}")

    assert remainder == ""
    assert server._results["abc"] == {"id": "abc", "ok": True}
