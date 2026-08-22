from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProtocolStep:
    operation: str
    verification: str

    def to_dict(self) -> dict[str, str]:
        return {"operation": self.operation, "verification": self.verification}


def post_capture_save_protocol() -> dict[str, Any]:
    steps = (
        ProtocolStep("verify-gotcha-message", "Screenshot names the captured target."),
        ProtocolStep("decline-nickname", "Canonical species name is retained."),
        ProtocolStep("wait-for-overworld", "Battle/catch UI is fully closed."),
        ProtocolStep("open-menu", "Menu is visible; keyboard S maps to DS X."),
        ProtocolStep("select-save", "SAVE entry is visibly selected."),
        ProtocolStep("confirm-save", "Save confirmation is accepted."),
        ProtocolStep("wait-save-complete", "Save completion message or overworld return is visible."),
        ProtocolStep("refresh-master-inventory", "Party/PC/save and session catches are reconciled."),
        ProtocolStep("recompute-route-targets", "Owned species are removed from catch targets."),
        ProtocolStep("resume-route-loop", "Overworld lane resumes with refreshed target policy."),
    )
    return {
        "mandatory": True,
        "save_after_every_capture": True,
        "steps": [step.to_dict() for step in steps],
    }
