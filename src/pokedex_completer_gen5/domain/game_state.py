from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GameMode = Literal["overworld", "menu", "battle", "dialog", "pc", "unknown"]
Facing = Literal["up", "down", "left", "right", "unknown"]


class Position(BaseModel):
    map_id: int | None = None
    x: int | None = None
    y: int | None = None
    facing: Facing = "unknown"


class PartyPokemon(BaseModel):
    species_id: int
    species_name: str
    level: int | None = None
    current_hp: int | None = None
    max_hp: int | None = None
    status: str | None = None


class BattleState(BaseModel):
    active: bool = False
    wild: bool = False
    opponent_species_id: int | None = None
    opponent_species_name: str | None = None
    opponent_level: int | None = None


class EmulatorState(BaseModel):
    game_profile: str = "unknown"
    mode: GameMode = "unknown"
    position: Position | None = None
    party: list[PartyPokemon] = Field(default_factory=list)
    battle: BattleState | None = None
    frame: int | None = None
    bridge_connected: bool = False
    raw_state: dict[str, Any] = Field(default_factory=dict)


def semantic_state_from_bridge(raw_state: dict[str, Any], *, game_profile: str = "white-us-eu-rev0") -> EmulatorState:
    payload = raw_state.get("result") if isinstance(raw_state.get("result"), dict) else raw_state
    frame = payload.get("frame") if isinstance(payload, dict) else None
    return EmulatorState(
        game_profile=game_profile,
        mode="unknown",
        frame=frame if isinstance(frame, int) else None,
        bridge_connected=bool(raw_state.get("ok", True)),
        raw_state=raw_state,
    )
