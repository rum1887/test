"""
Watch Evaluator for Trust Analyst.
Monitors graph pattern conditions and telemetry streams against active Watch nodes in FalkorDB.
Uses an allowlisted query template registry to safely evaluate graph watches without raw Cypher injection.
"""

import json
import logging
from typing import Any

from backend.app.db.sqlite import list_active_watches, update_watch_status
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.sim.telemetry import telemetry_source

logger = logging.getLogger("trust_analyst.watcher")

# Allowlisted Cypher templates for graph_pattern watches
ALLOWLISTED_GRAPH_PATTERNS: dict[str, str] = {
    "check_sensitive_access": (
        "MATCH (p:Pod {id: $pod_id})-[:CAN_ACCESS]->(sr:SensitiveResource) RETURN count(sr) AS cnt"
    ),
    "check_role_binding": (
        "MATCH (sa:ServiceAccount {id: $sa_id})-[:HAS_PERMISSION]->(p:Permission {verb: $verb}) RETURN count(p) AS cnt"
    ),
    "check_active_session": ("MATCH (s:AgentSession {id: $session_id, status: 'active'}) RETURN count(s) AS cnt"),
    "check_outbound_connection": (
        "MATCH (p:Pod {id: $pod_id})-[:CONNECTED_TO]->(ep:NetworkEndpoint {address: $address}) RETURN count(ep) AS cnt"
    ),
}


class WatchEvaluator:
    """Evaluates active condition watches in FalkorDB on clock ticks."""

    def evaluate_all(
        self,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> list[dict[str, Any]]:
        """
        Scans all active Watch nodes in FalkorDB, evaluates trigger predicates,
        and transitions state to 'triggered' or 'expired'.
        Returns list of triggered watch events.
        """
        c = client or get_graph_client()
        sim_clock = clock or get_clock()
        now = sim_clock.now()

        # Query all active watches from relational operational SQLite first
        sqlite_watches = list_active_watches()
        if sqlite_watches:
            rows = sqlite_watches
        else:
            # Fallback to FalkorDB for backwards compatibility with raw Cypher seeds
            rows = c.query_dicts(
                """
                MATCH (w:Watch {status: 'active'})
                OPTIONAL MATCH (inv:Investigation)-[:REGISTERED]->(w)
                RETURN w.id AS id, w.kind AS kind, w.spec AS spec, w.expires_at AS expires_at, inv.id AS inv_id, w.investigation_id AS investigation_id
                """
            )

        triggered_events: list[dict[str, Any]] = []

        for row in rows:
            wid = row["id"]
            kind = row["kind"]
            inv_id = row.get("investigation_id") or row.get("inv_id")
            expires_at = row.get("expires_at") or (now + 86400)

            # Check expiration
            if now >= expires_at:
                update_watch_status(wid, status="expired")
                c.query("MATCH (w:Watch {id: $id}) SET w.status = 'expired'", {"id": wid})
                continue

            # Parse spec
            raw_spec = row.get("spec", "{}")
            spec = json.loads(raw_spec) if isinstance(raw_spec, str) else raw_spec

            is_triggered = False
            evidence_summary = ""

            if kind == "graph_pattern":
                template_name = spec.get("template")
                params = spec.get("params", {})

                if template_name in ALLOWLISTED_GRAPH_PATTERNS:
                    query = ALLOWLISTED_GRAPH_PATTERNS[template_name]
                    res = c.query(query, params)
                    count = res[0][0] if res else 0
                    threshold = spec.get("threshold", 1)
                    if count >= threshold:
                        is_triggered = True
                        evidence_summary = f"Graph pattern watch '{template_name}' matched count {count} >= {threshold}"

            elif kind == "telemetry":
                pod_id = spec.get("pod_id")
                event_kind = spec.get("kind")
                dest = spec.get("dest")
                window_seconds = spec.get("window_seconds", 300)
                since = now - window_seconds

                events = telemetry_source.get_events(
                    pod_id=pod_id,
                    kind=event_kind,
                    window_start=since,
                    window_end=now,
                )
                if dest:
                    events = [e for e in events if e.dest == dest or (e.args and dest in e.args)]

                if events:
                    is_triggered = True
                    evidence_summary = (
                        f"Telemetry watch matched {len(events)} events for pod '{pod_id}' (kind: {event_kind})"
                    )

            if is_triggered:
                # Transition status to triggered in SQLite and FalkorDB
                update_watch_status(wid, status="triggered", triggered_at=now)
                c.query(
                    """
                    MATCH (w:Watch {id: $id})
                    SET w.status = 'triggered', w.triggered_at = $now, w.evidence = $ev
                    """,
                    {"id": wid, "now": now, "ev": evidence_summary},
                )

                # Attach trigger evidence and wake investigation if linked
                if inv_id:
                    ev_id = f"ev:watch:{wid}"
                    c.query(
                        """
                        MATCH (inv:Investigation {id: $invid})
                        MERGE (ev:Evidence {id: $evid})
                        SET ev.source = 'watch_evaluator', ev.summary = $summary, ev.at = $now
                        MERGE (inv)-[:CITES]->(ev)
                        SET inv.status = 'running'
                        """,
                        {"invid": inv_id, "evid": ev_id, "summary": evidence_summary, "now": now},
                    )

                triggered_events.append(
                    {
                        "watch_id": wid,
                        "kind": kind,
                        "investigation_id": inv_id,
                        "summary": evidence_summary,
                        "at": now,
                    }
                )
                logger.info(f"Watch {wid} triggered at {now}: {evidence_summary}")

        return triggered_events


# Global watch evaluator instance
watch_evaluator = WatchEvaluator()
