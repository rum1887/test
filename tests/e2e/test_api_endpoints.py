"""
End-to-End API Integration Tests for FastAPI Application.
Tests health, graph export, workloads, agents, blast radius, containment, and scenario reset.
"""

import pytest
from starlette.testclient import TestClient
from apps.api.main import app
from graph.client import get_graph_client
from graph.fixtures.seeder import seed_scenarios

@pytest.fixture(scope="module")
def api_client():
    client = get_graph_client()
    seed_scenarios(client)
    return TestClient(app)

def test_health_and_stats(api_client):
    """GET /api/health and /api/stats return healthy diagnostic."""
    res = api_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["HEALTHY", "DEGRADED"]
    assert "database" in data
    assert "sensor" in data

    stats_res = api_client.get("/api/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["workloads_count"] >= 1
    assert stats["agents_count"] >= 1

def test_cytoscape_graph_export(api_client):
    """GET /api/graph returns valid Cytoscape elements structure."""
    res = api_client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "elements" in data
    assert "nodes" in data["elements"]
    assert "edges" in data["elements"]
    assert len(data["elements"]["nodes"]) > 0
    assert len(data["elements"]["edges"]) > 0

def test_workload_inventory_and_detail(api_client):
    """GET /api/workloads and /api/workloads/{id}."""
    res = api_client.get("/api/workloads")
    assert res.status_code == 200
    workloads = res.json()
    assert len(workloads) >= 1
    w_id = workloads[0]["id"]

    detail_res = api_client.get(f"/api/workloads/{w_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == w_id
    assert "blast_radius" in detail

def test_blast_radius_api(api_client):
    """GET /api/blast-radius returns computed traversal."""
    res = api_client.get("/api/blast-radius?target_id=workload-checkout")
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "workload-checkout"
    assert data["total_paths"] > 0
    assert "paths" in data

def test_delegation_chain_api(api_client):
    """GET /api/delegation-chain traces session."""
    res = api_client.get("/api/delegation-chain?session_id=session-alice-dev-01")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["principal"]["name"] == "Alice Henderson"

def test_shared_attack_paths_api(api_client):
    """GET /api/attack-paths returns converged targets."""
    res = api_client.get("/api/attack-paths?sources=workload-proxy,session-bob-compromised-02")
    assert res.status_code == 200
    data = res.json()
    assert "findings" in data

def test_containment_simulation_and_enforcement(api_client):
    """POST /api/containment/simulate and /api/enforcement/apply."""
    # Simulation
    sim_res = api_client.post(
        "/api/containment/simulate",
        json={"source_id": "workload-checkout", "excluded_node_id": "pod-checkout-7f89b"},
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["simulation"] is True
    assert sim_data["impact"]["exposure_reduction_pct"] == 100.0

    # Apply containment action
    apply_res = api_client.post(
        "/api/enforcement/apply",
        json={
            "target_id": "pod-checkout-7f89b",
            "action_type": "ISOLATE_POD",
            "enforcement_mechanism": "k8s_network_policy",
            "is_live_action": False,
        },
    )
    assert apply_res.status_code == 200
    act = apply_res.json()
    assert act["status"] == "APPLIED"

    # Verify containment action
    ver_res = api_client.post("/api/enforcement/verify", json={"action_id": act["action_id"]})
    assert ver_res.status_code == 200
    assert ver_res.json()["status"] == "VERIFIED"

def test_gateway_invoke_api_blocked(api_client):
    """POST /api/gateway/invoke rejects unauthorized tool."""
    res = api_client.post(
        "/api/gateway/invoke",
        json={
            "session_id": "session-alice-dev-01",
            "tool_name": "db_drop_table",
            "action": "EXECUTE",
        },
    )
    # Gateway returns 403 for DENY
    assert res.status_code == 403
    data = res.json()
    assert data["blocked"] is True

def test_scenarios_reset_and_load(api_client):
    """POST /api/scenarios/reset and GET /api/scenarios."""
    list_res = api_client.get("/api/scenarios")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 5

    reset_res = api_client.post("/api/scenarios/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "RESET_SUCCESSFUL"
