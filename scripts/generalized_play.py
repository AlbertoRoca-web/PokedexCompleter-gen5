from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from pokedex_completer_gen5.agents.providers.openai_vision_provider import OpenAIVisionPlannerProvider
from pokedex_completer_gen5.autonomy.gameplay_agent import GeneralizedGameplayAgent, VisionLanguageGameplayPlanner
from pokedex_completer_gen5.autonomy.http_gameplay_environment import HttpGameplayEnvironment

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "generalized-play"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run generalized closed-loop visual gameplay.")
    parser.add_argument("objective", help="Concrete gameplay objective, e.g. 'go downstairs'.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--movement-press-frames", type=int, default=12)
    parser.add_argument("--button-press-frames", type=int, default=4)
    parser.add_argument("--settle-frames", type=int, default=90)
    parser.add_argument("--observe-only", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180)
    environment = HttpGameplayEnvironment(
        client,
        movement_press_frames=args.movement_press_frames,
        button_press_frames=args.button_press_frames,
        settle_frames=args.settle_frames,
    )
    ready = environment.ensure_ready()
    if ready.get("ok") is not True:
        print(json.dumps({"ok": False, "stage": "ensure-ready", "response": ready}, indent=2))
        return 1

    if args.observe_only:
        observation = environment.observe(
            step=0,
            objective=args.objective,
            recent_actions=(),
            repeated_frame_count=0,
        )
        print(json.dumps({"ok": True, "observation": observation.to_prompt_payload()}, indent=2))
        return 0

    planner = VisionLanguageGameplayPlanner(OpenAIVisionPlannerProvider(model=args.model))
    agent = GeneralizedGameplayAgent(
        environment,
        planner,
        checkpoint_every=args.checkpoint_every,
    )
    result = agent.run(args.objective, max_steps=args.max_steps)
    payload = result.to_dict()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-run.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output_path": str(output_path), **payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
