"""
Action Tools: Containment execution and post-action verification.
All containment actions require prior human approval and are governed by the Policy Gateway.
"""

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.graph.temporal import invalidate_edge
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.sim.telemetry import isolate_pod, telemetry_source
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 23. Apply Isolation


class ApplyIsolationInput(BaseModel):
    pod_id: str = Field(description="Pod identifier to apply network quarantine to")


class ApplyIsolationOutput(BaseModel):
    pod_id: str
    isolated: bool
    status: str


@registry.register(
    name="apply_isolation",
    description="Applies network isolation to quarantine a pod, cutting outbound egress and ingress.",
    input_schema=ApplyIsolationInput,
    output_schema=ApplyIsolationOutput,
    read_only=False,
    requires_approval=True,
)
def apply_isolation(
    pod_id: str,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()

    # 1. Update in-memory telemetry filter
    isolate_pod(pod_id)

    # 2. Update FalkorDB Pod state
    c.query(
        "MATCH (p:Pod {id: $id}) SET p.status = 'isolated', p.isolated_at = $now",
        {"id": pod_id, "now": now},
    )

    data = {"pod_id": pod_id, "isolated": True, "status": "isolated"}
    evidence_ids = [f"ev:action:isolate:{pod_id}", f"ev:node:{pod_id}"]
    return ToolResult(tool="apply_isolation", success=True, data=data, evidence_ids=evidence_ids)


# 24. Revoke Session


class RevokeSessionInput(BaseModel):
    session_id: str = Field(description="AgentSession ID to immediately terminate and invalidate")


class RevokeSessionOutput(BaseModel):
    session_id: str
    revoked: bool
    status: str


@registry.register(
    name="revoke_session",
    description="Immediately revokes an active AgentSession and invalidates its delegation.",
    input_schema=RevokeSessionInput,
    output_schema=RevokeSessionOutput,
    read_only=False,
    requires_approval=True,
)
def revoke_session(
    session_id: str,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()

    c.query(
        """
        MATCH (s:AgentSession {id: $id})
        SET s.status = 'revoked', s.revoked_at = $now
        """,
        {"id": session_id, "now": now},
    )

    data = {"session_id": session_id, "revoked": True, "status": "revoked"}
    evidence_ids = [f"ev:action:revoke:{session_id}", f"ev:node:{session_id}"]
    return ToolResult(tool="revoke_session", success=True, data=data, evidence_ids=evidence_ids)


# 25. Revoke Permission


class RevokePermissionInput(BaseModel):
    sa_id: str = Field(description="ServiceAccount ID")
    perm_id: str = Field(description="Permission ID to revoke")


class RevokePermissionOutput(BaseModel):
    sa_id: str
    perm_id: str
    revoked: bool


@registry.register(
    name="revoke_permission",
    description="Revokes an over-granted permission from a service account by setting its temporal valid_to.",
    input_schema=RevokePermissionInput,
    output_schema=RevokePermissionOutput,
    read_only=False,
    requires_approval=True,
)
def revoke_permission(
    sa_id: str,
    perm_id: str,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()

    invalidate_edge(
        client=c,
        from_id=sa_id,
        to_id=perm_id,
        rel_type="HAS_PERMISSION",
        at_time=now,
    )

    data = {"sa_id": sa_id, "perm_id": perm_id, "revoked": True}
    evidence_ids = [f"ev:action:revoke_perm:{sa_id}:{perm_id}"]
    return ToolResult(tool="revoke_permission", success=True, data=data, evidence_ids=evidence_ids)


# 26. Block Endpoint


class BlockEndpointInput(BaseModel):
    endpoint_id: str = Field(description="NetworkEndpoint ID or IP address to block")


class BlockEndpointOutput(BaseModel):
    endpoint_id: str
    blocked: bool


@registry.register(
    name="block_endpoint",
    description="Blocks an untrusted external network endpoint and marks it in the security graph.",
    input_schema=BlockEndpointInput,
    output_schema=BlockEndpointOutput,
    read_only=False,
    requires_approval=True,
)
def block_endpoint(
    endpoint_id: str,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()

    c.query(
        """
        MATCH (ep:NetworkEndpoint)
        WHERE ep.id = $id OR ep.address = $id
        SET ep.blocked = true, ep.known = false
        """,
        {"id": endpoint_id},
    )

    data = {"endpoint_id": endpoint_id, "blocked": True}
    evidence_ids = [f"ev:action:block:{endpoint_id}"]
    return ToolResult(tool="block_endpoint", success=True, data=data, evidence_ids=evidence_ids)


# 27. Verify Containment


class VerifyContainmentInput(BaseModel):
    subject_id: str = Field(description="Subject entity ID (pod, workload, session) to verify containment for")
    window_seconds: int = Field(default=300, description="Verification telemetry observation window")


class VerifyContainmentOutput(BaseModel):
    subject_id: str
    contained: bool
    remaining_events_count: int
    remaining_paths_count: int
    details: str
    escalation_needed: bool


@registry.register(
    name="verify_containment",
    description="Verifies whether containment succeeded by inspecting fresh telemetry and remaining graph access paths.",
    input_schema=VerifyContainmentInput,
    output_schema=VerifyContainmentOutput,
    read_only=True,
    requires_approval=False,
)
def verify_containment(
    subject_id: str,
    window_seconds: int = 300,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    since = now - window_seconds

    # 1. Telemetry egress check
    pod_res = c.query_dicts(
        "MATCH (p:Pod {id: $id}) RETURN p.status AS status, p.isolated_at AS isolated_at",
        {"id": subject_id},
    )
    if pod_res and pod_res[0].get("status") == "isolated":
        iso_at = pod_res[0].get("isolated_at")
        if iso_at is not None:
            since = max(since, int(iso_at) + 1)

    sess_res = c.query_dicts(
        "MATCH (s:AgentSession {id: $id}) RETURN s.status AS status, s.revoked_at AS revoked_at",
        {"id": subject_id},
    )
    if sess_res and sess_res[0].get("status") == "revoked":
        rev_at = sess_res[0].get("revoked_at")
        if rev_at is not None:
            since = max(since, int(rev_at) + 1)

    fresh_events = telemetry_source.get_events(
        pod_id=subject_id,
        kind="connect",
        window_start=since,
        window_end=now,
    )
    remaining_events = len(fresh_events)

    # 2. Check remaining topological access paths from subject to sensitive resources
    path_res = c.query_dicts(
        """
        MATCH path = (s {id: $id})-[*1..4]->(sr:SensitiveResource)
        RETURN count(path) AS remaining_paths
        """,
        {"id": subject_id},
    )
    remaining_paths = path_res[0].get("remaining_paths", 0) if path_res else 0

    # 3. Check for multi-path stubborn exposure (e.g. Pair 7 crown jewel convergence)
    # Check if a parallel active rogue session also has direct access to crown jewel secrets
    escalation_needed = False
    sibling_res = c.query_dicts(
        """
        MATCH (s {id: $id})-[:CAN_ACCESS]->(sr:SensitiveResource {id: 'sr-cloud-iam'})
        MATCH (other:AgentSession {status: 'active'})-[:CAN_ACCESS]->(sr)
        WHERE other.id <> $id
        RETURN other.id AS rogue_session, sr.id AS targeted_resource
        """,
        {"id": subject_id},
    )
    if sibling_res:
        escalation_needed = True

    contained = (remaining_events == 0) and (not escalation_needed)
    details = (
        "Containment verified: no egress events observed and no parallel exposure paths."
        if contained
        else f"Containment verification failed: {remaining_events} egress events and {len(sibling_res)} parallel rogue access paths remaining."
    )

    data = {
        "subject_id": subject_id,
        "contained": contained,
        "remaining_events_count": remaining_events,
        "remaining_paths_count": remaining_paths,
        "details": details,
        "escalation_needed": escalation_needed,
    }
    evidence_ids = [f"ev:verification:{subject_id}"]
    for sib in sibling_res:
        evidence_ids.append(f"ev:node:{sib['rogue_session']}")
    return ToolResult(tool="verify_containment", success=True, data=data, evidence_ids=evidence_ids)
