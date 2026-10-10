"""
Integration & Unit Tests for Agent MCP Gateway & Policy Engine.
Verifies pre-execution blocking, effective authority boundaries, and session checks.
"""

import pytest
from graph.client import get_graph_client
from graph.fixtures.seeder import seed_scenarios
from services.agent_gateway.gateway import (
    AgentMCPGateway,
    ToolInvocationRequest,
)
from policies.rules import DecisionEffect

@pytest.fixture(autouse=True)
def reset_baseline():
    client = get_graph_client()
    seed_scenarios(client)

@pytest.fixture
def gateway():
    client = get_graph_client()
    return AgentMCPGateway(client)

def test_gateway_allows_authorized_tool(gateway):
    """Verifies that an authorized tool call succeeds and returns output."""
    req = ToolInvocationRequest(
        session_id="session-alice-dev-01",
        tool_name="audit_read",
        action="EXECUTE",
    )
    res = gateway.invoke_tool(req)
    assert res.success is True
    assert res.blocked is False
    assert res.status_code == 200
    assert res.decision.decision == DecisionEffect.ALLOW
    assert res.execution_result is not None
    assert res.evidence_hash is not None

def test_gateway_blocks_excessive_tool_before_execution(gateway):
    """Verifies that an out-of-scope tool call is BLOCKED BEFORE execution."""
    req = ToolInvocationRequest(
        session_id="session-alice-dev-01",
        tool_name="db_drop_table",  # Alice only has audit_read and report_generate
        action="EXECUTE",
    )
    res = gateway.invoke_tool(req)
    assert res.success is False
    assert res.blocked is True
    assert res.status_code == 403
    assert res.decision.decision == DecisionEffect.DENY
    assert res.execution_result is None  # NEVER executed!
    assert "exceeds user's active delegation scopes" in res.decision.rationale

def test_gateway_rejects_invalid_session(gateway):
    """Verifies that an unauthenticated / unknown session is rejected."""
    req = ToolInvocationRequest(
        session_id="invalid-session-9999",
        tool_name="audit_read",
    )
    res = gateway.invoke_tool(req)
    assert res.success is False
    assert res.blocked is True
    assert res.status_code == 401

def test_gateway_requires_approval_for_destructive_tool(gateway):
    """Verifies that admin session calling destructive tool requires approval."""
    # Bob has full scopes in session-bob-compromised-02
    req = ToolInvocationRequest(
        session_id="session-bob-compromised-02",
        tool_name="db_drop_table",
        action="EXECUTE",
    )
    res = gateway.invoke_tool(req)
    # db_drop_table is marked is_destructive: true, so policy engine must require approval
    assert res.blocked is True
    assert res.status_code == 428  # Precondition Required
    assert res.decision.decision == DecisionEffect.REQUIRE_APPROVAL
    assert res.execution_result is None  # Blocked pending human approval
