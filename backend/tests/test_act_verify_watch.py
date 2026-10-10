"""
Tests for Milestone 7: Human Approval, Verification with Escalation (Pair 7),
Watch Evaluator (Wake Events), Task Scheduler, and Graph Memory Persistence.
"""

from backend.app.agent.analyst import AnalystAgent
from backend.app.agent.llm import LLMClient
from backend.app.agent.runner import DurableRunner
from backend.app.agent.scheduler import task_scheduler
from backend.app.agent.verifier import VerdictVerifier
from backend.app.agent.watcher import watch_evaluator
from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock
from backend.app.sim.scenarios import apply_scenario, load_scenario
from backend.app.sim.telemetry import TelemetryEvent, emit_event, reset_telemetry
from backend.app.sim.world import seed_world
from backend.app.tools.registry import ToolContext, registry


def test_standard_approval_and_containment():
    """Verify approval workflow: human approval executes action, verifies, and closes investigation."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    reset_telemetry()
    seed_world(client, seed=42)

    mock_llm = LLMClient(mode="mock")
    agent = AnalystAgent(llm=mock_llm, verifier=VerdictVerifier(client=mock_llm))
    runner = DurableRunner(agent=agent)

    # 1. Trigger malicious alert
    sc = load_scenario("pair1_shell_metadata_malicious")
    alert_id = apply_scenario(client, sc, clock=clock)

    # 2. Run investigation -> enters awaiting_approval
    state = runner.start_investigation(alert_id=alert_id, client=client, clock=clock)
    assert state.status == "awaiting_approval"

    # Find pending approval request
    appr_rows = client.query_dicts(
        "MATCH (ar:ApprovalRequest {status: 'pending'}) RETURN ar.id AS id, ar.action AS action"
    )
    assert len(appr_rows) >= 1
    appr_id = appr_rows[0]["id"]

    # 3. Approve and remediate
    res = runner.approve_and_remediate(approval_id=appr_id, approver="alice_security_lead", client=client, clock=clock)
    assert res["status"] == "contained"

    # 4. Verify investigation status in FalkorDB is done
    inv_rows = client.query_dicts(
        "MATCH (inv:Investigation {id: $id}) RETURN inv.status AS status",
        {"id": state.investigation_id},
    )
    assert inv_rows[0]["status"] == "done"


def test_pair7_stubborn_convergence_escalation():
    """
    Verify Pair 7 Stubborn Exposure:
    Pod isolation leaves parallel rogue agent session open to crown jewel secrets;
    verification detects exposure and escalates to secondary session revocation action.
    """
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    reset_telemetry()
    seed_world(client, seed=42)

    mock_llm = LLMClient(mode="mock")
    agent = AnalystAgent(llm=mock_llm, verifier=VerdictVerifier(client=mock_llm))
    runner = DurableRunner(agent=agent)

    # 1. Apply Pair 7 Malicious scenario
    sc = load_scenario("pair7_convergence_stubborn_malicious")
    alert_id = apply_scenario(client, sc, clock=clock)

    # 2. Run investigation -> enters awaiting_approval with pod isolation action
    state = runner.start_investigation(alert_id=alert_id, client=client, clock=clock)
    assert state.status == "awaiting_approval"

    first_appr = client.query_dicts(
        "MATCH (ar:ApprovalRequest {status: 'pending'}) RETURN ar.id AS id, ar.action AS action"
    )
    assert len(first_appr) >= 1
    first_appr_id = first_appr[0]["id"]

    # 3. Approve first action (apply_isolation)
    # Verification should detect remaining path from rogue session and ESCALATE
    esc_res = runner.approve_and_remediate(approval_id=first_appr_id, client=client, clock=clock)
    assert esc_res["status"] == "escalated"
    assert esc_res["next_action"] == "revoke_session"

    second_appr_id = esc_res["approval_id"]
    assert second_appr_id is not None

    # 4. Approve escalated second action (revoke_session)
    final_res = runner.approve_and_remediate(approval_id=second_appr_id, client=client, clock=clock)
    assert final_res["status"] == "contained"

    # 5. Verify final status in FalkorDB is done and Finding was written
    inv_rows = client.query_dicts(
        """
        MATCH (inv:Investigation {id: $id})-[:CONCLUDED]->(f:Finding)
        RETURN inv.status AS status, f.verdict AS verdict
        """,
        {"id": state.investigation_id},
    )
    assert len(inv_rows) >= 1
    assert inv_rows[0]["status"] == "done"
    assert inv_rows[0]["verdict"] == "malicious"


def test_watch_evaluator_triggers_and_wakes_investigation():
    """Verify active telemetry watch fires upon matching event and awakens investigation."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    seed_world(client, seed=42)

    # Create dummy investigation in paused_watch status
    inv_id = "inv-watch-test-1"
    client.query(
        """
        CREATE (inv:Investigation {id: $id, status: 'paused_watch', started_at: $t0, updated_at: $t0})
        """,
        {"id": inv_id, "t0": clock.now()},
    )

    # Register watch for pod-checkout-1 connect events
    ctx = ToolContext(investigation_id=inv_id)
    watch_res = registry.execute(
        name="register_watch",
        arguments={
            "investigation_id": inv_id,
            "kind": "telemetry",
            "spec": {"pod_id": "pod-checkout-1", "kind": "connect", "dest": "169.254.169.254"},
            "expires_in": 3600,
        },
        context=ctx,
        client=client,
        clock=clock,
    )
    assert watch_res.success is True
    watch_id = watch_res.data["watch_id"]

    # Before event: watch is active and evaluate_all triggers nothing
    events_before = watch_evaluator.evaluate_all(client=client, clock=clock)
    assert len(events_before) == 0

    # Emit matching telemetry event
    clock.advance(60)
    ev = TelemetryEvent(
        ts=clock.now(),
        pod_id="pod-checkout-1",
        pid=999,
        ppid=1,
        binary="/usr/bin/curl",
        args=["169.254.169.254"],
        kind="connect",
        dest="169.254.169.254",
    )
    emit_event(client, ev)

    # Evaluate watches -> watch should trigger and awaken investigation
    triggered = watch_evaluator.evaluate_all(client=client, clock=clock)
    assert len(triggered) >= 1
    assert triggered[0]["watch_id"] == watch_id

    # Verify investigation status was transitioned to 'running'
    inv_rows = client.query_dicts(
        "MATCH (inv:Investigation {id: $id}) RETURN inv.status AS status",
        {"id": inv_id},
    )
    assert inv_rows[0]["status"] == "running"


