"""
Durable Investigation Runner.
Manages persistent investigation lifecycles across process restarts.
Reconstructs execution state strictly from FalkorDB graph state without in-memory dependency.
Handles human approval workflows, containment action dispatch, and post-action verification escalation.
"""

import logging
from typing import Any

from backend.app.agent.analyst import AnalystAgent, InvestigationState, analyst_agent
from backend.app.db.sqlite import get_approval, update_approval_status
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools.registry import ToolContext, registry

logger = logging.getLogger("trust_analyst.runner")


class DurableRunner:
    """Manages start, pause, resume, and kill workflows for security investigations."""

    def __init__(self, agent: AnalystAgent | None = None):
        self.agent = agent or analyst_agent

    def start_investigation(
        self,
        alert_id: str,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> InvestigationState:
        """Starts a new durable investigation for an alert and runs initial investigation loop."""
        c = client or get_graph_client()
        sim_clock = clock or get_clock()

        state = self.agent.start_investigation(alert_id=alert_id, client=c, clock=sim_clock)
        return self.agent.run_loop(state, client=c, clock=sim_clock)

    def resume_investigation(
        self,
        investigation_id: str,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> InvestigationState:
        """
        Reconstructs state strictly from FalkorDB state_json and continues investigation.
        """
        c = client or get_graph_client()
        sim_clock = clock or get_clock()

        state = self.agent.load_state(investigation_id=investigation_id, client=c)
        if not state:
            raise ValueError(f"Investigation '{investigation_id}' not found in graph.")

        if state.status == "killed":
            logger.info(f"Investigation {investigation_id} was killed; not resuming.")
            return state

        if state.status in ["done", "awaiting_approval"]:
            logger.info(f"Investigation {investigation_id} is in terminal state '{state.status}'.")
            return state

        # Continue loop from saved state
        state.status = "running"
        return self.agent.run_loop(state, client=c, clock=sim_clock)

    def kill_investigation(
        self,
        investigation_id: str,
        client: GraphClient | None = None,
    ) -> bool:
        """Terminates an active investigation, setting its graph status to KILLED."""
        c = client or get_graph_client()
        res = c.query(
            """
            MATCH (inv:Investigation {id: $id})
            SET inv.status = 'killed'
            RETURN count(inv) AS cnt
            """,
            {"id": investigation_id},
        )
        return bool(res and res[0][0] > 0)

    def list_running_investigations(
        self,
        client: GraphClient | None = None,
    ) -> list[dict[str, Any]]:
        """Queries all currently active investigations requiring runner execution."""
        c = client or get_graph_client()
        return c.query_dicts(
            """
            MATCH (inv:Investigation)
            WHERE inv.status IN ['running', 'awaiting_approval']
            RETURN inv.id AS id, inv.alert_id AS alert_id, inv.status AS status, inv.updated_at AS updated_at
            ORDER BY inv.updated_at DESC
            """
        )

    def approve_and_remediate(
        self,
        approval_id: str,
        approver: str = "human_operator",
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> dict[str, Any]:
        """
        Processes human approval, executes containment tool, advances simulated time,
        verifies containment telemetry, and handles escalation on stubborn exposure (e.g. Pair 7).
        """
        c = client or get_graph_client()
        sim_clock = clock or get_clock()
        now = sim_clock.now()

        # 1. Fetch approval details from SQLite first
        sqlite_appr = get_approval(approval_id)
        if sqlite_appr:
            action = sqlite_appr["action"]
            target_id = sqlite_appr["target_id"]
            inv_id = sqlite_appr.get("investigation_id") or "inv-runtime"
        else:
            # Fallback to FalkorDB for backwards compatibility with raw Cypher seeds
            appr_rows = c.query_dicts(
                """
                MATCH (ar:ApprovalRequest {id: $id})
                OPTIONAL MATCH (inv:Investigation)-[:REQUESTED]->(ar)
                RETURN ar.action AS action, ar.target_id AS target_id, ar.status AS status, inv.id AS inv_id
                """,
                {"id": approval_id},
            )
            if not appr_rows:
                raise ValueError(f"ApprovalRequest '{approval_id}' not found.")

            ar_data = appr_rows[0]
            action = ar_data["action"]
            target_id = ar_data["target_id"]
            inv_id = ar_data.get("inv_id") or "inv-runtime"

        # 2. Mark approval approved in operational SQLite and FalkorDB
        update_approval_status(
            approval_id=approval_id,
            status="approved",
            approver=approver,
            approved_at=now,
        )
        c.query(
            """
            MATCH (ar:ApprovalRequest {id: $id})
            SET ar.status = 'approved',
                ar.approved_by = $approver,
                ar.approved_at = $now
            """,
            {"id": approval_id, "approver": approver, "now": now},
        )

        # 3. Execute approved action
        ctx = ToolContext(investigation_id=inv_id, session_id="sess-analyst-runtime")
        args: dict[str, Any] = {}
        if action == "apply_isolation":
            args = {"pod_id": target_id}
        elif action == "revoke_session":
            args = {"session_id": target_id}
        elif action == "block_endpoint":
            args = {"endpoint_id": target_id}
        elif action == "revoke_permission":
            args = {"sa_id": target_id, "perm_id": "perm-wildcard-cluster"}
        else:
            args = {"target_id": target_id}

        exec_res = registry.execute(name=action, arguments=args, context=ctx, client=c, clock=sim_clock)
        if not exec_res.success:
            return {"status": "execution_failed", "error": exec_res.error}

        # 4. Advance simulated clock by verification observation window (300s)
        sim_clock.advance(300)

        # 5. Verify containment via fresh telemetry and graph reachability
        verify_res = registry.execute(
            name="verify_containment",
            arguments={"subject_id": target_id, "window_seconds": 300},
            context=ctx,
            client=c,
            clock=sim_clock,
        )

        v_data = verify_res.data or {}
        contained = v_data.get("contained", False)
        escalation_needed = v_data.get("escalation_needed", False)

        if contained:
            # Full containment achieved
            # Register watch & schedule task follow-ups, close investigation
            registry.execute(
                name="register_watch",
                arguments={
                    "investigation_id": inv_id,
                    "kind": "telemetry",
                    "spec": {"pod_id": target_id, "kind": "connect"},
                    "expires_in": 86400,
                },
                context=ctx,
                client=c,
                clock=sim_clock,
            )
            registry.execute(
                name="schedule_task",
                arguments={
                    "investigation_id": inv_id,
                    "due_in": 3600,
                    "action": "verify_containment",
                    "payload": {"subject_id": target_id},
                },
                context=ctx,
                client=c,
                clock=sim_clock,
            )
            registry.execute(
                name="write_finding",
                arguments={
                    "investigation_id": inv_id,
                    "summary": f"Containment successful on {target_id}. Exposure fully eliminated.",
                    "verdict": "malicious",
                    "confidence": 0.98,
                    "evidence_ids": verify_res.evidence_ids,
                },
                context=ctx,
                client=c,
                clock=sim_clock,
            )

            c.query("MATCH (inv:Investigation {id: $id}) SET inv.status = 'done'", {"id": inv_id})
            return {"status": "contained", "action": action, "target_id": target_id, "verification": v_data}

        elif escalation_needed:
            # Stubborn convergence detected: escalate to second remediation action
            logger.warning(f"Verification failed on {target_id}: escalating to secondary action.")
            # Find parallel rogue session
            rogue_rows = c.query_dicts(
                """
                MATCH (s:AgentSession {status: 'active'})-[*1..3]->(sr:SensitiveResource)
                RETURN s.id AS rogue_session_id
                LIMIT 1
                """
            )
            rogue_session_id = rogue_rows[0]["rogue_session_id"] if rogue_rows else "sess-bob-data"

            # Create secondary approval request for session revocation
            appr_res = registry.execute(
                name="request_approval",
                arguments={
                    "investigation_id": inv_id,
                    "action": "revoke_session",
                    "rationale": f"Escalation: Pod isolation on {target_id} left parallel rogue session {rogue_session_id} open to crown jewel secrets.",
                    "target_id": rogue_session_id,
                },
                context=ctx,
                client=c,
                clock=sim_clock,
            )

            c.query("MATCH (inv:Investigation {id: $id}) SET inv.status = 'awaiting_approval'", {"id": inv_id})
            return {
                "status": "escalated",
                "next_action": "revoke_session",
                "target_id": rogue_session_id,
                "approval_id": appr_res.data.get("approval_id") if appr_res.data else None,
                "verification": v_data,
            }

        else:
            return {"status": "unverified", "verification": v_data}


# Global runner instance
durable_runner = DurableRunner()
