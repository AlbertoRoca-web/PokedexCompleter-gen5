from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokedex_completer_gen5.application.service import service
from pokedex_completer_gen5.autonomy.capture_protocol import post_capture_save_protocol
from pokedex_completer_gen5.dex.breeding_protocol import build_breeding_plan
from pokedex_completer_gen5.dex.catch_legality import CatchContext, choose_legal_ball
from pokedex_completer_gen5.dex.encounter_policy import decide_encounter
from pokedex_completer_gen5.dex.evolution_kb import evolution_record
from pokedex_completer_gen5.dex.nickname_generator import generate_safe_nickname
from pokedex_completer_gen5.dex.route_target_planner import build_route_target_plan
from pokedex_completer_gen5.persistence.living_dex_progress import (
    build_master_route_cross_reference,
    record_verified_catch,
)


@dataclass(frozen=True)
class McpToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


TOOL_SPECS: tuple[McpToolSpec, ...] = (
    McpToolSpec(
        name="pokemon.inspect_save",
        description="Read a local Gen 5 save file and return physical party/PC bodies plus planner status.",
        input_schema={
            "type": "object",
            "properties": {
                "save_path": {"type": "string"},
                "game": {"type": "string", "default": "white"},
                "copy": {"type": "string", "default": "auto"},
            },
            "required": ["save_path"],
        },
    ),
    McpToolSpec(
        name="pokemon.get_missing_species",
        description="Return missing regional Living Dex species when the selected game planner is supported.",
        input_schema={
            "type": "object",
            "properties": {
                "save_path": {"type": "string"},
                "game": {"type": "string", "default": "white"},
                "copy": {"type": "string", "default": "auto"},
            },
            "required": ["save_path"],
        },
    ),
    McpToolSpec(
        name="pokemon.plan_missing_targets_by_route",
        description="Group save-missing catchable Pokemon by encounter area and choose walk/Fly navigation.",
        input_schema={
            "type": "object",
            "properties": {
                "save_path": {"type": "string"},
                "current_area": {"type": "string"},
                "fly_available": {"type": "boolean", "default": True},
                "game": {"type": "string", "default": "white"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["save_path", "current_area"],
        },
    ),
    McpToolSpec(
        name="pokemon.choose_legal_ball",
        description=(
            "Choose a PKHeX/HOME-compatible ball. Master Ball is always forbidden; Safari Ball is illegal here."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "available_balls": {"type": "array", "items": {"type": "string"}},
                "game": {"type": "string", "default": "white"},
                "turn": {"type": "integer", "default": 1},
                "is_cave_or_night": {"type": "boolean", "default": False},
                "is_water_or_bug": {"type": "boolean", "default": False},
                "is_safari_zone": {"type": "boolean", "default": False},
            },
            "required": ["available_balls"],
        },
    ),
    McpToolSpec(
        name="pokemon.decide_encounter",
        description="Catch or run by live PC/party/session inventory, family quota, and route-specific spawn rarity.",
        input_schema={
            "type": "object",
            "properties": {
                "save_path": {"type": "string"},
                "species_id": {"type": "integer"},
                "encounter_chance": {"type": "number"},
                "game": {"type": "string", "default": "white"},
            },
            "required": ["save_path", "species_id", "encounter_chance"],
        },
    ),
    McpToolSpec(
        name="pokemon.record_verified_catch",
        description="Record a screenshot-verified legal catch in the session master inventory.",
        input_schema={
            "type": "object",
            "properties": {
                "species_id": {"type": "integer"},
                "species_name": {"type": "string"},
                "ball": {"type": "string"},
                "location_area": {"type": "string"},
                "evidence_path": {"type": "string"},
            },
            "required": ["species_id", "species_name", "ball", "location_area", "evidence_path"],
        },
    ),
    McpToolSpec(
        name="pokemon.get_route_cross_reference",
        description=(
            "Merge save PC/party bodies with verified session catches and return missing targets for the route."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "save_path": {"type": "string"},
                "current_area": {"type": "string"},
                "fly_available": {"type": "boolean", "default": True},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["save_path", "current_area"],
        },
    ),
    McpToolSpec(
        name="pokemon.generate_safe_nickname",
        description="Generate a fun ASCII nickname within Gen 5 length limits for PKHeX/HOME-safe use.",
        input_schema={
            "type": "object",
            "properties": {"seed": {"type": ["integer", "string", "null"]}},
        },
    ),
    McpToolSpec(
        name="pokemon.get_evolution_record",
        description="Return verified PokeAPI evolution triggers for a Unova National species ID.",
        input_schema={
            "type": "object",
            "properties": {"species_id": {"type": "integer"}},
            "required": ["species_id"],
        },
    ),
    McpToolSpec(
        name="pokemon.get_breeding_protocol",
        description="Build a Ditto-aware, Gen 5 legal breeding plan before evolution gap filling.",
        input_schema={
            "type": "object",
            "properties": {
                "parent_species": {"type": "string"},
                "base_species": {"type": "string"},
                "eggs_needed": {"type": "integer"},
                "ditto_owned": {"type": "boolean"},
                "bicycle_owned": {"type": "boolean", "default": True}
            },
            "required": ["parent_species", "base_species", "eggs_needed", "ditto_owned"],
        },
    ),
    McpToolSpec(
        name="pokemon.get_post_capture_protocol",
        description="Return the mandatory save-and-refresh loop performed after every verified capture.",
        input_schema={"type": "object", "properties": {}},
    ),
    McpToolSpec(
        name="pokemon.get_macro_reliability",
        description="Return local persistent macro feedback reliability summary.",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 1000}},
        },
    ),
)


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in TOOL_SPECS
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "pokemon.inspect_save":
        return service().inspect_save(
            Path(str(arguments["save_path"])),
            str(arguments.get("game", "white")),
            str(arguments.get("copy", "auto")),
        )
    if name == "pokemon.get_missing_species":
        payload = service().inspect_save(
            Path(str(arguments["save_path"])),
            str(arguments.get("game", "white")),
            str(arguments.get("copy", "auto")),
        )
        dex_status = payload.get("dex_status")
        if not isinstance(dex_status, dict):
            return {"planner_supported": False, "missing": []}
        return {
            "planner_supported": True,
            "missing": dex_status.get("missing", []),
        }
    if name == "pokemon.plan_missing_targets_by_route":
        return build_route_target_plan(
            save_path=Path(str(arguments["save_path"])),
            current_area=str(arguments["current_area"]),
            fly_available=bool(arguments.get("fly_available", True)),
            game=str(arguments.get("game", "white")),
            limit=int(arguments.get("limit", 20)),
        )
    if name == "pokemon.choose_legal_ball":
        raw_balls = arguments.get("available_balls", [])
        if not isinstance(raw_balls, list) or not all(isinstance(ball, str) for ball in raw_balls):
            raise ValueError("available_balls must be a list of strings")
        context = CatchContext(
            game=str(arguments.get("game", "white")),
            turn=int(arguments.get("turn", 1)),
            is_cave_or_night=bool(arguments.get("is_cave_or_night", False)),
            is_water_or_bug=bool(arguments.get("is_water_or_bug", False)),
            is_safari_zone=bool(arguments.get("is_safari_zone", False)),
        )
        return {"selected_ball": choose_legal_ball(raw_balls, context), "legal": True}
    if name == "pokemon.decide_encounter":
        return decide_encounter(
            save_path=Path(str(arguments["save_path"])),
            species_id=int(arguments["species_id"]),
            encounter_chance=float(arguments["encounter_chance"]),
            game=str(arguments.get("game", "white")),
        ).to_dict()
    if name == "pokemon.record_verified_catch":
        catch = record_verified_catch(
            species_id=int(arguments["species_id"]),
            species_name=str(arguments["species_name"]),
            ball=str(arguments["ball"]),
            location_area=str(arguments["location_area"]),
            evidence_path=str(arguments["evidence_path"]),
        )
        return {"recorded": True, "catch": catch.__dict__}
    if name == "pokemon.get_route_cross_reference":
        return build_master_route_cross_reference(
            save_path=Path(str(arguments["save_path"])),
            current_area=str(arguments["current_area"]),
            fly_available=bool(arguments.get("fly_available", True)),
            limit=int(arguments.get("limit", 20)),
        )
    if name == "pokemon.generate_safe_nickname":
        return {"nickname": generate_safe_nickname(seed=arguments.get("seed")), "home_safe": True}
    if name == "pokemon.get_evolution_record":
        return evolution_record(int(arguments["species_id"]))
    if name == "pokemon.get_breeding_protocol":
        return build_breeding_plan(
            parent_species=str(arguments["parent_species"]),
            base_species=str(arguments["base_species"]),
            eggs_needed=int(arguments["eggs_needed"]),
            ditto_owned=bool(arguments["ditto_owned"]),
            bicycle_owned=bool(arguments.get("bicycle_owned", True)),
        ).to_dict()
    if name == "pokemon.get_post_capture_protocol":
        return post_capture_save_protocol()
    if name == "pokemon.get_macro_reliability":
        return {"reliability": service().macro_reliability(limit=int(arguments.get("limit", 1000)))}
    raise ValueError(f"Unknown MCP tool: {name}")
