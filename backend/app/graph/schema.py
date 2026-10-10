"""
Graph Schema Definitions and Index Initialization for FalkorDB.
Defines canonical node labels, relationship types, and indexing logic.
"""

import logging

from backend.app.graph.client import GraphClient

logger = logging.getLogger("trust_analyst.schema")

# Canonical Node Labels
NODE_LABELS = [
    "Principal",
    "Agent",
    "AgentSession",
    "Delegation",
    "Tool",
    "MCPServer",
    "Workload",
    "Pod",
    "ServiceAccount",
    "Permission",
    "SensitiveResource",
    "NetworkEndpoint",
    "ChangeSet",
    "Document",
    "EventSummary",
    "Alert",
    "Investigation",
    "Hypothesis",
    "Evidence",
    "Finding",
    "Baseline",
    "Playbook",
    "Watch",
    "ScheduledTask",
    "ApprovalRequest",
    "ToolCall",
]

# Canonical Relationship Types
RELATIONSHIP_TYPES = [
    "OWNS_SESSION",
    "USES_AGENT",
    "GRANTED",
    "TO_SESSION",
    "CAN_INVOKE",
    "CONTAINS",
    "CAN_ACCESS",
    "RUNS_AS",
    "HAS_PERMISSION",
    "CONNECTED_TO",
    "TOUCHED",
    "DOCUMENTED_BY",
    "ABOUT",
    "INVESTIGATES",
    "HAS_HYPOTHESIS",
    "SUPPORTS",
    "REFUTES",
    "DERIVED_FROM",
    "CONCLUDED",
    "CITES",
    "REGISTERED",
    "SCHEDULED",
    "REQUESTED",
    "MADE_CALL",
    "DESCRIBES",
    "SIMILAR_TO",
    "TARGETS",
]


def init_schema(client: GraphClient) -> dict[str, int]:
    """
    Idempotently creates indexes on the 'id' property for all node labels in FalkorDB.
    Returns counts of created and existing indexes.
    """
    created = 0
    existing = 0

    for label in NODE_LABELS:
        try:
            client.query(f"CREATE INDEX FOR (n:{label}) ON (n.id)", ignore_errors=True)
            created += 1
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "already indexed" in err_msg:
                existing += 1
            else:
                logger.warning(f"Could not index label {label}: {e}")

    logger.info(f"Schema initialized in FalkorDB: {created} labels processed ({existing} existing).")
    return {"created": created, "existing": existing, "total_labels": len(NODE_LABELS)}
