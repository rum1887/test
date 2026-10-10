"""
Unit tests for API health and fail-closed FalkorDB reporting.
"""

from fastapi.testclient import TestClient

from backend.app.graph.client import get_graph_client
from backend.app.main import app

client = TestClient(app)


def test_api_health_online():
    """Verify /api/health returns 200 when FalkorDB is online."""
    response = client.get("/api/health")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "HEALTHY"
    assert data["falkordb_online"] is True
    assert data["graph_name"] == "trust"


def test_api_health_offline(monkeypatch):
    """Verify /api/health fails closed with 503 DEGRADED when database is offline."""
    graph_client = get_graph_client()
    monkeypatch.setattr(graph_client, "is_alive", lambda: False)

    response = client.get("/api/health")
    data = response.json()
    assert response.status_code == 503
    assert data["status"] == "DEGRADED"
    assert data["falkordb_online"] is False
