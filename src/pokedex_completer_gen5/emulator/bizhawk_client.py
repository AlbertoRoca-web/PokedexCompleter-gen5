from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any

from pokedex_completer_gen5.settings import get_settings


@dataclass(frozen=True)
class BizHawkBridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_seconds: float = 5.0


def bizhawk_config_from_env() -> BizHawkBridgeConfig:
    settings = get_settings().emulator
    return BizHawkBridgeConfig(
        host=settings.legacy_bridge_host,
        port=settings.legacy_bridge_port,
        timeout_seconds=settings.legacy_bridge_timeout_seconds,
    )


class BizHawkBridgeError(RuntimeError):
    """Raised when the BizHawk bridge cannot complete a request."""


class BizHawkClient:
    """Minimal JSON-over-TCP client scaffold for the future BizHawk Lua bridge.

    The Lua scaffold does not serve TCP yet. This class defines the Python-side protocol
    boundary we will implement next. Keeping it small avoids building a fake bridge castle
    in the sky. Tiny puppy hates castles in the sky.
    """

    def __init__(self, config: BizHawkBridgeConfig | None = None) -> None:
        self.config = config or BizHawkBridgeConfig()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"method": method, "params": params or {}}
        raw = (json.dumps(payload) + "\n").encode("utf-8")
        try:
            with socket.create_connection(
                (self.config.host, self.config.port),
                timeout=self.config.timeout_seconds,
            ) as sock:
                sock.sendall(raw)
                response = self._read_line(sock)
        except OSError as exc:
            raise BizHawkBridgeError(f"BizHawk bridge request failed: {exc}") from exc

        try:
            decoded = json.loads(response)
        except json.JSONDecodeError as exc:
            raise BizHawkBridgeError(f"Invalid bridge JSON response: {response!r}") from exc
        if not isinstance(decoded, dict):
            raise BizHawkBridgeError("Bridge response must be a JSON object")
        return decoded

    def get_state(self) -> dict[str, Any]:
        return self.request("get_state")

    def press(self, button: str, frames: int = 1) -> dict[str, Any]:
        return self.request("press", {"button": button, "frames": frames})

    def press_sequence(self, buttons: list[str], frames: int = 1, gap_frames: int = 1) -> dict[str, Any]:
        return self.request(
            "press_sequence",
            {"buttons_csv": ",".join(buttons), "frames": frames, "gap_frames": gap_frames},
        )

    def frame_advance(self, frames: int = 1) -> dict[str, Any]:
        return self.request("frame_advance", {"frames": frames})

    def pause(self) -> dict[str, Any]:
        return self.request("pause")

    def resume(self) -> dict[str, Any]:
        return self.request("resume")

    def save_checkpoint(self, name: str) -> dict[str, Any]:
        return self.request("save_checkpoint", {"name": name})

    def load_checkpoint(self, name: str) -> dict[str, Any]:
        return self.request("load_checkpoint", {"name": name})

    def screenshot(self) -> dict[str, Any]:
        return self.request("screenshot")

    @staticmethod
    def _read_line(sock: socket.socket) -> str:
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        if not chunks:
            raise BizHawkBridgeError("Bridge closed without a response")
        return b"".join(chunks).split(b"\n", 1)[0].decode("utf-8")
