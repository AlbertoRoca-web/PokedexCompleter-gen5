from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pokedex_completer_gen5.persistence.living_dex_progress import build_master_route_cross_reference

TravelMode = Literal["stay", "walk", "fly"]
FLY_FIXED_COST = 2


def plan_route_transition(
    *,
    save_path: Path,
    current_area: str,
    available_methods: set[str],
    fly_available: bool,
    kb_path: Path = Path("data/knowledge/white-catchable-locations.jsonl"),
) -> dict[str, Any]:
    master = build_master_route_cross_reference(
        save_path=save_path,
        current_area=current_area,
        fly_available=fly_available,
        limit=1000,
    )
    routes = master["route_plan"]["routes"]
    current = next((route for route in routes if route["area"] == current_area), None)
    current_targets = _accessible_targets(current, available_methods)
    if current_targets:
        return {
            "current_area": current_area,
            "route_complete": False,
            "travel_mode": "stay",
            "remaining_accessible_targets": current_targets,
            "reason": "Current route still has missing targets available with owned field methods.",
        }

    candidates = []
    for route in routes:
        if route["area"] == current_area:
            continue
        targets = _accessible_targets(route, available_methods)
        if targets:
            candidates.append((route, targets))
    if not candidates:
        return {
            "current_area": current_area,
            "route_complete": True,
            "travel_mode": "stay",
            "remaining_accessible_targets": [],
            "reason": "No remaining catchable targets match current field capabilities.",
        }
    candidates.sort(key=lambda pair: (-pair[0]["score"], pair[0]["walking_cost"], pair[0]["area"]))
    destination, targets = candidates[0]
    walking_cost = int(destination["walking_cost"])
    mode = choose_travel_mode(walking_cost=walking_cost, fly_available=fly_available)
    return {
        "current_area": current_area,
        "route_complete": True,
        "destination_area": destination["area"],
        "travel_mode": mode,
        "walking_cost": walking_cost,
        "fly_fixed_cost": FLY_FIXED_COST,
        "destination_targets": targets,
        "navigation": _navigation(mode, destination["area"]),
        "reason": f"Current route exhausted; {mode} is the fastest available travel mode.",
    }


def choose_travel_mode(*, walking_cost: int, fly_available: bool) -> Literal["walk", "fly"]:
    return "fly" if fly_available and walking_cost > FLY_FIXED_COST else "walk"


def _accessible_targets(route: dict[str, Any] | None, available_methods: set[str]) -> list[dict[str, Any]]:
    if route is None:
        return []
    targets = []
    for target in route.get("missing_targets", []):
        methods = {str(method) for method in target.get("methods", [])}
        if _methods_overlap(methods, available_methods):
            targets.append(target)
    return targets


def _methods_overlap(target_methods: set[str], available_methods: set[str]) -> bool:
    for method in target_methods:
        normalized = method.replace("-", "_")
        if method in available_methods or normalized in available_methods:
            return True
        if "walk" in method and "grass" in available_methods:
            return True
        if "surf" in method and "surf" in available_methods:
            return True
        if "rod" in method and "super-rod" in available_methods:
            return True
    return False


def _navigation(mode: Literal["walk", "fly"], destination: str) -> list[dict[str, str]]:
    if mode == "walk":
        return [
            {"operation": "walk-to-area", "value": destination},
            {"operation": "verify-map", "value": destination},
        ]
    return [
        {"operation": "toggle-menu", "value": "S"},
        {"operation": "open-party", "value": "Pokemon"},
        {"operation": "select-pokemon", "value": "Unfezant"},
        {"operation": "select-move", "value": "Fly"},
        {"operation": "select-destination", "value": destination},
        {"operation": "verify-map", "value": destination},
    ]
