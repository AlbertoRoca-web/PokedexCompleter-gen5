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
    analysis: dict[str, Any] = {}
    if artifact_type == "screenshot" and path.exists() and path.is_file():
        try:
            from pokedex_completer_gen5.emulator.vision import analyze_screenshot

            analysis = analyze_screenshot(path)
        except Exception as exc:
            analysis = {"analysis_error": str(exc)}
    metadata: dict[str, Any] = {
        "id": str(uuid4()),
        "artifact_type": artifact_type,
        "path": str(path),
        "exists": path.exists(),
        "sha256": None,
        "analysis": analysis,
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
                width=analysis.get("width") if isinstance(analysis.get("width"), int) else None,
                height=analysis.get("height") if isinstance(analysis.get("height"), int) else None,
                payload={**(payload or {}), "analysis": analysis},
            )
        )
    return metadata


def list_artifacts(artifact_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with session_scope() as session:
        query = session.query(ArtifactRecord)
        if artifact_type:
            query = query.filter(ArtifactRecord.artifact_type == artifact_type)
        records = query.order_by(ArtifactRecord.created_at.desc()).limit(limit).all()
    return [_artifact_to_dict(record) for record in records]


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        record = session.get(ArtifactRecord, artifact_id)
        return _artifact_to_dict(record) if record else None


def latest_artifact_path(artifact_type: str) -> Path | None:
    artifacts = list_artifacts(artifact_type=artifact_type, limit=1)
    if not artifacts:
        return None
    return Path(str(artifacts[0]["path"]))


def macro_reliability(limit: int = 1000) -> list[dict[str, Any]]:
    with session_scope() as session:
        records = (
            session.query(MacroAttemptRecord.macro_name, MacroFeedbackRecord.outcome)
            .join(MacroFeedbackRecord, MacroFeedbackRecord.macro_run_id == MacroAttemptRecord.id)
            .order_by(MacroFeedbackRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    by_macro: dict[str, Counter[str]] = {}
    for macro_name, outcome in records:
        by_macro.setdefault(str(macro_name), Counter())[str(outcome)] += 1
    return [
        {
            "macro_name": macro_name,
            "attempts": sum(counts.values()),
            "successes": counts.get("success", 0),
            "failures": counts.get("failure", 0),
            "uncertain": counts.get("uncertain", 0),
            "success_rate": counts.get("success", 0) / sum(counts.values()),
        }
        for macro_name, counts in sorted(by_macro.items())
        if sum(counts.values()) > 0
    ]


def _artifact_to_dict(record: ArtifactRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "artifact_type": record.artifact_type,
        "path": record.path,
        "sha256": record.sha256,
        "width": record.width,
        "height": record.height,
        "payload": record.payload,
        "created_at": record.created_at.isoformat(),
    }
