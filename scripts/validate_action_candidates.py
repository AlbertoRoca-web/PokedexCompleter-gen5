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


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate RAM bytes against repeated checkpointed actions.")
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
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--checkpoint", default="candidate-validation")
    parser.add_argument("--press-frames", type=int, default=18)
    parser.add_argument("--advance-frames", type=int, default=90)
    parser.add_argument("--settle-frames", type=int, default=15)
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
    _press_and_wait(client, "B", 5, 30)
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
            _perform_action(client, action, args.press_frames, args.advance_frames)
            after = _read_addresses(client, domain=args.domain, addresses=addresses)
            observations.append({"cycle": cycle, "action": action, "before": before, "after": after})

    ranked = _rank_candidates(observations, addresses, control_action=args.control_action)
    payload = {
        "ok": True,
        "created_at": datetime.now(UTC).isoformat(),
        "domain": args.domain,
        "actions": actions,
        "cycles": args.cycles,
        "control_action": args.control_action,
        "checkpoint": args.checkpoint,
        "checkpoint_path": checkpoint_path,
        "addresses": [f"0x{address:X}" for address in addresses],
        "save_checkpoint": save_payload,
        "observations": observations,
        "ranked_candidates": ranked,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-candidate-validation.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(_summary(payload, output_path), indent=2))
    return 0


def _rank_candidates(
    observations: list[dict[str, Any]], addresses: list[int], *, control_action: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_action: dict[int, dict[str, list[tuple[int, int]]]] = {
        address: defaultdict(list) for address in addresses
    }
    for observation in observations:
        action = str(observation["action"])
        before = observation["before"]
        after = observation["after"]
        for address in addresses:
            key = f"0x{address:X}"
            by_action[address][action].append((int(before[key]), int(after[key])))

    for address in addresses:
        action_pairs = by_action[address]
        control_pairs = action_pairs.get(control_action, [])
        control_changed = sum(1 for before, after in control_pairs if before != after)
        movement_pairs = [
            pair
            for action, pairs in action_pairs.items()
            if action != control_action
            for pair in pairs
        ]
        movement_changed = sum(1 for before, after in movement_pairs if before != after)
        baseline_values = [before for pairs in action_pairs.values() for before, _after in pairs]
        after_by_action = {
            action: [after for _before, after in pairs]
            for action, pairs in sorted(action_pairs.items())
        }
        before_by_action = {
            action: [before for before, _after in pairs]
            for action, pairs in sorted(action_pairs.items())
        }
        action_after_modes = {
            action: _mode(values)
            for action, values in after_by_action.items()
            if values
        }
        directional_after_modes = {
            action: value
            for action, value in action_after_modes.items()
            if action != control_action
        }
        control_after_mode = action_after_modes.get(control_action)
        distinct_directional_after_modes = len(set(directional_after_modes.values()))
        action_modes_different_from_control = sum(
            1 for value in directional_after_modes.values() if value != control_after_mode
        )
        baseline_stability = _same_ratio(baseline_values)
        movement_change_rate = movement_changed / max(1, len(movement_pairs))
        control_change_rate = control_changed / max(1, len(control_pairs))
        movement_specific_change_rate = max(0.0, movement_change_rate - control_change_rate)
        score = (
            movement_specific_change_rate * 8.0
            + baseline_stability * 2.0
            + action_modes_different_from_control * 1.5
            + distinct_directional_after_modes * 0.25
            - control_change_rate * 8.0
        )
        rows.append(
            {
                "address": address,
                "hex_address": f"0x{address:X}",
                "score": round(score, 3),
                "baseline_stability": round(baseline_stability, 3),
                "movement_change_rate": round(movement_change_rate, 3),
                "control_change_rate": round(control_change_rate, 3),
                "movement_specific_change_rate": round(movement_specific_change_rate, 3),
                "distinct_directional_after_modes": distinct_directional_after_modes,
                "action_modes_different_from_control": action_modes_different_from_control,
                "before_by_action": before_by_action,
                "after_by_action": after_by_action,
                "action_after_modes": action_after_modes,
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["score"]),
            float(row["baseline_stability"]),
            float(row["movement_specific_change_rate"]),
            int(row["action_modes_different_from_control"]),
            int(row["distinct_directional_after_modes"]),
        ),
        reverse=True,
    )
    return rows


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
            offset = address - start
            values[f"0x{address:X}"] = raw_values[offset]
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


def _with_control_action(actions: list[str], control_action: str) -> list[str]:
    normalized_actions = list(dict.fromkeys(actions))
    if control_action in normalized_actions:
        return normalized_actions
    return [control_action, *normalized_actions]


def _perform_action(client: httpx.Client, action: str, press_frames: int, advance_frames: int) -> None:
    if action.lower() in {"wait", "idle", "none", "noop", "no-op"}:
        _advance(client, press_frames + advance_frames)
        return
    _press_and_wait(client, action, press_frames, advance_frames)


def _press_and_wait(client: httpx.Client, button: str, press_frames: int, advance_frames: int) -> None:
    client.post("/api/emulator/press", json={"button": button, "frames": press_frames}).raise_for_status()
    _advance(client, advance_frames)


def _advance(client: httpx.Client, frames: int) -> None:
    client.post("/api/emulator/frame-advance", json={"frames": frames}).raise_for_status()


def _mode(values: list[int]) -> int | None:
    if not values:
        return None
    counts: dict[int, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return max(counts.items(), key=lambda item: (item[1], -item[0]))[0]


def _same_ratio(values: list[int]) -> float:
    if not values:
        return 0.0
    mode_value = _mode(values)
    if mode_value is None:
        return 0.0
    return mean(1.0 if value == mode_value else 0.0 for value in values)


def _summary(payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "ok": payload["ok"],
        "output_path": str(output_path),
        "domain": payload["domain"],
        "actions": payload["actions"],
        "control_action": payload["control_action"],
        "cycles": payload["cycles"],
        "top_candidates": payload["ranked_candidates"][:30],
    }


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


def _parse_int(value: str) -> int:
    stripped = value.strip().lower()
    return int(stripped, 16) if stripped.startswith("0x") else int(stripped)


if __name__ == "__main__":
    raise SystemExit(main())
