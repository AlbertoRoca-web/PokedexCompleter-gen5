from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

MacroFeedbackOutcome = Literal["success", "failure", "uncertain"]


@dataclass(frozen=True)
class MacroFeedback:
    macro_run_id: str
    outcome: MacroFeedbackOutcome
    notes: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "macro_run_id": self.macro_run_id,
            "outcome": self.outcome,
            "notes": self.notes,
            "payload": self.payload,
        }


_feedback: deque[MacroFeedback] = deque(maxlen=500)


def record_macro_feedback(
    macro_run_id: str,
    outcome: MacroFeedbackOutcome,
    notes: str = "",
    payload: dict[str, Any] | None = None,
) -> MacroFeedback:
    feedback = MacroFeedback(macro_run_id=macro_run_id, outcome=outcome, notes=notes, payload=payload or {})
    _feedback.append(feedback)
    return feedback


def recent_macro_feedback(limit: int = 50) -> list[dict[str, Any]]:
    return [item.to_dict() for item in list(_feedback)[-limit:]]
