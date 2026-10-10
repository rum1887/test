"""
Integration Tests for Target App Intent Decoupling & LLM Autonomy (P0.2).
Verifies:
1. Explicit simulated tool override (EXPLICIT_TEST_OVERRIDE)
2. Transparent reporting of intent engine (DETERMINISTIC_TEST_HARNESS vs AUTONOMOUS_OLLAMA_LLM)
3. Interception of simulated tool override by Runtime Trust Gateway
"""

import pytest
from starlette.testclient import TestClient
from apps.api.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_target_app_explicit_tool_override(client):
    """Verifies that automated CI callers can explicitly specify simulated_tool."""
    res = client.post(
        "/api/target-app/chat",
        json={
            "message": "Please export the customer vault keys",
            "session_id": "session-alice-dev-01",
            "simulated_tool": "export_customer_vault",
            "simulated_parameters": {"destination": "s3://test-bucket"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent_engine"] == "EXPLICIT_TEST_OVERRIDE"
    assert data["tool_called"]["name"] == "export_customer_vault"
    assert data["attack_detected"] is True
    assert data["gateway_intercepted"] is True

def test_target_app_deterministic_harness_reporting(client):
    """Verifies that default test harness transparently labels provenance as DETERMINISTIC_TEST_HARNESS."""
    client.post("/api/target-app/reset-session")
    res = client.post(
        "/api/target-app/chat",
        json={
            "message": "What is my account balance?",
            "session_id": "session-alice-dev-01",
            "account_id": "acc-104",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent_engine"] == "DETERMINISTIC_TEST_HARNESS"
    assert data["tool_called"]["name"] == "lookup_customer_balance"
    assert data["attack_detected"] is False
    assert data["gateway_intercepted"] is False
