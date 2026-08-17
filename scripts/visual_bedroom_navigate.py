from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from pokedex_completer_gen5.emulator.bedroom_navigation import TilePoint, decide_bedroom_next_action, tile_after_action

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "continuous-play"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


def main() -> int:
    parser = argparse.ArgumentParser(description="Use screenshot localization + A* to navigate the bedroom target.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--movement-press-frames", type=int, default=28)
    parser.add_argument("--settle-frames", type=int, default=150)
    parser.add_argument("--checkpoint-every", type=int, default=4)
    parser.add_argument("--initial-expected-tile", nargs=2, type=int, metavar=("X", "Y"))
    parser.add_argument("--ensure-ready", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-visual-bedroom.jsonl"
    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180)
    result = _run(
        client,
        output_path=output_path,
        max_steps=args.max_steps,
        movement_press_frames=args.movement_press_frames,
        settle_frames=args.settle_frames,
        checkpoint_every=args.checkpoint_every,
        initial_expected_tile=tuple(args.initial_expected_tile) if args.initial_expected_tile else None,
        ensure_ready=args.ensure_ready,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def _run(
    client: httpx.Client,
    *,
    output_path: Path,
    max_steps: int,
    movement_press_frames: int,
    settle_frames: int,
    checkpoint_every: int,
    initial_expected_tile: tuple[int, int] | None,
    ensure_ready: bool,
) -> dict[str, Any]:
    run_id = datetime.now(UTC).strftime("visual-bedroom-%Y%m%dT%H%M%SZ")
    events: list[dict[str, Any]] = []

    def record(event: str, payload: dict[str, Any]) -> None:
        row = {"created_at": datetime.now(UTC).isoformat(), "run_id": run_id, "event": event, "payload": payload}
        events.append(row)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    record("run-started", {"max_steps": max_steps})
    if ensure_ready:
        ready = _post(client, "/api/emulator/ensure-ready", {"relaunch_if_needed": True})
        record("ensure-ready", ready)
        if ready.get("ok") is not True:
            return _finish(False, run_id, output_path, events, "ensure-ready-failed")

    record("checkpoint-start", _post(client, "/api/emulator/checkpoint/save", {"name": f"{run_id}-start"}))
    blocked_tiles: set[tuple[int, int]] = set()
    last_tile: TilePoint | None = TilePoint(*initial_expected_tile) if initial_expected_tile else None
    last_action: str | None = None
    for step in range(1, max_steps + 1):
        screenshot = _get(client, "/api/emulator/screenshot")
        screenshot_path = screenshot.get("artifact_path") or screenshot.get("path")
        if not isinstance(screenshot_path, str):
            record("observe-failed", {"step": step, "screenshot": screenshot})
            return _finish(False, run_id, output_path, events, "screenshot-missing", step - 1)
        decision = decide_bedroom_next_action(
            Path(screenshot_path), blocked_tiles=blocked_tiles, expected_tile=last_tile
        )
        if last_tile is not None and last_action is not None and decision.player_tile == last_tile:
            blocked_tile = tile_after_action(last_tile, last_action)
            blocked_tiles.add(blocked_tile)
            record(
                "blocked-tile-learned",
                {"step": step, "from_tile": last_tile.to_dict(), "action": last_action, "blocked_tile": blocked_tile},
            )
            decision = decide_bedroom_next_action(
                Path(screenshot_path), blocked_tiles=blocked_tiles, expected_tile=last_tile
            )
        record(
            "decision",
            {
                "step": step,
                "screenshot": screenshot,
                "blocked_tiles": sorted(blocked_tiles),
                "decision": decision.to_dict(),
            },
        )
        if decision.next_action is None:
            return _finish(True, run_id, output_path, events, decision.reason, step - 1)
        last_tile = decision.player_tile
        last_action = decision.next_action
        press = _post(client, "/api/emulator/press", {"button": decision.next_action, "frames": movement_press_frames})
        advance = _post(client, "/api/emulator/frame-advance", {"frames": settle_frames})
        record(
            "step",
            {
                "step": step,
                "action": decision.next_action,
                "press": press,
                "advance": advance,
                "movement_press_frames": movement_press_frames,
                "settle_frames": settle_frames,
            },
        )
        if checkpoint_every > 0 and step % checkpoint_every == 0:
            record("checkpoint", _post(client, "/api/emulator/checkpoint/save", {"name": f"{run_id}-step-{step:04d}"}))
    return _finish(True, run_id, output_path, events, "stopped-step-budget", max_steps)


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