def test_scheduler_executes_due_tasks():
    """Verify task scheduler executes due tasks upon simulated clock advancement."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    seed_world(client, seed=42)

    # Schedule task due in 600 seconds
    ctx = ToolContext(session_id="sess-analyst-runtime")
    sched_res = registry.execute(
        name="schedule_task",
        arguments={
            "investigation_id": "inv-sched-test",
            "due_in": 600,
            "action": "get_baseline",
            "payload": {"subject_id": "workload-checkout"},
        },
        context=ctx,
        client=client,
        clock=clock,
    )
    assert sched_res.success is True
    task_id = sched_res.data["task_id"]

    # Before clock advance: task is pending and not due
    due_before = task_scheduler.evaluate_due_tasks(client=client, clock=clock)
    assert len(due_before) == 0

    # Advance clock past due time
    clock.advance(650)

    # Dispatch due tasks
    executed = task_scheduler.evaluate_due_tasks(client=client, clock=clock)
    assert len(executed) >= 1
    assert executed[0]["task_id"] == task_id
    assert executed[0]["status"] == "completed"

    # Verify task status in FalkorDB
    task_rows = client.query_dicts(
        "MATCH (st:ScheduledTask {id: $id}) RETURN st.status AS status",
        {"id": task_id},
    )
    assert task_rows[0]["status"] == "completed"
