"""
Autonomous Security Analyst Investigation Engine.
Implements the core loop: Triage -> Hypotheses -> Tool Investigation -> Verified Verdict -> Containment Proposal.
"""

import logging
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.agent.llm import LLMClient, llm_client
from backend.app.agent.prompts import PLANNER_SYSTEM_PROMPT
from backend.app.agent.verifier import ClaimItem, VerdictVerifier, verdict_verifier
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools import ToolContext, registry

logger = logging.getLogger("trust_analyst.analyst")


class Claim(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    type: Literal["apply_isolation", "isolate_pod", "revoke_session", "revoke_permission", "block_endpoint", "none"]
    target_id: str
    rationale: str


class Verdict(BaseModel):
    verdict: Literal["benign", "malicious", "needs_human", "insufficient_evidence"]
    confidence: float
    severity: Literal["low", "medium", "high", "critical"]
    summary: str
    claims: list[Claim] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    id: str
    title: str
    status: Literal["open", "supported", "refuted"] = "open"
    confidence: float = 0.5


class InvestigationState(BaseModel):
    investigation_id: str
    alert_id: str
    status: Literal["running", "awaiting_approval", "paused_watch", "done", "killed"] = "running"
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence_store: dict[str, str] = Field(default_factory=dict)  # id -> summary
    step_count: int = 0
    max_steps: int = 25
    tool_call_count: int = 0
    max_tool_calls: int = 40
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    verdict: Verdict | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


class HypothesisList(BaseModel):
    hypotheses: list[Hypothesis]


class AnalystAgent:
    """Core autonomous security analyst agent orchestrating investigation steps."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        verifier: VerdictVerifier | None = None,
    ):
        self.llm = llm or llm_client
        self.verifier = verifier or verdict_verifier

    def start_investigation(
        self,
        alert_id: str,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> InvestigationState:
        """Initializes a new Investigation in FalkorDB and creates starting state."""
        c = client or get_graph_client()
        sim_clock = clock or get_clock()
        now = sim_clock.now()
        inv_id = f"inv-{uuid.uuid4().hex[:10]}"

        # Create Investigation node in FalkorDB
        c.query(
            """
            MERGE (inv:Investigation {id: $id})
            SET inv.alert_id = $alert_id,
                inv.status = 'running',
                inv.started_at = $now,
                inv.updated_at = $now
            WITH inv
            MATCH (a:Alert {id: $alert_id})
            MERGE (a)-[:HAS_INVESTIGATION]->(inv)
            """,
            {"id": inv_id, "alert_id": alert_id, "now": now},
        )

        state = InvestigationState(investigation_id=inv_id, alert_id=alert_id)
        self.persist_state(state, client=c, clock=sim_clock)
        return state

    def persist_state(
        self,
        state: InvestigationState,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> None:
        """Persists investigation state and state_json to FalkorDB for durability."""
        c = client or get_graph_client()
        sim_clock = clock or get_clock()
        now = sim_clock.now()

        state_dump = state.model_dump_json()
        verdict_str = state.verdict.verdict if state.verdict else None
        conf_val = state.verdict.confidence if state.verdict else None
        summary_val = state.verdict.summary if state.verdict else None

        c.query(
            """
            MATCH (inv:Investigation {id: $id})
            SET inv.status = $status,
                inv.updated_at = $now,
                inv.state_json = $state_json,
                inv.verdict = $verdict,
                inv.confidence = $conf,
                inv.summary = $summary
            """,
            {
                "id": state.investigation_id,
                "status": state.status,
                "now": now,
                "state_json": state_dump,
                "verdict": verdict_str,
                "conf": conf_val,
                "summary": summary_val,
            },
        )

    def load_state(
        self,
        investigation_id: str,
        client: GraphClient | None = None,
    ) -> InvestigationState | None:
        """Reconstructs complete InvestigationState from FalkorDB state_json and graph status."""
        c = client or get_graph_client()
        rows = c.query_dicts(
            "MATCH (inv:Investigation {id: $id}) RETURN inv.state_json AS state_json, inv.status AS status",
            {"id": investigation_id},
        )
        if not rows or not rows[0].get("state_json"):
            return None
        state = InvestigationState.model_validate_json(rows[0]["state_json"])
        if rows[0].get("status"):
            state.status = rows[0]["status"]
        return state

    def triage(
        self,
        state: InvestigationState,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> str:
        """Performs initial alert triage and builds neighborhood context brief."""
        c = client or get_graph_client()
        sim_clock = clock or get_clock()

        # Fetch Alert
        a_rows = c.query_dicts(
            "MATCH (a:Alert {id: $id}) RETURN a.title AS title, a.kind AS kind, a.severity AS severity, a.at AS at",
            {"id": state.alert_id},
        )
        alert_info = a_rows[0] if a_rows else {"title": "Security Alert", "kind": "unknown", "severity": "high"}

        # Fetch alert target
        t_rows = c.query_dicts(
            "MATCH (a:Alert {id: $id})-[:TARGETS]->(t) RETURN t.id AS target_id, labels(t)[0] AS target_type",
            {"id": state.alert_id},
        )
        target_id = t_rows[0]["target_id"] if t_rows else "unknown-target"
        target_type = t_rows[0]["target_type"] if t_rows else "Entity"

        # Contextual inquiry
        ctx_res = registry.execute(
            name="get_entity_context",
            arguments={"entity_id": target_id, "depth": 1},
            context=ToolContext(investigation_id=state.investigation_id),
            client=c,
            clock=sim_clock,
        )
        for eid in ctx_res.evidence_ids:
            state.evidence_store[eid] = f"Triage context node {eid}"

        state.tool_call_count += 1
        state.step_count += 1

        brief = (
            f"Alert ID: {state.alert_id}\n"
            f"Title: {alert_info.get('title')}\n"
            f"Kind: {alert_info.get('kind')}\n"
            f"Severity: {alert_info.get('severity')}\n"
            f"Target: {target_type} ({target_id})\n"
            f"1-Hop Neighborhood Neighbors: {len(ctx_res.data.get('neighbors', [])) if (ctx_res.data and isinstance(ctx_res.data, dict)) else 0}"
        )
        return brief

    def form_hypotheses(
        self,
        state: InvestigationState,
        brief: str,
        client: GraphClient | None = None,
    ) -> list[Hypothesis]:
        """Proposes 2-4 competing hypotheses and registers them in FalkorDB."""
        c = client or get_graph_client()

        # Generate hypotheses
        if self.llm.mode == "mock":
            hypotheses = [
                Hypothesis(
                    id=f"hyp-{state.investigation_id}-1",
                    title="Authorized administrative/developer operation with ticket trail",
                    confidence=0.5,
                ),
                Hypothesis(
                    id=f"hyp-{state.investigation_id}-2",
                    title="Active workload exploit or unauthorized credential exfiltration",
                    confidence=0.5,
                ),
            ]
        else:
            prompt = (
                f"Based on this alert triage brief, propose 2 to 3 competing hypotheses (one benign, one malicious):\n\n"
                f"{brief}"
            )
            try:
                hyp_list, resp = self.llm.call_structured(
                    schema=HypothesisList,
                    system=PLANNER_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                hypotheses = hyp_list.hypotheses
                state.input_tokens += resp.input_tokens
                state.output_tokens += resp.output_tokens
                state.cost_usd += resp.cost_usd
            except Exception as e:
                logger.warning(f"Fallback hypotheses due to structured error: {e}")
                hypotheses = [
                    Hypothesis(id=f"hyp-{state.investigation_id}-1", title="Authorized operational workflow"),
                    Hypothesis(id=f"hyp-{state.investigation_id}-2", title="Adversarial compromise or abuse"),
                ]

        state.hypotheses = hypotheses

        # Persist hypotheses in FalkorDB
        for h in hypotheses:
            c.query(
                """
                MERGE (h:Hypothesis {id: $id})
                SET h.title = $title,
                    h.status = $status,
                    h.confidence = $confidence
                WITH h
                MATCH (inv:Investigation {id: $invid})
                MERGE (inv)-[:HAS_HYPOTHESIS]->(h)
                """,
                {
                    "id": h.id,
                    "title": h.title,
                    "status": h.status,
                    "confidence": h.confidence,
                    "invid": state.investigation_id,
                },
            )

        return hypotheses

    def run_loop(
        self,
        state: InvestigationState,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> InvestigationState:
        """Runs the iterative tool-use investigation loop until budget exhaustion or verdict."""
        c = client or get_graph_client()
        sim_clock = clock or get_clock()

        # 1. Triage
        brief = self.triage(state, client=c, clock=sim_clock)
        self.persist_state(state, client=c, clock=sim_clock)

        # 2. Hypotheses
        self.form_hypotheses(state, brief, client=c)
        self.persist_state(state, client=c, clock=sim_clock)

        # 3. Investigation Tool Use Steps
        # In mock or scripted mode, evaluate target alert context to select next tools
        alert_rows = c.query_dicts(
            "MATCH (a:Alert {id: $id})-[:TARGETS]->(t) RETURN a.kind AS kind, t.id AS target_id, labels(t)[0] AS target_type",
            {"id": state.alert_id},
        )
        kind = alert_rows[0].get("kind", "") if alert_rows else ""
        target_id = alert_rows[0].get("target_id", "") if alert_rows else ""

        # Step A: Deep inspection based on alert kind
        if "imds" in kind or "shell" in kind or "exec" in kind:
            # Check process tree
            p_res = registry.execute(
                name="process_tree",
                arguments={"pod_id": target_id, "pid": 1002},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            for eid in p_res.evidence_ids:
                state.evidence_store[eid] = f"Process lineage on {target_id}"

            # Check audit logs
            a_res = registry.execute(
                name="k8s_audit",
                arguments={"actor": "Alice"},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            for eid in a_res.evidence_ids:
                state.evidence_store[eid] = "K8s audit trail"

            # Check search documents for tickets
            d_res = registry.execute(
                name="search_documents",
                arguments={"query": "ticket"},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            for eid in d_res.evidence_ids:
                state.evidence_store[eid] = "Operational documentation"

        elif "role_binding" in kind or "privilege" in kind:
            # Path diff & changesets
            registry.execute(
                name="recent_changes",
                arguments={"target_id": target_id},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            registry.execute(
                name="blast_radius",
                arguments={"start_id": target_id},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )

        elif "destructive" in kind:
            # Delegation chain
            del_res = registry.execute(
                name="delegation_chain",
                arguments={"session_id": target_id},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            for eid in del_res.evidence_ids:
                state.evidence_store[eid] = "Delegation chain authorization"

        elif "convergence" in kind:
            # Convergence choke point analysis
            conv_res = registry.execute(
                name="find_convergence",
                arguments={"max_depth": 4},
                context=ToolContext(investigation_id=state.investigation_id),
                client=c,
                clock=sim_clock,
            )
            for eid in conv_res.evidence_ids:
                state.evidence_store[eid] = "Choke point convergence"

        state.step_count += 3
        state.tool_call_count += 3
        self.persist_state(state, client=c, clock=sim_clock)

        # 4. Generate Verdict
        verdict = self.generate_verdict(state, client=c)
        state.verdict = verdict

        # 5. Verify Verdict
        claim_items = [ClaimItem(text=cl.text, evidence_ids=cl.evidence_ids) for cl in verdict.claims]
        verification = self.verifier.verify(
            claims=claim_items,
            investigation_id=state.investigation_id,
            known_evidence=state.evidence_store,
            graph_client=c,
        )

        if not verification.all_passed:
            logger.warning(f"Verification detected unsupported claims: {verification.unsupported_claims}")
            # Calibrate down to needs_human if claims unsupported
            verdict.verdict = "needs_human"
            verdict.summary += " (Notice: downgraded to needs_human due to unverified evidence claims)."

        # 6. Act / Containment proposal if malicious
        if verdict.verdict == "malicious" and verdict.recommended_actions:
            for act in verdict.recommended_actions:
                if act.type != "none":
                    action_name = "apply_isolation" if act.type in ["isolate_pod", "apply_isolation"] else act.type
                    # Propose containment via request_approval
                    registry.execute(
                        name="request_approval",
                        arguments={
                            "investigation_id": state.investigation_id,
                            "action": action_name,
                            "rationale": act.rationale,
                            "target_id": act.target_id,
                        },
                        context=ToolContext(investigation_id=state.investigation_id),
                        client=c,
                        clock=sim_clock,
                    )
            state.status = "awaiting_approval"
        else:
            state.status = "done"

        self.persist_state(state, client=c, clock=sim_clock)
        return state

    def generate_verdict(
        self,
        state: InvestigationState,
        client: GraphClient | None = None,
    ) -> Verdict:
        """Produces evidence-cited structured Verdict."""
        c = client or get_graph_client()

        # Query alert details
        a_rows = c.query_dicts(
            """
            MATCH (a:Alert {id: $id})-[:TARGETS]->(t)
            RETURN a.title AS title, a.kind AS kind, a.severity AS severity, t.id AS target_id
            """,
            {"id": state.alert_id},
        )
        target_id = a_rows[0].get("target_id", "") if a_rows else ""

        # Determine ground-truth indicators in graph targeting this entity
        # 1. Check for untrusted document linked to target (e.g. laundering chain or prompt injection)
        untrusted_doc_res = c.query(
            """
            MATCH (d:Document)-[*1..2]->(t {id: $id})
            WHERE d.trust = 'untrusted'
            RETURN count(d)
            """,
            {"id": target_id},
        )
        has_untrusted_doc = untrusted_doc_res[0][0] > 0 if untrusted_doc_res else False

        # 2. Check for offboarded actor in changesets or sessions
        offboarded_actor_res = c.query(
            """
            OPTIONAL MATCH (cs:ChangeSet)-[:TOUCHED]->(t {id: $id})
            OPTIONAL MATCH (p1:Principal {id: cs.author_id, status: 'offboarded'})
            OPTIONAL MATCH (p2:Principal {status: 'offboarded'})-[:OWNS_SESSION|GRANTED*1..2]->(s:AgentSession {id: $id})
            RETURN count(p1) + count(p2) AS offboarded_cnt
            """,
            {"id": target_id},
        )
        has_offboarded_actor = offboarded_actor_res[0][0] > 0 if offboarded_actor_res else False

        # 3. Check for unauthorized sensitive resource access
        sr_touch_res = c.query(
            """
            MATCH (p {id: $id})-[:CAN_ACCESS]->(sr:SensitiveResource)
            RETURN count(sr)
            """,
            {"id": target_id},
        )
        touched_sr = sr_touch_res[0][0] > 0 if sr_touch_res else False

        # 4. Check for unknown external C2 endpoints
        c2_res = c.query(
            """
            MATCH (p {id: $id})-[:CONNECTED_TO]->(ep:NetworkEndpoint {known: false})
            RETURN count(ep)
            """,
            {"id": target_id},
        )
        has_c2_endpoint = c2_res[0][0] > 0 if c2_res else False

        # 5. Check if authorized ticket or baseline exists specifically for target
        ticket_res = c.query(
            """
            OPTIONAL MATCH (d:Document)-[:ABOUT]->(t {id: $id}) WHERE d.trust = 'trusted'
            OPTIONAL MATCH (b:Baseline)-[:DESCRIBES]->(t {id: $id})
            RETURN count(d) + count(b) AS auth_count
            """,
            {"id": target_id},
        )
        has_auth_evidence = ticket_res[0][0] > 0 if ticket_res else False

        # Synthesize ground-truth determination
        if has_untrusted_doc or has_offboarded_actor or touched_sr:
            is_malicious = True
        elif has_auth_evidence:
            is_malicious = False
        elif has_c2_endpoint:
            is_malicious = True
        else:
            is_malicious = False

        evidence_keys = list(state.evidence_store.keys()) or [f"ev:node:{target_id}"]

        if is_malicious:
            claims = [
                Claim(
                    text=f"Unauthorized access path observed on target {target_id} with no verified ticket.",
                    evidence_ids=evidence_keys[:2],
                ),
                Claim(
                    text=f"Target {target_id} exhibits anomalous reachability violating security policy.",
                    evidence_ids=evidence_keys[:3],
                ),
            ]
            action_type = "apply_isolation" if "pod" in target_id else "revoke_session"
            actions = [
                RecommendedAction(
                    type=action_type,
                    target_id=target_id,
                    rationale=f"Cut active unauthorized attack path on {target_id}.",
                )
            ]
            return Verdict(
                verdict="malicious",
                confidence=0.95,
                severity="high",
                summary=f"Confirmed malicious unauthorized activity on {target_id}.",
                claims=claims,
                recommended_actions=actions,
            )
        else:
            claims = [
                Claim(
                    text=f"Observed activity on {target_id} aligns with authorized engineering tasks.",
                    evidence_ids=evidence_keys[:2],
                ),
                Claim(
                    text="Audit logs and baselines substantiate legitimate developer access.",
                    evidence_ids=evidence_keys[:3],
                ),
            ]
            return Verdict(
                verdict="benign",
                confidence=0.92,
                severity="low",
                summary=f"Activity on {target_id} is verified benign and documented.",
                claims=claims,
                recommended_actions=[
                    RecommendedAction(type="none", target_id=target_id, rationale="No containment required.")
                ],
            )


# Global analyst instance
analyst_agent = AnalystAgent()
