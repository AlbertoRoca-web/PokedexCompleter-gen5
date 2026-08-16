from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

ValidatorStatus = Literal["pending", "accepted", "rejected", "needs-human"]

VALIDATOR_EVENT_TYPES = (
    "voice_commentary",
    "rare_encounter_claim",
    "target_found_claim",
    "route_progress",
    "capture_attempt",
    "living_dex_progress",
    "stuck_claim",
    "macro_visual_verification",
    "screenshot_visual_verification",
)


@dataclass(frozen=True)
class ValidatorEvent:
    event_type: str
    message: str
    payload: dict[str, Any]
    status: ValidatorStatus = "pending"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "event_type": self.event_type,
            "message": self.message,
            "payload": self.payload,
            "status": self.status,
        }


def build_validator_event(
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
    status: ValidatorStatus = "pending",
) -> ValidatorEvent:
    if event_type not in VALIDATOR_EVENT_TYPES:
        raise ValueError(f"Unsupported validator event type: {event_type}")
    return ValidatorEvent(
        event_type=event_type,
        message=message,
        payload=payload or {},
        status=status,
    )
