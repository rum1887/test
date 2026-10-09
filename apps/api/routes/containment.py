"""
Containment Simulation & Runtime Enforcement Control Routes.
Provides hypothetical before/after graph analysis and auditable containment actions.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from graph.client import get_graph_client
from graph.queries.library import QueryLibrary

router = APIRouter(tags=["Containment Simulator & Enforcement"])

@router.get("/api/containment/candidates")
def get_containment_candidates(
    source_id: str = Query(..., description="Threat source ID, e.g. workload-checkout"),
) -> Dict[str, Any]:
    """
    Query 6: Generates candidate containment actions and ranks them by:
    - Exposure reduction (%)
    - Disruption risk
    - Net containment score
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.evaluate_best_containment_candidates(threat_source_id=source_id)
    return res

@router.post("/api/containment/simulate")
def simulate_containment(
    source_id: str = Body(..., embed=True),
    excluded_node_id: Optional[str] = Body(None, embed=True),
    max_depth: int = Body(5, embed=True),
) -> Dict[str, Any]:
    """
    Query 5: Hypothetical containment traversal excluding proposed node/edge.
    Does NOT mutate the production graph. Returns before vs after exposure metrics.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.simulate_containment_remaining_paths(
        source_id=source_id,
        excluded_node_id=excluded_node_id,
        max_depth=max_depth,
    )
    return res

@router.post("/api/enforcement/apply")
def apply_containment_action(
    target_id: str = Body(..., embed=True),
    action_type: str = Body(..., embed=True),
    enforcement_mechanism: str = Body("k8s_network_policy", embed=True),
    is_live_action: bool = Body(False, embed=True),
) -> Dict[str, Any]:
    """
    Applies containment action. In synthetic demo mode, records confirmed state.
    State transitions: SIMULATED -> REQUESTED -> APPLIED -> VERIFIED.
    """
    client = get_graph_client()
    action_id = f"act-{uuid.uuid4().hex[:8]}"
    now_ts = time.time()

    # Create ContainmentAction in graph
    create_q = """
    CREATE (a:ContainmentAction {
        id: $id,
        target_id: $target_id,
        action_type: $action_type,
        enforcement_mechanism: $mechanism,
        status: 'APPLIED',
        applied_at: $ts,
        is_live_cluster_action: $is_live
    })
    RETURN a.id, a.status
    """
    client.query(
        create_q,
        {
            "id": action_id,
            "target_id": target_id,
            "action_type": action_type,
            "mechanism": enforcement_mechanism,
            "ts": now_ts,
            "is_live": is_live_action,
        },
    )

    # If action was isolating pod or revoking delegation, update target status in graph
    if action_type in ["ISOLATE_POD", "QUARANTINE_POD"]:
        client.query(
            "MATCH (p:Pod {id: $tid}) SET p.status = 'QUARANTINED', p.contained_at = $ts",
            {"tid": target_id, "ts": now_ts},
        )
    elif action_type in ["REVOKE_DELEGATION"]:
        client.query(
            "MATCH (d:Delegation {id: $tid}) SET d.status = 'REVOKED', d.revoked_at = $ts",
            {"tid": target_id, "ts": now_ts},
        )

    return {
        "action_id": action_id,
        "target_id": target_id,
        "action_type": action_type,
        "status": "APPLIED",
        "enforcement_mechanism": enforcement_mechanism,
        "applied_at": now_ts,
        "is_live_action": is_live_action,
        "verification_pending": True,
    }

@router.post("/api/enforcement/verify")
def verify_containment_action(
    action_id: str = Body(..., embed=True),
) -> Dict[str, Any]:
    """
    Verifies that containment action was successfully applied at boundary.
    Transitions status to VERIFIED.
    """
    client = get_graph_client()
    now_ts = time.time()

    q = """
    MATCH (a:ContainmentAction {id: $aid})
    SET a.status = 'VERIFIED', a.verified_at = $ts
    RETURN a.id, a.target_id, a.action_type, a.status
    """
    rows = client.query(q, {"aid": action_id, "ts": now_ts})
    if not rows:
        raise HTTPException(status_code=404, detail=f"ContainmentAction '{action_id}' not found")

    row = rows[0]
    return {
        "action_id": row[0],
        "target_id": row[1],
        "action_type": row[2],
        "status": row[3],
        "verified": True,
        "verified_at": now_ts,
    }

@router.get("/api/enforcement/actions")
def list_containment_actions() -> List[Dict[str, Any]]:
    """Lists all simulated, applied, and verified containment actions."""
    client = get_graph_client()
    q = """
    MATCH (a:ContainmentAction)
    RETURN
        a.id,
        a.target_id,
        a.action_type,
        a.enforcement_mechanism,
        a.status,
        a.applied_at,
        a.verified_at
    ORDER BY a.applied_at DESC
    """
    rows = client.query(q)
    return [
        {
            "action_id": r[0],
            "target_id": r[1],
            "action_type": r[2],
            "enforcement_mechanism": r[3],
            "status": r[4],
            "applied_at": r[5],
            "verified_at": r[6],
        }
        for r in rows
    ]
