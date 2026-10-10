"""
Unit tests for FalkorDB schema, temporal edge helpers, and the 8 core Cypher queries.
Runs against live FalkorDB instance.
"""

import pytest

from backend.app.graph import queries
from backend.app.graph.client import get_graph_client
from backend.app.graph.schema import init_schema
from backend.app.graph.temporal import create_temporal_edge, invalidate_edge


@pytest.fixture(autouse=True)
def clean_graph():
    """Isolate tests on a clean FalkorDB graph."""
    client = get_graph_client()
    client.reset_graph()
    init_schema(client)
    yield client


def test_schema_init(clean_graph):
    """Test schema index creation on all canonical labels."""
    res = init_schema(clean_graph)
    assert res["total_labels"] > 20
    assert res["created"] + res["existing"] >= res["total_labels"]


def test_temporal_edges(clean_graph):
    """Test temporal edge creation, validity filtering, and invalidation."""
    client = clean_graph
    client.query(
        "CREATE (:Pod {id: 'pod-1', name: 'checkout-pod'}), (:ServiceAccount {id: 'sa-1', name: 'checkout-sa'})"
    )

    # Create edge valid from t=100
    create_temporal_edge(client, "pod-1", "sa-1", "RUNS_AS", valid_from=100, provenance="configured")

    # Query at t=50 (before valid_from) -> should not see edge
    ctx_early = queries.entity_context(client, "pod-1", depth=1, at=50)
    assert len(ctx_early["edges"]) == 0

    # Query at t=150 (valid window) -> should see edge
    ctx_mid = queries.entity_context(client, "pod-1", depth=1, at=150)
    assert len(ctx_mid["edges"]) == 1

    # Invalidate edge at t=200
    invalidate_edge(client, "pod-1", "sa-1", "RUNS_AS", invalid_at=200)

    # Query at t=250 -> should be expired
    ctx_late = queries.entity_context(client, "pod-1", depth=1, at=250)
    assert len(ctx_late["edges"]) == 0


def test_blast_radius(clean_graph):
    """Test blast_radius query from Pod to SensitiveResource."""
    client = clean_graph
    client.query("""
    CREATE (p:Pod {id: 'pod-checkout', name: 'checkout-pod'}),
           (sa:ServiceAccount {id: 'sa-checkout', name: 'checkout-sa'}),
           (perm:Permission {id: 'perm-vault', verb: 'get', resource: 'secrets'}),
           (sr:SensitiveResource {id: 'sr-vault', name: 'customer-vault-secrets', sensitivity: 5})
    CREATE (p)-[:RUNS_AS {valid_from: 0, provenance: 'configured'}]->(sa)
    CREATE (sa)-[:HAS_PERMISSION {valid_from: 0, provenance: 'configured'}]->(perm)
    CREATE (perm)-[:CAN_ACCESS {valid_from: 0, provenance: 'configured'}]->(sr)
    """)

    paths = queries.blast_radius(client, "pod-checkout", max_hops=4)
    assert len(paths) == 1
    assert paths[0]["target_id"] == "sr-vault"
    assert paths[0]["sensitivity"] == 5
    assert paths[0]["path_length"] == 3


def test_path_diff(clean_graph):
    """Test path_diff detecting newly reachable targets across temporal window."""
    client = clean_graph
    client.query("""
    CREATE (p:Pod {id: 'pod-analytics'}),
           (sr1:SensitiveResource {id: 'sr-old', sensitivity: 3}),
           (sr2:SensitiveResource {id: 'sr-new', sensitivity: 5})
    CREATE (p)-[:CAN_ACCESS {valid_from: 0, valid_to: 2000}]->(sr1)
    CREATE (p)-[:CAN_ACCESS {valid_from: 1000, valid_to: 3000}]->(sr2)
    """)

    # At t=500, only sr-old is reachable. At t=1500, both are reachable.
    diff = queries.path_diff(client, "pod-analytics", t_before=500, t_after=1500)
    assert diff["start_id"] == "pod-analytics"
    assert "sr-new" in diff["newly_reachable_ids"]
    assert diff["net_diff_count"] >= 1


