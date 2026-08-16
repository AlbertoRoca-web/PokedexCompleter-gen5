from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from pokedex_completer_gen5.events import event_bus
from pokedex_completer_gen5.persistence.store import persist_event
from pokedex_completer_gen5.trajectory import append_jsonl_event


@dataclass(frozen=True)
class TelemetryEvent:
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


_events: deque[TelemetryEvent] = deque(maxlen=500)
_event_sinks_registered = False


def _ensure_event_sinks() -> None:
    global _event_sinks_registered
    if _event_sinks_registered:
        return
    event_bus().subscribe(append_jsonl_event)
    event_bus().subscribe(persist_event)
    _event_sinks_registered = True


def record_telemetry_event(event_type: str, payload: dict[str, Any] | None = None) -> TelemetryEvent:
    _ensure_event_sinks()
    event = TelemetryEvent(event_type=event_type, payload=payload or {})
    _events.append(event)
    event_bus().publish(event.event_type, event.payload)
    return event


def recent_telemetry_events(limit: int = 50) -> list[dict[str, Any]]:
    return [event.to_dict() for event in list(_events)[-limit:]]


async def telemetry_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    last_seen = 0
    while True:
        events = recent_telemetry_events(limit=100)
        if len(events) != last_seen:
            await websocket.send_json({"type": "telemetry", "events": events})
            last_seen = len(events)
        await asyncio.sleep(1)
