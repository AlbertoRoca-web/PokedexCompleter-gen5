from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokedex_completer_gen5.ai.router import PlanningTask, choose_model


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    task: PlanningTask
    expected_invariants: tuple[str, ...]
    payload: dict[str, Any]

    @classmethod
    def from_path(cls, path: Path) -> BenchmarkCase:
        data = json.loads(path.read_text(encoding="utf-8"))
        task_payload = data.get("task", {})
        return cls(
            name=str(data.get("name", path.stem)),
            task=PlanningTask(
                kind=str(task_payload.get("kind", "planning")),  # type: ignore[arg-type]
                complexity=int(task_payload.get("complexity", 1)),
                failures=int(task_payload.get("failures", 0)),
                can_be_solved_deterministically=bool(task_payload.get("can_be_solved_deterministically", False)),
            ),
            expected_invariants=tuple(str(item) for item in data.get("expected_invariants", [])),
            payload=dict(data.get("payload", {})),
        )


def load_benchmark_cases(directory: Path) -> list[BenchmarkCase]:
    if not directory.exists():
        return []
    return [BenchmarkCase.from_path(path) for path in sorted(directory.glob("*.json"))]


def dry_run_model_routing(directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "case": case.name,
            "selected_model": choose_model(case.task),
            "expected_invariants": list(case.expected_invariants),
        }
        for case in load_benchmark_cases(directory)
    ]
