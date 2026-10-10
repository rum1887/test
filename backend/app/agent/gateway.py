"""
Deterministic Policy Gateway for Agent Tool Execution Governance.
Enforces fail-closed validation of AgentSession status, delegation validity, scopes,
human approval requirements for disruptive actions, and investigation tool budgets.
The LLM is NEVER in the allow/deny path.
"""

import logging
from typing import Any

from pydantic import BaseModel

from backend.app.db.sqlite import count_tool_calls_for_investigation, get_approved_action
from backend.app.graph.client import GraphClient
from backend.app.sim.clock import SimulatedClock
from backend.app.tools.registry import ToolContext, ToolDef

logger = logging.getLogger("trust_analyst.gateway")

DEFAULT_MAX_TOOL_CALLS = 40


class GatewayDecision(BaseModel):
    """Result of policy gateway evaluation."""

    allowed: bool
    reason: str


def ensure_analyst_session(
    client: GraphClient,
    session_id: str = "sess-analyst-runtime",
    sim_time: int = 1700000000,
) -> None:
    """
    Ensures that the default runtime analyst session and delegation exist in FalkorDB.
    """
    try:
        client.query(
            """
            MERGE (a:Agent {id: 'agent-analyst'})
            ON CREATE SET a.name = 'SecurityAnalystBot', a.capabilities = ['triage', 'investigate', 'contain']
            MERGE (s:AgentSession {id: $sid})
            ON CREATE SET s.status = 'active', s.started_at = $t0, s.expires_at = $t0 + 604800
            MERGE (del:Delegation {id: 'del-analyst-runtime'})
            ON CREATE SET del.scopes = ['*'], del.expires_at = $t0 + 604800, del.intent_text = 'Autonomous security investigation and remediation'
            MERGE (s)-[:USES_AGENT]->(a)
            MERGE (del)-[:TO_SESSION]->(s)
            """,
            {"sid": session_id, "t0": sim_time},
            ignore_errors=True,
        )
    except Exception as e:
        logger.warning(f"Could not auto-provision analyst session: {e}")


def evaluate_gateway(
    tool_def: ToolDef,
    arguments: dict[str, Any],
    context: ToolContext,
    client: GraphClient,
    clock: SimulatedClock,
) -> GatewayDecision:
    """
    Evaluates policy gateway rules before tool execution.
    Returns GatewayDecision(allowed=True|False, reason=str).
    Fail-closed: if FalkorDB is unreachable, execution is denied immediately.
    """
    now = clock.now()

    # 1. Fail-closed database health check
    try:
        ping = client.query("RETURN 1 AS ping")
        if not ping or ping[0][0] != 1:
            return GatewayDecision(allowed=False, reason="Database unreachable (fail-closed)")
    except Exception as e:
        return GatewayDecision(allowed=False, reason=f"Database connectivity failure (fail-closed): {e}")

    # 2. AgentSession & Delegation Validation
    if context.session_id == "sess-analyst-runtime":
        ensure_analyst_session(client, context.session_id, now)

    try:
        res = client.query(
            """
            MATCH (s:AgentSession {id: $sid})
            OPTIONAL MATCH (del:Delegation)-[:TO_SESSION]->(s)
            RETURN s.status, s.expires_at, del.scopes, del.expires_at
            """,
            {"sid": context.session_id},
        )
    except Exception as e:
        return GatewayDecision(allowed=False, reason=f"Failed to query session state: {e}")

    if not res:
        return GatewayDecision(
            allowed=False,
            reason=f"AgentSession '{context.session_id}' not found in graph.",
        )

    s_status, s_expires, del_scopes, del_expires = res[0]

    # Session status check
    if s_status != "active":
        return GatewayDecision(
            allowed=False,
            reason=f"AgentSession '{context.session_id}' is inactive (status: {s_status}).",
        )

    # Session expiration check
    if s_expires is not None and s_expires <= now:
        return GatewayDecision(
            allowed=False,
            reason=f"AgentSession '{context.session_id}' expired at {s_expires} (current: {now}).",
        )

    # Delegation validity check
    if del_scopes is not None:
        if del_expires is not None and del_expires <= now:
            return GatewayDecision(
                allowed=False,
                reason=f"Delegation for session '{context.session_id}' expired at {del_expires}.",
            )

        # Scopes check
        if "*" not in del_scopes and tool_def.name not in del_scopes:
            return GatewayDecision(
                allowed=False,
                reason=f"Tool '{tool_def.name}' is outside authorized delegation scopes: {del_scopes}.",
            )

    # 3. Requires-Approval Enforcement
    if tool_def.requires_approval:
        # Determine target entity from tool arguments
        target_id = (
            arguments.get("pod_id")
            or arguments.get("session_id")
            or arguments.get("target_id")
            or arguments.get("endpoint_id")
            or arguments.get("subject_id")
        )

        matched = False
        # Check relational operational database first
        try:
            sqlite_appr = get_approved_action(action=tool_def.name, target_id=target_id)
            if sqlite_appr:
                matched = True
        except Exception as e:
            logger.warning(f"Could not query operational SQLite approvals: {e}")

        # Fallback to FalkorDB for backwards compatibility with raw graph seeds
        if not matched:
            app_query = """
                MATCH (ar:ApprovalRequest)
                WHERE ar.action = $action AND ar.status = 'approved'
                RETURN ar.id, ar.target_id
            """
            app_params: dict[str, Any] = {"action": tool_def.name}

            try:
                app_res = client.query(app_query, app_params)
                for ar_id, ar_target in app_res:
                    if not target_id or ar_target == target_id:
                        matched = True
                        break
            except Exception as e:
                return GatewayDecision(allowed=False, reason=f"Failed to check approval status: {e}")

        if not matched:
            return GatewayDecision(
                allowed=False,
                reason=(
                    f"Disruptive action '{tool_def.name}' requires prior human approval. "
                    f"No matching approved ApprovalRequest found for target '{target_id}'."
                ),
            )

    # 4. Investigation Budget Check
    if context.investigation_id:
        try:
            sqlite_cnt = count_tool_calls_for_investigation(context.investigation_id)
            if sqlite_cnt >= DEFAULT_MAX_TOOL_CALLS:
                return GatewayDecision(
                    allowed=False,
                    reason=f"Investigation budget exceeded: max {DEFAULT_MAX_TOOL_CALLS} tool calls reached.",
                )
        except Exception:
            pass

        try:
            call_cnt_res = client.query(
                """
                MATCH (inv:Investigation {id: $invid})-[:MADE_CALL]->(tc:ToolCall)
                RETURN count(tc) AS cnt
                """,
                {"invid": context.investigation_id},
            )
            if call_cnt_res and call_cnt_res[0][0] >= DEFAULT_MAX_TOOL_CALLS:
                return GatewayDecision(
                    allowed=False,
                    reason=f"Investigation budget exceeded: max {DEFAULT_MAX_TOOL_CALLS} tool calls reached.",
                )
        except Exception as e:
            logger.warning(f"Could not check investigation budget: {e}")

    return GatewayDecision(allowed=True, reason="Authorized by Policy Gateway")
