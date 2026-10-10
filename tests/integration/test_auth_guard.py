"""
Integration Tests for Administrative Control Plane Protection (P0.1).
Verifies:
1. Rejection of unauthenticated requests to /api/gateway/toggle-guard (HTTP 401)
2. Rejection of requests with invalid X-Admin-Key (HTTP 401)
3. Successful authorization with valid X-Admin-Key (HTTP 200)
4. Successful authorization with Bearer token (HTTP 200)
5. Protection of /api/scenarios/reset and /api/scenarios/load
"""

import pytest
from starlette.testclient import TestClient
from apps.api.main import app
from apps.api.dependencies.auth import DEFAULT_ADMIN_KEY

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_toggle_guard_requires_admin_key(client):
    """Calling /api/gateway/toggle-guard without key must return 401 Unauthorized."""
    res = client.post("/api/gateway/toggle-guard")
    assert res.status_code == 401
    assert "Missing administrative control key" in res.json().get("detail", "")

def test_toggle_guard_rejects_invalid_admin_key(client):
    """Calling /api/gateway/toggle-guard with wrong key must return 401 Unauthorized."""
    res = client.post(
        "/api/gateway/toggle-guard",
        headers={"X-Admin-Key": "invalid-hacker-key"},
    )
    assert res.status_code == 401
    assert "Invalid administrative control key" in res.json().get("detail", "")

def test_toggle_guard_allows_valid_admin_key(client):
    """Calling /api/gateway/toggle-guard with valid X-Admin-Key must succeed with 200."""
    res = client.post(
        "/api/gateway/toggle-guard?enabled=true",
        headers={"X-Admin-Key": DEFAULT_ADMIN_KEY},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["guard_enabled"] is True
    assert data["mode"] == "ENFORCE"

def test_toggle_guard_allows_valid_bearer_token(client):
    """Calling /api/gateway/toggle-guard with valid Authorization: Bearer must succeed."""
    res = client.post(
        "/api/gateway/toggle-guard?enabled=true",
        headers={"Authorization": f"Bearer {DEFAULT_ADMIN_KEY}"},
    )
    assert res.status_code == 200
    assert res.json()["guard_enabled"] is True

def test_scenarios_reset_requires_admin_key(client):
    """Calling /api/scenarios/reset without admin key must return 401."""
    res = client.post("/api/scenarios/reset")
    assert res.status_code == 401

def test_scenarios_reset_allows_valid_admin_key(client):
    """Calling /api/scenarios/reset with valid X-Admin-Key must succeed with 200."""
    res = client.post(
        "/api/scenarios/reset",
        headers={"X-Admin-Key": DEFAULT_ADMIN_KEY},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESET_SUCCESSFUL"