def test_delegation_chain(clean_graph):
    """Test delegation_chain query and scope mismatch detection."""
    client = clean_graph
    client.query("""
    CREATE (p:Principal {id: 'user-alice', name: 'Alice', role: 'DevOps', status: 'active'}),
           (d:Delegation {id: 'del-1', scopes: ['read_logs', 'lookup_metrics'], expires_at: 2000, intent_text: 'Debug staging'}),
           (s:AgentSession {id: 'sess-1', status: 'active'}),
           (a:Agent {id: 'agent-ops', name: 'OpsAgent', capabilities: ['k8s']}),
           (t1:Tool {id: 'tool-logs', name: 'read_logs', risk_level: 'low'}),
           (t2:Tool {id: 'tool-drop', name: 'db_drop_table', risk_level: 'critical'})
    CREATE (p)-[:GRANTED]->(d)-[:TO_SESSION]->(s)
    CREATE (s)-[:USES_AGENT]->(a)
    CREATE (s)-[:CAN_INVOKE]->(t1)
    CREATE (s)-[:CAN_INVOKE]->(t2)
    """)

    # Test allowed tool
    res_ok = queries.delegation_chain(client, "sess-1", requested_tool="read_logs", at=1000)
    assert res_ok["authorized"] is True

    # Test tool out of scope
    res_blocked = queries.delegation_chain(client, "sess-1", requested_tool="db_drop_table", at=1000)
    assert res_blocked["authorized"] is False
    assert "not permitted by delegation scopes" in res_blocked["mismatch_reason"]


def test_find_convergence(clean_graph):
    """Test find_convergence and transparent risk formula calculation."""
    client = clean_graph
    # Two sources (pod-1 and sess-1) reaching sr-crown
    client.query("""
    CREATE (p1:Pod {id: 'pod-1'}),
           (s1:AgentSession {id: 'sess-1'}),
           (sr:SensitiveResource {id: 'sr-crown', name: 'cloud-iam-secrets', sensitivity: 5})
    CREATE (p1)-[:CAN_ACCESS]->(sr)
    CREATE (s1)-[:CAN_ACCESS]->(sr)
    """)

    conv = queries.find_convergence(client, ["pod-1", "sess-1"])
    assert len(conv) == 1
    assert conv[0]["resource_id"] == "sr-crown"
    assert conv[0]["source_count"] == 2
    # Formula: sensitivity * (1 + 0.5*(sources-1)) * (1 + 0.1*paths)
    # sensitivity=5, sources=2 (mult=1.5), paths=2 (mult=1.2) => 5 * 1.5 * 1.2 = 9.0
    assert conv[0]["risk_score"] == 9.0


def test_simulate_containment(clean_graph):
    """Test simulate_containment read-only simulation."""
    client = clean_graph
    client.query("""
    CREATE (p1:Pod {id: 'pod-compromised'}),
           (p2:Pod {id: 'pod-safe'}),
           (sr1:SensitiveResource {id: 'sr-unique', sensitivity: 4}),
           (sr2:SensitiveResource {id: 'sr-shared', sensitivity: 5})
    CREATE (p1)-[:CAN_ACCESS]->(sr1)
    CREATE (p1)-[:CAN_ACCESS]->(sr2)
    CREATE (p2)-[:CAN_ACCESS]->(sr2)
    """)

    sim = queries.simulate_containment(client, "pod-compromised")
    assert sim["isolated_node_id"] == "pod-compromised"
    assert sim["initial_reachable_targets"] == 2
    # sr-shared is still reachable by pod-safe, so 1 target remains
    assert sim["remaining_reachable_targets"] == 1
    assert sim["exposure_reduction_pct"] == 50.0
    assert sim["containment_complete"] is False


def test_recall_similar_and_centrality(clean_graph):
    """Test recall_similar for findings and centrality ranking."""
    client = clean_graph
    client.query("""
    CREATE (f:Finding {id: 'find-1', verdict: 'malicious', severity: 'high', confidence: 0.95, summary: 'shell_metadata_access detected in checkout', created_at: 1000}),
           (subj:Pod {id: 'pod-checkout', name: 'checkout-pod'})
    CREATE (f)-[:ABOUT]->(subj)
    """)

    similar = queries.recall_similar(client, "shell_metadata_access", ["pod-checkout"])
    assert len(similar) >= 1
    assert similar[0]["verdict"] == "malicious"

    rank = queries.centrality_rank(client, label="Pod")
    assert len(rank) >= 1
    assert rank[0]["id"] == "pod-checkout"
