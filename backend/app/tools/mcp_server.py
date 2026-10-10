"""
Model Context Protocol (MCP) Server for Trust Analyst.
Exposes the unified typed tool registry over the official MCP protocol.
Allows external MCP clients to discover tools, execute them, and receive citations.
"""

import asyncio
import inspect
import json
import logging
from typing import Any

from mcp.server.mcpserver import MCPServer

# Import all tool modules to populate registry
import backend.app.tools.action_tools  # noqa: F401
import backend.app.tools.context_tools  # noqa: F401
import backend.app.tools.control_tools  # noqa: F401
import backend.app.tools.graph_tools  # noqa: F401
import backend.app.tools.memory_tools  # noqa: F401
import backend.app.tools.telemetry_tools  # noqa: F401
from backend.app.tools.registry import ToolContext, ToolDef, registry

logger = logging.getLogger("trust_analyst.mcp")


def _make_mcp_wrapper(tool_def: ToolDef):
    """
    Constructs a clean wrapper function with signature matching tool_def.input_schema.
    Ensures Pydantic and MCP generate a valid tool input schema without internal dependency parameters.
    """
    fields = tool_def.input_schema.model_fields
    params = []
    for fname, fval in fields.items():
        default = inspect.Parameter.empty if fval.is_required() else fval.default
        params.append(
            inspect.Parameter(
                name=fname,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=fval.annotation,
            )
        )

    sig = inspect.Signature(parameters=params, return_annotation=str)

    def wrapper(**kwargs) -> str:
        ctx = ToolContext(session_id="sess-analyst-runtime")
        res = registry.execute(name=tool_def.name, arguments=kwargs, context=ctx)
        return json.dumps(res.model_dump())

    wrapper.__signature__ = sig
    wrapper.__name__ = tool_def.name
    wrapper.__doc__ = tool_def.description
    return wrapper


def create_mcp_server() -> MCPServer:
    """
    Creates an MCPServer instance exposing every tool registered in ToolRegistry.
    """
    server = MCPServer(name="trust-analyst")

    for tool_def in registry.list_tools():
        wrapper = _make_mcp_wrapper(tool_def)
        server.add_tool(
            wrapper,
            name=tool_def.name,
            description=tool_def.description,
        )

    logger.info(f"Initialized MCP server with {len(registry.list_tools())} tools.")
    return server


async def list_registered_tools() -> list[dict[str, Any]]:
    """Convenience helper for programmatic inspection of registered MCP tools."""
    server = create_mcp_server()
    tools = await server.list_tools()
    return [{"name": t.name, "description": t.description} for t in tools]


if __name__ == "__main__":
    server = create_mcp_server()
    asyncio.run(server.run_stdio_async())
