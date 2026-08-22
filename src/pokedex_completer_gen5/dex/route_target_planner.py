from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokedex_completer_gen5.dex.bw_unova import UNOVA_DEX
from pokedex_completer_gen5.dex.catchable_targets import build_catchable_inventory_report
from pokedex_completer_gen5.dex.location_kb import FlyPolicy, LocationKnowledgeBase, NavigationStep
from pokedex_completer_gen5.saveio.gen5_save import build_save_payload

DEFAULT_KB_PATH = Path("data/knowledge/white-catchable-locations.jsonl")


@dataclass(frozen=True)
class RouteTarget:
    national: int
    name: str
    methods: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"national": self.national, "name": self.name, "methods": list(self.methods)}


@dataclass(frozen=True)
class RouteTargetGroup:
    area: str
    missing_targets: tuple[RouteTarget, ...]
    walking_cost: int
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "missing_target_count": len(self.missing_targets),
            "missing_targets": [target.to_dict() for target in self.missing_targets],
            "walking_cost": self.walking_cost,
            "score": self.score,
        }


def build_route_target_plan(
    *,
    save_path: Path,
    current_area: str,
    fly_available: bool,
    game: str = "white",
    kb_path: Path = DEFAULT_KB_PATH,
    limit: int = 20,
    additional_owned_ids: set[int] | None = None,
    additional_owned_counts: dict[int, int] | None = None,
) -> dict[str, Any]:
    payload = build_save_payload(save_path, game, "auto")
    report = build_catchable_inventory_report(payload, game, mode="direct")
    additional_owned_ids = additional_owned_ids or set()
    master_counts = _master_counts(payload, additional_owned_counts or {})
    missing = {
        target.national: target.name
        for target in report.missing_targets
        if target.national not in additional_owned_ids and not _family_quota_satisfied(target.national, master_counts)
    }
    knowledge_base = LocationKnowledgeBase.load(kb_path)
    grouped: dict[str, dict[int, set[str]]] = {}
    for national in missing:
        for location in knowledge_base.locations_for(national):
            grouped.setdefault(location.location_area, {}).setdefault(national, set()).add(location.method)

    route_groups = []
    for area, species in grouped.items():
        cost = knowledge_base.walking_cost(current_area, area)
        targets = tuple(
            RouteTarget(national, missing[national], tuple(sorted(methods)))
            for national, methods in sorted(species.items())
        )
        score = len(targets) / max(1, min(cost, 20))
        route_groups.append(RouteTargetGroup(area, targets, cost, round(score, 3)))
    route_groups.sort(key=lambda group: (-group.score, group.walking_cost, group.area))
    recommendation = route_groups[0] if route_groups else None
    navigation = _navigation_steps(
        recommendation.area if recommendation else current_area,
        recommendation.walking_cost if recommendation else 0,
        fly_available,
        knowledge_base.fly_policy,
    )
    return {
        "game": game,
        "current_area": current_area,
        "fly_available": fly_available,
        "missing_direct_target_count": len(report.missing_targets),
        "route_count": len(route_groups),
        "recommended_route": recommendation.to_dict() if recommendation else None,
        "navigation": [step.to_dict() for step in navigation],
        "routes": [group.to_dict() for group in route_groups[:limit]],
    }


def _master_counts(payload: dict[str, Any], additional: dict[int, int]) -> Counter[int]:
    counts: Counter[int] = Counter()
    raw_counts = payload.get("selected_species_counts", [])
    if not isinstance(raw_counts, list):
        raw_counts = []
    for entry in raw_counts:
        if not isinstance(entry, dict):
            continue
        species_id = entry.get("species_id")
        count = entry.get("count")
        if isinstance(species_id, int) and isinstance(count, int):
            counts[species_id] = max(counts[species_id], count)
    for species_id, count in additional.items():
        counts[species_id] = max(counts[species_id], count)
    return counts


def _family_quota_satisfied(species_id: int, counts: Counter[int]) -> bool:
    pokemon = next((entry for entry in UNOVA_DEX if entry.national == species_id), None)
    if pokemon is None:
        return False
    family_ids = {entry.national for entry in UNOVA_DEX if entry.name in pokemon.family}
    return sum(counts[national] for national in family_ids) >= min(3, len(pokemon.family))


def _navigation_steps(
    area: str,
    walking_cost: int,
    fly_available: bool,
    fly_policy: FlyPolicy,
) -> tuple[NavigationStep, ...]:
    if fly_available and walking_cost > 1:
        return (
            NavigationStep("toggle-menu", fly_policy.menu_toggle_button),
            NavigationStep("open-party", fly_policy.party_menu_label),
            NavigationStep("select-pokemon", fly_policy.selected_pokemon),
            NavigationStep("select-move", fly_policy.move_label),
            NavigationStep("select-destination", area),
            NavigationStep("verify-location", area),
        )
    return (NavigationStep("walk-to-area", area), NavigationStep("verify-location", area))
