"""
Kubernetes Workload & Pod Inventory Routes.
"""

from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any, List
from graph.client import get_graph_client
from graph.queries.library import QueryLibrary

router = APIRouter(tags=["Workload Explorer"])

@router.get("/api/workloads")
def list_workloads() -> List[Dict[str, Any]]:
    """
    Returns inventory of all Kubernetes workloads, correlated pods, and service accounts.
    """
    client = get_graph_client()
    query = """
    MATCH (w:Workload)
    OPTIONAL MATCH (w)-[:CONTAINS]->(p:Pod)
    OPTIONAL MATCH (p)-[:RUNS_AS]->(sa:ServiceAccount)
    OPTIONAL MATCH (p)-[:EMITTED_EVENT]->(e:RuntimeEvent)
    WITH w, p, sa, count(e) AS event_count, max(e.timestamp) AS last_event
    RETURN
        w.id AS id,
        w.name AS name,
        w.namespace AS namespace,
        w.kind AS kind,
        w.status AS status,
        w.replicas AS replicas,
        p.id AS pod_id,
        p.name AS pod_name,
        sa.id AS sa_id,
        sa.name AS sa_name,
        event_count,
        last_event
    ORDER BY w.name
    """
    rows = client.query(query)

    workloads_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        w_id, w_nm, w_ns, w_k, w_st, w_rep, p_id, p_nm, sa_id, sa_nm, evt_cnt, last_evt = r
        if w_id not in workloads_map:
            workloads_map[w_id] = {
                "id": w_id,
                "name": w_nm,
                "namespace": w_ns,
                "kind": w_k,
                "status": w_st,
                "replicas": w_rep,
                "pods": [],
                "service_account": {"id": sa_id, "name": sa_nm} if sa_id else None,
                "total_events": 0,
                "last_event_timestamp": None,
            }
        if p_id:
            workloads_map[w_id]["pods"].append({"id": p_id, "name": p_nm})
        workloads_map[w_id]["total_events"] += evt_cnt or 0
        if last_evt and (workloads_map[w_id]["last_event_timestamp"] is None or last_evt > workloads_map[w_id]["last_event_timestamp"]):
            workloads_map[w_id]["last_event_timestamp"] = last_evt

    return list(workloads_map.values())

@router.get("/api/workloads/{workload_id}")
def get_workload_detail(workload_id: str = Path(..., description="ID of workload")) -> Dict[str, Any]:
    """
    Returns granular security details, blast radius summary, and permissions for a workload.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)

    # Fetch workload
    w_q = "MATCH (w:Workload {id: $wid}) RETURN w.id, w.name, w.namespace, w.kind, w.status, w.replicas"
    w_rows = client.query(w_q, {"wid": workload_id})
    if not w_rows:
        raise HTTPException(status_code=404, detail=f"Workload '{workload_id}' not found")

    w = w_rows[0]
    blast = ql.get_workload_blast_radius(workload_id)

    # Fetch attached RBAC permissions
    perm_q = """
    MATCH (w:Workload {id: $wid})-[:CONTAINS]->(p:Pod)-[:RUNS_AS]->(sa:ServiceAccount)-[:HAS_PERMISSION]->(perm:Permission)
    RETURN perm.id, perm.action, perm.resource_pattern, perm.effect
    """
    perm_rows = client.query(perm_q, {"wid": workload_id})
    perms = [
        {"id": pr[0], "action": pr[1], "resource_pattern": pr[2], "effect": pr[3]}
        for pr in perm_rows
    ]

    return {
        "id": w[0],
        "name": w[1],
        "namespace": w[2],
        "kind": w[3],
        "status": w[4],
        "replicas": w[5],
        "permissions": perms,
        "blast_radius": {
            "total_paths": blast["total_paths"],
            "max_path_length": blast["max_path_length"],
            "reachable_resources_count": blast["reachable_resources_count"],
            "sensitive_targets": blast["targets"],
        },
    }
