from __future__ import annotations

from collections import deque
from typing import Any

from pokedex_completer_gen5.agents.validator import ValidatorEvent, ValidatorStatus, build_validator_event

_events: deque[ValidatorEvent] = deque(maxlen=500)


def record_validator_event(
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
    status: ValidatorStatus = "pending",
) -> ValidatorEvent:
    event = build_validator_event(event_type, message, payload=payload, status=status)
    _events.append(event)
    return event


def recent_validator_events(limit: int = 50) -> list[dict[str, Any]]:
    return [event.to_dict() for event in list(_events)[-limit:]]
