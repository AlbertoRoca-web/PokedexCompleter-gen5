from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".runtime" / "ram-validation"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"
DEFAULT_CONTROL_ACTION = "Wait"
DEFAULT_ACTIONS = [DEFAULT_CONTROL_ACTION, "Up", "Down", "Left", "Right"]
DEFAULT_SAMPLE_FRAMES = [0, 5, 10, 20, 40, 80, 120, 180]


def main() -> int:
    parser = argparse.ArgumentParser(description="Timeline RAM candidate values after checkpointed actions.")
    parser.add_argument("addresses", nargs="*", help="Candidate addresses, decimal or hex.")
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        nargs=2,
        metavar=("START", "LENGTH"),
        help="Add every byte in an address range. START is decimal/hex; LENGTH is decimal/hex byte count.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--domain", default="ARM9 System Bus")
    parser.add_argument("--actions", nargs="+", default=DEFAULT_ACTIONS)
    parser.add_argument("--control-action", default=DEFAULT_CONTROL_ACTION)
    parser.add_argument("--sample-frames", nargs="+", type=int, default=DEFAULT_SAMPLE_FRAMES)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--checkpoint", default="timeline-candidate-validation")
    parser.add_argument("--press-frames", type=int, default=8)
    parser.add_argument("--settle-frames", type=int, default=60)
    parser.add_argument("--pre-checkpoint-settle-frames", type=int, default=180)
    parser.add_argument("--no-ensure-ready", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120)
    if not args.no_ensure_ready:
        ready = client.post("/api/emulator/ensure-ready", json={"relaunch_if_needed": True}).json()
        if ready.get("ok") is not True:
            print(json.dumps({"ok": False, "stage": "ensure-ready", "ready": ready}, indent=2))
            return 1

    addresses = _candidate_addresses(args.addresses, args.ranges)
    actions = _with_control_action(args.actions, args.control_action)
    sample_frames = _sample_frames(args.sample_frames)

    _press_and_wait(client, "B", 5, 30)
    _advance(client, args.pre_checkpoint_settle_frames)
    save_response = client.post("/api/emulator/checkpoint/save", json={"name": args.checkpoint})
    save_response.raise_for_status()
    save_payload = save_response.json()
    checkpoint_path = _checkpoint_path_from_save(save_payload)

    observations: list[dict[str, Any]] = []
    for cycle in range(1, args.cycles + 1):
        for action in actions:
            _load_checkpoint(client, checkpoint_path)
            if args.settle_frames > 0:
                _advance(client, args.settle_frames)
            before = _read_addresses(client, domain=args.domain, addresses=addresses)
            timeline = _action_timeline(
                client,
                action=action,
                domain=args.domain,
                addresses=addresses,
                press_frames=args.press_frames,
                sample_frames=sample_frames,
            )
            observations.append({"cycle": cycle, "action": action, "before": before, "timeline": timeline})

    ranked = _rank_timelines(
        observations,
        addresses,
        sample_frames=sample_frames,
        control_action=args.control_action,
    )
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "actions": actions,
        "control_action": args.control_action,
        "sample_frames": sample_frames,
        "cycles": args.cycles,
        "checkpoint": args.checkpoint,
        "checkpoint_path": checkpoint_path,
        "addresses": [f"0x{address:X}" for address in addresses],
        "save_checkpoint": save_payload,
        "observations": observations,
        "ranked_candidates": ranked,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-timeline-validation.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(_summary(payload, output_path), indent=2))
    return 0


def _action_timeline(
    client: httpx.Client,
    *,
    action: str,
    domain: str,
    addresses: list[int],
    press_frames: int,
    sample_frames: list[int],
) -> list[dict[str, Any]]:
    if not _is_wait_action(action):
        client.post("/api/emulator/press", json={"button": action, "frames": press_frames}).raise_for_status()
    timeline: list[dict[str, Any]] = []
    elapsed = 0
    for frame in sample_frames:
        delta = frame - elapsed
        if delta > 0:
            _advance(client, delta)
            elapsed = frame
        values = _read_addresses(client, domain=domain, addresses=addresses)
        timeline.append({"frame": frame, "values": values})
    return timeline


