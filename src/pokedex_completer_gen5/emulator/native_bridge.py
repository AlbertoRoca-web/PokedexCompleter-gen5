from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any
from uuid import uuid4

from pokedex_completer_gen5.settings import get_settings


def native_bridge_config_from_env() -> NativeBridgeConfig:
    settings = get_settings().emulator
    return NativeBridgeConfig(
        host=settings.native_bridge_host,
        port=settings.native_bridge_port,
        timeout_seconds=settings.native_bridge_timeout_seconds,
    )


class NativeBridgeError(RuntimeError):
    """Raised when the BizHawk native comm bridge is unavailable."""


@dataclass(frozen=True)
class NativeBridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8766
    timeout_seconds: float = 5.0


@dataclass
class NativeBridgeServer:
    config: NativeBridgeConfig = field(default_factory=NativeBridgeConfig)
    _commands: Queue[str] = field(default_factory=Queue)
    _results: dict[str, dict[str, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _thread: threading.Thread | None = None
    _running: bool = False
    _connected: bool = False
    _last_event: dict[str, Any] | None = None
    _last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, name="bizhawk-native-bridge", daemon=True)
        self._thread.start()

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "thread_alive": bool(self._thread and self._thread.is_alive()),
            "connected": self._connected,
            "host": self.config.host,
            "port": self.config.port,
            "last_event": self._last_event,
            "last_error": self._last_error,
        }

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.start()
        request_id = str(uuid4())
        payload = json.dumps({"id": request_id, "method": method, "params": params or {}})
        self._commands.put(payload)
        deadline = time.monotonic() + self.config.timeout_seconds
        while time.monotonic() < deadline:
            with self._lock:
                result = self._results.pop(request_id, None)
            if result is not None:
                return result
            time.sleep(0.05)
        raise NativeBridgeError("BizHawk native bridge did not return a response before timeout")

    def _serve(self) -> None:
        while self._running:
            try:
                self._accept_once()
            except OSError as exc:
                self._last_error = str(exc)
                time.sleep(0.5)

    def _accept_once(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.config.host, self.config.port))
            server.listen(1)
            server.settimeout(1)
            while self._running:
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                with conn:
                    self._connected = True
                    conn.settimeout(0.1)
                    self._connection_loop(conn)
                    self._connected = False

    def _connection_loop(self, conn: socket.socket) -> None:
        buffer = ""
        while self._running:
            try:
                chunk = conn.recv(65536)
            except TimeoutError:
                chunk = b""
            except OSError as exc:
                self._last_error = str(exc)
                return
            if chunk:
                buffer += chunk.decode("utf-8", errors="replace")
                buffer = self._handle_lines(buffer)
            try:
                command = self._commands.get_nowait()
            except Empty:
                continue
            conn.sendall(_frame_for_bizhawk(command))

    def _handle_lines(self, buffer: str) -> str:
        lines = buffer.split("\n")
        remainder = lines.pop()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            self._handle_message(line)
        if _looks_like_complete_json_message(remainder):
            self._handle_message(remainder.strip())
            return ""
        return remainder

    def _handle_message(self, message: str) -> None:
        message = _strip_bizhawk_frame_prefix(message)
        try:
            decoded = json.loads(message)
        except json.JSONDecodeError:
            self._last_event = {"raw": message}
            return
        if not isinstance(decoded, dict):
            self._last_event = {"raw": decoded}
            return
        self._last_event = decoded
        request_id = decoded.get("id")
        if isinstance(request_id, str):
            with self._lock:
                self._results[request_id] = decoded


def _looks_like_complete_json_message(message: str) -> bool:
    payload = _strip_bizhawk_frame_prefix(message.strip())
    if not payload.startswith("{") or not payload.endswith("}"):
        return False
    try:
        json.loads(payload)
    except json.JSONDecodeError:
        return False
    return True


def _strip_bizhawk_frame_prefix(message: str) -> str:
    length_text, separator, payload = message.partition(" ")
    if separator and length_text.isdigit() and payload.lstrip().startswith("{"):
        # BizHawk documents native socket responses as "<length> <payload>".
        # In practice the reported length can disagree with Python's decoded str length
        # because encodings/newlines are goblins. The JSON start is the useful contract.
        return payload.lstrip()
    return message


def _frame_for_bizhawk(payload: str) -> bytes:
    return f"{len(payload)} {payload}".encode()


_native_bridge: NativeBridgeServer | None = None


def wait_for_native_bridge(timeout_seconds: float = 8.0, interval_seconds: float = 0.5) -> dict[str, Any]:
    bridge = native_bridge()
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_error = "not attempted"
    while time.monotonic() < deadline:
        attempts += 1
        if bridge.status()["connected"]:
            try:
                response = bridge.request("get_state")
                return {"ok": True, "attempts": attempts, "response": response, "status": bridge.status()}
            except NativeBridgeError as exc:
                last_error = str(exc)
        time.sleep(interval_seconds)
    return {"ok": False, "attempts": attempts, "error": last_error, "status": bridge.status()}


def native_bridge() -> NativeBridgeServer:
    global _native_bridge
    config = native_bridge_config_from_env()
    if _native_bridge is None or _native_bridge.config != config:
        _native_bridge = NativeBridgeServer(config)
    _native_bridge.start()
    return _native_bridge
