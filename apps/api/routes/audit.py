"""
Security Audit, Timeline, Policy Violations, and Integrity Routes.
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
from graph.client import get_graph_client
from graph.queries.library import QueryLibrary

router = APIRouter(tags=["Audit & Integrity"])

@router.get("/api/audit/timeline")
def get_audit_timeline(
    entity_id: Optional[str] = Query(None, description="Optional entity ID filter"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Query 7: Returns unified ordered timeline of runtime events and policy decisions.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.get_evidence_backed_timeline(entity_id=entity_id, limit=limit)
    return res

@router.get("/api/audit/violations")
def get_correlated_violations(
    window_seconds: int = Query(3600, ge=60, le=86400),
) -> Dict[str, Any]:
    """
    Query 8: Identifies runtime events correlating with explicit policy violations.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.correlate_policy_violations(window_seconds=window_seconds)
    return res

@router.get("/api/audit/telemetry-health")
def get_telemetry_health(
    stale_threshold_seconds: int = Query(600, ge=60, le=7200),
) -> Dict[str, Any]:
    """
    Query 9: Detects workloads or entities with stale or missing telemetry.
    Degrades confidence to UNKNOWN or DEGRADED rather than false green.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.detect_stale_or_missing_evidence(stale_threshold_seconds=stale_threshold_seconds)
    return res

@router.get("/api/audit/integrity")
def check_graph_integrity_endpoint() -> Dict[str, Any]:
    """
    Query 10: Runs automated graph integrity checks across all entities and relationships.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.check_graph_integrity()
    return res
