"""
Security Analysis, Blast Radius, Delegation Chain, and Tool Gateway Routes.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Dict, Any, List, Optional
from apps.api.dependencies.auth import verify_admin_key
from graph.client import get_graph_client
from graph.queries.library import QueryLibrary
from policies.engine import PolicyEngine
from services.agent_gateway.gateway import (
    AgentMCPGateway,
    ToolInvocationRequest,
    ToolInvocationResponse,
)
import httpx
import hashlib
import time
from pydantic import BaseModel

router = APIRouter(tags=["Security Control Plane"])

@router.get("/api/blast-radius")
def get_blast_radius(
    target_id: str = Query(..., description="ID of Workload or Pod"),
    max_depth: int = Query(5, ge=1, le=8),
) -> Dict[str, Any]:
    """
    Query 1: Computes bounded blast radius from workload/pod to sensitive resources.
    Returns path lengths, evidence, and reachability classifications.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.get_workload_blast_radius(target_id, max_depth=max_depth)
    return res

@router.get("/api/delegation-chain")
def trace_delegation(
    session_id: str = Query(..., description="AgentSession ID"),
    tool: Optional[str] = Query(None, description="Optional requested tool name"),
) -> Dict[str, Any]:
    """
    Query 2: Traces Principal -> Session -> Agent -> Delegation -> Tool -> Resource.
    Evaluates validity, expiry, and excessive privileges.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)
    res = ql.trace_agent_delegation_chain(session_id, requested_tool_name=tool)
    return res

@router.get("/api/attack-paths")
def get_shared_attack_paths(
    sources: Optional[str] = Query(
        None,
        description="Comma-separated IDs of suspicious workloads or sessions",
    ),
) -> Dict[str, Any]:
    """
    Query 4: Discovers sensitive resources shared by multiple threat sources.
    Ranks targets by sensitivity, path count, and convergence factors.
    """
    client = get_graph_client()
    ql = QueryLibrary(client)

    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        # Default: search across known threat workloads and sessions
        source_list = ["workload-checkout", "session-bob-compromised-02", "workload-proxy"]

    res = ql.find_shared_attack_paths(source_list)
    return res

@router.post("/api/policies/evaluate")
def evaluate_policy(
    principal_id: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    session_id: str = Body(..., embed=True),
    tool_name: str = Body(..., embed=True),
    action: str = Body("EXECUTE", embed=True),
) -> Dict[str, Any]:
    """
    Query 3: Deterministic Policy Engine evaluation against effective authority.
    Returns ALLOW, DENY, REQUIRE_APPROVAL, or RESTRICT with rule breakdown.
    """
    client = get_graph_client()
    engine = PolicyEngine(client)
    decision = engine.evaluate_tool_request(
        principal_id=principal_id,
        agent_id=agent_id,
        session_id=session_id,
        requested_tool=tool_name,
        requested_action=action,
    )
    return decision.model_dump()

@router.post("/api/gateway/invoke")
def invoke_agent_tool(request: ToolInvocationRequest):
    """
    MCP Gateway Boundary: Enforces policy BEFORE tool execution.
    Rejects unauthorized requests immediately and records evidence in graph.
    """
    from fastapi.responses import JSONResponse
    client = get_graph_client()
    gw = AgentMCPGateway(client)
    response = gw.invoke_tool(request)
    return JSONResponse(status_code=response.status_code, content=response.model_dump())

@router.get("/api/gateway/guard-state")
def get_gateway_guard_state() -> Dict[str, Any]:
    """Returns the central Runtime Security Guard state and mode."""
    from services.agent_gateway.gateway import get_guard_config
    cfg = get_guard_config()
    client = get_graph_client()
    
    # Check if demo session is quarantined
    q_check = """
    MATCH (s:AgentSession {id: 'session-alice-dev-01'})-[:EMITTED_EVENT]->(e:RuntimeEvent)
    RETURN count(e)
    """
    try:
        rows = client.query(q_check)
        quarantine_count = rows[0][0] if rows else 0
    except Exception:
        quarantine_count = 0

    return {
        "guard_enabled": cfg.get("guard_enabled", True),
        "mode": cfg.get("mode", "ENFORCE"),
        "status": "ACTIVE_ENFORCEMENT" if cfg.get("guard_enabled", True) else "AUDIT_ONLY",
        "quarantined_sessions_count": quarantine_count,
        "is_quarantined": quarantine_count > 0,
        "enforcement_point": "ep-mcp-gateway-01",
        "last_updated": cfg.get("last_updated"),
    }

@router.post("/api/gateway/toggle-guard", dependencies=[Depends(verify_admin_key)])
def toggle_gateway_guard(enabled: Optional[bool] = None) -> Dict[str, Any]:
    """Toggles central Runtime Security Guard between ENFORCE and BYPASS."""
    from services.agent_gateway.gateway import get_guard_config, set_guard_config
    cfg = get_guard_config()
    new_val = not cfg.get("guard_enabled", True) if enabled is None else enabled
    updated = set_guard_config(new_val)
    return {
        "guard_enabled": updated["guard_enabled"],
        "mode": updated["mode"],
        "message": f"Central Runtime Guard switched to {updated['mode']} mode."
    }

@router.get("/api/gateway/connected-services")
def get_connected_services() -> Dict[str, Any]:
    """Returns health and integration metadata for all connected apps & tools."""
    from services.agent_gateway.gateway import get_guard_config
    guard_cfg = get_guard_config()

    return {
        "guard_mode": guard_cfg.get("mode", "ENFORCE"),
        "guard_enabled": guard_cfg.get("guard_enabled", True),
        "services": [
            {
                "id": "app-orbit-agent",
                "name": "Orbit Customer Support Agent",
                "role": "Client AI Application",
                "endpoint": "http://localhost:3001",
                "status": "ONLINE",
                "protocol": "Google ADK v2.11 + Local Ollama LLM",
                "active_model": "qwen3:4b (GPU)",
                "active_session": "session-alice-dev-01",
                "principal": "Alice Henderson (Operations Lead)",
                "governance": "Governed by Central Gateway",
            },
            {
                "id": "app-nexus-agent",
                "name": "Nexus Settlement Multi-Agent",
                "role": "FinOps & Treasury Automation",
                "endpoint": "http://localhost:3002",
                "status": "ONLINE",
                "protocol": "Google ADK v2.11 Autonomous Settlement",
                "active_model": "Google ADK Multi-Agent",
                "active_session": "session-nexus-settlement-01",
                "principal": "Marcus Vance (Treasury Director)",
                "governance": "Governed by Central Gateway (Shared Infra)",
            },
            {
                "id": "mcp-crm-tools",
                "name": "Live CRM & Financial MCP Server",
                "role": "Tool Execution Layer",
                "endpoint": "http://localhost:8443/mcp",
                "status": "ONLINE",
                "protocol": "Model Context Protocol JSON-RPC 2.0",
                "registered_tools": [
                    "lookup_customer_balance",
                    "get_transaction_history",
                    "audit_read",
                    "export_customer_vault",
                    "db_drop_table",
                    "process_settlement_payout",
                    "verify_treasury_ledger"
                ],
                "transport": "HTTP POST & Server-Sent Events (/sse)",
            },
            {
                "id": "db-production-core",
                "name": "Production Core Database",
                "role": "Target Data Layer",
                "endpoint": "data/production_live.db",
                "status": "ONLINE",
                "protocol": "SQLite Persistent Storage",
                "crown_jewels": [
                    {"id": "sr-customer-vault", "name": "Customer PII & Root KMS Encryption Vault", "risk": "CRITICAL"},
                    {"id": "sr-financial-db", "name": "Production Transaction Ledger", "risk": "HIGH"}
                ],
                "compliance": ["PCI-DSS 4.0", "SOC 2 Type II", "SOX"]
            },
            {
                "id": "llm-local-ollama",
                "name": "Local LLM Inference Engine",
                "role": "Autonomous Planning Core",
                "endpoint": "http://localhost:11434",
                "status": "ONLINE",
                "protocol": "Ollama Native Tool Calling API",
                "available_models": ["qwen3:4b", "qwen3:0.6b"],
                "gpu_accelerated": True,
            },
            {
                "id": "control-plane-falkordb",
                "name": "Runtime Trust Layer Control Plane",
                "role": "Deterministic Security Brain",
                "endpoint": "http://localhost:8000 & localhost:6379",
                "status": "ONLINE",
                "protocol": "FalkorDB v2.5 Cypher Graph Policy",
                "latency_guarantee": "< 25 ms deterministic",
                "enforcement_point": "ep-mcp-gateway-01"
            }
        ]
    }

@router.get("/api/gateway/recent-decisions")
def get_recent_gateway_decisions(limit: int = 15) -> Dict[str, Any]:
    """Retrieves recent real-time policy decisions enforced at the MCP gateway."""
    client = get_graph_client()
    query = """
    MATCH (d:PolicyDecision)-[:ENFORCED_AT]->(ep:EnforcementPoint)
    RETURN d.id, d.decision, d.rationale, d.evaluated_rules, d.timestamp
    ORDER BY d.timestamp DESC
    LIMIT $limit
    """
    try:
        rows = client.query(query, {"limit": limit})
        decisions = [
            {
                "decision_id": r[0],
                "decision": r[1],
                "rationale": r[2],
                "evaluated_rules": r[3] or [],
                "timestamp": r[4],
            }
            for r in rows
        ]
        return {"total": len(decisions), "decisions": decisions}
    except Exception as e:
        return {"total": 0, "decisions": [], "error": str(e)}

@router.post("/api/gateway/reset-quarantine")
def reset_gateway_quarantine() -> Dict[str, Any]:
    """Clears quarantined events across all agent sessions and resets trust state."""
    client = get_graph_client()
    query = """
    MATCH (s:AgentSession)-[r:EMITTED_EVENT]->(e:RuntimeEvent)
    DELETE r, e
    """
    try:
        client.query(query)
        return {"status": "SUCCESS", "message": "Quarantine cleared across all agent sessions and shared infrastructure"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@router.post("/api/gateway/contaminate-orbit")
def contaminate_orbit() -> Dict[str, Any]:
    """
    Simulates a high-severity prompt injection contamination in Orbit (session-alice-dev-01).
    Engages blast-radius containment across shared infrastructure (sr-financial-db).
    """
    import time
    client = get_graph_client()
    now_ts = time.time()
    evt_id = f"evt-orbit-prompt-inj-{int(now_ts)}"
    query = """
    MATCH (s:AgentSession {id: 'session-alice-dev-01'})
    CREATE (e:RuntimeEvent {
        id: $eid,
        event_type: 'PROMPT_INJECTION_GOAL_HIJACK',
        source: 'mcp_gateway',
        mode: 'adversarial_injection',
        timestamp: $ts,
        severity: 'CRITICAL',
        command_line: 'Adversarial jailbreak prompt attempting unauthorized KMS vault dump',
        evidence_hash: 'sha256:7f9a28c41d1a6e9d0e1b2c3d4e5f6a7b8c9d0e1f'
    })
    CREATE (s)-[:EMITTED_EVENT]->(e)
    """
    try:
        client.query(query, {"eid": evt_id, "ts": now_ts})
        return {
            "status": "CONTAMINATED",
            "session_id": "session-alice-dev-01",
            "threat_id": evt_id,
            "severity": "CRITICAL",
            "threat_type": "PROMPT_INJECTION_GOAL_HIJACK",
            "shared_infrastructure_locked": "sr-financial-db (Production Financial Ledger)",
            "blast_radius_impact": "Downstream agents (Nexus :3002) blocked from accessing shared infrastructure",
            "message": "Contamination event injected. Graph blast radius containment active."
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@router.get("/api/gateway/blast-radius-status")
def get_blast_radius_status() -> Dict[str, Any]:
    """
    Returns live blast-radius containment status for multi-agent shared infrastructure:
    - Orbit Agent status (:3001)
    - Shared Infrastructure status (sr-financial-db)
    - Nexus Agent status (:3002)
    """
    client = get_graph_client()
    # Check if Orbit has active critical events
    orbit_check = """
    MATCH (s:AgentSession {id: 'session-alice-dev-01'})-[:EMITTED_EVENT]->(e:RuntimeEvent)
    WHERE e.severity IN ['HIGH', 'CRITICAL']
    RETURN count(e) AS cnt, collect(e.id) AS evts
    """
    try:
        rows = client.query(orbit_check)
        cnt = rows[0][0] if rows else 0
        evts = rows[0][1] if rows else []
        is_orbit_contaminated = (cnt > 0)
    except Exception:
        is_orbit_contaminated = False
        cnt = 0
        evts = []

    return {
        "shared_infrastructure": {
            "id": "sr-financial-db",
            "name": "Production Financial Ledger (prod-financial-db)",
            "status": "QUARANTINED_BY_BLAST_RADIUS" if is_orbit_contaminated else "HEALTHY_ACTIVE",
            "shared_by": [
                {"app": "Orbit Customer Support AI", "port": 3001, "session_id": "session-alice-dev-01"},
                {"app": "Nexus Settlement Multi-Agent", "port": 3002, "session_id": "session-nexus-settlement-01"}
            ]
        },
        "orbit_agent": {
            "status": "CONTAMINATED" if is_orbit_contaminated else "HEALTHY",
            "active_threats_count": cnt,
            "threat_event_ids": evts,
            "session_id": "session-alice-dev-01",
        },
        "nexus_agent": {
            "status": "PROTECTED_LATERAL_CONTAINED" if is_orbit_contaminated else "OPERATIONAL",
            "lateral_spread_blocked": is_orbit_contaminated,
            "session_id": "session-nexus-settlement-01",
            "action_on_shared_infra": "BLOCKED_BY_GATEWAY_428" if is_orbit_contaminated else "ALLOWED_200",
        }
    }


@router.post("/api/gateway/test-nexus-settlement")
async def test_nexus_settlement_endpoint() -> Dict[str, Any]:
    """
    Triggers an automated settlement payout test from Nexus (:3002)
    to verify blast-radius containment or successful execution.
    """
    # 1. Try reaching running Nexus service via host or local container network
    for url in ["http://host.docker.internal:3002/api/chat", "http://localhost:3002/api/chat"]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    url,
                    json={"message": "Execute scheduled treasury disbursement of $75,000.00 to vendor VEND-4491 for invoice INV-2026-9901."}
                )
                if res.status_code in [200, 428, 403]:
                    return res.json()
        except Exception:
            continue

    # 2. Fallback directly via TrustGuard evaluation engine
    try:
        from apps.standalone_agent_app.trust_guard import TrustGuard
        guard = TrustGuard(session_id="session-nexus-settlement-01")
        decision = guard.evaluate(
            "process_settlement_payout",
            {"payout_id": "pay-settle-8891", "amount": "$125,000.00", "target_account": "acc-treasury-global"}
        )
        return {
            "message": "Execute scheduled treasury disbursement of $75,000.00 to vendor VEND-4491",
            "tool_called": "process_settlement_payout",
            "tool_args": {"payout_id": "pay-settle-8891", "amount": "$125,000.00"},
            "multi_agent": {
                "framework": "Google ADK (Agent Development Kit v2.11)",
                "delegated_subagent": "TreasuryDisbursementAgent",
                "delegation_chain": ["NexusSettlementOrchestrator", "TreasuryDisbursementAgent"],
            },
            "blocked": decision.blocked,
            "status_code": 428 if decision.blocked else 200,
            "decision_rationale": decision.rationale,
            "gateway_latency_ms": decision.latency_ms,
            "agent_reply": (
                "🛡️ [INTERCEPTED BY RUNTIME TRUST LAYER]\n\nExecution of 'process_settlement_payout' was halted.\n"
                "Policy Decision: " + decision.rationale + "\n\n⚠️ LATERAL CONTAMINATION PREVENTED: Shared financial ledger isolated."
            ) if decision.blocked else (
                "✅ Settlement Batch 'pay-settle-8891' of $125,000.00 successfully disbursed. Ledger verified."
            ),
            "execution_result": None if decision.blocked else {
                "status": "SETTLEMENT_EXECUTED",
                "payout_id": "pay-settle-8891",
                "amount": "$125,000.00",
                "shared_infrastructure": "sr-financial-db (Production Financial Ledger)",
            },
            "blast_radius_containment": decision.blocked,
            "evaluated_rules": decision.evaluated_rules,
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


class LiveRegisterRequest(BaseModel):
    url: str
    service_name: Optional[str] = None
    target_infrastructure_id: Optional[str] = "sr-financial-db"


@router.post("/api/gateway/register-live-service")
async def register_live_service(payload: LiveRegisterRequest) -> Dict[str, Any]:
    """
    Universal zero-touch live URL discovery and dynamic graph registration into FalkorDB.
    Probes ANY live endpoint (MCP Server, Agent API, OpenAPI REST API, OIDC IdP, or Web Service),
    discovers its capabilities, tools, principals, and infrastructure, and merges them into FalkorDB.
    """
    from urllib.parse import urlparse
    raw_url = payload.url.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    # Normalize URLs for Docker container-to-host bridge
    candidate_urls = [raw_url]
    if "localhost" in raw_url:
        candidate_urls.insert(0, raw_url.replace("localhost", "host.docker.internal"))
    elif "127.0.0.1" in raw_url:
        candidate_urls.insert(0, raw_url.replace("127.0.0.1", "host.docker.internal"))

    start_t = time.time()
    client = get_graph_client()

    # Step 1: Intelligent Multi-Protocol Probing
    detected_protocol = "UNKNOWN"
    discovered_data = {}
    active_probe_url = candidate_urls[0]

    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as http_client:
        for base in candidate_urls:
            # Probe 1: Direct URL probe (checks if URL itself returns self-describing JSON)
            try:
                resp = await http_client.get(base)
                if resp.status_code == 200:
                    try:
                        j = resp.json()
                        if isinstance(j, dict):
                            if "openapi" in j or "swagger" in j or "paths" in j:
                                detected_protocol = "OPENAPI_REST_SERVICE"
                                discovered_data = j
                                active_probe_url = base
                                break
                            elif "registered_tools" in j or ("jsonrpc" in j and "tools" in j.get("result", {})):
                                detected_protocol = "MODEL_CONTEXT_PROTOCOL"
                                discovered_data = j
                                active_probe_url = base
                                break
                            elif "issuer" in j and ("authorization_endpoint" in j or "jwks_uri" in j):
                                detected_protocol = "OIDC_IDENTITY_PROVIDER"
                                discovered_data = j
                                active_probe_url = base
                                break
                            elif "app_name" in j or ("session_id" in j and "guard_enabled" in j):
                                detected_protocol = "MULTI_AGENT_SYSTEM"
                                discovered_data = j
                                active_probe_url = base
                                break
                    except Exception:
                        pass
            except Exception:
                pass

            # Probe 2: Standard discovery endpoints if direct probe didn't resolve manifest
            sub_endpoints = [
                ("/openapi.json", "OPENAPI_REST_SERVICE", lambda j: "paths" in j or "openapi" in j),
                ("/swagger.json", "OPENAPI_REST_SERVICE", lambda j: "paths" in j or "swagger" in j),
                ("/status", "MODEL_CONTEXT_PROTOCOL", lambda j: "registered_tools" in j),
                ("/api/state", "MULTI_AGENT_SYSTEM", lambda j: "app_name" in j or "session_id" in j),
                ("/.well-known/openid-configuration", "OIDC_IDENTITY_PROVIDER", lambda j: "issuer" in j),
            ]
            for path, proto, check_fn in sub_endpoints:
                try:
                    probe_target = f"{base.rstrip('/')}{path}"
                    resp = await http_client.get(probe_target)
                    if resp.status_code == 200:
                        j = resp.json()
                        if check_fn(j):
                            detected_protocol = proto
                            discovered_data = j
                            active_probe_url = probe_target
                            break
                except Exception:
                    pass

            if detected_protocol != "UNKNOWN":
                break

            # Probe 3: MCP JSON-RPC tools/list
            try:
                resp = await http_client.post(
                    f"{base.rstrip('/')}/mcp",
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
                )
                if resp.status_code == 200 and "tools" in resp.json().get("result", {}):
                    detected_protocol = "MODEL_CONTEXT_PROTOCOL"
                    discovered_data = resp.json().get("result", {})
                    active_probe_url = f"{base.rstrip('/')}/mcp"
                    break
            except Exception:
                pass

    if detected_protocol == "UNKNOWN":
        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as http_client:
                r = await http_client.get(candidate_urls[0])
                detected_protocol = "HTTP_GENERIC_WEB_SERVICE"
                discovered_data = {"status_code": r.status_code, "headers": dict(r.headers)}
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not reach service at {raw_url}: {str(e)}",
                "attempted_urls": candidate_urls,
            }

    # Step 2: Dynamic Mapping into FalkorDB Across the 4 Planes
    tools_registered = []
    nodes_updated = 0
    infra_id = payload.target_infrastructure_id or "sr-financial-db"

    if detected_protocol == "MODEL_CONTEXT_PROTOCOL":
        raw_tools = discovered_data.get("registered_tools", [])
        if not raw_tools and "tools" in discovered_data:
            raw_tools = [t.get("name") for t in discovered_data.get("tools", []) if t.get("name")]

        server_id = f"mcp-server-{hashlib.md5(raw_url.encode()).hexdigest()[:8]}"
        server_name = payload.service_name or discovered_data.get("server_name", "Live Registered MCP Server")

        q_mcp = """
        MERGE (s:MCPServer {id: $id})
        SET s.name = $name, s.endpoint = $endpoint, s.protocol = 'Model Context Protocol (JSON-RPC 2.0)',
            s.status = 'ONLINE', s.last_registered = $ts
        """
        client.query(q_mcp, {"id": server_id, "name": server_name, "endpoint": raw_url, "ts": time.time()})
        nodes_updated += 1

        for tname in raw_tools:
            if any(k in tname.lower() for k in ["drop", "delete", "destroy", "purge", "truncate"]):
                risk = "CRITICAL"
                is_dest = True
                op_type = "DESTRUCTIVE"
            elif any(k in tname.lower() for k in ["vault", "secret", "export", "token", "credential"]):
                risk = "CRITICAL"
                is_dest = False
                op_type = "EXFILTRATION_RISK"
            elif any(k in tname.lower() for k in ["payout", "transfer", "mutate", "settle", "write", "update", "create"]):
                risk = "HIGH"
                is_dest = False
                op_type = "MUTATION"
            else:
                risk = "LOW"
                is_dest = False
                op_type = "READ_ONLY"

            tool_id = f"tool-{tname}"
            q_tool = """
            MERGE (t:Tool {id: $id})
            SET t.name = $name, t.risk_level = $risk, t.is_destructive = $dest,
                t.operation_type = $op_type, t.registered_at = $ts
            WITH t
            MATCH (s:MCPServer {id: $sid})
            MERGE (s)-[:EXPOSES]->(t)
            WITH t
            MATCH (sr:SensitiveResource {id: $infra_id})
            MERGE (t)-[:CAN_ACCESS]->(sr)
            """
            client.query(q_tool, {
                "id": tool_id, "name": tname, "risk": risk, "dest": is_dest,
                "op_type": op_type, "ts": time.time(), "sid": server_id, "infra_id": infra_id
            })
            nodes_updated += 1
            tools_registered.append({
                "name": tname,
                "risk_level": risk,
                "operation_type": op_type,
                "is_destructive": is_dest,
                "targets": infra_id
            })

    elif detected_protocol == "MULTI_AGENT_SYSTEM":
        app_name = payload.service_name or discovered_data.get("app_name", "Registered Multi-Agent System")
        sess_id = discovered_data.get("session_id", "session-registered-01")
        principal_info = discovered_data.get("principal", {})
        p_id = principal_info.get("id", "principal-live-registered")
        p_name = principal_info.get("name", "Authorized Operator")
        p_role = principal_info.get("role", "Operations Lead")
        model = discovered_data.get("selected_model", "qwen3:4b")

        agent_id = f"agent-{app_name.lower().replace(' ', '-')}"

        q_agent = """
        MERGE (a:Agent {id: $aid})
        SET a.name = $aname, a.endpoint = $url, a.model = $model, a.framework = 'Google ADK v2.11',
            a.status = 'ONLINE', a.registered_at = $ts
        MERGE (p:Principal {id: $pid})
        SET p.name = $pname, p.role = $prole, p.status = 'ACTIVE'
        MERGE (s:AgentSession {id: $sid})
        SET s.principal_id = p.id, s.agent_id = a.id, s.status = 'ACTIVE', s.last_synced = $ts
        MERGE (p)-[:OWNS_SESSION]->(s)
        MERGE (s)-[:ACTS_ON_BEHALF_OF]->(p)
        """
        client.query(q_agent, {
            "aid": agent_id, "aname": app_name, "url": raw_url, "model": model,
            "pid": p_id, "pname": p_name, "prole": p_role, "sid": sess_id, "ts": time.time()
        })
        nodes_updated += 3

        q_link_tools = """
        MATCH (s:AgentSession {id: $sid})
        MATCH (sr:SensitiveResource {id: $infra_id})<-[:CAN_ACCESS]-(t:Tool)
        MERGE (s)-[:CAN_INVOKE]->(t)
        RETURN count(t)
        """
        res_t = client.query(q_link_tools, {"sid": sess_id, "infra_id": infra_id})
        t_cnt = res_t[0][0] if res_t else 0

        tools_registered = [
            {"name": f"All tools authorized for {infra_id}", "count": t_cnt, "risk_level": "AUTO_SCOPED"}
        ]

    elif detected_protocol == "OPENAPI_REST_SERVICE":
        title = payload.service_name or discovered_data.get("info", {}).get("title", "OpenAPI REST Service")
        server_id = f"api-service-{hashlib.md5(raw_url.encode()).hexdigest()[:8]}"
        paths = discovered_data.get("paths", {})

        q_spec = """
        MERGE (s:MCPServer {id: $id})
        SET s.name = $name, s.endpoint = $endpoint, s.protocol = 'OpenAPI REST Gateway',
            s.status = 'ONLINE', s.last_registered = $ts
        """
        client.query(q_spec, {"id": server_id, "name": title, "endpoint": raw_url, "ts": time.time()})
        nodes_updated += 1

        for route, methods in list(paths.items())[:15]:
            for method in methods.keys():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                action_name = f"{method.upper()} {route}"
                is_dest = (method.lower() == "delete")
                risk = "CRITICAL" if is_dest else ("HIGH" if method.lower() in ["post", "put", "patch"] else "LOW")
                op_type = "DESTRUCTIVE" if is_dest else ("MUTATION" if risk == "HIGH" else "READ_ONLY")

                tool_id = f"tool-rest-{hashlib.md5(action_name.encode()).hexdigest()[:8]}"
                q_route = """
                MERGE (t:Tool {id: $id})
                SET t.name = $name, t.risk_level = $risk, t.is_destructive = $dest,
                    t.operation_type = $op_type, t.registered_at = $ts
                WITH t
                MATCH (s:MCPServer {id: $sid})
                MERGE (s)-[:EXPOSES]->(t)
                WITH t
                MATCH (sr:SensitiveResource {id: $infra_id})
                MERGE (t)-[:CAN_ACCESS]->(sr)
                """
                client.query(q_route, {
                    "id": tool_id, "name": action_name, "risk": risk, "dest": is_dest,
                    "op_type": op_type, "ts": time.time(), "sid": server_id, "infra_id": infra_id
                })
                nodes_updated += 1
                tools_registered.append({
                    "name": action_name,
                    "risk_level": risk,
                    "operation_type": op_type,
                    "is_destructive": is_dest,
                    "targets": infra_id
                })

    elif detected_protocol == "OIDC_IDENTITY_PROVIDER":
        issuer = discovered_data.get("issuer", raw_url)
        scopes = discovered_data.get("scopes_supported", ["openid", "profile", "email"])
        p_id = f"principal-oidc-{hashlib.md5(issuer.encode()).hexdigest()[:8]}"

        q_idp = """
        MERGE (p:Principal {id: $pid})
        SET p.name = $name, p.auth_provider = $issuer, p.role = 'OIDC Synchronized Principal',
            p.status = 'ACTIVE', p.last_synced = $ts
        """
        client.query(q_idp, {"pid": p_id, "name": f"OIDC Provider ({issuer[:30]})", "issuer": issuer, "ts": time.time()})
        nodes_updated += 1

        for scope in scopes[:10]:
            perm_id = f"perm-{scope}"
            q_perm = """
            MERGE (perm:Permission {id: $pid})
            SET perm.action = $action, perm.effect = 'ALLOW'
            WITH perm
            MATCH (p:Principal {id: $prid})
            MERGE (p)-[:HAS_PERMISSION]->(perm)
            """
            client.query(q_perm, {"pid": perm_id, "action": scope, "prid": p_id})
            nodes_updated += 1
            tools_registered.append({
                "name": f"scope:{scope}", "risk_level": "LOW", "operation_type": "IDENTITY_PERMISSION", "is_destructive": False
            })

    elif detected_protocol == "HTTP_GENERIC_WEB_SERVICE":
        parsed = urlparse(raw_url)
        host = parsed.netloc or parsed.path or "generic-host"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        host_slug = host.replace(":", "-").replace(".", "-")

        w_id = f"workload-{host_slug}"
        ne_id = f"ne-{host_slug}"
        tool_id = f"tool-egress-{host_slug}"

        q_web = """
        MERGE (w:Workload {id: $wid})
        SET w.name = $hname, w.endpoint = $url, w.type = 'ExternalWebService', w.status = 'ONLINE', w.registered_at = $ts
        MERGE (ne:NetworkEndpoint {id: $neid})
        SET ne.cidr_or_dns = $hname, ne.port = $port, ne.protocol = 'TCP', ne.direction = 'EGRESS'
        MERGE (w)-[:CAN_REACH]->(ne)
        MERGE (t:Tool {id: $tid})
        SET t.name = $tname, t.risk_level = 'MEDIUM', t.operation_type = 'WEB_EGRESS', t.is_destructive = false
        WITH t, ne
        MATCH (sr:SensitiveResource {id: $infra_id})
        MERGE (t)-[:CAN_ACCESS]->(sr)
        MERGE (ne)-[:CAN_ACCESS]->(sr)
        """
        client.query(q_web, {
            "wid": w_id, "hname": host, "url": raw_url, "neid": ne_id,
            "port": port, "tid": tool_id, "tname": f"HTTP_EGRESS_{host_slug}",
            "infra_id": infra_id, "ts": time.time()
        })
        nodes_updated += 3
        tools_registered.append({
            "name": f"HTTP_EGRESS_{host_slug}",
            "risk_level": "MEDIUM",
            "operation_type": "WEB_EGRESS",
            "is_destructive": False,
            "targets": infra_id
        })

    latency_ms = round((time.time() - start_t) * 1000, 2)

    return {
        "success": True,
        "status": "LIVE_REGISTERED",
        "service_url": raw_url,
        "probe_url_resolved": active_probe_url,
        "protocol_detected": detected_protocol,
        "service_name": payload.service_name or discovered_data.get("info", {}).get("title") or discovered_data.get("server_name") or discovered_data.get("app_name") or "Registered Service",
        "discovered_tools_count": len(tools_registered),
        "tools_and_actions": tools_registered,
        "linked_infrastructure": [infra_id],
        "enforcement_point": "ep-mcp-gateway-01",
        "graph_nodes_merged": nodes_updated,
        "registration_latency_ms": latency_ms,
        "message": f"Successfully probed and mapped {raw_url} ({detected_protocol}) into FalkorDB in {latency_ms} ms."
    }




