from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pokedex_completer_gen5.events import DomainEvent
from pokedex_completer_gen5.persistence.database import session_scope
from pokedex_completer_gen5.persistence.models import (
    ArtifactRecord,
    EventRecord,
    MacroAttemptRecord,
    MacroFeedbackRecord,
)


def persist_event(event: DomainEvent) -> None:
    with session_scope() as session:
        session.merge(
            EventRecord(
                id=event.id,
                event_type=event.event_type,
                payload=event.payload,
                created_at=datetime.fromisoformat(event.created_at),
            )
        )


def persist_macro_attempt(run_payload: dict[str, Any], run_id: str | None = None) -> None:
    with session_scope() as session:
        session.merge(
            MacroAttemptRecord(
                id=str(run_payload["id"]),
                run_id=run_id,
                macro_name=str(run_payload["macro_name"]),
                status=str(run_payload["status"]),
                expected_result=str(run_payload.get("expected_result", "")),
                payload=run_payload,
                created_at=datetime.fromisoformat(str(run_payload["created_at"])),
            )
        )


def persist_macro_feedback(feedback_payload: dict[str, Any]) -> None:
    with session_scope() as session:
        session.merge(
            MacroFeedbackRecord(
                id=str(feedback_payload["id"]),
                macro_run_id=str(feedback_payload["macro_run_id"]),
                outcome=str(feedback_payload["outcome"]),
                notes=str(feedback_payload.get("notes", "")),
                payload=dict(feedback_payload.get("payload", {})),
                created_at=datetime.fromisoformat(str(feedback_payload["created_at"])),
            )
        )


def persist_artifact(artifact_type: str, path: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "id": str(uuid4()),
        "artifact_type": artifact_type,
        "path": str(path),
        "exists": path.exists(),
        "sha256": None,
    }
    if path.exists() and path.is_file():
        metadata["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with session_scope() as session:
        session.add(
            ArtifactRecord(
                id=str(metadata["id"]),
                artifact_type=artifact_type,
                path=str(path),
                sha256=metadata["sha256"],
                payload=payload or {},
            )
        )
    return metadata


def macro_reliability(limit: int = 1000) -> list[dict[str, Any]]:
    with session_scope() as session:
        records = (
            session.query(MacroFeedbackRecord.macro_run_id, MacroFeedbackRecord.outcome)
            .order_by(MacroFeedbackRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    # Feedback currently stores macro_run_id, not macro_name. Until attempts are joined by run id,
    # expose honest run-level reliability instead of fake precision. Accuracy beats vibes.
    counts: Counter[str] = Counter(outcome for _, outcome in records)
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {
            "scope": "all_macros",
            "attempts": total,
            "successes": counts.get("success", 0),
            "failures": counts.get("failure", 0),
            "uncertain": counts.get("uncertain", 0),
            "success_rate": counts.get("success", 0) / total,
        }
    ]