def _rank_timelines(
    observations: list[dict[str, Any]],
    addresses: list[int],
    *,
    sample_frames: list[int],
    control_action: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for address in addresses:
        key = f"0x{address:X}"
        baseline_values = [int(observation["before"][key]) for observation in observations]
        baseline_stability = _same_ratio(baseline_values)
        modes_by_action = _modes_by_action(observations, key)
        control_modes = modes_by_action.get(control_action, {})
        differing_action_frames = _differing_action_frames(
            modes_by_action,
            control_action=control_action,
            control_modes=control_modes,
        )
        stable_control_timeline = _stable_timeline_ratio(modes_by_action.get(control_action, {}))
        action_divergence_count = sum(len(frames) for frames in differing_action_frames.values())
        action_divergence_rate = action_divergence_count / max(
            1,
            (len(modes_by_action) - 1) * len(sample_frames),
        )
        distinct_final_modes = len(
            {
                frame_modes.get(sample_frames[-1])
                for action, frame_modes in modes_by_action.items()
                if action != control_action and sample_frames[-1] in frame_modes
            }
        )
        score = (
            action_divergence_rate * 8.0
            + baseline_stability * 2.0
            + stable_control_timeline * 2.0
            + distinct_final_modes * 0.5
        )
        if action_divergence_count == 0:
            score = -100.0 + baseline_stability * 0.25
        rows.append(
            {
                "address": address,
                "hex_address": key,
                "score": round(score, 3),
                "baseline_stability": round(baseline_stability, 3),
                "stable_control_timeline": round(stable_control_timeline, 3),
                "action_divergence_rate": round(action_divergence_rate, 3),
                "action_divergence_count": action_divergence_count,
                "distinct_final_modes": distinct_final_modes,
                "modes_by_action": modes_by_action,
                "differing_action_frames": differing_action_frames,
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["score"]),
            float(row["action_divergence_rate"]),
            int(row["distinct_final_modes"]),
            float(row["baseline_stability"]),
        ),
        reverse=True,
    )
    return rows


def _modes_by_action(observations: list[dict[str, Any]], key: str) -> dict[str, dict[int, int]]:
    values_by_action_frame: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        action = str(observation["action"])
        for sample in observation["timeline"]:
            frame = int(sample["frame"])
            values_by_action_frame[action][frame].append(int(sample["values"][key]))
    return {
        action: {frame: _mode(values) for frame, values in sorted(frame_values.items())}
        for action, frame_values in sorted(values_by_action_frame.items())
    }


def _differing_action_frames(
    modes_by_action: dict[str, dict[int, int]],
    *,
    control_action: str,
    control_modes: dict[int, int],
) -> dict[str, list[int]]:
    return {
        action: [frame for frame, value in frame_modes.items() if control_modes.get(frame) != value]
        for action, frame_modes in sorted(modes_by_action.items())
        if action != control_action
    }


def _stable_timeline_ratio(frame_modes: dict[int, int]) -> float:
    return _same_ratio(list(frame_modes.values()))


