"""
System Health, Readiness, and Summary Statistics Routes.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from graph.client import get_graph_client, GraphClient
from services.runtime_collector.collector import RuntimeCollector

router = APIRouter(tags=["Health & Status"])
collector = RuntimeCollector(get_graph_client())

@router.get("/api/health")
def get_health() -> Dict[str, Any]:
    """
    Returns platform health, FalkorDB status, and sensor telemetry status.
    """
    client = get_graph_client()
    db_health = client.get_health_status()
    sensor_health = collector.get_health()

    status_str = "HEALTHY" if (db_health["healthy"] and not sensor_health.is_stale) else "DEGRADED"

    return {
        "status": status_str,
        "database": db_health,
        "sensor": sensor_health.model_dump(),
        "version": "1.0.0",
        "service": "runtime-trust-layer",
    }

@router.get("/api/ready")
def get_readiness() -> Dict[str, Any]:
    """Readiness probe endpoint for Kubernetes."""
    client = get_graph_client()
    is_ready = client.is_alive()
    return {"ready": is_ready}

@router.get("/api/stats")
def get_system_stats() -> Dict[str, Any]:
    """
    Returns counts of all canonical security entities in the FalkorDB graph.
    """
    client = get_graph_client()
    if not client.is_alive():
        return {"error": "Database unreachable"}

    counts_q = """
    MATCH (n)
    RETURN labels(n)[0] AS label, count(n) AS cnt
    """
    rows = client.query(counts_q)
    entity_counts = {r[0]: r[1] for r in rows if r[0]}

    edges_q = """
    MATCH ()-[r]->()
    RETURN type(r) AS rel_type, count(r) AS cnt
    """
    edge_rows = client.query(edges_q)
    edge_counts = {r[0]: r[1] for r in edge_rows if r[0]}

    return {
        "nodes_total": sum(entity_counts.values()),
        "edges_total": sum(edge_counts.values()),
        "entities": entity_counts,
        "relationships": edge_counts,
        "workloads_count": entity_counts.get("Workload", 0),
        "pods_count": entity_counts.get("Pod", 0),
        "agents_count": entity_counts.get("Agent", 0),
        "principals_count": entity_counts.get("Principal", 0),
        "events_count": entity_counts.get("RuntimeEvent", 0),
        "sensitive_resources_count": entity_counts.get("SensitiveResource", 0),
        "decisions_count": entity_counts.get("PolicyDecision", 0),
    }
