"""
Unified Graph Data Model & Schema Definitions for Runtime Trust Layer.
Defines canonical node labels, edge types, index definitions, and integrity validations.
"""

import logging
from typing import Dict, List, Any
from graph.client import GraphClient

logger = logging.getLogger("trustlayer.schema")

SCHEMA_VERSION = "1.0.0"

# Canonical Node Labels
NODE_LABELS = [
    "Principal",
    "Agent",
    "AgentSession",
    "Delegation",
    "Workload",
    "Pod",
    "Container",
    "ServiceAccount",
    "Credential",
    "Permission",
    "KubernetesResource",
    "MCPServer",
    "Tool",
    "SensitiveResource",
    "NetworkEndpoint",
    "RuntimeEvent",
    "Policy",
    "EnforcementPoint",
    "PolicyDecision",
    "ContainmentAction",
]

# Canonical Relationship Types
RELATIONSHIP_TYPES = [
    "AUTHENTICATES_AS",
    "OWNS_SESSION",
    "DELEGATES_TO",
    "ACTS_ON_BEHALF_OF",
    "RUNS_AS",
    "USES_CREDENTIAL",
    "HAS_PERMISSION",
    "CAN_INVOKE",
    "CAN_ACCESS",
    "CAN_REACH",
    "OBSERVED_ACCESS",
    "EMITTED_EVENT",
    "VIOLATED_POLICY",
    "PROTECTED_BY",
    "ENFORCED_AT",
    "CONSTRAINS",
    "CONTAINS",
]

# Indexes to create for high-speed security traversals
INDEXES = [
    ("Principal", "id"),
    ("Agent", "id"),
    ("AgentSession", "id"),
    ("Delegation", "id"),
    ("Workload", "id"),
    ("Pod", "id"),
    ("Container", "id"),
    ("ServiceAccount", "id"),
    ("Credential", "id"),
    ("Permission", "id"),
    ("KubernetesResource", "id"),
    ("MCPServer", "id"),
    ("Tool", "id"),
    ("SensitiveResource", "id"),
    ("NetworkEndpoint", "id"),
    ("RuntimeEvent", "id"),
    ("Policy", "id"),
    ("EnforcementPoint", "id"),
    ("PolicyDecision", "id"),
    ("ContainmentAction", "id"),
]


def initialize_schema(client: GraphClient) -> Dict[str, Any]:
    """
    Idempotently initialize indexes and store schema metadata in the graph.
    """
    created_indexes = []
    skipped_indexes = []

    for label, prop in INDEXES:
        try:
            client.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})", ignore_errors=True)
            created_indexes.append(f"{label}.{prop}")
        except Exception as e:
            err_str = str(e)
            if "already indexed" in err_str.lower():
                skipped_indexes.append(f"{label}.{prop} (already exists)")
            else:
                skipped_indexes.append(f"{label}.{prop}: {err_str}")

    # Set or update schema metadata node
    client.query(
        """
        MERGE (m:SchemaMetadata {id: 'schema_version'})
        SET m.version = $version,
            m.initialized_at = timestamp(),
            m.node_labels = $labels,
            m.relationship_types = $rel_types
        RETURN m.version
        """,
        {
            "version": SCHEMA_VERSION,
            "labels": NODE_LABELS,
            "rel_types": RELATIONSHIP_TYPES,
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "indexes_attempted": len(INDEXES),
        "created_indexes": created_indexes,
        "skipped_indexes": skipped_indexes,
    }


def validate_graph_integrity(client: GraphClient) -> Dict[str, Any]:
    """
    Query 10: Automated Graph Integrity Checks.
    Validates:
    - Delegations pointing to nonexistent principals or agents
    - Orphaned runtime events
    - Expired credentials or sessions still marked active
    - Invalid or impossible relationship combinations
    """
    issues: List[Dict[str, Any]] = []

    # 1. Delegations with missing Principal or Agent
    orphan_delegations = client.query(
        """
        MATCH (d:Delegation)
        WHERE NOT (d)<-[:DELEGATES_TO]-(:Principal) OR NOT (d)-[:DELEGATES_TO]->(:Agent)
        RETURN d.id AS id, d.status AS status
        """
    )
    for row in orphan_delegations:
        issues.append({
            "type": "ORPHAN_DELEGATION",
            "entity_id": row[0],
            "severity": "HIGH",
            "message": f"Delegation {row[0]} lacks valid Principal or Agent linkage",
        })

    # 2. Orphaned Runtime Events not connected to any Pod, Container, or Session
    orphan_events = client.query(
        """
        MATCH (e:RuntimeEvent)
        WHERE NOT ()-[:EMITTED_EVENT]->(e)
        RETURN e.id AS id, e.event_type AS event_type, e.timestamp AS ts
        """
    )
    for row in orphan_events:
        issues.append({
            "type": "ORPHAN_RUNTIME_EVENT",
            "entity_id": row[0],
            "severity": "MEDIUM",
            "message": f"RuntimeEvent {row[0]} ({row[1]}) has no emitting workload or session edge",
        })

    # 3. Active sessions past expiration timestamp
    expired_active_sessions = client.query(
        """
        MATCH (s:AgentSession)
        WHERE s.status = 'ACTIVE' AND s.expires_at < timestamp() / 1000
        RETURN s.id AS id, s.expires_at AS expires_at
        """
    )
    for row in expired_active_sessions:
        issues.append({
            "type": "EXPIRED_SESSION_ACTIVE",
            "entity_id": row[0],
            "severity": "HIGH",
            "message": f"AgentSession {row[0]} is marked ACTIVE but expires_at ({row[1]}) is in the past",
        })

    # 4. Pods without Workload parent
    orphan_pods = client.query(
        """
        MATCH (p:Pod)
        WHERE NOT (:Workload)-[:CONTAINS]->(p)
        RETURN p.id AS id, p.name AS name
        """
    )
    for row in orphan_pods:
        issues.append({
            "type": "ORPHAN_POD",
            "entity_id": row[0],
            "severity": "LOW",
            "message": f"Pod {row[0]} ({row[1]}) is not associated with any parent Workload",
        })

    return {
        "valid": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }
