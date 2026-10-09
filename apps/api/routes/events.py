"""
Runtime Telemetry & Event Ingestion Routes.
Provides live and replay telemetry endpoints with clear provenance labeling.
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Dict, Any, List, Optional
from graph.client import get_graph_client
from services.runtime_collector.collector import RuntimeCollector, NormalizedRuntimeEvent

router = APIRouter(tags=["Runtime Events & Telemetry"])
collector = RuntimeCollector(get_graph_client())

@router.get("/api/events")
def get_events(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    mode: Optional[str] = Query(None, description="Filter by mode: live_ebpf, replay_synthetic"),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """
    Returns ordered runtime events with provenance, Kubernetes pod correlation, and severity.
    """
    client = get_graph_client()
    where_parts = []
    params: Dict[str, Any] = {"limit": limit}

    if severity:
        where_parts.append("e.severity = $sev")
        params["sev"] = severity
    if mode:
        where_parts.append("e.mode = $mode")
        params["mode"] = mode

    where_str = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    query = f"""
    MATCH (e:RuntimeEvent)
    {where_str}
    OPTIONAL MATCH (src)-[:EMITTED_EVENT]->(e)
    OPTIONAL MATCH (e)-[:VIOLATED_POLICY]->(p:Policy)
    RETURN
        e.id AS id,
        e.event_type AS event_type,
        e.source AS source,
        e.mode AS mode,
        e.timestamp AS timestamp,
        e.severity AS severity,
        e.process_name AS process_name,
        e.command_line AS command_line,
        e.evidence_hash AS evidence_hash,
        src.id AS source_id,
        labels(src)[0] AS source_label,
        p.id AS policy_id,
        p.name AS policy_name
    ORDER BY e.timestamp DESC
    LIMIT $limit
    """
    rows = client.query(query, params)

    events = []
    for r in rows:
        events.append({
            "id": r[0],
            "event_type": r[1],
            "source": r[2],
            "mode": r[3],
            "timestamp": r[4],
            "severity": r[5],
            "process_name": r[6],
            "command_line": r[7],
            "evidence_hash": r[8],
            "correlated_source": {"id": r[9], "label": r[10]} if r[9] else None,
            "policy_violation": {"id": r[11], "name": r[12]} if r[11] else None,
            "is_live_telemetry": (r[3] == "live_ebpf"),
        })

    return events

@router.post("/api/events/ingest")
def ingest_telemetry_event(raw_event: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Ingests live or simulated event, correlates with graph, and checks policy rules.
    """
    try:
        # Check if Tetragon format
        if "process_exec" in raw_event:
            norm_event = collector.normalize_tetragon_event(raw_event)
        else:
            norm_event = NormalizedRuntimeEvent(**raw_event)

        result = collector.ingest_event(norm_event)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest event: {e}")

@router.post("/api/events/replay")
def trigger_replay_stream(count: int = Query(3, ge=1, le=10)) -> Dict[str, Any]:
    """
    Emits deterministic synthetic events with explicit replay provenance.
    """
    results = collector.generate_replay_stream(count=count)
    return {
        "mode": "replay_synthetic",
        "generated_count": len(results),
        "results": results,
    }
