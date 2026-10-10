"""
Typed Tool Registry for Trust Analyst.
Exposes a unified typed registry used by both the analyst agent loop and the MCP server.
Enforces Pydantic input/output validation and audit logging of ToolCall nodes in FalkorDB.
"""

import inspect
import logging
import time
import uuid
from typing import Any, Callable, Type

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock

logger = logging.getLogger("trust_analyst.registry")


class ToolContext(BaseModel):
    """Execution context provided to tool handlers."""

    session_id: str = "sess-analyst-runtime"
    investigation_id: str | None = None
    actor_id: str = "agent-analyst"
    check_gateway: bool = True

    model_config = {"arbitrary_types_allowed": True}


class ToolResult(BaseModel):
    """Standardized tool response including evidence citation IDs."""

    tool: str
    success: bool
    evidence_ids: list[str] = Field(default_factory=list)
    data: Any = None
    error: str | None = None


class ToolDef:
    """Definition of a registered tool with typed input/output and governance flags."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel],
        output_schema: Type[BaseModel],
        handler: Callable[..., Any],
        read_only: bool = True,
        requires_approval: bool = False,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.handler = handler
        self.read_only = read_only
        self.requires_approval = requires_approval

    def to_mcp_dict(self) -> dict[str, Any]:
        """Returns JSON-schema compatible dictionary for MCP and Anthropic tool use."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "read_only": self.read_only,
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    """Singleton repository of all available agent and MCP tools."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel],
        output_schema: Type[BaseModel],
        read_only: bool = True,
        requires_approval: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a tool handler."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool = ToolDef(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                handler=fn,
                read_only=read_only,
                requires_approval=requires_approval,
            )
            self._tools[name] = tool
            return fn

        return decorator

    def register_tool_def(self, tool_def: ToolDef) -> None:
        """Directly registers a ToolDef instance."""
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> ToolDef:
        """Retrieves a registered tool definition by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> list[ToolDef]:
        """Lists all registered tools."""
        return list(self._tools.values())

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext | None = None,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> ToolResult:
        """
        Validates input arguments, evaluates the deterministic policy gateway,
        runs the tool, records the ToolCall audit node in FalkorDB, and returns ToolResult.
        """
        ctx = context or ToolContext()
        graph_client = client or get_graph_client()
        sim_clock = clock or get_clock()
        call_id = f"tc-{uuid.uuid4().hex[:12]}"
        start_ts = time.time()
        now_sim = sim_clock.now()

        if name not in self._tools:
            return ToolResult(
                tool=name,
                success=False,
                error=f"Tool '{name}' not found in registry.",
            )

        tool_def = self._tools[name]

        # 1. Input validation
        try:
            parsed_args = tool_def.input_schema.model_validate(arguments)
        except Exception as e:
            return ToolResult(
                tool=name,
                success=False,
                error=f"Invalid arguments for tool '{name}': {e}",
            )

        # 2. Policy Gateway Check (deterministic fail-closed governance)
        if ctx.check_gateway:
            from backend.app.agent.gateway import evaluate_gateway

            decision = evaluate_gateway(
                tool_def=tool_def,
                arguments=parsed_args.model_dump(),
                context=ctx,
                client=graph_client,
                clock=sim_clock,
            )
            if not decision.allowed:
                # Audit log the denial
                self._log_tool_call(
                    client=graph_client,
                    call_id=call_id,
                    tool_name=name,
                    arguments=arguments,
                    allowed=False,
                    reason=decision.reason,
                    evidence_ids=[],
                    duration_ms=int((time.time() - start_ts) * 1000),
                    sim_time=now_sim,
                    context=ctx,
                )
                return ToolResult(
                    tool=name,
                    success=False,
                    error=f"Policy Gateway Denied: {decision.reason}",
                )

        # 3. Tool execution
        try:
            sig = inspect.signature(tool_def.handler)
            kwargs = parsed_args.model_dump()
            if "context" in sig.parameters:
                kwargs["context"] = ctx
            if "client" in sig.parameters:
                kwargs["client"] = graph_client
            if "clock" in sig.parameters:
                kwargs["clock"] = sim_clock

            raw_result = tool_def.handler(**kwargs)

            # Format result
            if isinstance(raw_result, ToolResult):
                result = raw_result
            elif isinstance(raw_result, tuple) and len(raw_result) == 2:
                data, ev_ids = raw_result
                result = ToolResult(
                    tool=name,
                    success=True,
                    data=data,
                    evidence_ids=ev_ids,
                )
            else:
                result = ToolResult(
                    tool=name,
                    success=True,
                    data=raw_result,
                    evidence_ids=[],
                )
        except Exception as e:
            logger.exception(f"Error executing tool '{name}': {e}")
            result = ToolResult(
                tool=name,
                success=False,
                error=str(e),
            )

        duration_ms = int((time.time() - start_ts) * 1000)

        # 4. Audit Log to FalkorDB
        self._log_tool_call(
            client=graph_client,
            call_id=call_id,
            tool_name=name,
            arguments=arguments,
            allowed=result.success,
            reason=result.error or "Success",
            evidence_ids=result.evidence_ids,
            duration_ms=duration_ms,
            sim_time=now_sim,
            context=ctx,
        )

        return result

    def _log_tool_call(
        self,
        client: GraphClient,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        allowed: bool,
        reason: str,
        evidence_ids: list[str],
        duration_ms: int,
        sim_time: int,
        context: ToolContext,
    ) -> None:
        """Idempotently writes a ToolCall node to FalkorDB and links it to session and investigation."""
        try:
            client.query(
                """
                MERGE (tc:ToolCall {id: $id})
                SET tc.tool = $tool,
                    tc.allowed = $allowed,
                    tc.reason = $reason,
                    tc.duration_ms = $duration_ms,
                    tc.evidence_ids = $evidence_ids,
                    tc.at = $at
                """,
                {
                    "id": call_id,
                    "tool": tool_name,
                    "allowed": allowed,
                    "reason": reason[:256],
                    "duration_ms": duration_ms,
                    "evidence_ids": evidence_ids,
                    "at": sim_time,
                },
            )

            # Connect session if exists
            if context.session_id:
                client.query(
                    """
                    MATCH (s:AgentSession {id: $sid}), (tc:ToolCall {id: $tcid})
                    MERGE (s)-[:MADE_CALL]->(tc)
                    """,
                    {"sid": context.session_id, "tcid": call_id},
                    ignore_errors=True,
                )

            # Connect investigation if exists
            if context.investigation_id:
                client.query(
                    """
                    MATCH (inv:Investigation {id: $invid}), (tc:ToolCall {id: $tcid})
                    MERGE (inv)-[:MADE_CALL]->(tc)
                    """,
                    {"invid": context.investigation_id, "tcid": call_id},
                    ignore_errors=True,
                )
        except Exception as e:
            logger.warning(f"Could not write ToolCall audit node {call_id}: {e}")


# Global ToolRegistry singleton
registry = ToolRegistry()
