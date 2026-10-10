"""
Control Tools: Register state watches, schedule follow-up tasks, and submit human approval requests in FalkorDB.
"""

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 20. Register Watch


class RegisterWatchInput(BaseModel):
    investigation_id: str = Field(description="Investigation ID that owns this watch")
    kind: str = Field(description="Kind of watch (e.g. egress_reoccurrence, permission_change, tool_invocation)")
    spec: dict[str, Any] = Field(description="Watch criteria specification")
    expires_in: int = Field(default=86400, description="Expiration time in simulated seconds from now")


class RegisterWatchOutput(BaseModel):
    watch_id: str
    investigation_id: str
    expires_at: int


@registry.register(
    name="register_watch",
    description="Registers an active condition watch in FalkorDB that awakens the investigation if triggered.",
    input_schema=RegisterWatchInput,
    output_schema=RegisterWatchOutput,
    read_only=False,
    requires_approval=False,
)
def register_watch(
    investigation_id: str,
    kind: str,
    spec: dict[str, Any],
    expires_in: int = 86400,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    watch_id = f"watch-{uuid.uuid4().hex[:10]}"
    expires_at = now + expires_in

    c.query(
        """
        MERGE (w:Watch {id: $id})
        SET w.kind = $kind,
            w.spec = $spec,
            w.status = 'active',
            w.created_at = $now,
            w.expires_at = $expires_at
        """,
        {
            "id": watch_id,
            "kind": kind,
            "spec": json.dumps(spec),
            "now": now,
            "expires_at": expires_at,
        },
    )

    c.query(
        """
        MATCH (inv:Investigation {id: $invid}), (w:Watch {id: $wid})
        MERGE (inv)-[:REGISTERED]->(w)
        """,
        {"invid": investigation_id, "wid": watch_id},
        ignore_errors=True,
    )

    data = {"watch_id": watch_id, "investigation_id": investigation_id, "expires_at": expires_at}
    return ToolResult(tool="register_watch", success=True, data=data, evidence_ids=[f"ev:watch:{watch_id}"])


# 21. Schedule Task


class ScheduleTaskInput(BaseModel):
    investigation_id: str = Field(description="Investigation ID scheduling the follow-up task")
    due_in: int = Field(description="Delay in simulated seconds until task execution")
    action: str = Field(description="Action to execute when task is due (e.g. verify_containment, recheck_exposure)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Action arguments payload")


class ScheduleTaskOutput(BaseModel):
    task_id: str
    due_at: int
    action: str


@registry.register(
    name="schedule_task",
    description="Schedules a durable follow-up task in FalkorDB to be dispatched by the worker clock loop.",
    input_schema=ScheduleTaskInput,
    output_schema=ScheduleTaskOutput,
    read_only=False,
    requires_approval=False,
)
def schedule_task(
    investigation_id: str,
    due_in: int,
    action: str,
    payload: dict[str, Any] = {},
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    task_id = f"task-{uuid.uuid4().hex[:10]}"
    due_at = now + due_in

    c.query(
        """
        MERGE (st:ScheduledTask {id: $id})
        SET st.action = $action,
            st.payload = $payload,
            st.due_at = $due_at,
            st.status = 'pending',
            st.created_at = $now
        """,
        {
            "id": task_id,
            "action": action,
            "payload": json.dumps(payload),
            "due_at": due_at,
            "now": now,
        },
    )

    c.query(
        """
        MATCH (inv:Investigation {id: $invid}), (st:ScheduledTask {id: $tid})
        MERGE (inv)-[:SCHEDULED]->(st)
        """,
        {"invid": investigation_id, "tid": task_id},
        ignore_errors=True,
    )

    data = {"task_id": task_id, "due_at": due_at, "action": action}
    return ToolResult(tool="schedule_task", success=True, data=data, evidence_ids=[f"ev:task:{task_id}"])


# 22. Request Approval


class RequestApprovalInput(BaseModel):
    investigation_id: str = Field(description="Investigation ID requesting containment approval")
    action: str = Field(description="Disruptive action to request (apply_isolation, revoke_session, block_endpoint)")
    rationale: str = Field(description="Evidence-based justification for human operator review")
    target_id: str = Field(description="Target entity ID to apply containment to")


class RequestApprovalOutput(BaseModel):
    approval_id: str
    action: str
    target_id: str
    status: str


@registry.register(
    name="request_approval",
    description="Submits a human approval request for disruptive containment action to the operator queue.",
    input_schema=RequestApprovalInput,
    output_schema=RequestApprovalOutput,
    read_only=False,
    requires_approval=False,
)
def request_approval(
    investigation_id: str,
    action: str,
    rationale: str,
    target_id: str,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    approval_id = f"appr-{uuid.uuid4().hex[:10]}"

    c.query(
        """
        MERGE (ar:ApprovalRequest {id: $id})
        SET ar.action = $action,
            ar.rationale = $rationale,
            ar.target_id = $target_id,
            ar.status = 'pending',
            ar.created_at = $now
        """,
        {
            "id": approval_id,
            "action": action,
            "rationale": rationale,
            "target_id": target_id,
            "now": now,
        },
    )

    c.query(
        """
        MATCH (inv:Investigation {id: $invid}), (ar:ApprovalRequest {id: $aid})
        MERGE (inv)-[:REQUESTED]->(ar)
        """,
        {"invid": investigation_id, "aid": approval_id},
        ignore_errors=True,
    )

    data = {
        "approval_id": approval_id,
        "action": action,
        "target_id": target_id,
        "status": "pending",
    }
    return ToolResult(tool="request_approval", success=True, data=data, evidence_ids=[f"ev:approval:{approval_id}"])
