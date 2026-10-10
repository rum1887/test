"""
Scenario Loader and Graph State Reset Routes.
Supports Scenarios A through E with deterministic reproducibility.
"""

from fastapi import APIRouter, Body, Depends
from typing import Dict, Any, List
from apps.api.dependencies.auth import verify_admin_key
from graph.client import get_graph_client
from graph.fixtures.seeder import seed_scenarios

router = APIRouter(tags=["Scenario Control & Reset"])

SCENARIOS_META = [
    {
        "id": "scenario_a",
        "key": "A",
        "name": "Compromised Kubernetes Workload",
        "description": "Checkout service container runs unauthorized shell and accesses metadata service. Demonstrates Tetragon eBPF correlation, blast-radius traversal, and network policy containment.",
        "primary_entity": "workload-checkout",
        "threat_level": "CRITICAL",
    },
    {
        "id": "scenario_b",
        "key": "B",
        "name": "AI-Agent Delegation Violation",
        "description": "Compliance user delegates read-only scope to AutoDev agent. Agent requests destructive db_drop_table. Demonstrates pre-execution blocking at MCP gateway.",
        "primary_entity": "session-alice-dev-01",
        "threat_level": "HIGH",
    },
    {
        "id": "scenario_c",
        "key": "C",
        "name": "Shared Attack Path Convergence",
        "description": "Suspicious proxy workload and compromised admin session share access to cloud-iam-secrets through independent paths. Evaluates multi-source risk ranking and containment simulation.",
        "primary_entity": "workload-proxy",
        "threat_level": "CRITICAL",
    },
    {
        "id": "scenario_d",
        "key": "D",
        "name": "Stale & Missing Telemetry Detection",
        "description": "Workload telemetry heartbeat ceases. System marks trust status DEGRADED or UNKNOWN rather than showing false green safety.",
        "primary_entity": "workload-order-processor",
        "threat_level": "MEDIUM",
    },
    {
        "id": "scenario_e",
        "key": "E",
        "name": "Control Plane Outage & Fail-Closed Resilience",
        "description": "Tests system behavior when graph database or tool gateway is unreachable. Proves fail-closed security for all protected actions.",
        "primary_entity": "ep-mcp-gateway-01",
        "threat_level": "HIGH",
    },
]

@router.get("/api/scenarios")
def list_scenarios() -> List[Dict[str, Any]]:
    """Returns catalog of reproducible demonstration scenarios."""
    return SCENARIOS_META

@router.post("/api/scenarios/reset", dependencies=[Depends(verify_admin_key)])
def reset_graph_state() -> Dict[str, Any]:
    """
    Clears the entire FalkorDB graph and re-seeds deterministic state for all scenarios.
    """
    client = get_graph_client()
    res = seed_scenarios(client)
    return {
        "status": "RESET_SUCCESSFUL",
        "message": "Graph successfully cleared and re-seeded with canonical baseline.",
        "details": res,
    }

@router.post("/api/scenarios/load", dependencies=[Depends(verify_admin_key)])
def load_scenario(scenario_key: str = Body("ALL", embed=True)) -> Dict[str, Any]:
    """
    Loads deterministic graph state for a specified scenario.
    """
    client = get_graph_client()
    res = seed_scenarios(client, scenario=scenario_key)
    return {
        "status": "SCENARIO_LOADED",
        "scenario": scenario_key,
        "details": res,
    }
