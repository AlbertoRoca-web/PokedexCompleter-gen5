from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

GameplayAction = str
ALLOWED_ACTIONS = frozenset({"Up", "Down", "Left", "Right", "A", "B", "X", "Y", "Start", "Select", "L", "R"})

LIVING_DEX_PROTOCOL = """This is a fully completed Pokemon White save. The sole mission is the physical Living Dex.
Allowed subgoals are only navigation required for a Dex task, mandatory dialogue dismissal,
party/PC inventory inspection, Fly capability, route discovery, wild encounters, catching,
Pokemon Center recovery, evolution, breeding, and required travel between those operations.
Do not pursue story progression, optional NPC errands, item collection, trainer cleanup, badges,
achievements, shiny hunting, or any other side objective. Treat non-Dex activity as noise unless
it is an unavoidable gate for the current Dex operation. The PC and party physical inventory
are the source of truth, not Pokédex flags. Never use a Master Ball. Never use a Safari Ball
outside a legitimate Safari Zone encounter; Pokemon White has no valid Safari Zone context.
Every captured Pokemon must preserve a legal species, encounter, origin-game, and ball combination
that PKHeX accepts and that remains compatible with Pokemon HOME. After every verified capture,
finish catch registration, save the game, wait for save completion, refresh the master physical
inventory, recompute route targets, and only then resume the encounter loop.
"""


@dataclass(frozen=True)
class GameplayObservation:
    step: int
    screenshot_path: Path
    screenshot_sha256: str
    semantic_state: dict[str, Any]
    recent_actions: tuple[GameplayAction, ...] = ()
    repeated_frame_count: int = 0
    objective: str = ""

    @property
    def stuck(self) -> bool:
        return self.repeated_frame_count >= 2

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "screenshot_path": str(self.screenshot_path),
            "screenshot_sha256": self.screenshot_sha256,
            "semantic_state": self.semantic_state,
            "recent_actions": list(self.recent_actions[-12:]),
            "repeated_frame_count": self.repeated_frame_count,
            "stuck": self.stuck,
            "objective": self.objective,
            "mission_protocol": LIVING_DEX_PROTOCOL,
        }


@dataclass(frozen=True)
class GameplayPlan:
    goal: str
    actions: tuple[GameplayAction, ...]
    rationale: str
    expected_visual_change: str = ""
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if not self.actions:
            raise ValueError("Gameplay plan needs at least one action.")
        if len(self.actions) > 8:
            raise ValueError("Gameplay plans are bounded to at most 8 actions.")
        unknown = [action for action in self.actions if action not in ALLOWED_ACTIONS]
        if unknown:
            raise ValueError(f"Unsupported gameplay actions: {unknown}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "actions": list(self.actions),
            "rationale": self.rationale,
            "expected_visual_change": self.expected_visual_change,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class GameplayTransition:
    before: GameplayObservation
    action: GameplayAction
    after: GameplayObservation
    plan: GameplayPlan
    changed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.before.step,
            "action": self.action,
            "changed": self.changed,
            "before": self.before.to_prompt_payload(),
            "after": self.after.to_prompt_payload(),
            "plan": self.plan.to_dict(),
        }


@dataclass(frozen=True)
class GameplayRun:
    status: str
    objective: str
    transitions: tuple[GameplayTransition, ...]
    final_observation: GameplayObservation

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "objective": self.objective,
            "transitions": [transition.to_dict() for transition in self.transitions],
            "final_observation": self.final_observation.to_prompt_payload(),
        }


class GameplayEnvironment(Protocol):
    def observe(
        self,
        *,
        step: int,
        objective: str,
        recent_actions: tuple[GameplayAction, ...],
        repeated_frame_count: int,
    ) -> GameplayObservation: ...

    def act(self, action: GameplayAction) -> None: ...

    def checkpoint(self, name: str) -> dict[str, Any]: ...


class GameplayPlanner(Protocol):
    def plan(self, observation: GameplayObservation) -> GameplayPlan: ...

    def objective_complete(self, observation: GameplayObservation) -> bool: ...


