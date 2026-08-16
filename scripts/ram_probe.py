from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "ram-probes"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


@dataclass(frozen=True)
class MemorySnapshot:
    domain: str
    address: int
    length: int
    values: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "address": self.address,
            "length": self.length,
            "hex_address": f"0x{self.address:X}",
            "values": self.values,
            "hex": "".join(f"{value:02X}" for value in self.values),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe/diff BizHawk memory through the local REST bridge.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--address", default="0x02000000", help="Start address, decimal or hex.")
    parser.add_argument("--length", type=int, default=4096)
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--press", default="", help="Optional button/action to press between before/after snapshots.")
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--advance-frames", type=int, default=120)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=60)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    address = _parse_int(args.address)
    before = _read_snapshot(
        client,
        domain=args.domain,
        address=address,
        length=args.length,
        chunk_size=args.chunk_size,
    )

    action_payload: dict[str, Any] | None = None
    if args.press:
        press_response = client.post(
            "/api/emulator/press",
            json={"button": args.press, "frames": args.press_frames},
        ).json()
        advance_response = client.post(
            "/api/emulator/frame-advance",
            json={"frames": args.advance_frames},
        ).json()
        action_payload = {"press": press_response, "advance": advance_response}

    after = _read_snapshot(
        client,
        domain=args.domain,
        address=address,
        length=args.length,
        chunk_size=args.chunk_size,
    )
    diff = _diff_snapshots(before, after)
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "address": address,
        "hex_address": f"0x{address:X}",
        "length": args.length,
        "action": action_payload,
        "before": before.to_dict(),
        "after": after.to_dict(),
        "diff": diff,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-ram-probe.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["output_path"] = str(output_path)
    print(json.dumps(_summary(payload), indent=2))
    return 0


def _read_snapshot(
    client: httpx.Client,
    *,
    domain: str,
    address: int,
    length: int,
    chunk_size: int,
) -> MemorySnapshot:
    values: list[int] = []
    remaining = length
    offset = 0
    while remaining > 0:
        current_length = min(max(1, chunk_size), remaining, 4096)
        response = client.post(
            "/api/emulator/memory/read-bytes",
            json={"domain": domain, "address": address + offset, "length": current_length},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ok") is not True:
            raise RuntimeError(json.dumps(payload, indent=2))
        values.extend(int(value) for value in payload.get("values", []))
        remaining -= current_length
        offset += current_length
    return MemorySnapshot(domain=domain, address=address, length=length, values=values)


def _diff_snapshots(before: MemorySnapshot, after: MemorySnapshot) -> dict[str, Any]:
    changed: list[dict[str, Any]] = []
    for index, before_value in enumerate(before.values):
        after_value = after.values[index]
        if before_value == after_value:
            continue
        absolute_address = before.address + index
        changed.append(
            {
                "offset": index,
                "address": absolute_address,
                "hex_address": f"0x{absolute_address:X}",
                "before": before_value,
                "after": after_value,
            }
        )
    return {
        "changed_count": len(changed),
        "changed_ratio": len(changed) / before.length if before.length else 0,
        "changed": changed[:500],
        "truncated": len(changed) > 500,
    }


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": payload["output_path"],
        "domain": payload["domain"],
        "hex_address": payload["hex_address"],
        "length": payload["length"],
        "action": payload["action"],
        "changed_count": payload["diff"]["changed_count"],
        "changed_ratio": payload["diff"]["changed_ratio"],
        "first_changes": payload["diff"]["changed"][:20],
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
