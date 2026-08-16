from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from pokedex_completer_gen5.emulator.controls import normalize_button_or_action
from pokedex_completer_gen5.emulator.screen_classifier import classify_screenshot, compare_screenshots
from pokedex_completer_gen5.emulator.visual_wait import InformativeScreenshotResult, capture_informative_screenshot

BridgeRequest = Callable[[str, dict[str, Any] | None], dict[str, Any]]


@dataclass(frozen=True)
class TitleFlowPhase:
    name: str
    action: dict[str, Any]
    result: dict[str, Any]
    screenshot: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "action": self.action,
            "result": self.result,
            "screenshot": self.screenshot,
        }


@dataclass(frozen=True)
class TitleResumeFlowResult:
    id: str
    status: str
    phases: list[TitleFlowPhase] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "macro_name": "resume_saved_game_from_title",
            "status": self.status,
            "phases": [phase.to_dict() for phase in self.phases],
            "verification": self.verification,
        }


def run_resume_saved_game_from_title(
    bridge_request: BridgeRequest,
    *,
    initial_wait_frames: int = 60,
    wait_after_start_frames: int = 90,
    wait_after_continue_frames: int = 600,
    visual_max_attempts: int = 5,
    visual_advance_frames: int = 30,
) -> TitleResumeFlowResult:
    flow_id = str(uuid4())
    phases: list[TitleFlowPhase] = []

    phases.append(_advance_phase(bridge_request, "initial-settle", initial_wait_frames))
    before = capture_informative_screenshot(
        bridge_request,
        label=f"title-flow-{flow_id}-before",
        max_attempts=visual_max_attempts,
        advance_frames=visual_advance_frames,
    )
    phases.append(_screenshot_phase("before", before))

    phases.append(_press_phase(bridge_request, "press-start-on-title", "start"))
    phases.append(_advance_phase(bridge_request, "wait-after-start", wait_after_start_frames))
    after_start = capture_informative_screenshot(
        bridge_request,
        label=f"title-flow-{flow_id}-after-start",
        max_attempts=visual_max_attempts,
        advance_frames=visual_advance_frames,
    )
    phases.append(_screenshot_phase("after-start", after_start))

    phases.append(_press_phase(bridge_request, "confirm-continue", "confirm"))
    phases.append(_advance_phase(bridge_request, "wait-after-continue", wait_after_continue_frames))
    final = capture_informative_screenshot(
        bridge_request,
        label=f"title-flow-{flow_id}-final",
        max_attempts=visual_max_attempts,
        advance_frames=visual_advance_frames,
    )
    phases.append(_screenshot_phase("final", final))

    verification = _verify_title_resume(before, final)
    return TitleResumeFlowResult(
        id=flow_id,
        status=str(verification["status"]),
        phases=phases,
        verification=verification,
    )


def _press_phase(bridge_request: BridgeRequest, name: str, action: str) -> TitleFlowPhase:
    button = normalize_button_or_action(action)
    params = {"button": button, "frames": 1}
    return TitleFlowPhase(
        name=name,
        action={"method": "press", "params": params},
        result=bridge_request("press", params),
    )


def _advance_phase(bridge_request: BridgeRequest, name: str, frames: int) -> TitleFlowPhase:
    params = {"frames": frames}
    return TitleFlowPhase(
        name=name,
        action={"method": "frame_advance", "params": params},
        result=bridge_request("frame_advance", params),
    )


def _screenshot_phase(name: str, result: InformativeScreenshotResult) -> TitleFlowPhase:
    return TitleFlowPhase(
        name=f"screenshot-{name}",
        action={"method": "capture_informative_screenshot"},
        result={"ok": result.ok, "reason": result.reason},
        screenshot=result.to_dict(),
    )


def _verify_title_resume(before: InformativeScreenshotResult, final: InformativeScreenshotResult) -> dict[str, Any]:
    if not before.ok or not final.ok or not before.attempts or not final.attempts:
        return {
            "mode": "title-resume-visual-v1",
            "status": "needs-human",
            "reason": "before or final screenshot was not informative",
            "before_ok": before.ok,
            "final_ok": final.ok,
        }

    before_path = Path(before.attempts[-1].path)
    final_path = Path(final.attempts[-1].path)
    delta = compare_screenshots(before_path=before_path, after_path=final_path)
    before_classification = classify_screenshot(before_path)
    final_classification = classify_screenshot(final_path)
    final_type = final_classification.screen_type
    accepted = delta.changed_enough and final_type not in {"blank-white", "blank-black", "boot-or-logo"}
    return {
        "mode": "title-resume-visual-v1",
        "status": "candidate-overworld" if accepted else "needs-human",
        "reason": (
            "final screen changed and is no longer blank/boot"
            if accepted
            else "final screen did not prove save loaded"
        ),
        "screen_delta": delta.to_dict(),
        "before_classification": before_classification.to_dict(),
        "final_classification": final_classification.to_dict(),
    }
