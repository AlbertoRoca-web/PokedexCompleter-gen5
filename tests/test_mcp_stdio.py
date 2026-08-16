from __future__ import annotations

import json

import mcp.types as types
import pytest

from pokedex_completer_gen5.server.mcp_stdio import call_tool_handler, create_mcp_server, list_tools_handler


def test_create_mcp_server() -> None:
    server = create_mcp_server()

    assert server.server_info.name == "pokedex-completer-gen5"


@pytest.mark.asyncio
async def test_mcp_list_tools_handler() -> None:
    result = await list_tools_handler(None, types.PaginatedRequestParams())  # type: ignore[arg-type]

    names = {tool.name for tool in result.tools}
    assert "pokemon.inspect_save" in names
    assert "pokemon.get_macro_reliability" in names


@pytest.mark.asyncio
async def test_mcp_call_tool_handler_error_is_structured() -> None:
    result = await call_tool_handler(
        None,  # type: ignore[arg-type]
        types.CallToolRequestParams(name="pokemon.nope", arguments={}),
    )

    assert result.is_error is True
    assert "Unknown MCP tool" in result.content[0].text  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_call_tool_handler_success() -> None:
    result = await call_tool_handler(
        None,  # type: ignore[arg-type]
        types.CallToolRequestParams(name="pokemon.get_macro_reliability", arguments={}),
    )

    assert result.is_error is False
    payload = json.loads(result.content[0].text)  # type: ignore[attr-defined]
    assert "reliability" in payload
