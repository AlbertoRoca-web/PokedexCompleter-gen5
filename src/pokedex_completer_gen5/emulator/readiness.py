from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pokedex_completer_gen5.emulator.artifacts import screenshot_path
from pokedex_completer_gen5.emulator.launcher import bizhawk_launch_config_from_env, launch_bizhawk
from pokedex_completer_gen5.emulator.native_bridge import NativeBridgeError, native_bridge, wait_for_native_bridge
from pokedex_completer_gen5.emulator.vision import analyze_screenshot
from pokedex_completer_gen5.settings import get_settings


@dataclass(frozen=True)
class ReadinessProbe:
    name: str
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "payload": self.payload}


@dataclass(frozen=True)
class EmulatorReadinessResult:
    ok: bool
    probes: list[ReadinessProbe]
    launched: dict[str, Any] | None = None
    retried_launch: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "probes": [probe.to_dict() for probe in self.probes],
            "launched": self.launched,
            "retried_launch": self.retried_launch,
        }


def ensure_emulator_ready(*, relaunch_if_needed: bool = True) -> EmulatorReadinessResult:
    probes = _probe_current_bridge()
    if _all_ok(probes):
        return EmulatorReadinessResult(ok=True, probes=probes)
    if not relaunch_if_needed:
        return EmulatorReadinessResult(ok=False, probes=probes)

    bridge = native_bridge()
    bridge.start()
    launch_payload = launch_bizhawk(bizhawk_launch_config_from_env(), install_save=True, restart_existing=True)
    wait_payload = wait_for_native_bridge(timeout_seconds=25)
    probes.append(ReadinessProbe("launch", bool(launch_payload.get("ok")), launch_payload))
    probes.append(ReadinessProbe("wait_for_native_bridge", bool(wait_payload.get("ok")), wait_payload))
    probes.extend(_probe_current_bridge())
    return EmulatorReadinessResult(
        ok=_all_ok(probes[-4:]),
        probes=probes,
        launched=launch_payload,
        retried_launch=True,
    )


def _probe_current_bridge() -> list[ReadinessProbe]:
    bridge = native_bridge()
    bridge.start()
    probes: list[ReadinessProbe] = []
    try:
        speed = bridge.request("emulator.set_speed", {"percent": get_settings().emulator.speed_percent})
        probes.append(ReadinessProbe("emulator.set_speed", bool(speed.get("ok")), speed))
        info = bridge.request("bridge.info")
        probes.append(ReadinessProbe("bridge.info", True, info))
    except NativeBridgeError as exc:
        probes.append(ReadinessProbe("bridge.info", False, {"error": str(exc), "status": bridge.status()}))
        return probes

    try:
        state = bridge.request("get_state")
        probes.append(ReadinessProbe("get_state", True, state))
    except NativeBridgeError as exc:
        probes.append(ReadinessProbe("get_state", False, {"error": str(exc), "status": bridge.status()}))

    try:
        path = screenshot_path("readiness")
        response = bridge.request("screenshot", {"path": path.as_posix()})
        analysis = analyze_screenshot(path) if path.exists() else {"error": "screenshot file missing"}
        probes.append(ReadinessProbe("screenshot", path.exists(), {"response": response, "analysis": analysis}))
    except (NativeBridgeError, RuntimeError) as exc:
        probes.append(ReadinessProbe("screenshot", False, {"error": str(exc), "status": bridge.status()}))
    return probes


def _all_ok(probes: list[ReadinessProbe]) -> bool:
    required = {"emulator.set_speed", "bridge.info", "get_state", "screenshot"}
    ok_names = {probe.name for probe in probes if probe.ok}
    return required.issubset(ok_names)
