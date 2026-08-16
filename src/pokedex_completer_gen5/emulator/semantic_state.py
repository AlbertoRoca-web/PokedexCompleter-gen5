from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BridgeRequest = Callable[[str, dict[str, Any] | None], dict[str, Any]]

PROFILE_DIR = Path(__file__).resolve().parents[3] / "data" / "emulator_memory_profiles"
DEFAULT_PROFILE_ID = "white_us_eu"


@dataclass(frozen=True)
class MemoryField:
    address: int
    length: int = 1
    kind: str = "u8"
    meaning: dict[str, list[int]] = field(default_factory=dict)
    confidence: str = "unknown"
    evidence: str = ""


@dataclass(frozen=True)
class MemoryProfile:
    profile_id: str
    game: str
    domain: str
    fields: dict[str, MemoryField | None]
    enum_maps: dict[str, dict[str, str]] = field(default_factory=dict)
    notes: str = ""

    def missing_fields(self) -> list[str]:
        return [name for name, memory_field in self.fields.items() if memory_field is None]

    def known_fields(self) -> list[str]:
        return [name for name, memory_field in self.fields.items() if memory_field is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "game": self.game,
            "domain": self.domain,
            "known_fields": self.known_fields(),
            "missing_fields": self.missing_fields(),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticStateSnapshot:
    profile: MemoryProfile
    bridge_info: dict[str, Any]
    raw_values: dict[str, Any]
    state: dict[str, Any]
    confidence: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.state.get("mode", "unknown"),
            "confidence": self.confidence,
            "reasons": self.reasons,
            "profile": self.profile.to_dict(),
            "bridge_info": self.bridge_info,
            "raw_values": self.raw_values,
            "state": self.state,
            "missing_profile_fields": self.profile.missing_fields(),
        }


def load_memory_profile(profile_id: str = DEFAULT_PROFILE_ID) -> MemoryProfile:
    path = PROFILE_DIR / f"{profile_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_fields = payload.get("fields", {})
    fields: dict[str, MemoryField | None] = {}
    for name, raw_field in raw_fields.items():
        fields[str(name)] = _parse_memory_field(raw_field)
    return MemoryProfile(
        profile_id=str(payload.get("profile_id", profile_id)),
        game=str(payload.get("game", "unknown")),
        domain=str(payload.get("domain", "")),
        fields=fields,
        enum_maps=_parse_enum_maps(payload.get("enum_maps", {})),
        notes=str(payload.get("notes", "")),
    )


def build_semantic_state(
    bridge_request: BridgeRequest,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
) -> SemanticStateSnapshot:
    profile = load_memory_profile(profile_id)
    bridge_info = _safe_bridge_info(bridge_request)
    raw_values = _read_known_fields(bridge_request, profile)
    state = _interpret_state(profile, raw_values)
    confidence, reasons = _score_state(profile, raw_values, state)
    return SemanticStateSnapshot(
        profile=profile,
        bridge_info=bridge_info,
        raw_values=raw_values,
        state=state,
        confidence=confidence,
        reasons=reasons,
    )


def _parse_memory_field(raw_field: Any) -> MemoryField | None:
    if raw_field is None:
        return None
    if isinstance(raw_field, int):
        return MemoryField(address=raw_field)
    if isinstance(raw_field, str):
        return MemoryField(address=int(raw_field, 16) if raw_field.lower().startswith("0x") else int(raw_field))
    if isinstance(raw_field, dict):
        raw_address = raw_field.get("address")
        if raw_address is None:
            return None
        address = (
            int(raw_address, 16)
            if isinstance(raw_address, str) and raw_address.lower().startswith("0x")
            else int(raw_address)
        )
        return MemoryField(
            address=address,
            length=int(raw_field.get("length", 1)),
            kind=str(raw_field.get("kind", "u8")),
            meaning=_parse_meaning(raw_field.get("meaning", {})),
            confidence=str(raw_field.get("confidence", "unknown")),
            evidence=str(raw_field.get("evidence", "")),
        )
    raise ValueError(f"Unsupported memory field: {raw_field!r}")


def _parse_meaning(raw_meaning: Any) -> dict[str, list[int]]:
    if not isinstance(raw_meaning, dict):
        return {}
    parsed: dict[str, list[int]] = {}
    for name, raw_values in raw_meaning.items():
        if isinstance(raw_values, list):
            parsed[str(name)] = [int(value) for value in raw_values]
    return parsed


def _parse_enum_maps(raw_maps: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw_maps, dict):
        return {}
    parsed: dict[str, dict[str, str]] = {}
    for name, raw_map in raw_maps.items():
        if isinstance(raw_map, dict):
            parsed[str(name)] = {str(key): str(value) for key, value in raw_map.items()}
    return parsed


