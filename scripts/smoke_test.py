#!/usr/bin/env python3
"""
Deployment Smoke Test for Runtime Trust Layer.
Runs end-to-end checks across FalkorDB, Cypher traversals, policy engine,
and API health to verify a deployment from a fresh clone.
"""

import sys
import os
import time

# Ensure repository root is on Python module search path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

def run_smoke_test():
    print("=" * 70)
    print("RUNTIME TRUST LAYER — DEPLOYMENT SMOKE TEST")
    print("=" * 70)

    # 1. Test FalkorDB Connectivity
    print("\n[1/6] Connecting to FalkorDB...")
    try:
        from graph.client import get_graph_client
        client = get_graph_client()
        assert client.is_alive(), "FalkorDB ping failed"
        print("  -> Connected successfully to FalkorDB.")
    except Exception as e:
        print(f"  FAILED: Could not connect to FalkorDB: {e}")
        return 1

    # 2. Test Idempotent Schema Initialization & Seed
    print("\n[2/6] Initializing Schema and Seeding Graph...")
    try:
        from graph.fixtures.seeder import seed_scenarios
        res = seed_scenarios(client)
        assert res["status"] == "SEEDED_SUCCESSFULLY"
        print("  -> Schema initialized and baseline scenarios seeded.")
    except Exception as e:
        print(f"  FAILED: Schema initialization or seed failed: {e}")
        return 1

    # 3. Test Graph Integrity (Query 10)
    print("\n[3/6] Verifying Graph Integrity (Query 10)...")
    try:
        from graph.queries.library import QueryLibrary
        ql = QueryLibrary(client)
        integrity = ql.check_graph_integrity()
        assert integrity["valid"] is True, f"Integrity check failed: {integrity}"
        print("  -> Graph integrity verified (0 orphaned nodes or invalid mappings).")
    except Exception as e:
        print(f"  FAILED: Integrity verification failed: {e}")
        return 1

    # 4. Test Workload Blast Radius Traversal (Query 1)
    print("\n[4/6] Executing Workload Blast Radius Traversal (Query 1)...")
    try:
        blast = ql.get_workload_blast_radius("workload-checkout")
        assert blast["total_paths"] > 0, "No blast radius paths found"
        assert blast["sensitive_resources_count"] >= 1, "No sensitive resources reached"
        print(f"  -> Successfully traversed {blast['total_paths']} plausible paths reaching {blast['sensitive_resources_count']} sensitive targets.")
    except Exception as e:
        print(f"  FAILED: Blast radius traversal failed: {e}")
        return 1

    # 5. Test MCP Pre-Execution Enforcement (Gateway)
    print("\n[5/6] Testing MCP Pre-Execution Tool Enforcement (Gateway)...")
    try:
        from services.agent_gateway.gateway import AgentMCPGateway, ToolInvocationRequest
        gw = AgentMCPGateway(client)
        req = ToolInvocationRequest(
            session_id="session-alice-dev-01",
            tool_name="db_drop_table",
            action="EXECUTE",
        )
        res = gw.invoke_tool(req)
        assert res.blocked is True, "Unauthorized tool call was NOT blocked!"
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        assert res.execution_result is None, "Tool was executed despite policy denial!"
        print("  -> Confirmed: Unauthorized tool call BLOCKED BEFORE execution (HTTP 403).")
    except Exception as e:
        print(f"  FAILED: Gateway enforcement failed: {e}")
        return 1

    # 6. Test FastAPI Application Endpoints
    print("\n[6/6] Verifying FastAPI Application Health & Routes...")
    try:
        from starlette.testclient import TestClient
        from apps.api.main import app
        api_client = TestClient(app)
        h_res = api_client.get("/api/health")
        assert h_res.status_code == 200, f"Health check returned {h_res.status_code}"
        g_res = api_client.get("/api/graph")
        assert g_res.status_code == 200, f"Graph endpoint returned {g_res.status_code}"
        assert len(g_res.json()["elements"]["nodes"]) > 0, "Graph returned 0 nodes"
        print("  -> FastAPI endpoints responded with 200 OK and valid payloads.")
    except Exception as e:
        print(f"  FAILED: API route verification failed: {e}")
        return 1

    print("\n" + "=" * 70)
    print("ALL 6 SMOKE TESTS PASSED! SYSTEM VERIFIED & READY.")
    print("=" * 70 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(run_smoke_test())
