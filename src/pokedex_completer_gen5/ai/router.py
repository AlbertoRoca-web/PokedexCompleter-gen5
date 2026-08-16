from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pokedex_completer_gen5.settings import AISettings, get_settings

PlanningTaskKind = Literal[
    "deterministic",
    "classification",
    "small_ranking",
    "failure_label",
    "bounded_planning",
    "planning",
    "recovery",
]


@dataclass(frozen=True)
class PlanningTask:
    kind: PlanningTaskKind
    complexity: int = 1
    failures: int = 0
    can_be_solved_deterministically: bool = False


def choose_model(task: PlanningTask, settings: AISettings | None = None) -> str | None:
    config = settings or get_settings().ai
    if config.profile == "offline" or task.can_be_solved_deterministically or task.kind == "deterministic":
        return None
    if task.kind in {"classification", "small_ranking", "failure_label"}:
        return config.model_classifier
    if task.kind == "bounded_planning" or task.complexity <= 2:
        return config.model_bounded_planner
    if task.failures == 0 and task.kind == "planning":
        return config.model_planner
    if task.failures <= 2 or task.kind == "recovery":
        return config.model_recovery
    return config.model_hard


def router_payload() -> dict[str, str | None]:
    config = get_settings().ai
    return {
        "profile": config.profile,
        "deterministic": None,
        "classifier": config.model_classifier,
        "bounded_planner": config.model_bounded_planner,
        "planner": config.model_planner,
        "recovery": config.model_recovery,
        "hard": config.model_hard,
    }
