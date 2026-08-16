from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from pokedex_completer_gen5.dex.pc_living_dex import build_pc_living_dex_report
from pokedex_completer_gen5.events import DomainEvent, event_bus
from pokedex_completer_gen5.persistence.database import init_database
from pokedex_completer_gen5.saveio.gen5_save import build_save_payload
from pokedex_completer_gen5.trajectory import append_jsonl_event


@dataclass(frozen=True)
class AutonomyBudget:
    max_iterations: int = 1
    max_seconds: int = 60
    token_budget: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "max_seconds": self.max_seconds,
            "token_budget": self.token_budget,
        }


@dataclass(frozen=True)
class AutonomyConfig:
    game: str = "white"
    scope: str = "regional"
    target_policy: str = "game-regional"
    save_path: Path | None = None
    dry_run: bool = True
    budget: AutonomyBudget = field(default_factory=AutonomyBudget)

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game,
            "scope": self.scope,
            "target_policy": self.target_policy,
            "save_path": str(self.save_path) if self.save_path else None,
            "dry_run": self.dry_run,
            "budget": self.budget.to_dict(),
        }


@dataclass(frozen=True)
class AutonomyStep:
    iteration: int
    phase: str
    decision: str
    rationale: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "phase": self.phase,
            "decision": self.decision,
            "rationale": self.rationale,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class AutonomyRunResult:
    run_id: str
    status: str
    config: AutonomyConfig
    steps: list[AutonomyStep]
    events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "config": self.config.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "events": self.events,
        }


class AutonomySupervisor:
    def __init__(self, config: AutonomyConfig) -> None:
        self.config = config
        self.run_id = str(uuid4())
        self.steps: list[AutonomyStep] = []
        self.events: list[dict[str, Any]] = []
        self._event_sink_registered = False

    def run(self) -> AutonomyRunResult:
        init_database()
        self._ensure_event_sink()
        started = time.monotonic()
        self._publish("autonomy.run_started", {"run_id": self.run_id, "config": self.config.to_dict()})

        status = "completed-budget"
        for iteration in range(1, self.config.budget.max_iterations + 1):
            if time.monotonic() - started >= self.config.budget.max_seconds:
                status = "stopped-time-budget"
                break
            step = self._run_iteration(iteration)
            self.steps.append(step)
            self._publish("autonomy.step", {"run_id": self.run_id, "step": step.to_dict()})
            if step.decision == "stop-complete":
                status = "completed-dex"
                break
            if self.config.dry_run:
                status = "stopped-dry-run"
                break

        self._publish("autonomy.run_finished", {"run_id": self.run_id, "status": status})
        return AutonomyRunResult(
            run_id=self.run_id,
            status=status,
            config=self.config,
            steps=self.steps,
            events=self.events,
        )

    def _run_iteration(self, iteration: int) -> AutonomyStep:
        observation = self._observe()
        decision, rationale = _choose_next_bridge_gap(observation)
        return AutonomyStep(
            iteration=iteration,
            phase="observe-plan",
            decision=decision,
            rationale=rationale,
            payload={"observation": observation},
        )

    def _observe(self) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "capabilities": {
                "save_parser": True,
                "bizhawk_bridge": True,
                "visual_title_resume": True,
                "memory_read": True,
                "semantic_state": False,
                "navigation_primitives": False,
                "encounter_detection": False,
                "capture_loop": False,
                "pc_box_automation": False,
            }
        }
        if self.config.save_path is None:
            observation["living_dex"] = {"available": False, "reason": "no save path supplied"}
            return observation
        payload = build_save_payload(self.config.save_path, self.config.game, "auto")
        report = build_pc_living_dex_report(
            payload,
            self.config.game,
            scope=self.config.scope,
            include_party=True,
            target_policy=self.config.target_policy,
        ).to_dict()
        missing = report.get("missing")
        observation["living_dex"] = {
            "available": True,
            "missing_count": len(missing) if isinstance(missing, list) else None,
            "report": report,
        }
        return observation

    def _ensure_event_sink(self) -> None:
        if self._event_sink_registered:
            return
        event_bus().subscribe(append_jsonl_event)
        self._event_sink_registered = True

    def _publish(self, event_type: str, payload: dict[str, Any]) -> DomainEvent:
        event = event_bus().publish(event_type, payload)
        self.events.append(event.to_dict())
        return event


def run_autonomy(config: AutonomyConfig) -> AutonomyRunResult:
    return AutonomySupervisor(config).run()


def _choose_next_bridge_gap(observation: dict[str, Any]) -> tuple[str, str]:
    living_dex = observation.get("living_dex", {})
    if isinstance(living_dex, dict) and living_dex.get("missing_count") == 0:
        return "stop-complete", "Living Dex report has zero missing targets."

    capabilities = observation.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return "needs-human", "Capability observation was malformed."
    ordered_gaps = [
        ("discover-semantic-state", "Need RAM-backed overworld/menu/battle/map/player state before safe navigation."),
        ("build-navigation-primitives", "Need validated movement/menu primitives before route execution."),
        ("build-encounter-detection", "Need battle/species detection before catch loops."),
        ("build-capture-loop", "Need deterministic catch workflow before grinding missing targets."),
        ("build-pc-box-automation", "Need PC verification/deposit workflow for durable Living Dex completion."),
    ]
    capability_key_by_decision = {
        "discover-semantic-state": "semantic_state",
        "build-navigation-primitives": "navigation_primitives",
        "build-encounter-detection": "encounter_detection",
        "build-capture-loop": "capture_loop",
        "build-pc-box-automation": "pc_box_automation",
    }
    for decision, rationale in ordered_gaps:
        key = capability_key_by_decision[decision]
        if capabilities.get(key) is not True:
            return decision, rationale
    return "plan-next-target", "Core automation capabilities exist; ready to plan the next missing Pokémon target."
