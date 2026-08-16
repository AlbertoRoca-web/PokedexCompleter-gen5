from __future__ import annotations

import json
from threading import RLock
from typing import Any

from pokedex_completer_gen5.events import DomainEvent
from pokedex_completer_gen5.runtime import ensure_runtime_dirs

_lock = RLock()


def append_jsonl_event(event: DomainEvent) -> None:
    paths = ensure_runtime_dirs()
    log_path = paths.logs / "events.jsonl"
    line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
    with _lock, log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_jsonl_events(limit: int = 100) -> list[dict[str, Any]]:
    paths = ensure_runtime_dirs()
    log_path = paths.logs / "events.jsonl"
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()[-limit:]
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events
