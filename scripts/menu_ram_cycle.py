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
    parser = argparse.ArgumentParser(
        description="Repeatedly toggle Gen 5 overworld menu and sample candidate RAM bytes."
    )
    parser.add_argument("addresses", nargs="+", help="Candidate addresses, decimal or hex.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--advance-frames", type=int, default=60)
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=90)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    addresses = [_parse_int(value) for value in args.addresses]
    samples: list[dict[str, Any]] = []
    _press_and_wait(client, "B", args.press_frames, args.advance_frames)
    for cycle in range(1, args.cycles + 1):
        samples.append(_sample(client, domain=args.domain, addresses=addresses, label="closed", cycle=cycle))
        _press_and_wait(client, "X", args.press_frames, args.advance_frames)
        samples.append(_sample(client, domain=args.domain, addresses=addresses, label="open", cycle=cycle))
        _press_and_wait(client, "B", args.press_frames, args.advance_frames)
        samples.append(_sample(client, domain=args.domain, addresses=addresses, label="closed-after", cycle=cycle))

    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "cycles": args.cycles,
        "addresses": [f"0x{address:X}" for address in addresses],
        "samples": samples,
        "patterns": _patterns(samples, addresses),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-menu-cycle.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))
    return 0


def _press_and_wait(client: httpx.Client, button: str, press_frames: int, advance_frames: int) -> None:
    client.post("/api/emulator/press", json={"button": button, "frames": press_frames}).raise_for_status()
    client.post("/api/emulator/frame-advance", json={"frames": advance_frames}).raise_for_status()


def _sample(client: httpx.Client, *, domain: str, addresses: list[int], label: str, cycle: int) -> dict[str, Any]:
    values = {}
    for address in addresses:
        response = client.post("/api/emulator/memory/read-u8", json={"domain": domain, "address": address})
        response.raise_for_status()
        values[f"0x{address:X}"] = int(response.json()["value"])
    screenshot = client.get("/api/emulator/screenshot")
    screenshot.raise_for_status()
    screenshot_payload = screenshot.json()
    return {
        "cycle": cycle,
        "label": label,
        "values": values,
        "screenshot_path": screenshot_payload.get("path") or screenshot_payload.get("artifact_path"),
    }


def _patterns(samples: list[dict[str, Any]], addresses: list[int]) -> dict[str, dict[str, list[int]]]:
    patterns: dict[str, dict[str, list[int]]] = {}
    for address in addresses:
        key = f"0x{address:X}"
        patterns[key] = {
            "closed": [int(sample["values"][key]) for sample in samples if sample["label"] == "closed"],
            "open": [int(sample["values"][key]) for sample in samples if sample["label"] == "open"],
            "closed_after": [int(sample["values"][key]) for sample in samples if sample["label"] == "closed-after"],
        }
    return patterns


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
