from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pokedex_completer_gen5.emulator.controls import normalize_button_or_action

MacroStatus = Literal["executed-needs-human-confirmation", "confirmed-success", "confirmed-failure"]
BridgeRequest = Callable[[str, dict[str, Any] | None], dict[str, Any]]


@dataclass(frozen=True)
class MacroStep:
    method: str
    params: dict[str, Any]
    result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"method": self.method, "params": self.params, "result": self.result}


@dataclass(frozen=True)
class MacroRun:
    macro_name: str
    expected_result: str
    steps: list[MacroStep]
    status: MacroStatus = "executed-needs-human-confirmation"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "macro_name": self.macro_name,
            "expected_result": self.expected_result,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "verification": {
                "mode": "human-confirmation-v1",
                "note": "No memory/vision verifier yet. Confirm result in the dashboard.",
            },
        }


def run_open_menu_macro(bridge_request: BridgeRequest, wait_frames: int = 20) -> MacroRun:
    return _run_button_wait_macro(
        bridge_request,
        macro_name="open_menu",
        action="menu",
        expected_result="Pokemon pause/menu screen is open.",
        wait_frames=wait_frames,
    )


def run_close_menu_macro(bridge_request: BridgeRequest, wait_frames: int = 20) -> MacroRun:
    return _run_button_wait_macro(
        bridge_request,
        macro_name="close_menu",
        action="cancel",
        expected_result="Pokemon pause/menu screen is closed or backed out one level.",
        wait_frames=wait_frames,
    )


def _run_button_wait_macro(
    bridge_request: BridgeRequest,
    *,
    macro_name: str,
    action: str,
    expected_result: str,
    wait_frames: int,
) -> MacroRun:
    button = normalize_button_or_action(action)
    press_params = {"button": button, "frames": 1}
    wait_params = {"frames": wait_frames}
    steps = [
        MacroStep("press", press_params, bridge_request("press", press_params)),
        MacroStep("frame_advance", wait_params, bridge_request("frame_advance", wait_params)),
    ]
    return MacroRun(macro_name=macro_name, expected_result=expected_result, steps=steps)
