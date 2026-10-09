"""
Cytoscape Graph Export and Exploration Routes.
Formats FalkorDB nodes and relationships into Cytoscape.js compatible schema.
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from graph.client import get_graph_client

router = APIRouter(tags=["Graph Explorer"])

# Category mapping for Cytoscape node visual styling
NODE_CATEGORY_MAP = {
    "Principal": "identity",
    "Agent": "agent",
    "AgentSession": "agent",
    "Delegation": "agent",
    "Workload": "workload",
    "Pod": "workload",
    "Container": "workload",
    "ServiceAccount": "identity",
    "Permission": "identity",
    "KubernetesResource": "infrastructure",
    "MCPServer": "agent",
    "Tool": "tool",
    "SensitiveResource": "sensitive",
    "NetworkEndpoint": "infrastructure",
    "RuntimeEvent": "event",
    "Policy": "policy",
    "EnforcementPoint": "policy",
    "PolicyDecision": "decision",
    "ContainmentAction": "containment",
}

@router.get("/api/graph")
def get_cytoscape_graph(
    labels: Optional[str] = Query(None, description="Comma-separated list of node labels to include"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario_id"),
    limit: int = Query(200, ge=1, le=500),
) -> Dict[str, Any]:
    """
    Returns nodes and edges formatted for Cytoscape.js rendering.
    """
    client = get_graph_client()
    if not client.is_alive():
        return {"elements": {"nodes": [], "edges": []}, "error": "Database offline"}

    # 1. Fetch Nodes
    where_clauses = []
    if labels:
        label_list = [l.strip() for l in labels.split(",") if l.strip()]
        if label_list:
            where_clauses.append("labels(n)[0] IN $labels")
    if scenario_id:
        where_clauses.append("n.scenario_id = $scenario_id")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    node_query = f"""
    MATCH (n)
    {where_str}
    RETURN
        n.id AS id,
        labels(n)[0] AS label,
        coalesce(n.name, n.id) AS name,
        coalesce(n.status, 'ACTIVE') AS status,
        coalesce(n.sensitivity_level, 'NONE') AS sensitivity,
        coalesce(n.severity, 'NONE') AS severity,
        coalesce(n.mode, 'NONE') AS mode,
        coalesce(n.event_type, 'NONE') AS event_type,
        coalesce(n.process_name, '') AS process_name,
        coalesce(n.command_line, '') AS command_line
    LIMIT {limit}
    """
    params = {}
    if labels:
        params["labels"] = [l.strip() for l in labels.split(",") if l.strip()]
    if scenario_id:
        params["scenario_id"] = scenario_id

    node_rows = client.query(node_query, params)

    node_ids = set()
    cytoscape_nodes = []

    for r in node_rows:
        nid, nlabel, nname, nstatus, nsens, nsev, nmode, netype, nproc, ncmd = r
        if not nid:
            continue
        node_ids.add(nid)
        category = NODE_CATEGORY_MAP.get(nlabel, "default")

        cytoscape_nodes.append({
            "data": {
                "id": str(nid),
                "label": nlabel,
                "name": nname,
                "category": category,
                "status": nstatus,
                "sensitivity": nsens,
                "severity": nsev,
                "mode": nmode,
                "event_type": netype,
                "process_name": nproc,
                "command_line": ncmd,
            }
        })

    # 2. Fetch Relationships between retrieved nodes
    if not node_ids:
        return {"elements": {"nodes": [], "edges": []}, "counts": {"nodes": 0, "edges": 0}}

    edge_query = """
    MATCH (source)-[r]->(target)
    WHERE source.id IN $node_ids AND target.id IN $node_ids
    RETURN
        source.id AS source_id,
        target.id AS target_id,
        type(r) AS rel_type,
        coalesce(r.evidence, 'configured') AS evidence,
        coalesce(r.evidence_type, 'configured') AS evidence_type,
        coalesce(r.confidence, 1.0) AS confidence
    LIMIT 500
    """
    edge_rows = client.query(edge_query, {"node_ids": list(node_ids)})

    cytoscape_edges = []
    for i, er in enumerate(edge_rows):
        src_id, tgt_id, r_type, ev, ev_type, conf = er
        edge_id = f"e_{src_id}_{tgt_id}_{r_type}_{i}"
        cytoscape_edges.append({
            "data": {
                "id": edge_id,
                "source": str(src_id),
                "target": str(tgt_id),
                "label": r_type,
                "evidence": ev,
                "evidence_type": ev_type,  # configured, inferred, observed, simulated
                "confidence": conf,
            }
        })

    return {
        "elements": {
            "nodes": cytoscape_nodes,
            "edges": cytoscape_edges,
        },
        "counts": {
            "nodes": len(cytoscape_nodes),
            "edges": len(cytoscape_edges),
        },
    }
