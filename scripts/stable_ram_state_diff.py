from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "ram-validation"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


def main() -> int:
    parser = argparse.ArgumentParser(description="Find RAM bytes that differ stably between closed/open menu states.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--start", default="0x020A0000")
    parser.add_argument("--length", type=int, default=65536)
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--advance-frames", type=int, default=60)
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    start = _parse_int(args.start)
    _press_and_wait(client, "B", args.press_frames, args.advance_frames)
    closed_1 = _capture_state(client, domain=args.domain, start=start, length=args.length, label="closed-1")
    _press_and_wait(client, "X", args.press_frames, args.advance_frames)
    open_state = _capture_state(client, domain=args.domain, start=start, length=args.length, label="open")
    _press_and_wait(client, "B", args.press_frames, args.advance_frames)
    closed_2 = _capture_state(client, domain=args.domain, start=start, length=args.length, label="closed-2")

    candidates = _stable_candidates(
        start,
        closed_1["bytes"],
        open_state["bytes"],
        closed_2["bytes"],
        max_candidates=args.max_candidates,
    )
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "start": start,
        "hex_start": f"0x{start:X}",
        "length": args.length,
        "states": [
            _without_bytes(closed_1),
            _without_bytes(open_state),
            _without_bytes(closed_2),
        ],
        "stable_candidate_count": len(candidates),
        "stable_candidates": candidates,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-stable-state-diff.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))
    return 0


def _capture_state(
    client: httpx.Client,
    *,
    domain: str,
    start: int,
    length: int,
    label: str,
) -> dict[str, Any]:
    screenshot = client.get("/api/emulator/screenshot")
    screenshot.raise_for_status()
    screenshot_payload = screenshot.json()
    return {
        "label": label,
        "screenshot_path": screenshot_payload.get("path") or screenshot_payload.get("artifact_path"),
        "bytes": _read_bytes(client, domain=domain, start=start, length=length),
    }


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


def _stable_candidates(
    start: int,
    closed_1: list[int],
    open_state: list[int],
    closed_2: list[int],
    *,
    max_candidates: int,
) -> list[dict[str, int | str]]:
    candidates: list[dict[str, int | str]] = []
    for index, closed_value in enumerate(closed_1):
        if closed_value != closed_2[index] or closed_value == open_state[index]:
            continue
        address = start + index
        candidates.append(
            {
                "address": address,
                "hex_address": f"0x{address:X}",
                "closed": closed_value,
                "open": open_state[index],
            }
        )
        if len(candidates) >= max_candidates:
            break
    return candidates


def _without_bytes(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key != "bytes"}


def _press_and_wait(client: httpx.Client, button: str, press_frames: int, advance_frames: int) -> None:
    client.post("/api/emulator/press", json={"button": button, "frames": press_frames}).raise_for_status()
    client.post("/api/emulator/frame-advance", json={"frames": advance_frames}).raise_for_status()


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
