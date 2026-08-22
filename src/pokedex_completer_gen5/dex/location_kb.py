from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FlyPolicy:
    menu_toggle_button: str = "S"
    party_menu_label: str = "Pokemon"
    selected_pokemon: str = "Unfezant"
    move_label: str = "Fly"

    def to_dict(self) -> dict[str, str]:
        return {
            "menu_toggle_button": self.menu_toggle_button,
            "party_menu_label": self.party_menu_label,
            "selected_pokemon": self.selected_pokemon,
            "move_label": self.move_label,
        }


@dataclass(frozen=True)
class NavigationStep:
    operation: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"operation": self.operation, "value": self.value}


@dataclass(frozen=True)
class TargetLocation:
    national: int
    name: str
    location_area: str
    method: str
    min_level: int | None
    max_level: int | None
    chance: int | None


class LocationKnowledgeBase:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.fly_policy = FlyPolicy(
            menu_toggle_button=str(payload.get("fly_policy", {}).get("menu_toggle_button", "S")),
        )
        self.targets = tuple(self._target_locations(payload.get("targets", [])))

    @classmethod
    def load(cls, path: Path) -> LocationKnowledgeBase:
        return cls(json.loads(path.read_text(encoding="utf-8-sig")))

    def locations_for(self, national: int) -> tuple[TargetLocation, ...]:
        seen: set[tuple[int, str, str, int | None, int | None]] = set()
        locations: list[TargetLocation] = []
        for location in self.targets:
            key = (location.national, location.location_area, location.method, location.min_level, location.max_level)
            if location.national == national and key not in seen:
                seen.add(key)
                locations.append(location)
        return tuple(locations)

    def shortest_route(
        self,
        *,
        current_area: str,
        target_national: int,
        fly_available: bool,
    ) -> tuple[NavigationStep, ...]:
        locations = self.locations_for(target_national)
        if not locations:
            raise ValueError(f"No location knowledge for national species {target_national}.")
        target = min(locations, key=lambda location: _walking_area_cost(current_area, location.location_area))
        walk_cost = _walking_area_cost(current_area, target.location_area)
        if fly_available and walk_cost > 1:
            return (
                NavigationStep("toggle-menu", self.fly_policy.menu_toggle_button),
                NavigationStep("open-party", self.fly_policy.party_menu_label),
                NavigationStep("select-pokemon", self.fly_policy.selected_pokemon),
                NavigationStep("select-move", self.fly_policy.move_label),
                NavigationStep("select-destination", target.location_area),
                NavigationStep("verify-location", target.location_area),
            )
        return (
            NavigationStep("walk-to-area", target.location_area),
            NavigationStep("verify-location", target.location_area),
        )

    @staticmethod
    def _target_locations(raw_targets: Any) -> list[TargetLocation]:
        if not isinstance(raw_targets, list):
            return []
        locations: list[TargetLocation] = []
        for target in raw_targets:
            if not isinstance(target, dict):
                continue
            national = target.get("national")
            name = target.get("name")
            raw_locations = target.get("locations")
            if not isinstance(national, int) or not isinstance(name, str) or not isinstance(raw_locations, list):
                continue
            for raw_location in raw_locations:
                if not isinstance(raw_location, dict):
                    continue
                raw_area = raw_location.get("location_area")
                encounters = raw_location.get("encounters")
                areas = [raw_area] if isinstance(raw_area, str) else raw_area if isinstance(raw_area, list) else []
                if not areas or not isinstance(encounters, list):
                    continue
                for encounter in encounters:
                    if not isinstance(encounter, dict):
                        continue
                    for area in areas:
                        if not isinstance(area, str):
                            continue
                        locations.append(
                            TargetLocation(
                                national=national,
                                name=name,
                                location_area=area,
                                method=str(encounter.get("method", "unknown")),
                                min_level=_optional_int(encounter.get("min_level")),
                                max_level=_optional_int(encounter.get("max_level")),
                                chance=_optional_int(encounter.get("chance")),
                            )
                        )
        return locations


def _walking_area_cost(current_area: str, target_area: str) -> int:
    if current_area == target_area:
        return 0
    # Precise overworld graph costs are learned from emulator transitions. Until
    # then, different area names are conservatively more expensive than Fly.
    return 2


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None