def _safe_bridge_info(bridge_request: BridgeRequest) -> dict[str, Any]:
    try:
        return bridge_request("bridge.info", None)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _read_known_fields(bridge_request: BridgeRequest, profile: MemoryProfile) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, memory_field in profile.fields.items():
        if memory_field is None:
            continue
        response = bridge_request(
            "memory.read_bytes",
            {"domain": profile.domain, "address": memory_field.address, "length": memory_field.length},
        )
        values[name] = {
            "field": {
                "address": memory_field.address,
                "hex_address": f"0x{memory_field.address:X}",
                "length": memory_field.length,
                "kind": memory_field.kind,
                "meaning": memory_field.meaning,
                "confidence": memory_field.confidence,
                "evidence": memory_field.evidence,
            },
            "response": response,
            "value": _decode_value(response, memory_field),
        }
    return values


def _decode_value(response: dict[str, Any], memory_field: MemoryField) -> int | None:
    values_csv = str(response.get("values_csv", ""))
    values = [int(item) for item in values_csv.split(",") if item]
    if not values:
        return None
    if memory_field.kind == "u16le":
        return values[0] | ((values[1] if len(values) > 1 else 0) << 8)
    if memory_field.kind == "u32le":
        return sum((values[index] if index < len(values) else 0) << (8 * index) for index in range(4))
    return values[0]


def _interpret_state(profile: MemoryProfile, raw_values: dict[str, Any]) -> dict[str, Any]:
    menu_state = _field_value(raw_values, "menu_state")
    battle_state = _field_value(raw_values, "battle_state")
    transition_state = _field_value(raw_values, "transition_state")
    menu_open = _semantic_bool(profile, raw_values, "menu_state", true_label="open", false_label="closed")
    battle_active = _semantic_bool(profile, raw_values, "battle_state", true_label="active", false_label="inactive")
    transitioning = _semantic_bool(profile, raw_values, "transition_state", true_label="active", false_label="inactive")
    mode = "unknown"
    if battle_active is True or _legacy_nonzero_state(profile, "battle_state", battle_active, battle_state):
        mode = "battle"
    elif menu_open is True or _legacy_nonzero_state(profile, "menu_state", menu_open, menu_state):
        mode = "menu"
    elif transitioning is True or _legacy_nonzero_state(profile, "transition_state", transitioning, transition_state):
        mode = "transition"
    elif menu_open is False and battle_active is not True and transitioning is not True:
        mode = "overworld"
    facing_value = _field_value(raw_values, "facing")
    return {
        "game_profile": profile.profile_id,
        "mode": mode,
        "menu_open": menu_open,
        "battle_active": battle_active,
        "transitioning": transitioning,
        "position": {
            "map_id": _field_value(raw_values, "map_id"),
            "x": _field_value(raw_values, "player_x"),
            "y": _field_value(raw_values, "player_y"),
            "facing": _enum_value(profile, "facing", facing_value),
            "facing_raw": facing_value,
        },
    }


def _semantic_bool(
    profile: MemoryProfile,
    raw_values: dict[str, Any],
    field_name: str,
    *,
    true_label: str,
    false_label: str,
) -> bool | None:
    value = _field_value(raw_values, field_name)
    if value is None:
        return None
    memory_field = profile.fields.get(field_name)
    if memory_field is None:
        return None
    if value in memory_field.meaning.get(true_label, []):
        return True
    if value in memory_field.meaning.get(false_label, []):
        return False
    return None


def _legacy_nonzero_state(
    profile: MemoryProfile,
    field_name: str,
    semantic_value: bool | None,
    raw_value: int | None,
) -> bool:
    memory_field = profile.fields.get(field_name)
    if memory_field is None or memory_field.meaning:
        return False
    return semantic_value is None and raw_value not in {None, 0}


def _score_state(profile: MemoryProfile, raw_values: dict[str, Any], state: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    total = len(profile.fields)
    known = len(raw_values)
    if total == 0:
        return 0.0, ["memory profile has no fields"]
    coverage = known / total
    reasons.append(f"profile_field_coverage={known}/{total}")
    if state.get("mode") == "unknown":
        reasons.append("mode is unknown because required RAM offsets are missing")
    else:
        reasons.append(f"mode inferred as {state['mode']}")
    return round(min(0.95, coverage), 3), reasons


def _field_value(raw_values: dict[str, Any], name: str) -> int | None:
    payload = raw_values.get(name)
    return int(payload["value"]) if isinstance(payload, dict) and isinstance(payload.get("value"), int) else None


def _enum_value(profile: MemoryProfile, enum_name: str, value: int | None) -> str:
    if value is None:
        return "unknown"
    return profile.enum_maps.get(enum_name, {}).get(str(value), "unknown")
