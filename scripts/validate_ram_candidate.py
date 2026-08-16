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
    parser = argparse.ArgumentParser(description="Validate candidate RAM addresses before/after one input action.")
    parser.add_argument("addresses", nargs="+", help="Addresses as decimal or hex, e.g. 0x0214BAD8")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--button", default="Start")
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--advance-frames", type=int, default=30)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=90)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    addresses = [_parse_int(address) for address in args.addresses]
    before = _snapshot(client, domain=args.domain, addresses=addresses)
    press = client.post("/api/emulator/press", json={"button": args.button, "frames": args.press_frames}).json()
    advance = client.post("/api/emulator/frame-advance", json={"frames": args.advance_frames}).json()
    after = _snapshot(client, domain=args.domain, addresses=addresses)
    result = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "button": args.button,
        "press_frames": args.press_frames,
        "advance_frames": args.advance_frames,
        "before": before,
        "action": {"press": press, "advance": advance},
        "after": after,
        "changes": [
            {
                "address": address,
                "hex_address": f"0x{address:X}",
                "before": before["values"][f"0x{address:X}"],
                "after": after["values"][f"0x{address:X}"],
            }
            for address in addresses
            if before["values"][f"0x{address:X}"] != after["values"][f"0x{address:X}"]
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{args.button}-candidate.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **result}, indent=2))
    return 0


def _snapshot(client: httpx.Client, *, domain: str, addresses: list[int]) -> dict[str, Any]:
    values: dict[str, int] = {}
    for address in addresses:
        response = client.post(
            "/api/emulator/memory/read-u8",
            json={"domain": domain, "address": address},
        )
        response.raise_for_status()
        values[f"0x{address:X}"] = int(response.json()["value"])
    screenshot = client.get("/api/emulator/screenshot").json()
    analysis = screenshot.get("artifact", {}).get("analysis", {})
    return {
        "values": values,
        "screenshot_path": screenshot.get("path") or screenshot.get("artifact_path"),
        "classification": analysis.get("classification"),
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
