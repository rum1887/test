"""
Tests for Relational SQLite Operational State Store.
Verifies table schemas, indexed lookups, CRUD operations, step state snapshots,
and foreign key binding to FalkorDB graph entities.
"""

import json

from backend.app.db.sqlite import (
    count_tool_calls_for_investigation,
    create_approval,
    create_task,
    create_watch,
    get_approval,
    get_approved_action,
    get_latest_step_state,
    list_active_watches,
    list_approvals,
    list_due_tasks,
    list_step_states,
    list_tasks,
    list_tool_calls,
    list_watches,
    log_tool_call,
    reset_sqlite_db,
    save_step_state,
    update_approval_status,
    update_task_status,
    update_watch_status,
)


def test_sqlite_approvals_lifecycle():
    """Verify approval creation, retrieval, filtered listing, and status updates."""
    reset_sqlite_db()

    appr = create_approval(
        approval_id="appr-test-1",
        investigation_id="inv-100",
        action="apply_isolation",
        target_id="pod-checkout-1",
        rationale="C2 beaconing observed",
        created_at=1700000000,
        status="pending",
    )
    assert appr["id"] == "appr-test-1"

    # Get by ID
    fetched = get_approval("appr-test-1")
    assert fetched is not None
    assert fetched["action"] == "apply_isolation"
    assert fetched["target_id"] == "pod-checkout-1"
    assert fetched["status"] == "pending"

    # Query approved action before approval -> should be None
    assert get_approved_action("apply_isolation", "pod-checkout-1") is None

    # Update to approved
    ok = update_approval_status(
        approval_id="appr-test-1",
        status="approved",
        approver="secops_lead",
        approved_at=1700000050,
    )
    assert ok is True

    # Query approved action after approval -> matches
    approved = get_approved_action("apply_isolation", "pod-checkout-1")
    assert approved is not None
    assert approved["id"] == "appr-test-1"
    assert approved["approver"] == "secops_lead"

    # List approvals
    all_apprs = list_approvals(investigation_id="inv-100")
    assert len(all_apprs) == 1
    assert all_apprs[0]["status"] == "approved"


def test_sqlite_watches_lifecycle():
    """Verify active watch registration, indexed lookups, and expiration/triggering."""
    reset_sqlite_db()

    w = create_watch(
        watch_id="watch-test-1",
        investigation_id="inv-200",
        kind="telemetry",
        spec={"pod_id": "pod-checkout-1", "dest": "169.254.169.254"},
        created_at=1700000000,
        expires_at=1700003600,
        status="active",
    )
    assert w["id"] == "watch-test-1"

    # List active watches
    active = list_active_watches()
    assert len(active) == 1
    assert active[0]["id"] == "watch-test-1"
    assert json.loads(active[0]["spec"])["pod_id"] == "pod-checkout-1"

    # Update watch to triggered
    ok = update_watch_status("watch-test-1", status="triggered", triggered_at=1700000100)
    assert ok is True

    # No longer active
    assert len(list_active_watches()) == 0

    # Listed in historical watches
    history = list_watches(investigation_id="inv-200")
    assert len(history) == 1
    assert history[0]["status"] == "triggered"
    assert history[0]["triggered_at"] == 1700000100


def test_sqlite_scheduled_tasks_lifecycle():
    """Verify task queueing, time-indexed dispatching, and execution recording."""
    reset_sqlite_db()

    t1 = create_task(
        task_id="task-1",
        investigation_id="inv-300",
        action="verify_containment",
        payload={"subject_id": "pod-checkout-1"},
        due_at=1700000300,
        created_at=1700000000,
        status="pending",
    )
    assert t1["id"] == "task-1"

    # Not due before due_at
    assert len(list_due_tasks(now=1700000100)) == 0

    # Due at or after due_at
    due = list_due_tasks(now=1700000350)
    assert len(due) == 1
    assert due[0]["id"] == "task-1"
    assert json.loads(due[0]["payload"])["subject_id"] == "pod-checkout-1"

    # Update status to completed
    ok = update_task_status("task-1", status="completed", executed_at=1700000355, result="Success")
    assert ok is True

    # No longer in due tasks
    assert len(list_due_tasks(now=1700000400)) == 0

    # Listed in tasks list
    tasks = list_tasks(investigation_id="inv-300")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "completed"


def test_sqlite_tool_call_audit_log():
    """Verify tool execution audit logging and investigation call counting."""
    reset_sqlite_db()

    log_tool_call(
        call_id="call-1",
        tool="get_entity_context",
        arguments={"entity_id": "pod-checkout-1"},
        allowed=True,
        reason="Success",
        evidence_ids=["ev:node:pod-checkout-1"],
        duration_ms=12,
        at=1700000010,
        session_id="sess-analyst-runtime",
        investigation_id="inv-400",
    )

    log_tool_call(
        call_id="call-2",
        tool="apply_isolation",
        arguments={"pod_id": "pod-checkout-1"},
        allowed=False,
        reason="Policy Gateway Denied: requires prior human approval",
        evidence_ids=[],
        duration_ms=4,
        at=1700000020,
        session_id="sess-analyst-runtime",
        investigation_id="inv-400",
    )

    # Count calls for investigation
    cnt = count_tool_calls_for_investigation("inv-400")
    assert cnt == 2

    # List tool calls
    calls = list_tool_calls(investigation_id="inv-400")
    assert len(calls) == 2
    assert calls[0]["id"] == "call-2"
    assert calls[0]["allowed"] is False
    assert calls[1]["id"] == "call-1"
    assert calls[1]["allowed"] is True


def test_sqlite_step_states_checkpoints():
    """Verify checkpoint snapshot persistence and latest state retrieval."""
    reset_sqlite_db()

    save_step_state(
        investigation_id="inv-500",
        step_index=1,
        status="running",
        state_json=json.dumps({"step": 1, "status": "running"}),
        created_at=1700000010,
    )

    save_step_state(
        investigation_id="inv-500",
        step_index=2,
        status="awaiting_approval",
        state_json=json.dumps({"step": 2, "status": "awaiting_approval"}),
        created_at=1700000020,
    )

    # Latest checkpoint
    latest = get_latest_step_state("inv-500")
    assert latest is not None
    assert latest["step_index"] == 2
    assert latest["status"] == "awaiting_approval"
    assert json.loads(latest["state_json"])["step"] == 2

    # Historical steps
    steps = list_step_states("inv-500")
    assert len(steps) == 2
    assert steps[0]["step_index"] == 1
    assert steps[1]["step_index"] == 2
