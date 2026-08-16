from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PlannerTask:
    priority: int
    task_type: str
    title: str
    rationale: str
    species_id: int | None = None
    species_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "task_type": self.task_type,
            "title": self.title,
            "rationale": self.rationale,
            "species_id": self.species_id,
            "species_name": self.species_name,
        }


@dataclass(frozen=True)
class PlannerResult:
    provider: str
    summary: str
    tasks: tuple[PlannerTask, ...]
    raw_response: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "summary": self.summary,
            "tasks": [task.to_dict() for task in self.tasks],
            "raw_response": self.raw_response,
        }


class PlannerProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str:
        """Return a model response as text."""
        ...


SYSTEM_RULES = """You are planning a Pokemon Generation 5 regional Living Dex completion route.
Rules:
- This is a Living Dex: one physical Pokemon body per required species/stage.
- Save-file extraction is the source of truth.
- Prefer deterministic, verifiable tasks over vague advice.
- Do not claim the player owns Pokemon that are not in the report.
- For Black 2 / White 2, do not use Black / White regional dex data.
- Return strict JSON only. No markdown.
"""


def build_planner_prompt(report_payload: dict[str, Any], max_missing: int = 40) -> str:
    compact = compact_report_for_planner(report_payload, max_missing=max_missing)
    return SYSTEM_RULES + "\nReport payload:\n" + json.dumps(compact, indent=2, sort_keys=True)


def compact_report_for_planner(report_payload: dict[str, Any], max_missing: int = 40) -> dict[str, Any]:
    dex_status = report_payload.get("dex_status")
    if not isinstance(dex_status, dict):
        dex_status = {}

    missing = dex_status.get("missing")
    if not isinstance(missing, list):
        missing = []

    return {
        "game_profile": report_payload.get("game_profile"),
        "regional_dex_key": report_payload.get("regional_dex_key"),
        "planner_supported": report_payload.get("planner_supported"),
        "selected_species_counts": report_payload.get("selected_species_counts", []),
        "unique_species_owned": dex_status.get("unique_species_owned"),
        "missing_species_count": dex_status.get("missing_species_count"),
        "missing_preview": missing[:max_missing],
        "expected_response_schema": {
            "summary": "short plain-English summary",
            "tasks": [
                {
                    "priority": 10,
                    "task_type": "catch|breed|evolve|trade|legendary|event|setup",
                    "title": "specific action",
                    "rationale": "why this helps",
                    "species_id": 506,
                    "species_name": "Lillipup",
                }
            ],
        },
    }


def plan_next_tasks(report_payload: dict[str, Any], provider: PlannerProvider) -> PlannerResult:
    prompt = build_planner_prompt(report_payload)
    raw_response = provider.complete(prompt)
    parsed = parse_planner_response(raw_response)
    return PlannerResult(
        provider=provider.name,
        summary=parsed["summary"],
        tasks=tuple(parsed["tasks"]),
        raw_response=raw_response,
    )


def parse_planner_response(raw_response: str) -> dict[str, Any]:
    try:
        decoded = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("Planner provider returned invalid JSON") from exc

    if not isinstance(decoded, dict):
        raise ValueError("Planner response must be a JSON object")

    summary = decoded.get("summary")
    if not isinstance(summary, str):
        raise ValueError("Planner response missing string field: summary")

    raw_tasks = decoded.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("Planner response missing list field: tasks")

    tasks = tuple(parse_task(task) for task in raw_tasks)
    return {"summary": summary, "tasks": tasks}


def parse_task(raw_task: Any) -> PlannerTask:
    if not isinstance(raw_task, dict):
        raise ValueError("Planner task must be an object")

    return PlannerTask(
        priority=_int_or_default(raw_task.get("priority"), 100),
        task_type=_str_or_default(raw_task.get("task_type"), "setup"),
        title=_str_or_default(raw_task.get("title"), "Review planner output"),
        rationale=_str_or_default(raw_task.get("rationale"), "No rationale provided."),
        species_id=_optional_int(raw_task.get("species_id")),
        species_name=raw_task.get("species_name") if isinstance(raw_task.get("species_name"), str) else None,
    )


def _int_or_default(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _str_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default
