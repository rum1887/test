"""
Durable Investigation Runner.
Manages persistent investigation lifecycles across process restarts.
Reconstructs execution state strictly from FalkorDB graph state without in-memory dependency.
"""

import logging
from typing import Any

from backend.app.agent.analyst import AnalystAgent, InvestigationState, analyst_agent
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock

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


# Global runner instance
durable_runner = DurableRunner()
