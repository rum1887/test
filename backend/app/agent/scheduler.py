"""
Scheduler for Trust Analyst.
Evaluates pending ScheduledTask nodes in FalkorDB as simulated time advances,
dispatches follow-up verification actions, and records completion state.
"""

import json
import logging
from typing import Any

from backend.app.db.sqlite import list_due_tasks, update_task_status
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools.registry import ToolContext, registry

logger = logging.getLogger("trust_analyst.scheduler")


class TaskScheduler:
    """Dispatches due ScheduledTask nodes from FalkorDB on simulated clock ticks."""

    def evaluate_due_tasks(
        self,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> list[dict[str, Any]]:
        """
        Finds all pending ScheduledTask nodes where due_at <= current simulated time,
        executes their action handlers, and records status in FalkorDB.
        """
        c = client or get_graph_client()
        sim_clock = clock or get_clock()
        now = sim_clock.now()

        # Query due tasks from operational SQLite first
        sqlite_due = list_due_tasks(now=now)
        if sqlite_due:
            rows = sqlite_due
        else:
            # Fallback to FalkorDB for backwards compatibility with raw Cypher seeds
            rows = c.query_dicts(
                """
                MATCH (st:ScheduledTask {status: 'pending'})
                WHERE st.due_at <= $now
                OPTIONAL MATCH (inv:Investigation)-[:SCHEDULED]->(st)
                RETURN st.id AS id, st.action AS action, st.payload AS payload, st.due_at AS due_at, inv.id AS inv_id, st.investigation_id AS investigation_id
                ORDER BY st.due_at ASC
                """,
                {"now": now},
            )

        executed_tasks: list[dict[str, Any]] = []

        for row in rows:
            tid = row["id"]
            action = row["action"]
            inv_id = row.get("investigation_id") or row.get("inv_id")
            raw_payload = row.get("payload", "{}")
            payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

            success = True
            error_msg = None

            try:
                # Dispatch action via tool registry
                ctx = ToolContext(investigation_id=inv_id, session_id="sess-analyst-runtime")
                res = registry.execute(
                    name=action,
                    arguments=payload,
                    context=ctx,
                    client=c,
                    clock=sim_clock,
                )
                success = res.success
                error_msg = res.error
            except Exception as e:
                logger.exception(f"Error executing scheduled task {tid} ({action}): {e}")
                success = False
                error_msg = str(e)

            # Update ScheduledTask status in operational SQLite and FalkorDB
            status = "completed" if success else "failed"
            update_task_status(
                task_id=tid,
                status=status,
                executed_at=now,
                result=error_msg or "Success",
            )
            c.query(
                """
                MATCH (st:ScheduledTask {id: $id})
                SET st.status = $status,
                    st.executed_at = $now,
                    st.result = $result
                """,
                {"id": tid, "status": status, "now": now, "result": error_msg or "Success"},
            )

            executed_tasks.append(
                {
                    "task_id": tid,
                    "action": action,
                    "status": status,
                    "investigation_id": inv_id,
                    "at": now,
                }
            )
            logger.info(f"Executed scheduled task {tid} ({action}) -> {status}")

        return executed_tasks


# Global scheduler instance
task_scheduler = TaskScheduler()
