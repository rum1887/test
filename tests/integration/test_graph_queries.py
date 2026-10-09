"""
Integration Tests for the 10 FalkorDB Graph Queries & Algorithms.
Runs directly against the real FalkorDB instance without mocking Cypher behavior.
"""

import pytest
from graph.client import get_graph_client
from graph.fixtures.seeder import seed_scenarios
from graph.queries.library import QueryLibrary

@pytest.fixture(scope="module")
def setup_graph():
    """Initializes and seeds the real FalkorDB instance."""
    client = get_graph_client()
    assert client.is_alive(), "FalkorDB must be running for integration tests"
    res = seed_scenarios(client)
    assert res["status"] == "SEEDED_SUCCESSFULLY"
    return QueryLibrary(client)

def test_query_1_workload_blast_radius(setup_graph):
    """Query 1: Workload blast radius bounded traversal."""
    ql = setup_graph
    blast = ql.get_workload_blast_radius("workload-checkout", max_depth=5)

    assert blast["total_paths"] > 0
    assert blast["sensitive_resources_count"] >= 1
    assert blast["max_path_length"] >= 2
    # Verify customer-vault-secrets or payment-records-db are in targets
    target_names = [t["name"] for t in blast["targets"]]
    assert "customer-vault-secrets" in target_names or "payment-records-db" in target_names

    # Check path classifications
    classifications = {p["classification"] for p in blast["paths"]}
    assert "configured" in classifications or "inferred" in classifications or "observed" in classifications

def test_query_2_agent_delegation_chain_authorized(setup_graph):
    """Query 2: Agent delegation chain for valid in-scope tool."""
    ql = setup_graph
    chain = ql.trace_agent_delegation_chain("session-alice-dev-01", requested_tool_name="audit_read")

    assert chain["found"] is True
    assert chain["is_valid"] is True
    assert chain["principal"]["name"] == "Alice Henderson"
    assert chain["tool_in_scope"] is True
    assert chain["tool_excessive"] is False
    assert len(chain["anomalies"]) == 0

def test_query_2_agent_delegation_chain_unauthorized(setup_graph):
    """Query 2: Agent delegation chain detecting excessive out-of-scope tool."""
    ql = setup_graph
    chain = ql.trace_agent_delegation_chain("session-alice-dev-01", requested_tool_name="db_drop_table")

    assert chain["found"] is True
    assert chain["is_valid"] is False
    assert chain["tool_in_scope"] is False
    assert len(chain["anomalies"]) > 0
    assert any("db_drop_table" in a for a in chain["anomalies"])

def test_query_3_effective_authority_comparison(setup_graph):
    """Query 3: Effective authority calculation step-by-step."""
    ql = setup_graph
    # Alice calling allowed tool
    auth_ok = ql.compare_effective_authority("principal-alice", "agent-autodev", "session-alice-dev-01", "audit_read")
    assert auth_ok["decision"] == "ALLOW"
    assert auth_ok["authorized"] is True

    # Alice calling unauthorized tool
    auth_deny = ql.compare_effective_authority("principal-alice", "agent-autodev", "session-alice-dev-01", "db_drop_table")
    assert auth_deny["decision"] == "DENY"
    assert auth_deny["authorized"] is False
    assert len(auth_deny["reasons_denied"]) >= 1

def test_query_4_shared_attack_paths(setup_graph):
    """Query 4: Shared downstream resources detection with convergence ranking."""
    ql = setup_graph
    shared = ql.find_shared_attack_paths(["workload-proxy", "session-bob-compromised-02"])

    assert len(shared["findings"]) > 0
    top = shared["findings"][0]
    assert top["risk_score"] > 0
    assert "score_breakdown" in top

def test_query_5_containment_simulation(setup_graph):
    """Query 5: Hypothetical containment without graph mutation."""
    ql = setup_graph
    sim = ql.simulate_containment_remaining_paths("workload-checkout", excluded_node_id="pod-checkout-7f89b")

    assert sim["simulation"] is True
    assert sim["baseline"]["paths_count"] > 0
    assert sim["impact"]["eliminated_paths_count"] > 0
    assert sim["impact"]["exposure_reduction_pct"] == 100.0

def test_query_6_best_containment_candidates(setup_graph):
    """Query 6: Ranked candidate containment actions."""
    ql = setup_graph
    candidates = ql.evaluate_best_containment_candidates("workload-checkout")

    assert candidates["candidates_count"] > 0
    rec = candidates["recommended_candidate"]
    assert rec is not None
    assert rec["action_type"] in ["ISOLATE_POD", "DISABLE_SERVICE_ACCOUNT", "SCALE_TO_ZERO"]
    assert "net_score" in rec

def test_query_7_evidence_backed_timeline(setup_graph):
    """Query 7: Ordered timeline of events and decisions."""
    ql = setup_graph
    tl = ql.get_evidence_backed_timeline(limit=10)

    assert tl["total_items"] > 0
    timestamps = [item["timestamp"] for item in tl["timeline"] if item.get("timestamp")]
    # Verify ordered descending
    assert timestamps == sorted(timestamps, reverse=True)

def test_query_8_policy_violation_correlation(setup_graph):
    """Query 8: Correlation of runtime events with explicit policy violations."""
    ql = setup_graph
    corr = ql.correlate_policy_violations()

    assert corr["count"] >= 1
    item = corr["correlations"][0]
    assert item["policy"]["id"] == "pol-no-interactive-shells"
    assert item["causality_link"] == "DIRECT_EVIDENCE_ATTACHMENT"

def test_query_9_stale_or_missing_evidence(setup_graph):
    """Query 9: Stale and missing telemetry detection with confidence degradation."""
    ql = setup_graph
    stale = ql.detect_stale_or_missing_evidence(stale_threshold_seconds=600)

    assert stale["stale_or_missing_count"] >= 2
    # Verify order-processor is marked STALE and analytics-worker is marked MISSING
    found_stale = any(f["workload_name"] == "order-processor" and f["telemetry_status"] == "STALE_TELEMETRY" for f in stale["findings"])
    found_missing = any(f["workload_name"] == "analytics-worker" and f["telemetry_status"] == "MISSING_TELEMETRY" for f in stale["findings"])
    assert found_stale, "order-processor must be flagged as stale telemetry"
    assert found_missing, "analytics-worker must be flagged as missing telemetry"

def test_query_10_graph_integrity(setup_graph):
    """Query 10: Graph integrity checks for orphaned nodes and invalid links."""
    ql = setup_graph
    integrity = ql.check_graph_integrity()

    assert integrity["valid"] is True
    assert integrity["issue_count"] == 0
