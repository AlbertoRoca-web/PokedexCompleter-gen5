from __future__ import annotations

import socket
from typing import Any

from pokedex_completer_gen5.emulator.native_bridge import native_bridge
from pokedex_completer_gen5.integrations.provider_health import provider_health_payload

KNOWN_LOCAL_PORTS = (8787, 8766, 8765)


def discover_local_connections(host: str = "127.0.0.1") -> dict[str, Any]:
    ports = {port: _port_open(host, port) for port in KNOWN_LOCAL_PORTS}
    bridge = native_bridge()
    bridge.start()
    bridge_status = bridge.status()
    return {
        "ok": True,
        "host": host,
        "services": {
            "rest_api": {
                "port": 8787,
                "reachable": ports[8787],
                "url": "http://127.0.0.1:8787",
            },
            "native_bridge": {
                "port": 8766,
                "listening": ports[8766],
                "connected": bool(bridge_status.get("connected")),
                "status": bridge_status,
            },
            "legacy_bridge": {"port": 8765, "listening": ports[8765]},
            "mcp_stdio": {"command": "uv run rld-mcp", "transport": "stdio"},
        },
        "providers": provider_health_payload(),
        "recommended_action": _recommended_action(ports[8787], bool(bridge_status.get("connected"))),
    }


def _port_open(host: str, port: int, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _recommended_action(api_reachable: bool, bridge_connected: bool) -> str:
    if not api_reachable:
        return "start-local-companion"
    if not bridge_connected:
        return "launch-or-connect-bizhawk"
    return "ready"
