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
    press_frames: int = 4,
    change_max_attempts: int = 8,
    change_advance_frames: int = 90,
) -> TitleResumeFlowResult:
    flow_id = str(uuid4())
    phases: list[TitleFlowPhase] = []

    phases.append(_info_phase(bridge_request, "bridge-info-start"))
    phases.append(_advance_phase(bridge_request, "initial-settle", initial_wait_frames))
    before = capture_informative_screenshot(
        bridge_request,
        label=f"title-flow-{flow_id}-before",
        max_attempts=visual_max_attempts,
        advance_frames=visual_advance_frames,
    )
    phases.append(_screenshot_phase("before", before))

    phases.append(_press_phase(bridge_request, "press-start-on-title", "start", press_frames=press_frames))
    phases.append(_advance_phase(bridge_request, "minimum-wait-after-start", wait_after_start_frames))
    after_start, after_start_phases = _observe_until_changed(
        bridge_request,
        reference=before,
        label=f"title-flow-{flow_id}-after-start",
        phase_prefix="after-start",
        max_change_attempts=change_max_attempts,
        change_advance_frames=change_advance_frames,
        visual_max_attempts=visual_max_attempts,
        visual_advance_frames=visual_advance_frames,
    )
    phases.extend(after_start_phases)

    phases.append(_press_phase(bridge_request, "confirm-continue", "confirm", press_frames=press_frames))
    phases.append(_advance_phase(bridge_request, "minimum-wait-after-continue", wait_after_continue_frames))
    final, final_phases = _observe_until_not_boot(
        bridge_request,
        reference=after_start,
        label=f"title-flow-{flow_id}-final",
        phase_prefix="final",
        max_change_attempts=change_max_attempts,
        change_advance_frames=change_advance_frames,
        visual_max_attempts=visual_max_attempts,
        visual_advance_frames=visual_advance_frames,
    )
    phases.extend(final_phases)
    phases.append(_info_phase(bridge_request, "bridge-info-end"))

    verification = _verify_title_resume(before, final)
    return TitleResumeFlowResult(
        id=flow_id,
        status=str(verification["status"]),
        phases=phases,
        verification=verification,
    )


def _press_phase(bridge_request: BridgeRequest, name: str, action: str, *, press_frames: int = 4) -> TitleFlowPhase:
    button = normalize_button_or_action(action)
    params = {"button": button, "frames": press_frames}
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


def _info_phase(bridge_request: BridgeRequest, name: str) -> TitleFlowPhase:
    try:
        result = bridge_request("bridge.info", None)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    return TitleFlowPhase(name=name, action={"method": "bridge.info"}, result=result)


def _screenshot_phase(name: str, result: InformativeScreenshotResult) -> TitleFlowPhase:
    return TitleFlowPhase(
        name=f"screenshot-{name}",
        action={"method": "capture_informative_screenshot"},
        result={"ok": result.ok, "reason": result.reason},
        screenshot=result.to_dict(),
    )


def _observe_until_changed(
    bridge_request: BridgeRequest,
    *,
    reference: InformativeScreenshotResult,
    label: str,
    phase_prefix: str,
    max_change_attempts: int,
    change_advance_frames: int,
    visual_max_attempts: int,
    visual_advance_frames: int,
) -> tuple[InformativeScreenshotResult, list[TitleFlowPhase]]:
    phases: list[TitleFlowPhase] = []
    latest: InformativeScreenshotResult | None = None
    for attempt in range(1, max_change_attempts + 1):
        phases.append(_advance_phase(bridge_request, f"{phase_prefix}-smart-advance-{attempt}", change_advance_frames))
        latest = capture_informative_screenshot(
            bridge_request,
            label=f"{label}-change-{attempt}",
            max_attempts=visual_max_attempts,
            advance_frames=visual_advance_frames,
        )
        phases.append(_screenshot_phase(f"{phase_prefix}-smart-{attempt}", latest))
        if _screens_changed(reference, latest):
            return latest, phases
    if latest is None:
        latest = reference
    return latest, phases


def _observe_until_not_boot(
    bridge_request: BridgeRequest,
    *,
    reference: InformativeScreenshotResult,
    label: str,
    phase_prefix: str,
    max_change_attempts: int,
    change_advance_frames: int,
    visual_max_attempts: int,
    visual_advance_frames: int,
) -> tuple[InformativeScreenshotResult, list[TitleFlowPhase]]:
    phases: list[TitleFlowPhase] = []
    latest: InformativeScreenshotResult | None = None
    for attempt in range(1, max_change_attempts + 1):
        phases.append(_advance_phase(bridge_request, f"{phase_prefix}-smart-advance-{attempt}", change_advance_frames))
        latest = capture_informative_screenshot(
            bridge_request,
            label=f"{label}-settle-{attempt}",
            max_attempts=visual_max_attempts,
            advance_frames=visual_advance_frames,
        )
        phases.append(_screenshot_phase(f"{phase_prefix}-smart-{attempt}", latest))
        changed = _screens_changed(reference, latest)
        no_longer_boot = _latest_type(latest) not in {"blank-white", "blank-black", "boot-or-logo"}
        if changed and no_longer_boot:
            return latest, phases
    if latest is None:
        latest = reference
    return latest, phases


def _screens_changed(before: InformativeScreenshotResult, after: InformativeScreenshotResult) -> bool:
    if not before.ok or not after.ok or not before.attempts or not after.attempts:
        return False
    return compare_screenshots(Path(before.attempts[-1].path), Path(after.attempts[-1].path)).changed_enough


def _latest_type(result: InformativeScreenshotResult) -> str:
    if not result.ok or not result.attempts:
        return "unknown"
    return classify_screenshot(Path(result.attempts[-1].path)).screen_type


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
