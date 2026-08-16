from __future__ import annotations

import json
from typing import Any

import anyio
import mcp.types as types
from mcp.server import stdio
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server

from pokedex_completer_gen5 import __version__
from pokedex_completer_gen5.server.mcp import call_tool, list_tools


async def list_tools_handler(
    _context: ServerRequestContext[Any, Any],
    _params: types.PaginatedRequestParams,
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
            )
            for tool in list_tools()
        ]
    )


async def call_tool_handler(
    _context: ServerRequestContext[Any, Any],
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    arguments = params.arguments if isinstance(params.arguments, dict) else {}
    try:
        result = call_tool(params.name, arguments)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, sort_keys=True))]
        )
    except Exception as exc:
        return types.CallToolResult(
            is_error=True,
            content=[types.TextContent(type="text", text=f"{type(exc).__name__}: {exc}")],
        )


def create_mcp_server() -> Server:
    server = Server("pokedex-completer-gen5", version=__version__)
    server.add_request_handler("tools/list", types.PaginatedRequestParams, list_tools_handler)
    server.add_request_handler("tools/call", types.CallToolRequestParams, call_tool_handler)
    return server


async def run_stdio_server() -> None:
    server = create_mcp_server()
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    anyio.run(run_stdio_server)


if __name__ == "__main__":
    main()
