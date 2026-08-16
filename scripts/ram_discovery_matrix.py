from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "ram-discovery"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repeated RAM diff probes and rank candidate changing addresses.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--start", default="0x02000000")
    parser.add_argument("--chunks", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=65536)
    parser.add_argument("--action", default="Start", help="Button/action to press between snapshots.")
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--advance-frames", type=int, default=120)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=90)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    start = _parse_int(args.start)
    all_runs: list[dict[str, Any]] = []
    address_hits: Counter[int] = Counter()
    toggled_hits: Counter[int] = Counter()

    for repeat in range(1, args.repeats + 1):
        for chunk_index in range(args.chunks):
            address = start + (chunk_index * args.chunk_size)
            run = _probe_chunk(
                client,
                domain=args.domain,
                address=address,
                length=args.chunk_size,
                action=args.action,
                press_frames=args.press_frames,
                advance_frames=args.advance_frames,
                repeat=repeat,
                chunk_index=chunk_index,
            )
            all_runs.append(run)
            for change in run["changes"]:
                absolute = int(change["address"])
                address_hits[absolute] += 1
                if change["before"] != change["after"]:
                    toggled_hits[absolute] += 1

    ranked = [
        {
            "address": address,
            "hex_address": f"0x{address:X}",
            "hit_count": count,
            "toggle_count": toggled_hits[address],
        }
        for address, count in address_hits.most_common(200)
    ]
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "start": start,
        "hex_start": f"0x{start:X}",
        "chunks": args.chunks,
        "chunk_size": args.chunk_size,
        "action": args.action,
        "repeats": args.repeats,
        "runs": all_runs,
        "ranked_candidates": ranked,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{args.action}-matrix.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(_summary(payload, output_path), indent=2))
    return 0


def _probe_chunk(
    client: httpx.Client,
    *,
    domain: str,
    address: int,
    length: int,
    action: str,
    press_frames: int,
    advance_frames: int,
    repeat: int,
    chunk_index: int,
) -> dict[str, Any]:
    before = _read_bytes(client, domain=domain, address=address, length=length)
    press = client.post("/api/emulator/press", json={"button": action, "frames": press_frames}).json()
    advance = client.post("/api/emulator/frame-advance", json={"frames": advance_frames}).json()
    after = _read_bytes(client, domain=domain, address=address, length=length)
    changes = _changes(address, before, after)
    return {
        "repeat": repeat,
        "chunk_index": chunk_index,
        "address": address,
        "hex_address": f"0x{address:X}",
        "length": length,
        "action_result": {"press": press, "advance": advance},
        "changed_count": len(changes),
        "changes": changes[:1000],
        "truncated": len(changes) > 1000,
    }


def _read_bytes(client: httpx.Client, *, domain: str, address: int, length: int) -> list[int]:
    values: list[int] = []
    remaining = length
    offset = 0
    while remaining > 0:
        current_length = min(4096, remaining)
        response = client.post(
            "/api/emulator/memory/read-bytes",
            json={"domain": domain, "address": address + offset, "length": current_length},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ok") is not True:
            raise RuntimeError(json.dumps(payload, indent=2))
        values.extend(int(value) for value in payload.get("values", []))
        offset += current_length
        remaining -= current_length
    return values


def _changes(base_address: int, before: list[int], after: list[int]) -> list[dict[str, int | str]]:
    changes: list[dict[str, int | str]] = []
    for index, before_value in enumerate(before):
        after_value = after[index]
        if before_value == after_value:
            continue
        address = base_address + index
        changes.append(
            {
                "address": address,
                "hex_address": f"0x{address:X}",
                "offset": index,
                "before": before_value,
                "after": after_value,
            }
        )
    return changes


def _summary(payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": str(output_path),
        "domain": payload["domain"],
        "hex_start": payload["hex_start"],
        "chunks": payload["chunks"],
        "chunk_size": payload["chunk_size"],
        "action": payload["action"],
        "repeats": payload["repeats"],
        "run_changed_counts": [run["changed_count"] for run in payload["runs"]],
        "top_candidates": payload["ranked_candidates"][:30],
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
