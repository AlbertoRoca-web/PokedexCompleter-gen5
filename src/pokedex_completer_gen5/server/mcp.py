from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokedex_completer_gen5.application.service import service


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
    if name == "pokemon.get_macro_reliability":
        return {"reliability": service().macro_reliability(limit=int(arguments.get("limit", 1000)))}
    raise ValueError(f"Unknown MCP tool: {name}")
