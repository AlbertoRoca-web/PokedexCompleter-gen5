from __future__ import annotations

import json
import socket
import threading

from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeConfig, BizHawkClient


def run_one_shot_server(response: dict[str, object]) -> tuple[str, int, threading.Thread]:
    ready = threading.Event()
    bound: dict[str, int | str] = {}

    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            host, port = sock.getsockname()
            bound["host"] = str(host)
            bound["port"] = int(port)
            ready.set()
            conn, _ = sock.accept()
            with conn:
                conn.recv(4096)
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2)
    return str(bound["host"]), int(bound["port"]), thread


def test_bizhawk_client_reads_json_response() -> None:
    host, port, thread = run_one_shot_server({"status": "ok"})
    client = BizHawkClient(BizHawkBridgeConfig(host=host, port=port, timeout_seconds=2))
    assert client.get_state() == {"status": "ok"}
    thread.join(timeout=2)
