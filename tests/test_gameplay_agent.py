from __future__ import annotations

from pathlib import Path

from pokedex_completer_gen5.autonomy.gameplay_agent import (
    GameplayObservation,
    GameplayPlan,
    GeneralizedGameplayAgent,
    build_gameplay_prompt,
    parse_gameplay_plan,
)


class FakeEnvironment:
    def __init__(self, hashes: list[str]) -> None:
        self.hashes = hashes
        self.observations = 0
        self.actions: list[str] = []
        self.checkpoints: list[str] = []

    def observe(
        self,
        *,
        step: int,
        objective: str,
        recent_actions: tuple[str, ...],
        repeated_frame_count: int,
    ) -> GameplayObservation:
        screenshot_hash = self.hashes[min(self.observations, len(self.hashes) - 1)]
        self.observations += 1
        return GameplayObservation(
            step=step,
            screenshot_path=Path(f"screen-{step}.png"),
            screenshot_sha256=screenshot_hash,
            semantic_state={},
            recent_actions=recent_actions,
            repeated_frame_count=repeated_frame_count,
            objective=objective,
        )

    def act(self, action: str) -> None:
        self.actions.append(action)

    def checkpoint(self, name: str) -> dict[str, object]:
        self.checkpoints.append(name)
        return {"ok": True, "name": name}


class FakePlanner:
    def __init__(self) -> None:
        self.observations: list[GameplayObservation] = []

    def plan(self, observation: GameplayObservation) -> GameplayPlan:
        self.observations.append(observation)
        action = "Left" if observation.stuck else "Right"
        return GameplayPlan("move", (action, "Up"), "correct from fresh observation")

    def objective_complete(self, observation: GameplayObservation) -> bool:
        return observation.step >= 3


def test_generalized_agent_reobserves_after_every_single_action() -> None:
    environment = FakeEnvironment(["a", "b", "c", "d"])
    planner = FakePlanner()
    agent = GeneralizedGameplayAgent(environment, planner, checkpoint_every=2)

    result = agent.run("reach stairs", max_steps=10)

    assert result.status == "objective-complete"
    assert environment.actions == ["Right", "Right", "Right"]
    assert environment.observations == 4
    assert environment.checkpoints == ["generalized-step-00002"]
    assert len(planner.observations) == 3


def test_generalized_agent_reports_stuck_state_to_planner() -> None:
    environment = FakeEnvironment(["same", "same", "same", "changed"])
    planner = FakePlanner()
    agent = GeneralizedGameplayAgent(environment, planner, checkpoint_every=0)

    result = agent.run("escape obstacle", max_steps=3)

    assert result.transitions[0].after.repeated_frame_count == 1
    assert result.transitions[1].after.repeated_frame_count == 2
    assert planner.observations[2].stuck is True
    assert environment.actions == ["Right", "Right", "Left"]


def test_parse_gameplay_plan_validates_and_bounds_actions() -> None:
    plan = parse_gameplay_plan(
        '{"goal":"stairs","actions":["Right","Up"],"rationale":"visible path","confidence":1.5}'
    )

    assert plan.actions == ("Right", "Up")
    assert plan.confidence == 1.0


def test_gameplay_prompt_contains_closed_loop_context() -> None:
    observation = GameplayObservation(
        step=4,
        screenshot_path=Path("screen.png"),
        screenshot_sha256="abc",
        semantic_state={"mode": "overworld"},
        recent_actions=("Right", "Right"),
        repeated_frame_count=2,
        objective="reach stairs",
    )

    prompt = build_gameplay_prompt(observation)

    assert "only the first action will execute" in prompt
    assert '"stuck": true' in prompt
    assert "reach stairs" in prompt
    assert "sole mission is the physical Living Dex" in prompt
    assert "Do not pursue story progression" in prompt
