from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pokedex_completer_gen5.emulator.screen_classifier import classify_screenshot, compare_screenshots
from pokedex_completer_gen5.emulator.visual_wait import InformativeScreenshotResult

MacroVisualStatus = Literal["verified-success", "verified-failure", "needs-human"]


@dataclass(frozen=True)
class MacroVisualVerification:
    macro_name: str
    status: MacroVisualStatus
    before: dict[str, Any]
    after: dict[str, Any]
    screen_delta: dict[str, Any] | None
    before_classification: dict[str, Any] | None
    after_classification: dict[str, Any] | None
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "visual-macro-v1",
            "macro_name": self.macro_name,
            "status": self.status,
            "before": self.before,
            "after": self.after,
            "screen_delta": self.screen_delta,
            "before_classification": self.before_classification,
            "after_classification": self.after_classification,
            "reasons": self.reasons,
        }


def verify_macro_visual_change(
    macro_name: str,
    before: InformativeScreenshotResult,
    after: InformativeScreenshotResult,
) -> MacroVisualVerification:
    reasons: list[str] = []
    before_payload = before.to_dict()
    after_payload = after.to_dict()
    if not before.ok:
        reasons.append("before screenshot never became informative")
    if not after.ok:
        reasons.append("after screenshot never became informative")
    if not before.ok or not after.ok or before.attempts[-1:] == [] or after.attempts[-1:] == []:
        return MacroVisualVerification(
            macro_name=macro_name,
            status="needs-human",
            before=before_payload,
            after=after_payload,
            screen_delta=None,
            before_classification=None,
            after_classification=None,
            reasons=reasons,
        )

    before_path = Path(before.attempts[-1].path)
    after_path = Path(after.attempts[-1].path)
    delta = compare_screenshots(before_path, after_path)
    before_classification = classify_screenshot(before_path)
    after_classification = classify_screenshot(after_path)
    reasons.extend(delta_reason(delta.changed_enough, after_classification.screen_type))

    status = _macro_status(
        macro_name,
        delta.changed_enough,
        before_classification.screen_type,
        after_classification.screen_type,
    )
    return MacroVisualVerification(
        macro_name=macro_name,
        status=status,
        before=before_payload,
        after=after_payload,
        screen_delta=delta.to_dict(),
        before_classification=before_classification.to_dict(),
        after_classification=after_classification.to_dict(),
        reasons=reasons,
    )


def _macro_status(
    macro_name: str,
    changed_enough: bool,
    before_type: str,
    after_type: str,
) -> MacroVisualStatus:
    if not changed_enough:
        return "verified-failure"
    if macro_name == "open_menu" and after_type == "menu-like":
        return "verified-success"
    if macro_name == "close_menu" and before_type == "menu-like" and after_type != "menu-like":
        return "verified-success"
    # Changed screen is promising, but primitive classifier cannot prove menu semantics yet.
    return "needs-human"


def delta_reason(changed_enough: bool, after_type: str) -> list[str]:
    reasons = ["screen changed enough" if changed_enough else "screen did not change enough"]
    reasons.append(f"after classified as {after_type}")
    return reasons
