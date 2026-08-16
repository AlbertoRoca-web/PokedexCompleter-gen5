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
    parser = argparse.ArgumentParser(description="Fast Lua-side RAM diff scanner.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--start", default="0x02000000")
    parser.add_argument("--chunks", type=int, default=16)
    parser.add_argument("--chunk-size", type=int, default=65536)
    parser.add_argument("--button", default="Start")
    parser.add_argument("--press-frames", type=int, default=5)
    parser.add_argument("--advance-frames", type=int, default=120)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-changes", type=int, default=1000)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    start = _parse_int(args.start)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{args.button}-fast-matrix.json"
    runs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    hits: Counter[int] = Counter()
    values: dict[int, Counter[str]] = {}
    for repeat in range(1, args.repeats + 1):
        for chunk in range(args.chunks):
            address = start + (chunk * args.chunk_size)
            request_payload = {
                "domain": args.domain,
                "address": address,
                "length": args.chunk_size,
                "button": args.button,
                "press_frames": args.press_frames,
                "advance_frames": args.advance_frames,
                "max_changes": args.max_changes,
            }
            try:
                payload = _post_diff_with_retry(client, request_payload)
            except httpx.HTTPError as exc:
                errors.append(
                    {
                        "repeat": repeat,
                        "chunk": chunk,
                        "address": address,
                        "hex_address": f"0x{address:X}",
                        "error": str(exc),
                    }
                )
                _write_payload(
                    output_path,
                    _build_payload(args, start=start, runs=runs, errors=errors, hits=hits, values=values),
                )
                continue
            runs.append(
                {
                    "repeat": repeat,
                    "chunk": chunk,
                    "address": address,
                    "hex_address": f"0x{address:X}",
                    "changed_count": payload.get("changed_count"),
                    "changes": payload.get("changes", []),
                }
            )
            for change in payload.get("changes", []):
                changed_address = int(change["address"])
                hits[changed_address] += 1
                values.setdefault(changed_address, Counter())[f"{change['before']}->{change['after']}"] += 1
            _write_payload(
                output_path,
                _build_payload(args, start=start, runs=runs, errors=errors, hits=hits, values=values),
            )
    payload = _build_payload(args, start=start, runs=runs, errors=errors, hits=hits, values=values)
    _write_payload(output_path, payload)
    print(json.dumps(_summary(payload, output_path), indent=2))
    return 0 if runs else 1


def _build_payload(
    args: argparse.Namespace,
    *,
    start: int,
    runs: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    hits: Counter[int],
    values: dict[int, Counter[str]],
) -> dict[str, Any]:
    ranked = [
        {
            "address": address,
            "hex_address": f"0x{address:X}",
            "hit_count": hit_count,
            "transitions": dict(values.get(address, Counter()).most_common(8)),
        }
        for address, hit_count in hits.most_common(200)
    ]
    return {
        "ok": bool(runs),
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "start": start,
        "hex_start": f"0x{start:X}",
        "chunks": args.chunks,
        "chunk_size": args.chunk_size,
        "button": args.button,
        "repeats": args.repeats,
        "runs": runs,
        "errors": errors,
        "ranked_candidates": ranked,
    }


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _post_diff_with_retry(client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/emulator/memory/diff-after-press", json=payload)
    if response.status_code != 503:
        response.raise_for_status()
        return response.json()
    client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).raise_for_status()
    retry = client.post("/api/emulator/memory/diff-after-press", json=payload)
    retry.raise_for_status()
    return retry.json()


def _summary(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": str(path),
        "button": payload["button"],
        "run_changed_counts": [run["changed_count"] for run in payload["runs"]],
        "error_count": len(payload.get("errors", [])),
        "errors": payload.get("errors", [])[:5],
        "top_candidates": payload["ranked_candidates"][:40],
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
