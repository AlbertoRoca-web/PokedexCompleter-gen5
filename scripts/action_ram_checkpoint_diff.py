from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "ram-validation"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff RAM after actions, resetting from one checkpoint each time.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--start", default="0x020A0000")
    parser.add_argument("--length", type=int, default=65536)
    parser.add_argument("--actions", nargs="+", default=["Up", "Down", "Left", "Right"])
    parser.add_argument("--checkpoint", default="ram-action-probe")
    parser.add_argument("--press-frames", type=int, default=16)
    parser.add_argument("--advance-frames", type=int, default=120)
    parser.add_argument("--max-changes-per-action", type=int, default=300)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    start = _parse_int(args.start)
    _press_and_wait(client, "B", 5, 60)
    save_response = client.post("/api/emulator/checkpoint/save", json={"name": args.checkpoint})
    save_response.raise_for_status()
    baseline = _read_bytes(client, domain=args.domain, start=start, length=args.length)

    runs: list[dict[str, Any]] = []
    hit_counter: Counter[int] = Counter()
    action_counter: dict[int, set[str]] = {}
    for action in args.actions:
        client.post("/api/emulator/checkpoint/load", json={"name": args.checkpoint}).raise_for_status()
        _press_and_wait(client, action, args.press_frames, args.advance_frames)
        values = _read_bytes(client, domain=args.domain, start=start, length=args.length)
        changes = _changes(start, baseline, values, max_changes=args.max_changes_per_action)
        for change in changes:
            address = int(change["address"])
            hit_counter[address] += 1
            action_counter.setdefault(address, set()).add(action)
        screenshot = client.get("/api/emulator/screenshot").json()
        runs.append(
            {
                "action": action,
                "changed_count": len(changes),
                "changes": changes,
                "screenshot_path": screenshot.get("path") or screenshot.get("artifact_path"),
            }
        )

    ranked = [
        {
            "address": address,
            "hex_address": f"0x{address:X}",
            "hit_count": hit_count,
            "actions": sorted(action_counter.get(address, set())),
        }
        for address, hit_count in hit_counter.most_common(200)
    ]
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "start": start,
        "hex_start": f"0x{start:X}",
        "length": args.length,
        "actions": args.actions,
        "checkpoint": args.checkpoint,
        "save_checkpoint": save_response.json(),
        "runs": runs,
        "ranked_candidates": ranked,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-action-checkpoint-diff.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(_summary(payload, output_path), indent=2))
    return 0


def _read_bytes(client: httpx.Client, *, domain: str, start: int, length: int) -> list[int]:
    values: list[int] = []
    offset = 0
    while offset < length:
        current_length = min(65536, length - offset)
        response = client.post(
            "/api/emulator/memory/read-bytes",
            json={"domain": domain, "address": start + offset, "length": current_length},
        )
        response.raise_for_status()
        values.extend(int(value) for value in response.json().get("values", []))
        offset += current_length
    return values


def _changes(start: int, before: list[int], after: list[int], *, max_changes: int) -> list[dict[str, int | str]]:
    changes: list[dict[str, int | str]] = []
    for index, before_value in enumerate(before):
        after_value = after[index]
        if before_value == after_value:
            continue
        address = start + index
        changes.append(
            {
                "address": address,
                "hex_address": f"0x{address:X}",
                "offset": index,
                "before": before_value,
                "after": after_value,
            }
        )
        if len(changes) >= max_changes:
            break
    return changes


def _press_and_wait(client: httpx.Client, button: str, press_frames: int, advance_frames: int) -> None:
    client.post("/api/emulator/press", json={"button": button, "frames": press_frames}).raise_for_status()
    client.post("/api/emulator/frame-advance", json={"frames": advance_frames}).raise_for_status()


def _summary(payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": str(output_path),
        "domain": payload["domain"],
        "hex_start": payload["hex_start"],
        "length": payload["length"],
        "action_counts": [(run["action"], run["changed_count"]) for run in payload["runs"]],
        "top_candidates": payload["ranked_candidates"][:40],
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
