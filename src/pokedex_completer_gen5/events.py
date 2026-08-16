from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "event_type": self.event_type,
            "payload": self.payload,
        }


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._lock = RLock()

    def subscribe(self, handler: EventHandler) -> None:
        with self._lock:
            self._handlers.append(handler)

    def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> DomainEvent:
        event = DomainEvent(event_type=event_type, payload=payload or {})
        with self._lock:
            handlers = tuple(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # Event subscribers are side effects (logs, persistence, commentary).
                # They must not break emulator control flow. Bad subscriber, no biscuit.
                continue
        return event


_default_bus = EventBus()


def event_bus() -> EventBus:
    return _default_bus
