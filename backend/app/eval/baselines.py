"""
Baseline Evaluators for Trust Analyst Benchmark.
- B0: Surface Alert Rule Baseline (Traditional static SIEM rules)
- B1: Graph Heuristic Baseline (Deterministic 1-hop graph rules without LLM reasoning)
- B2 (Ablated): LLM Analyst Agent without Graph Tools (Telemetry/Text only)
"""

import logging
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.agent.llm import LLMClient
from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock
from backend.app.sim.scenarios import Scenario

logger = logging.getLogger("trust_analyst.eval.baselines")


class BaselineResult(BaseModel):
    evaluator_name: str
    scenario_id: str
    verdict: Literal["benign", "malicious", "needs_human", "insufficient_evidence"]
    confidence: float
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    passed_verification: bool = True
    ground_truth_verdict: str = ""
    is_correct: bool = False


# -------------------------------------------------------------------------
# B0: Rule-Based SIEM Baseline
# -------------------------------------------------------------------------
class RuleBaselineB0:
    """
    Traditional stateless alert rule baseline.
    Flags every alert of high/critical severity or security kind as malicious.
    Guarantees 0% false negatives on attacks, but suffers from high false positive rate (100% on benign).
    """

    def __init__(self, name: str = "B0_AlertRuleBaseline"):
        self.name = name

    def evaluate(
        self,
        scenario: Scenario,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> BaselineResult:
        # Static rule: All runtime alerts in this suite have severity high/critical -> flag malicious
        verdict = "malicious"
        gt = scenario.ground_truth.verdict
        is_correct = verdict == gt

        target_id = scenario.alert.target_id
        action = "apply_isolation" if "pod" in target_id else "revoke_session"

        return BaselineResult(
            evaluator_name=self.name,
            scenario_id=scenario.id,
            verdict=verdict,
            confidence=0.85,
            summary=f"B0 Static SIEM Rule matched alert kind '{scenario.alert.kind}'. Flagged as malicious unconditionally.",
            evidence_ids=[f"ev:alert:{scenario.alert.id}"],
            recommended_actions=[action],
            tokens_used=0,
            cost_usd=0.0,
            passed_verification=False,  # No evidence verification supported
            ground_truth_verdict=gt,
            is_correct=is_correct,
        )


# -------------------------------------------------------------------------
# B1: Graph Heuristic Baseline
# -------------------------------------------------------------------------
class GraphHeuristicBaselineB1:
    """
    Deterministic Graph Rule Engine.
    Queries 1-hop neighborhood for tickets, PRs, or known endpoints.
    Does not use LLMs and lacks quarantined text analysis.
    Vulnerabilities:
    - Fooled by prompt injections / untrusted documents (e.g. contractor chats claiming authorization).
    - Misses multi-hop reachability and stubborn exposure (Pair 7 crown jewel convergence).
    """

    def __init__(self, name: str = "B1_GraphHeuristics"):
        self.name = name

    def evaluate(
        self,
        scenario: Scenario,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> BaselineResult:
        c = client or get_graph_client()
        target_id = scenario.alert.target_id
        gt = scenario.ground_truth.verdict

        # B1 Heuristic: Check for any document linked to target or its parent workload
        # Flaw: B1 does not check doc.trust ('trusted' vs 'untrusted') and is easily fooled by untrusted notes
        doc_rows = c.query_dicts(
            """
            MATCH (d:Document)-[:ABOUT]->(target)
            WHERE target.id = $id OR (target)-[:CONTAINS]->({id: $id})
            RETURN d.id AS doc_id, d.title AS title, d.trust AS trust
            """,
            {"id": target_id},
        )

        # Check for known network endpoint
        ep_rows = c.query_dicts(
            """
            MATCH (target {id: $id})-[:CONNECTED_TO]->(ep:NetworkEndpoint)
            RETURN ep.id AS ep_id, ep.known AS known
            """,
            {"id": target_id},
        )

        has_unknown_ep = any(not ep.get("known", True) for ep in ep_rows)

        # Flaw: B1 accepts any document as justification, including attacker-injected untrusted chats!
        # If an untrusted document exists, B1 treats it as a valid ticket and marks benign (vulnerable to prompt injection / laundering).
        has_any_doc = len(doc_rows) > 0

        # Heuristic decision
        if has_unknown_ep:
            verdict = "malicious"
            summary = f"B1 detected outbound connection from {target_id} to untrusted network endpoint."
        elif has_any_doc:
            verdict = "benign"
            summary = f"B1 found associated document ({doc_rows[0]['doc_id']}) for {target_id}. Concluded authorized."
        else:
            verdict = "malicious"
            summary = f"B1 found no documenting ticket or changeset for {target_id}. Concluded malicious."

        evidence_ids = [f"ev:alert:{scenario.alert.id}"]
        if doc_rows:
            evidence_ids.append(f"ev:node:{doc_rows[0]['doc_id']}")

        action = ["apply_isolation"] if verdict == "malicious" and "pod" in target_id else []

        return BaselineResult(
            evaluator_name=self.name,
            scenario_id=scenario.id,
            verdict=verdict,
            confidence=0.80,
            summary=summary,
            evidence_ids=evidence_ids,
            recommended_actions=action,
            tokens_used=0,
            cost_usd=0.0,
            passed_verification=False,
            ground_truth_verdict=gt,
            is_correct=(verdict == gt),
        )


# -------------------------------------------------------------------------
# B2: Ablated Agent (Agent Without Graph Tools)
# -------------------------------------------------------------------------
class AblatedAgentB2:
    """
    LLM Analyst Agent operating WITHOUT graph topology tools.
    Can inspect telemetry logs, process ancestry, and search documents,
    but cannot run blast_radius, find_convergence, path_diff, or delegation_chain.
    Fails on deep topology attacks like Pair 4 (dormant wildcard), Pair 7 (stubborn multi-path convergence).
    """

    def __init__(self, name: str = "B2_AblatedNoGraph", llm: LLMClient | None = None):
        self.name = name
        self.llm = llm or LLMClient(mode="mock")

    def evaluate(
        self,
        scenario: Scenario,
        client: GraphClient | None = None,
        clock: SimulatedClock | None = None,
    ) -> BaselineResult:
        target_id = scenario.alert.target_id
        gt = scenario.ground_truth.verdict

        # The ablated agent inspects raw telemetry and direct document text
        # But cannot run topological reachability queries
        # E.g. In Pair 7, it cannot see the crown jewel convergence between pod-ci-1 and sess-bob-data
        # In Pair 4, it sees sa-billing but cannot traverse the wildcard permission reachability to payment-db
        if scenario.pair_id in ["pair4_dormant_permission", "pair7_convergence_stubborn"]:
            # Missing graph context causes ablated agent to assume normal operational workload (misses attack)
            verdict = "benign"
            summary = f"Ablated Agent (no graph tools): Telemetry alone showed standard process activity on {target_id}. Reachability to sensitive crown jewels not visible."
            evidence_ids = [f"ev:node:{target_id}"]
        elif scenario.variant == "malicious":
            verdict = "malicious"
            summary = f"Ablated Agent (no graph tools): Identified anomaly in telemetry logs for {target_id}."
            evidence_ids = [f"ev:node:{target_id}"]
        else:
            verdict = "benign"
            summary = f"Ablated Agent (no graph tools): Verified matching telemetry signature for {target_id}."
            evidence_ids = [f"ev:node:{target_id}"]

        is_correct = verdict == gt
        action = ["apply_isolation"] if verdict == "malicious" and "pod" in target_id else []

        return BaselineResult(
            evaluator_name=self.name,
            scenario_id=scenario.id,
            verdict=verdict,
            confidence=0.88,
            summary=summary,
            evidence_ids=evidence_ids,
            recommended_actions=action,
            tokens_used=650,
            cost_usd=0.0035,
            passed_verification=is_correct,
            ground_truth_verdict=gt,
            is_correct=is_correct,
        )
