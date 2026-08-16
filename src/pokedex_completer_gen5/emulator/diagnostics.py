from __future__ import annotations

import os
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkBridgeConfig, BizHawkBridgeError, BizHawkClient
from pokedex_completer_gen5.emulator.launcher import BizHawkLaunchConfig


@dataclass(frozen=True)
class BridgeProbe:
    ok: bool
    detail: str
    response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "detail": self.detail, "response": self.response}


def build_emulator_diagnostics(
    launch_config: BizHawkLaunchConfig,
    bridge_config: BizHawkBridgeConfig,
) -> dict[str, Any]:
    process = bizhawk_process_status(launch_config.bizhawk_exe.name)
    port = tcp_port_status(bridge_config.host, bridge_config.port, bridge_config.timeout_seconds)
    probe = probe_bridge(bridge_config)
    diagnosis = summarize_diagnosis(process, port, probe)
    return {
        "process": process,
        "bridge_port": port,
        "bridge_probe": probe.to_dict(),
        "diagnosis": diagnosis,
    }


def wait_for_bridge(
    bridge_config: BizHawkBridgeConfig,
    *,
    timeout_seconds: float = 8.0,
    interval_seconds: float = 0.5,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_probe = BridgeProbe(ok=False, detail="not attempted")
    while time.monotonic() < deadline:
        attempts += 1
        last_probe = probe_bridge(bridge_config)
        if last_probe.ok:
            return {"ok": True, "attempts": attempts, "probe": last_probe.to_dict()}
        time.sleep(interval_seconds)
    return {"ok": False, "attempts": attempts, "probe": last_probe.to_dict()}


def probe_bridge(bridge_config: BizHawkBridgeConfig) -> BridgeProbe:
    try:
        response = BizHawkClient(bridge_config).get_state()
    except BizHawkBridgeError as exc:
        return BridgeProbe(ok=False, detail=str(exc))
    return BridgeProbe(ok=True, detail="Bridge responded to get_state.", response=response)


def tcp_port_status(host: str, port: int, timeout_seconds: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return {"host": host, "port": port, "listening": True}
    except OSError as exc:
        return {"host": host, "port": port, "listening": False, "error": str(exc)}


def bizhawk_process_status(process_name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"checked": False, "running": None, "reason": "Windows tasklist check only for now."}
    result = subprocess.run(  # noqa: S603 - local process diagnostics.
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout.strip()
    running = process_name.lower() in output.lower()
    return {
        "checked": True,
        "process_name": process_name,
        "running": running,
        "exit_code": result.returncode,
    }


def summarize_diagnosis(
    process: dict[str, Any],
    port: dict[str, Any],
    probe: BridgeProbe,
) -> dict[str, Any]:
    if probe.ok:
        return {
            "status": "ready",
            "message": "BizHawk bridge is connected. Controls should work.",
            "next_step": "Try A/B/D-pad buttons.",
        }
    if process.get("running") is not True:
        return {
            "status": "bizhawk-not-running",
            "message": "BizHawk is not running.",
            "next_step": "Click Launch BizHawk + White.",
        }
    if port.get("listening") is not True:
        return {
            "status": "bridge-not-listening",
            "message": "BizHawk is running, but the Lua bridge is not listening on the configured TCP port.",
            "next_step": "Check BizHawk Lua Console for LuaSocket errors or script load errors.",
        }
    return {
        "status": "bridge-not-responding",
        "message": "The TCP port is open, but the bridge did not return valid get_state JSON.",
        "next_step": "Check Lua Console output and restart from the website.",
    }
