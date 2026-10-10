"""
Resilience & End-to-End Scenario Verification Tests.
Verifies Scenarios A through E, fail-closed behavior during outages,
and degraded confidence under telemetry loss.
"""

import pytest
from graph.client import GraphClient, get_graph_client
from graph.fixtures.seeder import seed_scenarios
from graph.queries.library import QueryLibrary
from services.agent_gateway.gateway import (
    AgentMCPGateway,
    ToolInvocationRequest,
)
from policies.engine import PolicyEngine
from policies.rules import DecisionEffect

@pytest.fixture(autouse=True)
def reset_baseline():
    client = get_graph_client()
    seed_scenarios(client)

def test_scenario_a_compromised_workload():
    """Scenario A: Shell breach correlated to workload, blast radius discovered, containment effective."""
    client = get_graph_client()
    ql = QueryLibrary(client)

    # 1. Event correlated to pod
    evts = client.query("MATCH (p:Pod {id: 'pod-checkout-7f89b'})-[:EMITTED_EVENT]->(e:RuntimeEvent) RETURN e.id, e.process_name, e.severity")
    assert len(evts) >= 1
    assert evts[0][1] == "sh"
    assert evts[0][2] == "CRITICAL"

    # 2. Blast radius identifies critical vault and payment db
    blast = ql.get_workload_blast_radius("workload-checkout")
    target_names = [t["name"] for t in blast["targets"]]
    assert "customer-vault-secrets" in target_names
    assert "payment-records-db" in target_names

    # 3. Containment eliminates 100% of paths
    sim = ql.simulate_containment_remaining_paths("workload-checkout", excluded_node_id="pod-checkout-7f89b")
    assert sim["impact"]["exposure_reduction_pct"] == 100.0

def test_scenario_b_delegation_violation():
    """Scenario B: User with read-only authority attempts destructive action via agent."""
    client = get_graph_client()
    gw = AgentMCPGateway(client)

    req = ToolInvocationRequest(
        session_id="session-alice-dev-01",
        tool_name="db_drop_table",
        action="EXECUTE",
    )
    res = gw.invoke_tool(req)

    assert res.blocked is True
    assert res.status_code == 403
    assert res.decision.decision == DecisionEffect.DENY
    assert "exceeds user's active delegation scopes" in res.decision.rationale
    assert res.execution_result is None

def test_scenario_c_shared_attack_path():
    """Scenario C: Workload and agent share path to cloud-iam-secrets."""
    client = get_graph_client()
    ql = QueryLibrary(client)

    paths = ql.find_shared_attack_paths(["workload-proxy", "session-bob-compromised-02"])
    assert len(paths["findings"]) >= 1

    iam_target = next((f for f in paths["findings"] if f["target_name"] == "cloud-iam-secrets"), None)
    assert iam_target is not None
    assert iam_target["is_shared"] is True
    assert len(iam_target["converging_sources"]) == 2
    assert iam_target["risk_score"] > 100.0

def test_scenario_d_stale_telemetry_degrades_confidence():
    """Scenario D: Missing or stale telemetry degrades confidence to DEGRADED or UNKNOWN."""
    client = get_graph_client()
    ql = QueryLibrary(client)

    res = ql.detect_stale_or_missing_evidence(stale_threshold_seconds=600)
    findings = {f["workload_name"]: f for f in res["findings"]}

    # order-processor has telemetry from 20m ago (> 10m threshold)
    assert findings["order-processor"]["telemetry_status"] == "STALE_TELEMETRY"
    assert findings["order-processor"]["trust_confidence"] == "DEGRADED"

    # analytics-worker has no telemetry events at all
    assert findings["analytics-worker"]["telemetry_status"] == "MISSING_TELEMETRY"
    assert findings["analytics-worker"]["trust_confidence"] == "UNKNOWN"

def test_scenario_e_fail_closed_during_outage():
    """Scenario E: Gateway and policy engine fail closed when database is unreachable."""
    # Create client pointing to unreachable port
    dead_client = GraphClient(host="127.0.0.1", port=59999)
    gw = AgentMCPGateway(dead_client)

    req = ToolInvocationRequest(
        session_id="session-alice-dev-01",
        tool_name="audit_read",
        action="EXECUTE",
    )
    res = gw.invoke_tool(req)

    # Must fail closed with 503 and DENY!
    assert res.blocked is True
    assert res.status_code == 503
    assert res.decision.decision == DecisionEffect.DENY
    assert "FAIL-CLOSED" in res.decision.rationale
    assert res.execution_result is None

def test_scenario_f_multi_agent_shared_infra_blast_radius_containment():
    """
    Scenario F: Multi-Agent Shared Infrastructure Blast-Radius Isolation.
    Orbit (session-alice-dev-01) and Nexus (session-nexus-settlement-01) share sr-financial-db.
    1. Before contamination: Nexus calls process_settlement_payout -> ALLOW (200).
    2. Orbit suffers prompt injection / attack -> creates CRITICAL RuntimeEvent on session-alice-dev-01.
    3. Nexus attempts process_settlement_payout on shared sr-financial-db.
    4. Trust Layer intercepts Nexus with 428 PRECONDITION_REQUIRED / RESTRICT via Rule POL_BLAST_RADIUS_SHARED_CONTAINMENT!
    5. Downstream fleet and shared ledger are protected from lateral contamination.
    """
    client = get_graph_client()
    gw = AgentMCPGateway(client)

    # 1. Nexus settlement is initially allowed
    req_nexus = ToolInvocationRequest(
        session_id="session-nexus-settlement-01",
        tool_name="process_settlement_payout",
        action="EXECUTE",
        parameters={"payout_id": "pay-101", "amount": "$50,000.00"},
    )
    res_clean = gw.invoke_tool(req_nexus)
    assert res_clean.blocked is False
    assert res_clean.status_code == 200

    # 2. Contaminate Orbit (session-alice-dev-01) with a CRITICAL breach event
    client.query("""
    MATCH (s:AgentSession {id: 'session-alice-dev-01'})
    CREATE (e:RuntimeEvent {
        id: 'evt-orbit-prompt-injection-test',
        event_type: 'GOAL_HIJACKING_ATTEMPT',
        severity: 'CRITICAL',
        timestamp: 1791613000.0,
        command_line: 'Prompt injection attempting KMS vault dump'
    })
    CREATE (s)-[:EMITTED_EVENT]->(e)
    """)

    # 3. Nexus now tries to call the shared tool
    res_blocked = gw.invoke_tool(req_nexus)
    assert res_blocked.blocked is True
    assert res_blocked.status_code == 428  # Precondition Required / Restrict
    assert res_blocked.decision.decision == DecisionEffect.RESTRICT
    assert "BLAST RADIUS CONTAINMENT" in res_blocked.decision.rationale
    assert "session-alice-dev-01" in res_blocked.decision.rationale
    assert "prod-financial-db" in res_blocked.decision.rationale

    # 4. Clear threat on Orbit and reset quarantine -> Nexus is immediately unblocked
    client.query("MATCH (e:RuntimeEvent) WHERE e.id STARTS WITH 'evt-sec-' OR e.id STARTS WITH 'evt-orbit-' DETACH DELETE e")
    res_restored = gw.invoke_tool(req_nexus)
    assert res_restored.blocked is False
    assert res_restored.status_code == 200

