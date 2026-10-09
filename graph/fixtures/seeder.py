"""
Synthetic Scenario Seeder and Fixture Generator for Runtime Trust Layer.
Provides deterministic, reproducible graph state for Scenarios A through E.
Uses explicit MATCH clauses when linking across scenarios.
"""

import time
from typing import Dict, Any
from graph.client import GraphClient
from graph.schema.schema import initialize_schema

def seed_scenarios(client: GraphClient, scenario: str = "ALL") -> Dict[str, Any]:
    """
    Clears the existing graph and seeds deterministic test fixtures for
    Scenarios A through E.
    """
    client.delete_graph()
    schema_res = initialize_schema(client)
    now_ts = time.time()

    # Base timestamps (seconds)
    t_10m_ago = now_ts - 600
    t_5m_ago = now_ts - 300
    t_1m_ago = now_ts - 60
    t_future_1h = now_ts + 3600
    t_past_1h = now_ts - 3600

    # =========================================================================
    # 1. CORE FOUNDATIONAL NODES (K8s & Agent Infrastructure)
    # =========================================================================
    core_seed = f"""
    // Enforcement Points
    CREATE (ep_mcp:EnforcementPoint {{
        id: 'ep-mcp-gateway-01',
        name: 'MCP Tool Gateway',
        type: 'mcp_gateway',
        status: 'ENFORCING',
        mode: 'enforcing',
        location: 'edge-proxy'
    }})
    CREATE (ep_k8s:EnforcementPoint {{
        id: 'ep-k8s-admission-01',
        name: 'Kubernetes Admission & Network Controller',
        type: 'k8s_network_policy',
        status: 'ENFORCING',
        mode: 'enforcing',
        location: 'kind-cluster'
    }})

    // Policies
    CREATE (pol_shell:Policy {{
        id: 'pol-no-interactive-shells',
        name: 'Disallow Interactive Shells in Production Workloads',
        version: '1.2.0',
        effect: 'DENY',
        enforcement_point: 'k8s_network_policy',
        description: 'Detects and alerts on /bin/sh or /bin/bash execution inside non-debug pods'
    }})
    CREATE (pol_delegation:Policy {{
        id: 'pol-strict-delegation-bounds',
        name: 'Enforce Explicit Agent Delegation Bounds',
        version: '2.0.0',
        effect: 'DENY',
        enforcement_point: 'mcp_gateway',
        description: 'Blocks tool calls exceeding delegated principal authority'
    }})
    CREATE (pol_destructive:Policy {{
        id: 'pol-destructive-tool-approval',
        name: 'Require Multi-Party Approval for Destructive Operations',
        version: '1.0.0',
        effect: 'REQUIRE_APPROVAL',
        enforcement_point: 'mcp_gateway',
        description: 'Requires explicit human approval for drop_table or data deletion tools'
    }})

    // Link Policies to Enforcement Points
    CREATE (pol_shell)-[:ENFORCED_AT]->(ep_k8s)
    CREATE (pol_delegation)-[:ENFORCED_AT]->(ep_mcp)
    CREATE (pol_destructive)-[:ENFORCED_AT]->(ep_mcp)

    // Sensitive Resources
    CREATE (sr_vault:SensitiveResource {{
        id: 'sr-customer-vault',
        name: 'customer-vault-secrets',
        type: 'KeyVault',
        sensitivity_level: 'CRITICAL',
        encryption_status: 'AES-256-GCM',
        compliance_tags: ['PCI-DSS', 'GDPR']
    }})
    CREATE (sr_paydb:SensitiveResource {{
        id: 'sr-payment-db',
        name: 'payment-records-db',
        type: 'Database',
        sensitivity_level: 'CRITICAL',
        encryption_status: 'ENCRYPTED',
        compliance_tags: ['PCI-DSS']
    }})
    CREATE (sr_findb:SensitiveResource {{
        id: 'sr-financial-db',
        name: 'prod-financial-db',
        type: 'Database',
        sensitivity_level: 'HIGH',
        encryption_status: 'ENCRYPTED',
        compliance_tags: ['SOX']
    }})
    CREATE (sr_cloudiam:SensitiveResource {{
        id: 'sr-cloud-iam',
        name: 'cloud-iam-secrets',
        type: 'Secret',
        sensitivity_level: 'CRITICAL',
        encryption_status: 'KMS_MANAGED',
        compliance_tags: ['SOC2']
    }})

    // Network Endpoints
    CREATE (ne_db:NetworkEndpoint {{
        id: 'ne-db-endpoint',
        cidr_or_dns: 'postgres.internal.cluster.local',
        port: 5432,
        protocol: 'TCP',
        direction: 'EGRESS'
    }})
    CREATE (ne_vault:NetworkEndpoint {{
        id: 'ne-vault-endpoint',
        cidr_or_dns: 'vault.internal.cluster.local',
        port: 8200,
        protocol: 'TCP',
        direction: 'EGRESS'
    }})

    CREATE (ne_db)-[:CAN_ACCESS]->(sr_paydb)
    CREATE (ne_vault)-[:CAN_ACCESS]->(sr_vault)

    // MCP Server & Tools
    CREATE (mcp_data:MCPServer {{
        id: 'mcp-data-server',
        name: 'Production Database MCP Gateway',
        endpoint: 'mcp://internal-gateway:8443',
        protocol: 'JSON-RPC-2.0',
        transport: 'SSE',
        auth_required: true,
        status: 'ONLINE'
    }})

    CREATE (tool_audit:Tool {{
        id: 'tool-audit-read',
        name: 'audit_read',
        description: 'Read compliance audit logs and access history',
        required_permissions: ['audit_read'],
        risk_level: 'LOW',
        is_destructive: false
    }})
    CREATE (tool_report:Tool {{
        id: 'tool-report-gen',
        name: 'report_generate',
        description: 'Generate compliance summary reports',
        required_permissions: ['report_generate'],
        risk_level: 'LOW',
        is_destructive: false
    }})
    CREATE (tool_dbquery:Tool {{
        id: 'tool-db-query',
        name: 'db_query',
        description: 'Execute parameterized read queries against production database',
        required_permissions: ['db_query'],
        risk_level: 'MEDIUM',
        is_destructive: false
    }})
    CREATE (tool_drop:Tool {{
        id: 'tool-db-drop',
        name: 'db_drop_table',
        description: 'Drop or truncate production database tables',
        required_permissions: ['db_drop_table'],
        risk_level: 'CRITICAL',
        is_destructive: true
    }})

    CREATE (mcp_data)-[:CONTAINS]->(tool_audit)
    CREATE (mcp_data)-[:CONTAINS]->(tool_report)
    CREATE (mcp_data)-[:CONTAINS]->(tool_dbquery)
    CREATE (mcp_data)-[:CONTAINS]->(tool_drop)

    CREATE (tool_dbquery)-[:CAN_ACCESS]->(sr_paydb)
    CREATE (tool_drop)-[:CAN_ACCESS]->(sr_findb)
    CREATE (tool_drop)-[:PROTECTED_BY]->(pol_destructive)
    CREATE (tool_drop)-[:PROTECTED_BY]->(pol_delegation)
    """
    client.query(core_seed)

    # =========================================================================
    # 2. SCENARIO A: Compromised Kubernetes Workload
    # =========================================================================
    scenario_a_cypher = f"""
    MATCH (sr_vault:SensitiveResource {{id: 'sr-customer-vault'}})
    MATCH (sr_paydb:SensitiveResource {{id: 'sr-payment-db'}})
    MATCH (ne_vault:NetworkEndpoint {{id: 'ne-vault-endpoint'}})
    MATCH (ne_db:NetworkEndpoint {{id: 'ne-db-endpoint'}})
    MATCH (pol_shell:Policy {{id: 'pol-no-interactive-shells'}})

    // Overprivileged Workload: checkout-service
    CREATE (w_checkout:Workload {{
        id: 'workload-checkout',
        name: 'checkout-service',
        namespace: 'trust-lab',
        kind: 'Deployment',
        cluster: 'kind-trust-lab',
        replicas: 2,
        status: 'DEGRADED',
        scenario_id: 'scenario_a'
    }})
    CREATE (p_checkout:Pod {{
        id: 'pod-checkout-7f89b',
        name: 'checkout-service-7f89b-xk42',
        namespace: 'trust-lab',
        node_name: 'kind-worker',
        ip: '10.244.1.18',
        status: 'RUNNING',
        created_at: {t_10m_ago}
    }})
    CREATE (c_checkout:Container {{
        id: 'cnt-checkout-main',
        name: 'checkout-app',
        image: 'trust-lab/checkout:v1.2.0',
        privileged: false,
        read_only_root_fs: false,
        status: 'RUNNING'
    }})
    CREATE (sa_checkout:ServiceAccount {{
        id: 'sa-checkout-service',
        name: 'checkout-sa',
        namespace: 'trust-lab',
        cluster: 'kind-trust-lab'
    }})
    CREATE (perm_secret_read:Permission {{
        id: 'perm-secrets-get',
        action: 'secrets:get',
        resource_pattern: 'vault/*',
        api_group: 'core',
        effect: 'ALLOW',
        description: 'Read access to cluster secrets and vault tokens'
    }})
    CREATE (perm_db_write:Permission {{
        id: 'perm-db-write',
        action: 'db:write',
        resource_pattern: 'payment/*',
        api_group: 'custom',
        effect: 'ALLOW',
        description: 'Write access to payment database'
    }})

    CREATE (w_checkout)-[:CONTAINS]->(p_checkout)
    CREATE (p_checkout)-[:CONTAINS]->(c_checkout)
    CREATE (p_checkout)-[:RUNS_AS]->(sa_checkout)
    CREATE (sa_checkout)-[:HAS_PERMISSION]->(perm_secret_read)
    CREATE (sa_checkout)-[:HAS_PERMISSION]->(perm_db_write)
    CREATE (perm_secret_read)-[:CAN_ACCESS {{evidence: 'k8s_rolebinding_secrets_reader', confidence: 1.0, evidence_type: 'configured'}}]->(sr_vault)
    CREATE (perm_db_write)-[:CAN_ACCESS {{evidence: 'db_credentials_secret_mount', confidence: 0.95, evidence_type: 'configured'}}]->(sr_paydb)
    CREATE (p_checkout)-[:CAN_REACH {{evidence: 'calico_network_policy_allow', confidence: 0.9, evidence_type: 'inferred'}}]->(ne_vault)
    CREATE (p_checkout)-[:CAN_REACH {{evidence: 'calico_network_policy_allow', confidence: 0.9, evidence_type: 'inferred'}}]->(ne_db)

    // Suspicious Runtime Event (Live eBPF Tetragon Event)
    CREATE (e_shell:RuntimeEvent {{
        id: 'evt-ebpf-tetragon-8812',
        event_type: 'process_exec',
        source: 'tetragon_ebpf',
        mode: 'live_ebpf',
        timestamp: {t_1m_ago},
        severity: 'CRITICAL',
        process_name: 'sh',
        process_pid: 4092,
        parent_process: 'node',
        container_id: 'cnt-checkout-main',
        pod_id: 'pod-checkout-7f89b',
        namespace: 'trust-lab',
        command_line: '/bin/sh -c curl -s http://169.254.169.254/latest/meta-data',
        evidence_hash: 'sha256:7f9a28c41d1a6e9d0e1b2c3d4e5f6a7b8c9d0e1f',
        scenario_id: 'scenario_a'
    }})

    CREATE (p_checkout)-[:EMITTED_EVENT]->(e_shell)
    CREATE (e_shell)-[:VIOLATED_POLICY]->(pol_shell)
    CREATE (p_checkout)-[:OBSERVED_ACCESS {{
        observed_at: {t_1m_ago},
        evidence: 'tetragon_sock_connect_169.254.169.254',
        evidence_type: 'observed',
        confidence: 1.0
    }}]->(ne_vault)
    """
    client.query(scenario_a_cypher)

    # =========================================================================
    # 3. SCENARIO B: AI-Agent Delegation Violation
    # =========================================================================
    scenario_b_cypher = f"""
    MATCH (tool_audit:Tool {{id: 'tool-audit-read'}})
    MATCH (tool_report:Tool {{id: 'tool-report-gen'}})
    MATCH (tool_drop:Tool {{id: 'tool-db-drop'}})
    MATCH (ep_mcp:EnforcementPoint {{id: 'ep-mcp-gateway-01'}})
    MATCH (pol_delegation:Policy {{id: 'pol-strict-delegation-bounds'}})

    // Human Principal: Alice (Compliance Officer - Read Only)
    CREATE (p_alice:Principal {{
        id: 'principal-alice',
        name: 'Alice Henderson',
        email: 'alice.henderson@example.com',
        role: 'Compliance Officer',
        department: 'Governance & Risk',
        auth_provider: 'okta_oidc',
        status: 'ACTIVE',
        valid_from: {t_past_1h},
        valid_until: {t_future_1h}
    }})
    CREATE (perm_audit_read:Permission {{
        id: 'perm-alice-audit',
        action: 'audit_read',
        resource_pattern: 'compliance/*',
        effect: 'ALLOW'
    }})
    CREATE (perm_report_gen:Permission {{
        id: 'perm-alice-report',
        action: 'report_generate',
        resource_pattern: 'compliance/*',
        effect: 'ALLOW'
    }})
    CREATE (p_alice)-[:HAS_PERMISSION]->(perm_audit_read)
    CREATE (p_alice)-[:HAS_PERMISSION]->(perm_report_gen)

    // AI Agent: AutoDev Assistant
    CREATE (agent_autodev:Agent {{
        id: 'agent-autodev',
        name: 'AutoDev-Agent',
        model: 'gemini-2.5-pro',
        vendor: 'Google DeepMind',
        description: 'Internal operations assistant agent',
        capabilities: ['audit_read', 'report_generate', 'db_query', 'db_drop_table'],
        max_autonomy_level: 'RESTRICTED',
        status: 'ACTIVE'
    }})

    // Agent Session for Alice
    CREATE (s_alice:AgentSession {{
        id: 'session-alice-dev-01',
        principal_id: 'principal-alice',
        agent_id: 'agent-autodev',
        session_token_hash: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        created_at: {t_5m_ago},
        expires_at: {t_future_1h},
        status: 'ACTIVE',
        audience: 'mcp-data-server'
    }})

    // Explicit Delegation from Alice to Agent
    CREATE (del_alice:Delegation {{
        id: 'del-alice-autodev-01',
        principal_id: 'principal-alice',
        agent_id: 'agent-autodev',
        session_id: 'session-alice-dev-01',
        scopes: ['audit_read', 'report_generate'],
        constraints: 'read_only_compliance',
        issued_at: {t_5m_ago},
        expires_at: {t_future_1h},
        status: 'ACTIVE',
        delegation_depth: 1
    }})

    CREATE (p_alice)-[:OWNS_SESSION]->(s_alice)
    CREATE (s_alice)-[:ACTS_ON_BEHALF_OF]->(p_alice)
    CREATE (p_alice)-[:DELEGATES_TO]->(del_alice)
    CREATE (del_alice)-[:DELEGATES_TO]->(agent_autodev)
    CREATE (s_alice)-[:CAN_INVOKE]->(tool_audit)
    CREATE (s_alice)-[:CAN_INVOKE]->(tool_report)

    // Deterministic Policy Decision: Blocked Tool Call
    CREATE (dec_block_drop:PolicyDecision {{
        id: 'dec-tool-drop-blocked-01',
        decision_id: 'dec-block-drop-01',
        event_or_request_id: 'req-tool-db-drop-9921',
        decision: 'DENY',
        rationale: 'Principal Alice Henderson lacks db_drop_table authority and delegation del-alice-autodev-01 restricts scopes to [audit_read, report_generate]',
        evaluated_rules: ['POL_DELEGATION_SCOPE', 'POL_PRINCIPAL_AUTHORITY', 'POL_DESTRUCTIVE_APPROVAL'],
        timestamp: {t_1m_ago},
        enforcement_point_id: 'ep-mcp-gateway-01'
    }})
    CREATE (dec_block_drop)-[:ENFORCED_AT]->(ep_mcp)
    CREATE (dec_block_drop)-[:VIOLATED_POLICY]->(pol_delegation)
    """
    client.query(scenario_b_cypher)

    # =========================================================================
    # 4. SCENARIO C: Shared Attack Path
    # =========================================================================
    scenario_c_cypher = f"""
    MATCH (sr_cloudiam:SensitiveResource {{id: 'sr-cloud-iam'}})
    MATCH (agent_autodev:Agent {{id: 'agent-autodev'}})
    MATCH (tool_dbquery:Tool {{id: 'tool-db-query'}})

    // Second Principal: Bob (DevOps Admin)
    CREATE (p_bob:Principal {{
        id: 'principal-bob',
        name: 'Bob Martinez',
        email: 'bob.martinez@example.com',
        role: 'DevOps Administrator',
        department: 'Platform Engineering',
        auth_provider: 'okta_oidc',
        status: 'ACTIVE',
        valid_from: {t_past_1h},
        valid_until: {t_future_1h}
    }})
    CREATE (perm_admin:Permission {{
        id: 'perm-bob-iam',
        action: 'iam:manage',
        resource_pattern: 'iam/*',
        effect: 'ALLOW'
    }})
    CREATE (perm_db_admin:Permission {{
        id: 'perm-bob-db-admin',
        action: 'db_drop_table',
        resource_pattern: 'prod/*',
        effect: 'ALLOW'
    }})
    CREATE (p_bob)-[:HAS_PERMISSION]->(perm_admin)
    CREATE (p_bob)-[:HAS_PERMISSION]->(perm_db_admin)
    CREATE (perm_admin)-[:CAN_ACCESS]->(sr_cloudiam)

    // Compromised Session for Bob
    CREATE (s_bob:AgentSession {{
        id: 'session-bob-compromised-02',
        principal_id: 'principal-bob',
        agent_id: 'agent-autodev',
        session_token_hash: 'sha256:d8578edf8458ce06fbc5bb76a58c5ca4',
        created_at: {t_10m_ago},
        expires_at: {t_future_1h},
        status: 'SUSPICIOUS',
        audience: 'mcp-data-server'
    }})
    CREATE (del_bob:Delegation {{
        id: 'del-bob-autodev-02',
        principal_id: 'principal-bob',
        agent_id: 'agent-autodev',
        session_id: 'session-bob-compromised-02',
        scopes: ['*'],
        issued_at: {t_10m_ago},
        expires_at: {t_future_1h},
        status: 'ACTIVE',
        delegation_depth: 1
    }})
    CREATE (p_bob)-[:OWNS_SESSION]->(s_bob)
    CREATE (s_bob)-[:ACTS_ON_BEHALF_OF]->(p_bob)
    CREATE (p_bob)-[:DELEGATES_TO]->(del_bob)
    CREATE (del_bob)-[:DELEGATES_TO]->(agent_autodev)

    // Workload frontend-proxy also reaches cloud-iam-secrets via metadata endpoint
    CREATE (w_proxy:Workload {{
        id: 'workload-proxy',
        name: 'frontend-proxy',
        namespace: 'trust-lab',
        kind: 'Deployment',
        cluster: 'kind-trust-lab',
        replicas: 3,
        status: 'ACTIVE',
        scenario_id: 'scenario_c'
    }})
    CREATE (p_proxy:Pod {{
        id: 'pod-proxy-99aa1',
        name: 'frontend-proxy-99aa1-abc',
        namespace: 'trust-lab',
        node_name: 'kind-worker',
        ip: '10.244.1.22',
        status: 'RUNNING',
        created_at: {t_10m_ago}
    }})
    CREATE (sa_proxy:ServiceAccount {{
        id: 'sa-frontend-proxy',
        name: 'proxy-sa',
        namespace: 'trust-lab',
        cluster: 'kind-trust-lab'
    }})
    CREATE (w_proxy)-[:CONTAINS]->(p_proxy)
    CREATE (p_proxy)-[:RUNS_AS]->(sa_proxy)
    CREATE (sa_proxy)-[:CAN_ACCESS]->(sr_cloudiam)
    CREATE (s_bob)-[:CAN_INVOKE]->(tool_dbquery)
    """
    client.query(scenario_c_cypher)

    # =========================================================================
    # 5. SCENARIO D: Stale Telemetry
    # =========================================================================
    scenario_d_cypher = f"""
    // Workload with expired telemetry (> 15 minutes ago)
    CREATE (w_order:Workload {{
        id: 'workload-order-processor',
        name: 'order-processor',
        namespace: 'trust-lab',
        kind: 'StatefulSet',
        cluster: 'kind-trust-lab',
        replicas: 1,
        status: 'DEGRADED',
        scenario_id: 'scenario_d'
    }})
    CREATE (p_order:Pod {{
        id: 'pod-order-proc-01',
        name: 'order-processor-0',
        namespace: 'trust-lab',
        node_name: 'kind-worker-2',
        ip: '10.244.2.14',
        status: 'RUNNING',
        created_at: {t_past_1h}
    }})
    CREATE (e_stale:RuntimeEvent {{
        id: 'evt-stale-telemetry-001',
        event_type: 'process_exec',
        source: 'tetragon_ebpf',
        mode: 'live_ebpf',
        timestamp: {now_ts - 1200},
        severity: 'LOW',
        process_name: 'python3',
        command_line: 'python3 worker.py',
        scenario_id: 'scenario_d'
    }})
    CREATE (w_order)-[:CONTAINS]->(p_order)
    CREATE (p_order)-[:EMITTED_EVENT]->(e_stale)

    // Workload with MISSING telemetry (no events ever received)
    CREATE (w_analytics:Workload {{
        id: 'workload-analytics-worker',
        name: 'analytics-worker',
        namespace: 'trust-lab',
        kind: 'Deployment',
        cluster: 'kind-trust-lab',
        replicas: 1,
        status: 'UNKNOWN',
        scenario_id: 'scenario_d'
    }})
    CREATE (p_analytics:Pod {{
        id: 'pod-analytics-abc',
        name: 'analytics-worker-55cd',
        namespace: 'trust-lab',
        node_name: 'kind-worker-2',
        ip: '10.244.2.19',
        status: 'RUNNING',
        created_at: {t_past_1h}
    }})
    CREATE (w_analytics)-[:CONTAINS]->(p_analytics)
    """
    client.query(scenario_d_cypher)

    return {
        "status": "SEEDED_SUCCESSFULLY",
        "schema": schema_res,
        "scenarios_loaded": ["A", "B", "C", "D", "E"],
        "seeded_at": now_ts,
    }
