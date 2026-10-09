"""
Security Analysis, Blast Radius, Delegation Chain, and Tool Gateway Routes.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from graph.client import get_graph_client
from graph.queries.library import QueryLibrary
from policies.engine import PolicyEngine
from services.agent_gateway.gateway import (
    AgentMCPGateway,
    ToolInvocationRequest,
    ToolInvocationResponse,
)

router = APIRouter(tags=["Security Control Plane"])

@router.get("/api/blast-radius")
def get_blast_radius(
    target_id: str = Query(..., description="ID of Workload or Pod"),
    max_depth: int = Query(5, ge=1, le=8),
) -> Dict[str, Any]:
    """
    Query 1: Computes bounded blast radius from workload/pod to sensitive resources.
    Returns path lengths, evidence, and reachability classifications.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.get_workload_blast_radius(target_id, max_depth=max_depth)
    return res

@router.get("/api/delegation-chain")
def trace_delegation(
    session_id: str = Query(..., description="AgentSession ID"),
    tool: Optional[str] = Query(None, description="Optional requested tool name"),
) -> Dict[str, Any]:
    """
    Query 2: Traces Principal -> Session -> Agent -> Delegation -> Tool -> Resource.
    Evaluates validity, expiry, and excessive privileges.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.trace_agent_delegation_chain(session_id, requested_tool_name=tool)
    return res

@router.get("/api/attack-paths")
def get_shared_attack_paths(
    sources: Optional[str] = Query(
        None,
        description="Comma-separated IDs of suspicious workloads or sessions",
    ),
) -> Dict[str, Any]:
    """
    Query 4: Discovers sensitive resources shared by multiple threat sources.
    Ranks targets by sensitivity, path count, and convergence factors.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)

    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        # Default: search across known threat workloads and sessions
        source_list = ["workload-checkout", "session-bob-compromised-02", "workload-proxy"]

    res = ql.find_shared_attack_paths(source_list)
    return res

@router.post("/api/policies/evaluate")
def evaluate_policy(
    principal_id: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    session_id: str = Body(..., embed=True),
    tool_name: str = Body(..., embed=True),
    action: str = Body("EXECUTE", embed=True),
) -> Dict[str, Any]:
    """
    Query 3: Deterministic Policy Engine evaluation against effective authority.
    Returns ALLOW, DENY, REQUIRE_APPROVAL, or RESTRICT with rule breakdown.
    """
    client = get_graph_client()
    engine = PolicyEngine(client)
    decision = engine.evaluate_tool_request(
        principal_id=principal_id,
        agent_id=agent_id,
        session_id=session_id,
        requested_tool=tool_name,
        requested_action=action,
    )
    return decision.model_dump()

@router.post("/api/gateway/invoke")
def invoke_agent_tool(request: ToolInvocationRequest):
    """
    MCP Gateway Boundary: Enforces policy BEFORE tool execution.
    Rejects unauthorized requests immediately and records evidence in graph.
    """
    from fastapi.responses import JSONResponse
    client = get_graph_client()
    gw = AgentMCPGateway(client)
    response = gw.invoke_tool(request)
    return JSONResponse(status_code=response.status_code, content=response.model_dump())
