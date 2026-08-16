from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from PIL import Image, ImageStat

from pokedex_completer_gen5.emulator.controls import normalize_button_or_action
from pokedex_completer_gen5.emulator.screen_classifier import classify_screenshot, compare_screenshots
from pokedex_completer_gen5.emulator.semantic_state import build_semantic_state
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
    wait_after_cgear_prompt_frames: int = 180,
    wait_after_cgear_confirm_frames: int = 600,
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

    before_type = _latest_type(before)
    after_start = before
    if before_type != "menu-like":
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
    else:
        phases.append(
            TitleFlowPhase(
                name="skip-start-already-menu-like",
                action={"method": "classify_screenshot"},
                result={"ok": True, "screen_type": before_type},
            )
        )

    after_continue, continue_phases = _press_until_changed(
        bridge_request,
        reference=after_start,
        label=f"title-flow-{flow_id}-after-continue",
        phase_prefix="confirm-continue",
        action="confirm",
        press_frames=press_frames,
        wait_frames=wait_after_continue_frames,
        max_change_attempts=change_max_attempts,
        visual_max_attempts=visual_max_attempts,
        visual_advance_frames=visual_advance_frames,
    )
    phases.extend(continue_phases)
    phases.append(_press_phase(bridge_request, "cgear-prompt-select-no", "down", press_frames=press_frames))
    phases.append(_press_phase(bridge_request, "cgear-prompt-confirm-no", "confirm", press_frames=press_frames))
    phases.append(_advance_phase(bridge_request, "minimum-wait-after-cgear-no", wait_after_cgear_prompt_frames))
    phases.append(_press_phase(bridge_request, "cgear-restricted-confirm-yes", "confirm", press_frames=press_frames))
    phases.append(_advance_phase(bridge_request, "minimum-wait-after-cgear-confirm", wait_after_cgear_confirm_frames))
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
    semantic = _semantic_phase(bridge_request)
    phases.append(semantic)

    verification = _verify_title_resume(before, final, semantic.result)
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


def _semantic_phase(bridge_request: BridgeRequest) -> TitleFlowPhase:
    try:
        result = build_semantic_state(bridge_request).to_dict()
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    return TitleFlowPhase(
        name="semantic-state-final",
        action={"method": "build_semantic_state"},
        result=result,
    )


def _screenshot_phase(name: str, result: InformativeScreenshotResult) -> TitleFlowPhase:
    return TitleFlowPhase(
        name=f"screenshot-{name}",
        action={"method": "capture_informative_screenshot"},
        result={"ok": result.ok, "reason": result.reason},
        screenshot=result.to_dict(),
    )


def _press_until_changed(
    bridge_request: BridgeRequest,
    *,
    reference: InformativeScreenshotResult,
    label: str,
    phase_prefix: str,
    action: str,
    press_frames: int,
    wait_frames: int,
    max_change_attempts: int,
    visual_max_attempts: int,
    visual_advance_frames: int,
) -> tuple[InformativeScreenshotResult, list[TitleFlowPhase]]:
    phases: list[TitleFlowPhase] = []
    latest: InformativeScreenshotResult | None = None
    for attempt in range(1, max_change_attempts + 1):
        phases.append(
            _press_phase(bridge_request, f"{phase_prefix}-press-{attempt}", action, press_frames=press_frames)
        )
        phases.append(_advance_phase(bridge_request, f"{phase_prefix}-wait-{attempt}", wait_frames))
        latest = capture_informative_screenshot(
            bridge_request,
            label=f"{label}-{attempt}",
            max_attempts=visual_max_attempts,
            advance_frames=visual_advance_frames,
        )
        phases.append(_screenshot_phase(f"{phase_prefix}-after-{attempt}", latest))
        if _screens_changed(reference, latest):
            return latest, phases
    return latest or reference, phases


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


def _verify_title_resume(
    before: InformativeScreenshotResult,
    final: InformativeScreenshotResult,
    semantic: dict[str, Any],
) -> dict[str, Any]:
    if not before.ok or not final.ok or not before.attempts or not final.attempts:
        return {
            "mode": "title-resume-visual-v1",
            "status": "needs-human",
            "reason": "before or final screenshot was not informative",
            "before_ok": before.ok,
            "final_ok": final.ok,
            "semantic_state": semantic,
        }

    before_path = Path(before.attempts[-1].path)
    final_path = Path(final.attempts[-1].path)
    delta = compare_screenshots(before_path=before_path, after_path=final_path)
    before_classification = classify_screenshot(before_path)
    final_classification = classify_screenshot(final_path)
    final_type = final_classification.screen_type
    semantic_menu_open = semantic.get("state", {}).get("menu_open") if isinstance(semantic.get("state"), dict) else None
    ram_verified = semantic_menu_open is False
    visual_known_overworld = _looks_like_gen5_overworld_frame(final_path)
    visual_accepted = (
        delta.changed_enough
        and final_type not in {"blank-white", "blank-black", "boot-or-logo"}
        and visual_known_overworld
    )
    accepted = visual_accepted and ram_verified
    return {
        "mode": "title-resume-visual-v1",
        "status": "candidate-overworld" if accepted else "needs-human",
        "reason": (
            "final screen visually matches overworld and RAM menu_state is closed"
            if accepted
            else "final screen/RAM did not prove save loaded to known overworld"
        ),
        "screen_delta": delta.to_dict(),
        "visual_accepted": visual_accepted,
        "ram_verified": ram_verified,
        "visual_known_overworld": visual_known_overworld,
        "semantic_state": semantic,
        "before_classification": before_classification.to_dict(),
        "final_classification": final_classification.to_dict(),
    }


def _looks_like_gen5_overworld_frame(path: Path) -> bool:
    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        top = gray.crop((0, 0, width, height // 2))
        bottom = gray.crop((0, height // 2, width, height))
        top_mean = float(ImageStat.Stat(top).mean[0])
        bottom_mean = float(ImageStat.Stat(bottom).mean[0])
        bottom_dark_ratio = _dark_ratio(bottom, threshold=70)
    return top_mean >= 85.0 and 8.0 <= bottom_mean <= 80.0 and bottom_dark_ratio >= 0.70


def _dark_ratio(image: Image.Image, *, threshold: int) -> float:
    mask = image.point(lambda value: 255 if cast(int, value) < threshold else 0)
    return float(ImageStat.Stat(mask).mean[0] / 255)
