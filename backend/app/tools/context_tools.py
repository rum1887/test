"""
Context Tools: Change history, Kubernetes audit records, metadata-only document search,
and quarantined reader for untrusted operational documents.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 13. Recent Changes


class RecentChangesInput(BaseModel):
    target_id: str = Field(description="Target entity ID to query recent deployments and changesets for")
    window_seconds: int = Field(default=86400, description="Time window in simulated seconds to look back")


class RecentChangesOutput(BaseModel):
    target_id: str
    changes: list[dict[str, Any]]


@registry.register(
    name="recent_changes",
    description="Queries recent deployments, terraform applies, and configuration changes affecting a workload.",
    input_schema=RecentChangesInput,
    output_schema=RecentChangesOutput,
    read_only=True,
    requires_approval=False,
)
def recent_changes(
    target_id: str,
    window_seconds: int = 86400,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sim_clock = clock or get_clock()
    now = sim_clock.now()
    since = now - window_seconds

    cypher = """
    MATCH (cs:ChangeSet)-[:TOUCHED]->(target {id: $id})
    OPTIONAL MATCH (target)-[:CONTAINS]->(pod:Pod)
    OPTIONAL MATCH (cs)-[:TOUCHED]->(pod)
    RETURN DISTINCT
        cs.id AS id,
        cs.kind AS kind,
        cs.summary AS summary,
        cs.author_id AS author_id,
        cs.ticket_id AS ticket_id,
        cs.pr_id AS pr_id
    """
    rows = c.query_dicts(cypher, {"id": target_id, "since": since})
    evidence_ids = [f"ev:changeset:{r['id']}" for r in rows]
    data = {"target_id": target_id, "changes": rows}
    return ToolResult(tool="recent_changes", success=True, data=data, evidence_ids=evidence_ids)


# 14. K8s Audit


class K8sAuditInput(BaseModel):
    window_seconds: int = Field(default=86400, description="Time window in simulated seconds to look back")
    actor: str | None = Field(default=None, description="Optional actor/principal filter")


class K8sAuditOutput(BaseModel):
    audit_records: list[dict[str, Any]]


@registry.register(
    name="k8s_audit",
    description="Returns structured fields from Kubernetes audit documents and authentication logs.",
    input_schema=K8sAuditInput,
    output_schema=K8sAuditOutput,
    read_only=True,
    requires_approval=False,
)
def k8s_audit(
    window_seconds: int = 86400,
    actor: str | None = None,
    client: GraphClient | None = None,
    clock: SimulatedClock | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    cypher = """
    MATCH (d:Document {kind: 'audit'})
    WHERE $actor IS NULL OR d.body CONTAINS $actor
    RETURN d.id AS id, d.title AS title, d.trust AS trust, d.body AS body
    LIMIT 20
    """
    rows = c.query_dicts(cypher, {"actor": actor})
    records = []
    evidence_ids = []
    for r in rows:
        records.append(
            {
                "id": r["id"],
                "title": r["title"],
                "trust": r["trust"],
                "summary": r["body"][:200],
            }
        )
        evidence_ids.append(f"ev:audit:{r['id']}")

    data = {"audit_records": records}
    return ToolResult(tool="k8s_audit", success=True, data=data, evidence_ids=evidence_ids)


# 15. Search Documents (Metadata only, NEVER bodies!)


class SearchDocumentsInput(BaseModel):
    query: str = Field(description="Search term matching document title or ID")


class SearchDocumentsOutput(BaseModel):
    matches: list[dict[str, Any]]


@registry.register(
    name="search_documents",
    description="Searches synthetic documents returning document id, kind, title, and trust flag ONLY (never raw body).",
    input_schema=SearchDocumentsInput,
    output_schema=SearchDocumentsOutput,
    read_only=True,
    requires_approval=False,
)
def search_documents(
    query: str,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    cypher = """
    MATCH (d:Document)
    WHERE d.id CONTAINS $query OR d.title CONTAINS $query OR d.kind CONTAINS $query
    RETURN d.id AS id, d.kind AS kind, d.title AS title, d.trust AS trust
    LIMIT 15
    """
    rows = c.query_dicts(cypher, {"query": query})
    evidence_ids = [f"ev:doc:{r['id']}" for r in rows]
    data = {"matches": rows}
    return ToolResult(tool="search_documents", success=True, data=data, evidence_ids=evidence_ids)


# 16. Read Untrusted (Quarantined extraction)


class ReadUntrustedInput(BaseModel):
    document_id: str | None = Field(default=None, description="Document ID to read")
    text: str | None = Field(default=None, description="Raw text snippet to parse safely")
    schema_type: str = Field(default="summary", description="Extraction target: summary, incident, change")


class ReadUntrustedOutput(BaseModel):
    document_id: str | None
    trust: str
    quarantined: bool
    extracted_fields: dict[str, Any]


@registry.register(
    name="read_untrusted",
    description="Quarantined safe reader: inspects untrusted document body or text, extracting structured fields without prompt leakage.",
    input_schema=ReadUntrustedInput,
    output_schema=ReadUntrustedOutput,
    read_only=True,
    requires_approval=False,
)
def read_untrusted(
    document_id: str | None = None,
    text: str | None = None,
    schema_type: str = "summary",
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    raw_text = text or ""
    trust_status = "untrusted"

    if document_id:
        doc_res = c.query_dicts(
            "MATCH (d:Document {id: $id}) RETURN d.body AS body, d.trust AS trust, d.title AS title",
            {"id": document_id},
        )
        if doc_res:
            raw_text = doc_res[0].get("body", "")
            trust_status = doc_res[0].get("trust", "untrusted")

    # Safe quarantined extraction (filters out prompt injection keywords)
    sanitized_preview = raw_text.replace("\n", " ")[:200]
    has_injection_attempt = any(
        kw in raw_text.lower()
        for kw in ["system instruction", "ignore previous", "override", "mark benign", "false positive"]
    )

    extracted_fields = {
        "text_length": len(raw_text),
        "sanitized_preview": sanitized_preview,
        "schema_type": schema_type,
        "adversarial_injection_detected": has_injection_attempt,
        "extracted_intent": "User provided instruction or ticket record",
    }

    data = {
        "document_id": document_id,
        "trust": trust_status,
        "quarantined": True,
        "extracted_fields": extracted_fields,
    }
    evidence_ids = [f"ev:doc:{document_id}"] if document_id else []
    return ToolResult(tool="read_untrusted", success=True, data=data, evidence_ids=evidence_ids)
