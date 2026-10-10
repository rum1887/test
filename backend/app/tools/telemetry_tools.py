"""
Telemetry Tools: Runtime event queries, process lineage reconstruction, baseline comparison, and egress profiling.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.telemetry import telemetry_source
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 9. Process Tree


class ProcessTreeInput(BaseModel):
    pod_id: str = Field(description="Pod identifier")
    pid: int = Field(description="Process ID to inspect ancestry for")


class ProcessTreeOutput(BaseModel):
    pod_id: str
    target_pid: int
    lineage: list[dict[str, Any]]


@registry.register(
    name="process_tree",
    description="Walks process ancestry (PID -> PPID) from the raw eBPF telemetry log to determine execution origin.",
    input_schema=ProcessTreeInput,
    output_schema=ProcessTreeOutput,
    read_only=True,
    requires_approval=False,
)
def process_tree(
    pod_id: str,
    pid: int,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    lineage = telemetry_source.get_process_tree(pod_id=pod_id, pid=pid)
    evidence_ids = [f"ev:proc:{pod_id}:{pid}"]
    for p in lineage:
        evidence_ids.append(f"ev:proc:{pod_id}:{p.get('pid')}")
    data = {"pod_id": pod_id, "target_pid": pid, "lineage": lineage}
    return ToolResult(tool="process_tree", success=True, data=data, evidence_ids=evidence_ids)


# 10. Query Events


class QueryEventsInput(BaseModel):
    pod_id: str | None = Field(default=None, description="Optional pod filter")
    kind: str | None = Field(default=None, description="Optional kind filter (exec, connect, file_read, secret_read)")
    window_start: int | None = Field(default=None, description="Epoch start timestamp")
    window_end: int | None = Field(default=None, description="Epoch end timestamp")


class QueryEventsOutput(BaseModel):
    count: int
    events: list[dict[str, Any]]


@registry.register(
    name="query_events",
    description="Queries Tetragon runtime security events from recorded telemetry log.",
    input_schema=QueryEventsInput,
    output_schema=QueryEventsOutput,
    read_only=True,
    requires_approval=False,
)
def query_events(
    pod_id: str | None = None,
    kind: str | None = None,
    window_start: int | None = None,
    window_end: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    events = telemetry_source.get_events(
        pod_id=pod_id,
        kind=kind,
        window_start=window_start,
        window_end=window_end,
    )
    data = {"count": len(events), "events": [e.model_dump() for e in events]}
    evidence_ids = [f"ev:event:{e.pod_id}:{e.kind}:{e.ts}" for e in events[:10]]
    return ToolResult(tool="query_events", success=True, data=data, evidence_ids=evidence_ids)


# 11. Get Baseline


class GetBaselineInput(BaseModel):
    subject_id: str = Field(description="Entity ID to fetch behavioral baseline for (e.g. workload or pod)")


class GetBaselineOutput(BaseModel):
    subject_id: str
    baselines: list[dict[str, Any]]


@registry.register(
    name="get_baseline",
    description="Fetches behavioral and operational baselines established for a workload or identity.",
    input_schema=GetBaselineInput,
    output_schema=GetBaselineOutput,
    read_only=True,
    requires_approval=False,
)
def get_baseline(
    subject_id: str,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    cypher = """
    MATCH (b:Baseline)
    WHERE b.id = $id OR EXISTS {
        MATCH (b)-[:DESCRIBES]->(s {id: $id})
    }
    RETURN b.id AS id, coalesce(b.category, 'general') AS category, coalesce(b.summary, '') AS summary
    """
    rows = c.query_dicts(cypher, {"id": subject_id})
    evidence_ids = [f"ev:baseline:{r['id']}" for r in rows]
    data = {"subject_id": subject_id, "baselines": rows}
    return ToolResult(tool="get_baseline", success=True, data=data, evidence_ids=evidence_ids)


# 12. Egress Summary


class EgressSummaryInput(BaseModel):
    pod_id: str = Field(description="Pod identifier to profile outbound network activity for")
    window_start: int | None = Field(default=None, description="Epoch start timestamp")
    window_end: int | None = Field(default=None, description="Epoch end timestamp")


class EgressSummaryOutput(BaseModel):
    pod_id: str
    total_connections: int
    destinations: list[dict[str, Any]]


@registry.register(
    name="egress_summary",
    description="Profiles outbound network connections, destinations, frequency, and whether endpoints are known.",
    input_schema=EgressSummaryInput,
    output_schema=EgressSummaryOutput,
    read_only=True,
    requires_approval=False,
)
def egress_summary(
    pod_id: str,
    window_start: int | None = None,
    window_end: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    events = telemetry_source.get_events(
        pod_id=pod_id,
        kind="connect",
        window_start=window_start,
        window_end=window_end,
    )

    dest_counts: dict[str, int] = {}
    for ev in events:
        dest = ev.dest or (ev.args[0] if ev.args else "unknown")
        dest_counts[dest] = dest_counts.get(dest, 0) + 1

    dest_details = []
    evidence_ids = [f"ev:node:{pod_id}"]

    for dest, count in dest_counts.items():
        ep_res = c.query_dicts(
            "MATCH (e:NetworkEndpoint) WHERE e.address = $dest OR e.id = $dest RETURN e.id AS id, e.known AS known, e.label AS label",
            {"dest": dest},
        )
        known = ep_res[0].get("known", False) if ep_res else False
        label = ep_res[0].get("label", "unregistered") if ep_res else "unregistered"
        dest_details.append({"destination": dest, "count": count, "known": known, "label": label})
        evidence_ids.append(f"ev:endpoint:{dest}")

    data = {
        "pod_id": pod_id,
        "total_connections": len(events),
        "destinations": dest_details,
    }
    return ToolResult(tool="egress_summary", success=True, data=data, evidence_ids=evidence_ids)
