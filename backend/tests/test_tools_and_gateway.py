"""
Tests for Tool Registry, Deterministic Policy Gateway, ToolCall Audit Logging, and MCP Server.
"""

import pytest

from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock
from backend.app.sim.world import seed_world
from backend.app.tools.mcp_server import create_mcp_server, list_registered_tools
from backend.app.tools.registry import ToolContext, registry


@pytest.fixture(autouse=True)
def setup_test_world():
    """Sets up a clean seed world and clock before each test."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    seed_world(client, seed=42)
    return client, clock


def test_registry_tool_count():
    """Verify that all core tools across graph, telemetry, context, memory, control, and action are registered."""
    tools = registry.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "get_entity_context",
        "blast_radius",
        "path_diff",
        "delegation_chain",
        "find_convergence",
        "shortest_path",
        "simulate_containment",
        "centrality_rank",
        "process_tree",
        "query_events",
        "get_baseline",
        "egress_summary",
        "recent_changes",
        "k8s_audit",
        "search_documents",
        "read_untrusted",
        "recall_similar",
        "write_finding",
        "update_baseline",
        "register_watch",
        "schedule_task",
        "request_approval",
        "apply_isolation",
        "revoke_session",
        "revoke_permission",
        "block_endpoint",
        "verify_containment",
    }

    missing = expected_tools - tool_names
    assert not missing, f"Missing tools in registry: {missing}"
    assert len(tools) >= 27


def test_read_only_tool_execution_and_audit():
    """Verify read-only tool runs through gateway, returns evidence, and logs ToolCall in FalkorDB."""
    client = get_graph_client()
    ctx = ToolContext(session_id="sess-analyst-runtime")

    # Execute get_entity_context
    result = registry.execute(
        name="get_entity_context",
        arguments={"entity_id": "pod-checkout-1", "depth": 1},
        context=ctx,
    )

    assert result.success is True
    assert result.tool == "get_entity_context"
    assert "ev:node:pod-checkout-1" in result.evidence_ids

    # Verify ToolCall node was written to FalkorDB
    calls = client.query(
        """
        MATCH (tc:ToolCall {tool: 'get_entity_context'})
        RETURN tc.allowed, tc.reason
        """
    )
    assert len(calls) >= 1
    allowed, reason = calls[-1]
    assert allowed is True
    assert reason == "Success"


def test_gateway_denies_unapproved_action():
    """Verify that disruptive containment tools are refused without prior human approval."""
    client = get_graph_client()
    ctx = ToolContext(session_id="sess-analyst-runtime")

    # Try applying isolation without an approved ApprovalRequest
    result = registry.execute(
        name="apply_isolation",
        arguments={"pod_id": "pod-checkout-1"},
        context=ctx,
    )

    assert result.success is False
    assert "Policy Gateway Denied" in result.error
    assert "requires prior human approval" in result.error

    # Verify denied ToolCall was logged in FalkorDB
    calls = client.query(
        """
        MATCH (tc:ToolCall {tool: 'apply_isolation'})
        RETURN tc.allowed, tc.reason
        """
    )
    assert len(calls) >= 1
    allowed, reason = calls[-1]
    assert allowed is False
    assert "requires prior human approval" in reason


def test_gateway_permits_approved_action():
    """Verify that disruptive actions execute once an approved ApprovalRequest exists."""
    client = get_graph_client()
    ctx = ToolContext(session_id="sess-analyst-runtime")

    # Seed approved ApprovalRequest in FalkorDB
    client.query(
        """
        CREATE (:ApprovalRequest {
            id: 'appr-test-isolate-1',
            action: 'apply_isolation',
            target_id: 'pod-checkout-1',
            status: 'approved',
            rationale: 'Confirmed C2 beaconing in checkout service'
        })
        """
    )

    # Now execute apply_isolation
    result = registry.execute(
        name="apply_isolation",
        arguments={"pod_id": "pod-checkout-1"},
        context=ctx,
    )

    assert result.success is True
    assert result.data["isolated"] is True

    # Verify pod status was updated in FalkorDB
    status_res = client.query("MATCH (p:Pod {id: 'pod-checkout-1'}) RETURN p.status")
    assert status_res[0][0] == "isolated"


def test_gateway_denies_expired_session():
    """Verify that execution is denied if agent session is expired."""
    client = get_graph_client()
    clock = get_clock()
    now = clock.now()

    # Create expired session
    client.query(
        """
        CREATE (:AgentSession {
            id: 'sess-expired-test',
            status: 'active',
            started_at: $t0 - 10000,
            expires_at: $t0 - 100
        })
        """,
        {"t0": now},
    )

    ctx = ToolContext(session_id="sess-expired-test")
    result = registry.execute(
        name="get_entity_context",
        arguments={"entity_id": "pod-checkout-1"},
        context=ctx,
    )

    assert result.success is False
    assert "expired" in result.error.lower()


def test_gateway_denies_out_of_scope_tool():
    """Verify that execution is denied if tool is outside delegation scopes."""
    client = get_graph_client()
    clock = get_clock()
    now = clock.now()

    # Create session with narrow delegation scope
    client.query(
        """
        CREATE (s:AgentSession {
            id: 'sess-narrow-test',
            status: 'active',
            started_at: $t0,
            expires_at: $t0 + 10000
        })
        CREATE (del:Delegation {
            id: 'del-narrow-test',
            scopes: ['search_documents'],
            expires_at: $t0 + 10000
        })
        CREATE (del)-[:TO_SESSION]->(s)
        """,
        {"t0": now},
    )

    ctx = ToolContext(session_id="sess-narrow-test")

    # Permitted tool: search_documents
    res1 = registry.execute(
        name="search_documents",
        arguments={"query": "ticket"},
        context=ctx,
    )
    assert res1.success is True

    # Forbidden tool: blast_radius (outside scopes)
    res2 = registry.execute(
        name="blast_radius",
        arguments={"start_id": "pod-checkout-1"},
        context=ctx,
    )
    assert res2.success is False
    assert "outside authorized delegation scopes" in res2.error


@pytest.mark.asyncio
async def test_mcp_server_lists_all_tools():
    """Verify MCP Server instantiates and lists all registered tools."""
    server = create_mcp_server()
    assert server is not None

    tools = await list_registered_tools()
    tool_names = {t["name"] for t in tools}

    assert "get_entity_context" in tool_names
    assert "apply_isolation" in tool_names
    assert "verify_containment" in tool_names
    assert len(tools) >= 27
