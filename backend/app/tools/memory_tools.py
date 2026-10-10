"""
Memory Tools: Recall historical cases, record verified investigation findings, and update baselines in FalkorDB.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.graph.queries import recall_similar as q_recall_similar
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 17. Recall Similar


class RecallSimilarInput(BaseModel):
    alert_id: str = Field(description="Alert ID to find structurally and contextually similar past alerts for")
    k: int = Field(default=5, description="Number of similar alerts to recall")


class RecallSimilarOutput(BaseModel):
    alert_id: str
    similar_alerts: list[dict[str, Any]]


@registry.register(
    name="recall_similar",
    description="Recalls historically similar security alerts and their resolved findings from the FalkorDB graph.",
    input_schema=RecallSimilarInput,
    output_schema=RecallSimilarOutput,
    read_only=True,
    requires_approval=False,
)
def recall_similar(
    alert_id: str,
    k: int = 5,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_recall_similar(c, alert_id=alert_id, k=k)
    evidence_ids = [f"ev:alert:{item['similar_alert_id']}" for item in data]
    return ToolResult(
        tool="recall_similar",
        success=True,
        data={"alert_id": alert_id, "similar_alerts": data},
        evidence_ids=evidence_ids,
    )


# 18. Write Finding


class WriteFindingInput(BaseModel):
    investigation_id: str = Field(description="Investigation ID that produced this finding")
    summary: str = Field(description="Summary of the finding and conclusion")
    verdict: str = Field(description="Verdict (benign or malicious)")
    confidence: float = Field(default=0.9, description="Confidence score (0.0 - 1.0)")
    evidence_ids: list[str] = Field(default_factory=list, description="List of evidence IDs cited by the finding")


class WriteFindingOutput(BaseModel):
    finding_id: str
    investigation_id: str
    verdict: str


@registry.register(
    name="write_finding",
    description="Persists a structured investigation Finding node and attaches cited Evidence in FalkorDB.",
    input_schema=WriteFindingInput,
    output_schema=WriteFindingOutput,
    read_only=False,
    requires_approval=False,
)
def write_finding(
    investigation_id: str,
    summary: str,
    verdict: str,
    confidence: float = 0.9,
    evidence_ids: list[str] = [],
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    finding_id = f"find-{uuid.uuid4().hex[:10]}"

    c.query(
        """
        MERGE (f:Finding {id: $id})
        SET f.summary = $summary,
            f.verdict = $verdict,
            f.confidence = $confidence,
            f.at = $at,
            f.evidence_ids = $evidence_ids
        """,
        {
            "id": finding_id,
            "summary": summary,
            "verdict": verdict,
            "confidence": confidence,
            "at": now,
            "evidence_ids": evidence_ids,
        },
    )

    # Link Finding to Investigation
    c.query(
        """
        MATCH (inv:Investigation {id: $invid}), (f:Finding {id: $fid})
        MERGE (inv)-[:CONCLUDED]->(f)
        """,
        {"invid": investigation_id, "fid": finding_id},
        ignore_errors=True,
    )

    data = {"finding_id": finding_id, "investigation_id": investigation_id, "verdict": verdict}
    return ToolResult(tool="write_finding", success=True, data=data, evidence_ids=[f"ev:finding:{finding_id}"])


# 19. Update Baseline


class UpdateBaselineInput(BaseModel):
    subject_id: str = Field(description="Subject entity ID (workload, principal, pod)")
    category: str = Field(description="Baseline category (e.g. approved_exec, normal_network)")
    summary: str = Field(description="Updated baseline description")


class UpdateBaselineOutput(BaseModel):
    baseline_id: str
    subject_id: str


@registry.register(
    name="update_baseline",
    description="Updates or creates a Baseline node in FalkorDB capturing learned behavioral norms.",
    input_schema=UpdateBaselineInput,
    output_schema=UpdateBaselineOutput,
    read_only=False,
    requires_approval=False,
)
def update_baseline(
    subject_id: str,
    category: str,
    summary: str,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    baseline_id = f"baseline-{subject_id}-{category}"

    c.query(
        """
        MERGE (b:Baseline {id: $id})
        SET b.category = $category,
            b.summary = $summary
        WITH b
        MATCH (s {id: $subject_id})
        MERGE (b)-[:DESCRIBES]->(s)
        """,
        {"id": baseline_id, "category": category, "summary": summary, "subject_id": subject_id},
    )

    data = {"baseline_id": baseline_id, "subject_id": subject_id}
    return ToolResult(tool="update_baseline", success=True, data=data, evidence_ids=[f"ev:baseline:{baseline_id}"])