@dataclass
class GeneralizedGameplayAgent:
    environment: GameplayEnvironment
    planner: GameplayPlanner
    checkpoint_every: int = 20
    action_history_limit: int = 24
    _recent_actions: list[GameplayAction] = field(default_factory=list, init=False)

    def run(self, objective: str, *, max_steps: int = 200) -> GameplayRun:
        repeated_frame_count = 0
        observation = self.environment.observe(
            step=0,
            objective=objective,
            recent_actions=(),
            repeated_frame_count=0,
        )
        transitions: list[GameplayTransition] = []
        for step in range(1, max_steps + 1):
            if self.planner.objective_complete(observation):
                return GameplayRun("objective-complete", objective, tuple(transitions), observation)
            plan = self.planner.plan(observation)
            # Closed loop by design: execute one action, then re-observe and re-plan.
            action = plan.actions[0]
            self.environment.act(action)
            self._recent_actions.append(action)
            self._recent_actions = self._recent_actions[-self.action_history_limit :]
            after = self.environment.observe(
                step=step,
                objective=objective,
                recent_actions=tuple(self._recent_actions),
                repeated_frame_count=repeated_frame_count,
            )
            changed = after.screenshot_sha256 != observation.screenshot_sha256
            repeated_frame_count = 0 if changed else repeated_frame_count + 1
            if after.repeated_frame_count != repeated_frame_count:
                after = GameplayObservation(
                    step=after.step,
                    screenshot_path=after.screenshot_path,
                    screenshot_sha256=after.screenshot_sha256,
                    semantic_state=after.semantic_state,
                    recent_actions=after.recent_actions,
                    repeated_frame_count=repeated_frame_count,
                    objective=after.objective,
                )
            transitions.append(GameplayTransition(observation, action, after, plan, changed))
            observation = after
            if self.checkpoint_every > 0 and step % self.checkpoint_every == 0:
                self.environment.checkpoint(f"generalized-step-{step:05d}")
        return GameplayRun("step-budget-exhausted", objective, tuple(transitions), observation)


class VisionLanguagePlannerProvider(Protocol):
    name: str

    def complete_with_image(self, prompt: str, image_path: Path) -> str: ...


@dataclass(frozen=True)
class VisionLanguageGameplayPlanner:
    provider: VisionLanguagePlannerProvider
    objective_verifier: Any | None = None

    def plan(self, observation: GameplayObservation) -> GameplayPlan:
        prompt = build_gameplay_prompt(observation)
        raw_response = self.provider.complete_with_image(prompt, observation.screenshot_path)
        return parse_gameplay_plan(raw_response)

    def objective_complete(self, observation: GameplayObservation) -> bool:
        if self.objective_verifier is None:
            return False
        return bool(self.objective_verifier(observation))


def build_gameplay_prompt(observation: GameplayObservation) -> str:
    payload = observation.to_prompt_payload()
    return (
        "You control Pokemon White through bounded controller inputs.\n"
        f"{LIVING_DEX_PROTOCOL}\n"
        "Inspect the attached emulator screenshot and return strict JSON only.\n"
        "Choose a short plan, but only the first action will execute before re-observation.\n"
        "Correct overshoot and blocked movement using recent actions and repeated_frame_count.\n"
        "Never choose New Game or destructive save actions.\n"
        "Allowed actions: Up, Down, Left, Right, A, B, X, Y, Start, Select, L, R.\n"
        "Schema: {goal: string, actions: string[1..8], rationale: string, "
        "expected_visual_change: string, confidence: number}.\n"
        f"Observation:\n{json.dumps(payload, indent=2, sort_keys=True)}"
    )


def parse_gameplay_plan(raw_response: str) -> GameplayPlan:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("Gameplay planner returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Gameplay planner response must be an object.")
    raw_actions = payload.get("actions")
    if not isinstance(raw_actions, list) or not all(isinstance(action, str) for action in raw_actions):
        raise ValueError("Gameplay planner response needs a string actions list.")
    confidence = payload.get("confidence", 0.5)
    if not isinstance(confidence, int | float):
        confidence = 0.5
    return GameplayPlan(
        goal=_required_string(payload, "goal"),
        actions=tuple(raw_actions),
        rationale=_required_string(payload, "rationale"),
        expected_visual_change=_optional_string(payload.get("expected_visual_change")),
        confidence=max(0.0, min(1.0, float(confidence))),
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Gameplay planner response missing string field: {key}")
    return value


def _optional_string(value: Any) -> str:
    return value if isinstance(value, str) else ""