def _read_addresses(client: httpx.Client, *, domain: str, addresses: list[int]) -> dict[str, int]:
    values: dict[str, int] = {}
    for start, grouped_addresses in _group_nearby_addresses(addresses, max_span=1024):
        length = max(grouped_addresses) - start + 1
        response = client.post(
            "/api/emulator/memory/read-bytes",
            json={"domain": domain, "address": start, "length": length},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ok") is not True:
            raise RuntimeError(f"RAM read failed at 0x{start:X}: {payload}")
        raw_values = [int(value) for value in payload.get("values", [])]
        for address in grouped_addresses:
            values[f"0x{address:X}"] = raw_values[address - start]
    return values


def _group_nearby_addresses(addresses: list[int], *, max_span: int) -> list[tuple[int, list[int]]]:
    sorted_addresses = sorted(set(addresses))
    groups: list[tuple[int, list[int]]] = []
    current_start: int | None = None
    current_addresses: list[int] = []
    for address in sorted_addresses:
        if current_start is None:
            current_start = address
            current_addresses = [address]
            continue
        if address - current_start < max_span:
            current_addresses.append(address)
            continue
        groups.append((current_start, current_addresses))
        current_start = address
        current_addresses = [address]
    if current_start is not None:
        groups.append((current_start, current_addresses))
    return groups


def _candidate_addresses(addresses: list[str], ranges: list[list[str]] | None) -> list[int]:
    parsed_addresses = [_parse_int(value) for value in addresses]
    for start_value, length_value in ranges or []:
        start = _parse_int(start_value)
        length = _parse_int(length_value)
        if length < 1:
            raise ValueError(f"Address range length must be positive: {length_value}")
        parsed_addresses.extend(range(start, start + length))
    unique_addresses = sorted(set(parsed_addresses))
    if not unique_addresses:
        raise ValueError("At least one address or --range START LENGTH is required.")
    return unique_addresses


def _with_control_action(actions: list[str], control_action: str) -> list[str]:
    normalized_actions = list(dict.fromkeys(actions))
    if control_action in normalized_actions:
        return normalized_actions
    return [control_action, *normalized_actions]


def _checkpoint_path_from_save(payload: dict[str, Any]) -> str:
    path = payload.get("artifact_path") or payload.get("path")
    if not isinstance(path, str) or not path:
        raise RuntimeError(f"Checkpoint save response did not include a path: {payload}")
    return path


def _load_checkpoint(client: httpx.Client, checkpoint_path: str) -> None:
    response = client.post("/api/emulator/checkpoint/load", json={"name": checkpoint_path})
    response.raise_for_status()
    payload = response.json()
    if payload.get("ok") is not True:
        raise RuntimeError(f"Checkpoint load failed: {payload}")


def _press_and_wait(client: httpx.Client, button: str, press_frames: int, advance_frames: int) -> None:
    client.post("/api/emulator/press", json={"button": button, "frames": press_frames}).raise_for_status()
    _advance(client, advance_frames)


def _advance(client: httpx.Client, frames: int) -> None:
    client.post("/api/emulator/frame-advance", json={"frames": frames}).raise_for_status()


def _is_wait_action(action: str) -> bool:
    return action.lower() in {"wait", "idle", "none", "noop", "no-op"}


def _mode(values: list[int]) -> int:
    counts: dict[int, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return max(counts.items(), key=lambda item: (item[1], -item[0]))[0]


def _same_ratio(values: list[int]) -> float:
    if not values:
        return 0.0
    mode_value = _mode(values)
    return mean(1.0 if value == mode_value else 0.0 for value in values)


def _sample_frames(values: list[int]) -> list[int]:
    frames = sorted(set(values))
    if not frames or frames[0] < 0:
        raise ValueError("Sample frames must be non-negative integers.")
    return frames


def _summary(payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": str(output_path),
        "domain": payload["domain"],
        "actions": payload["actions"],
        "control_action": payload["control_action"],
        "sample_frames": payload["sample_frames"],
        "cycles": payload["cycles"],
        "top_candidates": [_candidate_summary(row) for row in payload["ranked_candidates"][:30]],
    }


def _candidate_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "hex_address": row["hex_address"],
        "score": row["score"],
        "baseline_stability": row["baseline_stability"],
        "stable_control_timeline": row["stable_control_timeline"],
        "action_divergence_rate": row["action_divergence_rate"],
        "action_divergence_count": row["action_divergence_count"],
        "distinct_final_modes": row["distinct_final_modes"],
        "differing_action_frames": row["differing_action_frames"],
        "modes_by_action": row["modes_by_action"],
    }


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
