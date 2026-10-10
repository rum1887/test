"""
Deterministic Synthetic World Generator for Trust Analyst.
Builds the complete security topology in FalkorDB with fixed RNG seed.
"""

import hashlib
import logging
import random
from typing import Any

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.graph.schema import init_schema
from backend.app.sim.clock import get_clock

logger = logging.getLogger("trust_analyst.world")

DEFAULT_SEED = 42


def seed_world(client: GraphClient | None = None, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """
    Seeds the deterministic baseline environment into FalkorDB.
    Guarantees reproducible node counts, properties, and relationship topology.
    """
    client = client or get_graph_client()
    rng = random.Random(seed)
    clock = get_clock()
    t0 = clock.now()

    # Reset graph and re-initialize indexes
    client.reset_graph()
    init_schema(client)

    # 1. Workloads (6)
    workloads = [
        {
            "id": "workload-checkout",
            "name": "checkout-service",
            "namespace": "production",
            "owner_team": "payments-team",
        },
        {"id": "workload-frontend", "name": "frontend-proxy", "namespace": "ingress", "owner_team": "frontend-team"},
        {"id": "workload-order", "name": "order-processor", "namespace": "production", "owner_team": "core-backend"},
        {"id": "workload-analytics", "name": "analytics-worker", "namespace": "data", "owner_team": "data-eng"},
        {"id": "workload-billing", "name": "billing-api", "namespace": "production", "owner_team": "finance-infra"},
        {"id": "workload-ci", "name": "ci-runner", "namespace": "ci-cd", "owner_team": "devops-platform"},
    ]
    for w in workloads:
        client.query("CREATE (:Workload {id: $id, name: $name, namespace: $namespace, owner_team: $owner_team})", w)

    # 2. Pods (14) linked to Workloads
    pod_assignments = [
        ("pod-checkout-1", "workload-checkout", "checkout-v2.4.1", "Running"),
        ("pod-checkout-2", "workload-checkout", "checkout-v2.4.1", "Running"),
        ("pod-checkout-3", "workload-checkout", "checkout-v2.4.1", "Running"),
        ("pod-frontend-1", "workload-frontend", "nginx-ingress:1.25", "Running"),
        ("pod-frontend-2", "workload-frontend", "nginx-ingress:1.25", "Running"),
        ("pod-order-1", "workload-order", "order-svc:3.1.0", "Running"),
        ("pod-order-2", "workload-order", "order-svc:3.1.0", "Running"),
        ("pod-analytics-1", "workload-analytics", "spark-worker:3.5", "Running"),
        ("pod-analytics-2", "workload-analytics", "spark-worker:3.5", "Running"),
        ("pod-billing-1", "workload-billing", "billing-svc:1.8.0", "Running"),
        ("pod-billing-2", "workload-billing", "billing-svc:1.8.0", "Running"),
        ("pod-ci-1", "workload-ci", "k8s-builder:1.0", "Running"),
        ("pod-ci-2", "workload-ci", "k8s-builder:1.0", "Running"),
        ("pod-ci-3", "workload-ci", "k8s-builder:1.0", "Running"),
    ]
    for pid, wid, img, status in pod_assignments:
        client.query(
            """
            MATCH (w:Workload {id: $wid})
            CREATE (p:Pod {id: $pid, name: $pid, workload_id: $wid, image: $image, status: $status})
            CREATE (w)-[:CONTAINS {valid_from: $t0, provenance: 'configured', source: 'k8s_spec'}]->(p)
            """,
            {"pid": pid, "wid": wid, "image": img, "status": status, "t0": t0},
        )

    # 3. ServiceAccounts and Pod RUNS_AS
    sa_map = {
        "workload-checkout": "sa-checkout",
        "workload-frontend": "sa-frontend",
        "workload-order": "sa-order",
        "workload-analytics": "sa-analytics",
        "workload-billing": "sa-billing",
        "workload-ci": "sa-ci",
    }
    for wid, said in sa_map.items():
        client.query(
            """
            CREATE (sa:ServiceAccount {id: $said, name: $said, namespace: 'production'})
            WITH sa
            MATCH (w:Workload {id: $wid})-[:CONTAINS]->(p:Pod)
            CREATE (p)-[:RUNS_AS {valid_from: $t0, provenance: 'configured', source: 'k8s_spec'}]->(sa)
            """,
            {"said": said, "wid": wid, "t0": t0},
        )

    # 4. SensitiveResources (5)
    sensitive_resources = [
        {"id": "sr-customer-vault", "name": "customer-vault-secrets", "sensitivity": 5},
        {"id": "sr-payment-db", "name": "payment-records-db", "sensitivity": 5},
        {"id": "sr-cloud-iam", "name": "cloud-iam-secrets", "sensitivity": 5},
        {"id": "sr-analytics-lake", "name": "analytics-datalake", "sensitivity": 3},
        {"id": "sr-billing-ledger", "name": "billing-ledger-db", "sensitivity": 4},
    ]
    for sr in sensitive_resources:
        client.query("CREATE (:SensitiveResource {id: $id, name: $name, sensitivity: $sensitivity})", sr)

    # 5. Permissions linked to ServiceAccounts and SensitiveResources
    perms = [
        {
            "id": "perm-vault-get",
            "verb": "get",
            "resource": "secrets/vault",
            "scope": "production",
            "sa": "sa-checkout",
            "target": "sr-customer-vault",
        },
        {
            "id": "perm-payment-read",
            "verb": "read",
            "resource": "payment-db",
            "scope": "production",
            "sa": "sa-checkout",
            "target": "sr-payment-db",
        },
        {
            "id": "perm-billing-read",
            "verb": "read",
            "resource": "billing-ledger",
            "scope": "production",
            "sa": "sa-billing",
            "target": "sr-billing-ledger",
        },
        {
            "id": "perm-analytics-rw",
            "verb": "read_write",
            "resource": "datalake",
            "scope": "data",
            "sa": "sa-analytics",
            "target": "sr-analytics-lake",
        },
        {
            "id": "perm-ci-broad",
            "verb": "*",
            "resource": "*",
            "scope": "cluster",
            "sa": "sa-ci",
            "target": "sr-cloud-iam",
        },
    ]
    for p in perms:
        client.query(
            """
            MATCH (sa:ServiceAccount {id: $sa}), (sr:SensitiveResource {id: $target})
            CREATE (perm:Permission {id: $id, verb: $verb, resource: $resource, scope: $scope})
            CREATE (sa)-[:HAS_PERMISSION {valid_from: $t0, provenance: 'configured', source: 'rbac'}]->(perm)
            CREATE (perm)-[:CAN_ACCESS {valid_from: $t0, provenance: 'configured', source: 'rbac'}]->(sr)
            """,
            {
                "id": p["id"],
                "verb": p["verb"],
                "resource": p["resource"],
                "scope": p["scope"],
                "sa": p["sa"],
                "target": p["target"],
                "t0": t0,
            },
        )

    # 6. Network Endpoints (12)
    endpoints = [
        {"id": "10.0.1.5", "address": "10.0.1.5", "label": "internal-dns", "known": True},
        {"id": "10.0.1.12", "address": "10.0.1.12", "label": "redis-cluster", "known": True},
        {"id": "10.0.2.8", "address": "10.0.2.8", "label": "postgres-primary", "known": True},
        {"id": "api.stripe.com", "address": "api.stripe.com", "label": "stripe-gateway", "known": True},
        {"id": "auth.internal.corp", "address": "auth.internal.corp", "label": "corp-sso", "known": True},
        {"id": "db.production.local", "address": "db.production.local", "label": "prod-db-proxy", "known": True},
        {"id": "telemetry.internal", "address": "telemetry.internal", "label": "otel-collector", "known": True},
        {"id": "vault.internal", "address": "vault.internal", "label": "hashicorp-vault", "known": True},
        {"id": "169.254.169.254", "address": "169.254.169.254", "label": "aws-metadata", "known": False},
        {"id": "198.51.100.24", "address": "198.51.100.24", "label": "external-c2-beacon", "known": False},
        {"id": "203.0.113.88", "address": "203.0.113.88", "label": "unknown-external-host", "known": False},
        {"id": "45.33.32.156", "address": "45.33.32.156", "label": "unverified-scanner", "known": False},
    ]
    for ep in endpoints:
        client.query("CREATE (:NetworkEndpoint {id: $id, address: $address, label: $label, known: $known})", ep)

    # Connect default pods to baseline known endpoints
    client.query(
        """
        MATCH (p:Pod {id: 'pod-checkout-1'}), (ne:NetworkEndpoint {id: '10.0.1.5'})
        CREATE (p)-[:CONNECTED_TO {valid_from: $t0, provenance: 'observed', source: 'tetragon'}]->(ne)
        """,
        {"t0": t0},
    )

    # 7. Principals (4)
    principals = [
        {"id": "user-alice", "name": "Alice Henderson", "role": "Senior DevOps", "status": "active"},
        {"id": "user-marcus", "name": "Marcus Vance", "role": "Lead Payment Eng", "status": "active"},
        {"id": "user-bob", "name": "Bob Martinez", "role": "Data Engineer", "status": "active"},
        {"id": "user-offboarded", "name": "Eve Malory", "role": "Former Platform Admin", "status": "offboarded"},
    ]
    for pr in principals:
        client.query("CREATE (:Principal {id: $id, name: $name, role: $role, status: $status})", pr)

    # 8. Agents (2)
    agents = [
        {"id": "agent-ops", "name": "OpsAutomator", "capabilities": ["k8s", "logs", "restart", "deploy"]},
        {"id": "agent-analyst", "name": "SecurityAnalystBot", "capabilities": ["triage", "investigate", "audit"]},
    ]
    for ag in agents:
        client.query("CREATE (:Agent {id: $id, name: $name, capabilities: $capabilities})", ag)

    # 9. MCP Server (1) & Tools (8)
    client.query("CREATE (:MCPServer {id: 'mcp-edge-gateway', name: 'Model Context Protocol Gateway'})")

    tools = [
        {
            "id": "tool-lookup-balance",
            "name": "lookup_customer_balance",
            "risk_level": "low",
            "is_destructive": False,
            "target": "sr-customer-vault",
        },
        {
            "id": "tool-tx-history",
            "name": "get_transaction_history",
            "risk_level": "low",
            "is_destructive": False,
            "target": "sr-payment-db",
        },
        {
            "id": "tool-audit-read",
            "name": "audit_read",
            "risk_level": "low",
            "is_destructive": False,
            "target": "sr-billing-ledger",
        },
        {
            "id": "tool-report-gen",
            "name": "report_generate",
            "risk_level": "low",
            "is_destructive": False,
            "target": None,
        },
        {"id": "tool-read-logs", "name": "read_logs", "risk_level": "low", "is_destructive": False, "target": None},
        {
            "id": "tool-restart-pod",
            "name": "restart_pod",
            "risk_level": "medium",
            "is_destructive": False,
            "target": None,
        },
        {
            "id": "tool-drop-table",
            "name": "db_drop_table",
            "risk_level": "critical",
            "is_destructive": True,
            "target": "sr-payment-db",
        },
        {
            "id": "tool-delete-bucket",
            "name": "delete_bucket",
            "risk_level": "critical",
            "is_destructive": True,
            "target": "sr-analytics-lake",
        },
    ]
    for tl in tools:
        target_clause = ""
        if tl["target"]:
            target_clause = """
            WITH t
            MATCH (sr:SensitiveResource {id: $target})
            CREATE (t)-[:CAN_ACCESS {valid_from: $t0, provenance: 'configured', source: 'mcp_catalog'}]->(sr)
            """
        client.query(
            f"""
            MATCH (m:MCPServer {{id: 'mcp-edge-gateway'}})
            CREATE (t:Tool {{id: $id, name: $name, risk_level: $risk_level, is_destructive: $is_destructive}})
            CREATE (m)-[:CONTAINS {{valid_from: $t0, provenance: 'configured', source: 'mcp_spec'}}]->(t)
            {target_clause}
            """,
            {
                "id": tl["id"],
                "name": tl["name"],
                "risk_level": tl["risk_level"],
                "is_destructive": tl["is_destructive"],
                "target": tl["target"],
                "t0": t0,
            },
        )

    # 10. AgentSessions & Delegations (4)
    sessions = [
        {
            "session_id": "sess-alice-ops",
            "principal_id": "user-alice",
            "agent_id": "agent-ops",
            "del_id": "del-alice",
            "scopes": ["read_logs", "lookup_metrics", "restart_pod"],
            "intent": "Routine morning cluster health check",
            "expires_at": t0 + 86400,
        },
        {
            "session_id": "sess-marcus-fin",
            "principal_id": "user-marcus",
            "agent_id": "agent-ops",
            "del_id": "del-marcus",
            "scopes": ["lookup_customer_balance", "get_transaction_history", "report_generate"],
            "intent": "Generate daily financial compliance audit report",
            "expires_at": t0 + 86400,
        },
        {
            "session_id": "sess-bob-data",
            "principal_id": "user-bob",
            "agent_id": "agent-ops",
            "del_id": "del-bob",
            "scopes": ["*"],
            "intent": "Data pipeline maintenance and migration",
            "expires_at": t0 + 86400,
        },
        {
            "session_id": "sess-zombie",
            "principal_id": "user-offboarded",
            "agent_id": "agent-ops",
            "del_id": "del-zombie",
            "scopes": ["*"],
            "intent": "Legacy unattended cron script",
            "expires_at": t0 + 86400 * 30,
        },
    ]
    for s in sessions:
        client.query(
            """
            MATCH (p:Principal {id: $pid}), (a:Agent {id: $aid})
            CREATE (sess:AgentSession {id: $sid, status: 'active', started_at: $t0, expires_at: $exp})
            CREATE (del:Delegation {id: $did, scopes: $scopes, expires_at: $exp, intent_text: $intent})
            CREATE (p)-[:OWNS_SESSION {valid_from: $t0, provenance: 'configured'}]->(sess)
            CREATE (sess)-[:USES_AGENT {valid_from: $t0, provenance: 'configured'}]->(a)
            CREATE (p)-[:GRANTED {valid_from: $t0, provenance: 'configured'}]->(del)
            CREATE (del)-[:TO_SESSION {valid_from: $t0, provenance: 'configured'}]->(sess)
            """,
            {
                "sid": s["session_id"],
                "pid": s["principal_id"],
                "aid": s["agent_id"],
                "did": s["del_id"],
                "scopes": s["scopes"],
                "intent": s["intent"],
                "exp": s["expires_at"],
                "t0": t0,
            },
        )

    # Link permitted tools to sessions
    client.query(
        """
        MATCH (s:AgentSession {id: 'sess-alice-ops'}), (t:Tool)
        WHERE t.name IN ['read_logs', 'restart_pod']
        CREATE (s)-[:CAN_INVOKE {valid_from: $t0, provenance: 'configured'}]->(t)
        """,
        {"t0": t0},
    )
    client.query(
        """
        MATCH (s:AgentSession {id: 'sess-marcus-fin'}), (t:Tool)
        WHERE t.name IN ['lookup_customer_balance', 'get_transaction_history', 'report_generate']
        CREATE (s)-[:CAN_INVOKE {valid_from: $t0, provenance: 'configured'}]->(t)
        """,
        {"t0": t0},
    )
    client.query(
        """
        MATCH (s:AgentSession), (t:Tool)
        WHERE s.id IN ['sess-bob-data', 'sess-zombie']
        CREATE (s)-[:CAN_INVOKE {valid_from: $t0, provenance: 'configured'}]->(t)
        """,
        {"t0": t0},
    )

    # 11. Documents (~40 synthetic nodes: tickets, PRs, runbooks, audit, chat)
    doc_kinds = ["ticket", "pr", "runbook", "audit", "chat"]
    for i in range(1, 41):
        kind = doc_kinds[i % len(doc_kinds)]
        trust = "trusted" if i % 4 != 0 else "untrusted"  # 1 in 4 are untrusted
        doc_id = f"doc-{kind}-{i}"
        title = f"{kind.upper()} #{1000 + i}: Internal infrastructure note {i}"
        body = f"Synthetic {kind} record covering operational updates for cluster cluster-us-east-1."
        client.query(
            "CREATE (:Document {id: $id, kind: $kind, title: $title, body: $body, trust: $trust})",
            {"id": doc_id, "kind": kind, "title": title, "body": body, "trust": trust},
        )

    # 12. Low-risk filler nodes & edges (~200) for realistic graph density
    for i in range(1, 201):
        fid = f"filler-config-{i}"
        fname = f"cluster-config-cm-{i}"
        target_pod = pod_assignments[rng.randint(0, len(pod_assignments) - 1)][0]
        client.query(
            """
            MATCH (p:Pod {id: $pod_id})
            CREATE (c:Workload {id: $fid, name: $fname, namespace: 'kube-system', owner_team: 'platform'})
            CREATE (p)-[:CONTAINS {valid_from: $t0, provenance: 'configured'}]->(c)
            """,
            {"fid": fid, "fname": fname, "pod_id": target_pod, "t0": t0},
        )

    # Fetch stats
    stats_nodes = client.query("MATCH (n) RETURN count(n) AS cnt")[0][0]
    stats_edges = client.query("MATCH ()-[r]->() RETURN count(r) AS cnt")[0][0]
    world_hash = compute_world_hash(client)

    logger.info(f"Deterministic world seeded: {stats_nodes} nodes, {stats_edges} edges, hash: {world_hash}")
    return {
        "nodes": stats_nodes,
        "edges": stats_edges,
        "hash": world_hash,
        "t0": t0,
    }


def compute_world_hash(client: GraphClient) -> str:
    """
    Computes deterministic SHA256 signature of the graph state.
    Hashes sorted node IDs, labels, and sorted edge relationships.
    """
    node_rows = client.query("MATCH (n) RETURN n.id AS id, labels(n)[0] AS lbl ORDER BY id")
    edge_rows = client.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS src, type(r) AS rel, b.id AS tgt ORDER BY src, rel, tgt"
    )

    hasher = hashlib.sha256()
    for row in node_rows:
        hasher.update(f"{row[0]}:{row[1]};".encode("utf-8"))
    for row in edge_rows:
        hasher.update(f"{row[0]}->{row[1]}->{row[2]};".encode("utf-8"))

    return hasher.hexdigest()


if __name__ == "__main__":
    c = get_graph_client()
    res = seed_world(c)
    print(f"World Seed Completed: {res}")
