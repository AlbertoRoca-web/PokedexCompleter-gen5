from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from pokedex_completer_gen5.emulator.bedroom_navigation import TilePoint, decide_bedroom_next_action, tile_after_action

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "continuous-play"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"
MOVEMENT_BUTTONS = {"Up", "Down", "Left", "Right"}
CONTROL_BUTTONS = {"A", "B", "X", "Y", "Start", "Select", "L", "R"}

PRESETS: dict[str, list[str]] = {
    "wander": ["B", "Down", "Down", "Left", "Right", "Up", "Down", "Left", "Right"],
    "bedroom-exit-v1": ["B", "Down", "Down", "Down", "Left", "Left", "Down", "Down", "Right", "Down"],
    "stair-search": ["B", "Down", "Down", "Left", "Down", "Right", "Down", "Left", "Left", "Down"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuously play Pokemon through the local emulator REST API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--preset", choices=sorted(PRESETS), default="bedroom-exit-v1")
    parser.add_argument("--actions", nargs="+", help="Override preset with an explicit repeated action list.")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--max-seconds", type=int, default=600)
    parser.add_argument("--movement-press-frames", type=int, default=28)
    parser.add_argument("--button-press-frames", type=int, default=5)
    parser.add_argument("--settle-frames", type=int, default=120)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--observe-every", type=int, default=1)
    parser.add_argument("--resume-title", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ensure-ready", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-if-title-resume-fails", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--visual-bedroom-exit", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    actions = _action_plan(args.actions, args.preset)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-continuous-play.jsonl"

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180)
    result = _run(
        client,
        output_path=output_path,
        actions=actions,
        max_steps=args.max_steps,
        max_seconds=args.max_seconds,
        movement_press_frames=args.movement_press_frames,
        button_press_frames=args.button_press_frames,
        settle_frames=args.settle_frames,
        checkpoint_every=args.checkpoint_every,
        observe_every=args.observe_every,
        resume_title=args.resume_title,
        ensure_ready=args.ensure_ready,
        stop_if_title_resume_fails=args.stop_if_title_resume_fails,
        visual_bedroom_exit=args.visual_bedroom_exit,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def _run(
    client: httpx.Client,
    *,
    output_path: Path,
    actions: list[str],
    max_steps: int,
    max_seconds: int,
    movement_press_frames: int,
    button_press_frames: int,
    settle_frames: int,
    checkpoint_every: int,
    observe_every: int,
    resume_title: bool,
    ensure_ready: bool,
    stop_if_title_resume_fails: bool,
    visual_bedroom_exit: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    run_id = datetime.now(UTC).strftime("continuous-%Y%m%dT%H%M%SZ")
    events: list[dict[str, Any]] = []

    def record(event: str, payload: dict[str, Any]) -> None:
        row = {"created_at": datetime.now(UTC).isoformat(), "run_id": run_id, "event": event, "payload": payload}
        events.append(row)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    record("run-started", {"actions": actions, "max_steps": max_steps, "max_seconds": max_seconds})
    if ensure_ready:
        ready = _post(client, "/api/emulator/ensure-ready", {"relaunch_if_needed": True})
        record("ensure-ready", ready)
        if ready.get("ok") is not True:
            return _finish(False, run_id, output_path, events, "ensure-ready-failed")

    if resume_title:
        resume = _post(client, "/api/emulator/macro/resume-save-from-title", _resume_payload())
        record("resume-title", resume)
        verification = resume.get("verification")
        resume_status = str(verification.get("status")) if isinstance(verification, dict) else ""
        if stop_if_title_resume_fails and resume_status != "candidate-overworld":
            return _finish(False, run_id, output_path, events, f"resume-title-failed:{resume_status}")

    start_checkpoint = _post(client, "/api/emulator/checkpoint/save", {"name": f"{run_id}-start"})
    record("checkpoint-start", start_checkpoint)

    completed_steps = 0
    expected_bedroom_tile: TilePoint | None = None
    for step in range(1, max_steps + 1):
        if time.monotonic() - started >= max_seconds:
            return _finish(True, run_id, output_path, events, "stopped-time-budget", completed_steps)
        action = actions[(step - 1) % len(actions)]
        if visual_bedroom_exit:
            visual_observation = _observe(client)
            screenshot_path = _screenshot_path(visual_observation)
            if screenshot_path is None:
                record(
                    "visual-bedroom-decision",
                    {"ok": False, "reason": "missing-screenshot", "observation": visual_observation},
                )
                return _finish(False, run_id, output_path, events, "visual-bedroom-missing-screenshot", completed_steps)
            decision = decide_bedroom_next_action(
                Path(screenshot_path),
                expected_tile=expected_bedroom_tile,
            ).to_dict()
            record("visual-bedroom-decision", decision)
            if decision.get("reason") == "already at target tile":
                return _finish(True, run_id, output_path, events, "bedroom-target-reached", completed_steps)
            next_action = decision.get("next_action")
            if not isinstance(next_action, str):
                return _finish(False, run_id, output_path, events, "visual-bedroom-no-action", completed_steps)
            action = next_action
            player_tile = decision.get("player_tile")
            if isinstance(player_tile, dict):
                expected_bedroom_tile = TilePoint(
                    *tile_after_action((int(player_tile["x"]), int(player_tile["y"])), action)
                )
        _close_menu_if_known_open(client, record)
        press_frames = movement_press_frames if action in MOVEMENT_BUTTONS else button_press_frames
        press = _post(client, "/api/emulator/press", {"button": action, "frames": press_frames})
        advance = _post(client, "/api/emulator/frame-advance", {"frames": settle_frames})
        completed_steps = step
        record(
            "step",
            {
                "step": step,
                "action": action,
                "press_frames": press_frames,
                "settle_frames": settle_frames,
                "press": press,
                "advance": advance,
            },
        )
        if observe_every > 0 and step % observe_every == 0:
            record("observe", _observe(client))
        if checkpoint_every > 0 and step % checkpoint_every == 0:
            record("checkpoint", _post(client, "/api/emulator/checkpoint/save", {"name": f"{run_id}-step-{step:04d}"}))

    return _finish(True, run_id, output_path, events, "stopped-step-budget", completed_steps)


def _close_menu_if_known_open(client: httpx.Client, record: Any) -> None:
    semantic = _get(client, "/api/emulator/semantic-state")
    state = semantic.get("state") if isinstance(semantic, dict) else None
    if not isinstance(state, dict) or state.get("menu_open") is not True:
        return
    close = _post(client, "/api/emulator/press", {"button": "B", "frames": 5})
    wait = _post(client, "/api/emulator/frame-advance", {"frames": 60})
    record("close-menu", {"semantic": semantic, "press": close, "advance": wait})


def _observe(client: httpx.Client) -> dict[str, Any]:
    return {
        "semantic": _get(client, "/api/emulator/semantic-state"),
        "screenshot": _get(client, "/api/emulator/screenshot"),
    }


def _screenshot_path(observation: dict[str, Any]) -> str | None:
    screenshot = observation.get("screenshot")
    if not isinstance(screenshot, dict):
        return None
    path = screenshot.get("artifact_path") or screenshot.get("path")
    return path if isinstance(path, str) and path else None


def _resume_payload() -> dict[str, int]:
    return {
        "initial_wait_frames": 60,
        "wait_after_start_frames": 90,
        "wait_after_continue_frames": 600,
        "wait_after_cgear_prompt_frames": 180,
        "wait_after_cgear_down_frames": 30,
        "wait_after_cgear_confirm_frames": 600,
        "visual_max_attempts": 5,
        "visual_advance_frames": 30,
        "press_frames": 4,
        "continue_press_frames": 30,
        "change_max_attempts": 8,
        "change_advance_frames": 90,
    }


def _finish(
    ok: bool,
    run_id: str,
    output_path: Path,
    events: list[dict[str, Any]],
    reason: str,
    completed_steps: int = 0,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "run_id": run_id,
        "reason": reason,
        "completed_steps": completed_steps,
        "output_path": str(output_path),
        "event_count": len(events),
    }


def _action_plan(actions: list[str] | None, preset: str) -> list[str]:
    selected = actions if actions else PRESETS[preset]
    normalized = [_normalize_action(action) for action in selected]
    if not normalized:
        raise ValueError("Continuous play needs at least one action.")
    return normalized


def _normalize_action(action: str) -> str:
    aliases = {
        "confirm": "A",
        "cancel": "B",
        "menu": "X",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "start": "Start",
        "select": "Select",
    }
    stripped = action.strip()
    normalized = aliases.get(stripped.lower(), stripped)
    allowed = MOVEMENT_BUTTONS | CONTROL_BUTTONS
    if normalized not in allowed:
        raise ValueError(f"Unsupported action: {action}")
    return normalized


def _get(client: httpx.Client, path: str) -> dict[str, Any]:
    try:
        response = client.get(path)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "path": path}


def _post(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = client.post(path, json=payload)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "path": path, "payload": payload}


if __name__ == "__main__":
    raise SystemExit(main())
