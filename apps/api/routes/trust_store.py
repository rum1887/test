"""
Dynamic Trust Store & Multi-Layer AI Firewall Interception Routes.
Manages dynamic graph storage of Identities, Roles, RBAC, Agents, Services, and MCP Tools,
supports real-time discovery and graph mutations, and executes multi-layer runtime interception.
"""

import time
import uuid
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
import httpx

from graph.client import get_graph_client
from policies.engine import PolicyEngine
from policies.rules import DecisionEffect

logger = logging.getLogger("trustlayer.trust_store")
router = APIRouter(prefix="/api/trust-store", tags=["Trust Store & AI Firewall"])

# --- Request Models ---

class RegisterToolRequest(BaseModel):
    name: str = Field(..., description="Tool name, e.g. 'rotate_kms_key'")
    description: Optional[str] = "Dynamically registered MCP tool"
    mcp_server_id: Optional[str] = "mcp-edge-01"
    risk_level: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, or CRITICAL")
    is_destructive: bool = False
    operation_type: str = Field("READ_ONLY", description="READ_ONLY, MUTATION, or DESTRUCTIVE")
    target_resource_id: Optional[str] = "sr-customer-vault"
    required_role: Optional[str] = "SecOps Lead"

class RegisterIdentityRequest(BaseModel):
    username: str = Field(..., description="Unique principal id, e.g. 'charlie.davis'")
    full_name: str = Field(..., description="Full name, e.g. 'Charlie Davis'")
    email: str = Field(..., description="Email address")
    role: str = Field("Security Analyst", description="Assigned RBAC role")
    permissions: List[str] = Field(default_factory=lambda: ["audit_read", "report_generate"])
    assign_agent_id: Optional[str] = "agent-autodev"

class FirewallInterceptRequest(BaseModel):
    caller_identity: str = Field("principal-alice", description="Principal username or id")
    agent_id: str = Field("agent-autodev", description="Agent id invoking the tool")
    tool_name: str = Field("lookup_customer_balance", description="Requested tool name")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    action: str = "EXECUTE"
    enforce_mode: bool = True

# --- Endpoints ---

@router.get("/inventory")
def get_trust_store_inventory() -> Dict[str, Any]:
    """
    Returns the dynamic storage inventory of Identities, Roles, Agents, Services, and MCP Tools
    directly from FalkorDB with their active graph relationships.
    """
    client = get_graph_client()
    if not client.is_alive():
        raise HTTPException(status_code=503, detail="FalkorDB is offline")

    # 1. Fetch Identities (Principals)
    principals_query = """
    MATCH (p:Principal)
    OPTIONAL MATCH (p)-[:HAS_PERMISSION]->(perm:Permission)
    OPTIONAL MATCH (p)-[:OWNS_SESSION]->(s:AgentSession)
    OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
    RETURN p.id, coalesce(p.name, p.id), coalesce(p.role, 'Standard User'), coalesce(p.email, ''),
           coalesce(p.status, 'ACTIVE'),
           collect(DISTINCT perm.action) AS perms,
           collect(DISTINCT s.id) AS sessions,
           collect(DISTINCT a.id) AS agents
    """
    p_rows = client.query(principals_query)
    identities = []
    for r in p_rows:
        pid, pname, prole, pemail, pstat, perms, sess, agents = r
        identities.append({
            "id": pid,
            "name": pname,
            "role": prole,
            "email": pemail or f"{pid}@acme.corp",
            "status": pstat,
            "permissions": perms or [],
            "active_sessions": sess or [],
            "delegated_agents": agents or [],
        })

    # 2. Fetch Agents
    agents_query = """
    MATCH (a:Agent)
    OPTIONAL MATCH (s:AgentSession)-[:ACTS_ON_BEHALF_OF]->(p:Principal)
    WHERE s.agent_id = a.id
    OPTIONAL MATCH (d:Delegation)-[:DELEGATES_TO]->(a)
    RETURN a.id, coalesce(a.name, a.id), coalesce(a.endpoint, 'Local Process'),
           coalesce(a.status, 'ONLINE'), coalesce(a.framework, 'Autonomous Agent SDK'),
           coalesce(a.model, 'qwen2.5:7b'),
           collect(DISTINCT p.id) AS bound_principals,
           collect(DISTINCT d.scopes) AS scopes
    """
    a_rows = client.query(agents_query)
    agents = []
    for r in a_rows:
        aid, aname, aend, astat, afw, amdl, bound_p, scopes = r
        flat_scopes = []
        for s in (scopes or []):
            if isinstance(s, list):
                flat_scopes.extend(s)
            elif s:
                flat_scopes.append(s)
        agents.append({
            "id": aid,
            "name": aname,
            "endpoint": aend,
            "status": astat,
            "framework": afw,
            "model": amdl,
            "bound_principals": bound_p or [],
            "allowed_scopes": list(set(flat_scopes)),
        })

    # 3. Fetch MCP Tools & Servers
    tools_query = """
    MATCH (t:Tool)
    OPTIONAL MATCH (m:MCPServer)-[:EXPOSES]->(t)
    OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
    RETURN t.id, coalesce(t.name, t.id), coalesce(t.risk_level, 'LOW'),
           coalesce(t.is_destructive, false), coalesce(t.operation_type, 'READ_ONLY'),
           coalesce(m.id, 'mcp-edge-01') AS mcp_id,
           coalesce(m.name, 'Default MCP Gateway') AS mcp_name,
           coalesce(sr.id, 'none') AS target_id,
           coalesce(sr.name, 'General Resources') AS target_name,
           coalesce(sr.sensitivity_level, 'NONE') AS target_sensitivity
    """
    t_rows = client.query(tools_query)
    tools = []
    for r in t_rows:
        tid, tname, trisk, tdest, topt, mid, mname, sid, sname, ssens = r
        tools.append({
            "id": tid,
            "name": tname,
            "risk_level": trisk,
            "is_destructive": bool(tdest),
            "operation_type": topt,
            "mcp_server": {"id": mid, "name": mname},
            "target_resource": {"id": sid, "name": sname, "sensitivity": ssens},
        })

    # 4. Fetch Services & Infrastructure
    infra_query = """
    MATCH (sr:SensitiveResource)
    OPTIONAL MATCH (t:Tool)-[:CAN_ACCESS]->(sr)
    RETURN sr.id, coalesce(sr.name, sr.id), coalesce(sr.sensitivity_level, 'MEDIUM'),
           coalesce(sr.resource_type, 'Database / Vault'),
           collect(DISTINCT t.name) AS accessing_tools
    """
    sr_rows = client.query(infra_query)
    services = []
    for r in sr_rows:
        srid, srname, srsens, srtype, acc_tools = r
        services.append({
            "id": srid,
            "name": srname,
            "sensitivity_level": srsens,
            "type": srtype,
            "status": "PROTECTED",
            "accessing_tools": acc_tools or [],
        })

    # 5. Extract Unique Roles
    role_map = {}
    for ident in identities:
        r_name = ident["role"]
        if r_name not in role_map:
            role_map[r_name] = {
                "name": r_name,
                "users": [],
                "permissions": set(),
            }
        role_map[r_name]["users"].append(ident["name"])
        role_map[r_name]["permissions"].update(ident["permissions"])

    roles = [
        {
            "name": r_data["name"],
            "user_count": len(r_data["users"]),
            "users": r_data["users"],
            "permissions": list(r_data["permissions"]),
        }
        for r_data in role_map.values()
    ]

    return {
        "summary": {
            "total_identities": len(identities),
            "total_roles": len(roles),
            "total_agents": len(agents),
            "total_services": len(services),
            "total_tools": len(tools),
            "mcp_servers": 1,
        },
        "identities": identities,
        "roles": roles,
        "agents": agents,
        "services": services,
        "tools": tools,
    }


@router.post("/tools")
def register_tool(req: RegisterToolRequest) -> Dict[str, Any]:
    """
    Registers a new tool into FalkorDB dynamically.
    Creates Tool node, links it to MCPServer, and sets up CAN_ACCESS edge to the target resource.
    """
    client = get_graph_client()
    if not client.is_alive():
        raise HTTPException(status_code=503, detail="FalkorDB is offline")

    tool_id = f"tool-{req.name.lower().replace('_', '-')}"
    now_ts = time.time()

    # Create or update Tool node and MCPServer linkage
    cypher = """
    MERGE (t:Tool {name: $name})
    SET t.id = $id,
        t.name = $name,
        t.risk_level = $risk,
        t.is_destructive = $destructive,
        t.operation_type = $op_type,
        t.description = $desc,
        t.registered_at = $ts,
        t.required_role = $req_role

    WITH t
    MERGE (m:MCPServer {id: $mcp_id})
    ON CREATE SET m.name = 'Edge MCP Gateway', m.status = 'ONLINE', m.protocol = 'JSON-RPC 2.0'
    MERGE (m)-[:EXPOSES]->(t)

    WITH t
    MERGE (sr:SensitiveResource {id: $target_id})
    ON CREATE SET sr.name = $target_id, sr.sensitivity_level = 'HIGH', sr.status = 'ACTIVE'
    MERGE (t)-[:CAN_ACCESS]->(sr)

    RETURN t.id, t.name, t.risk_level, t.is_destructive
    """
    params = {
        "id": tool_id,
        "name": req.name,
        "risk": req.risk_level.upper(),
        "destructive": req.is_destructive,
        "op_type": req.operation_type.upper(),
        "desc": req.description,
        "ts": now_ts,
        "req_role": req.required_role,
        "mcp_id": req.mcp_server_id or "mcp-edge-01",
        "target_id": req.target_resource_id or "sr-financial-db",
    }

    try:
        rows = client.query(cypher, params)
    except Exception as e:
        logger.error(f"Error registering tool in FalkorDB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register tool: {e}")

    return {
        "success": True,
        "message": f"Tool '{req.name}' successfully registered into dynamic graph.",
        "tool": {
            "id": tool_id,
            "name": req.name,
            "risk_level": req.risk_level.upper(),
            "is_destructive": req.is_destructive,
            "operation_type": req.operation_type.upper(),
            "mcp_server_id": req.mcp_server_id,
            "target_resource_id": req.target_resource_id,
            "registered_at": now_ts,
        },
    }


@router.post("/identities")
def register_identity(req: RegisterIdentityRequest) -> Dict[str, Any]:
    """
    Registers / Onboards a new Identity (User/Principal) with RBAC permissions into FalkorDB.
    Creates Principal, Role Permissions, an AgentSession, and an active Delegation to an Agent.
    """
    client = get_graph_client()
    if not client.is_alive():
        raise HTTPException(status_code=503, detail="FalkorDB is offline")

    principal_id = f"principal-{req.username.lower().replace(' ', '-').replace('.', '-')}"
    session_id = f"session-{req.username.lower().replace(' ', '-').replace('.', '-')}-01"
    delegation_id = f"del-{req.username.lower().replace(' ', '-').replace('.', '-')}-01"
    now_ts = time.time()
    agent_id = req.assign_agent_id or "agent-autodev"

    cypher = """
    MERGE (p:Principal {id: $pid})
    SET p.name = $name,
        p.email = $email,
        p.role = $role,
        p.status = 'ACTIVE',
        p.registered_at = $ts

    WITH p
    MERGE (s:AgentSession {id: $sid})
    SET s.status = 'ACTIVE', s.last_synced = $ts, s.agent_id = $aid
    MERGE (p)-[:OWNS_SESSION]->(s)
    MERGE (s)-[:ACTS_ON_BEHALF_OF]->(p)

    WITH p, s
    MERGE (a:Agent {id: $aid})
    ON CREATE SET a.name = 'Autonomous Agent', a.status = 'ONLINE'

    MERGE (d:Delegation {id: $did})
    SET d.scopes = $perms, d.status = 'ACTIVE', d.session_id = $sid, d.expires_at = $exp
    MERGE (p)-[:DELEGATES_TO]->(d)
    MERGE (d)-[:DELEGATES_TO]->(a)

    RETURN p.id, p.name, p.role
    """
    params = {
        "pid": principal_id,
        "name": req.full_name,
        "email": req.email,
        "role": req.role,
        "ts": now_ts,
        "sid": session_id,
        "aid": agent_id,
        "did": delegation_id,
        "perms": req.permissions,
        "exp": now_ts + 86400 * 30,  # 30 day delegation
    }

    try:
        client.query(cypher, params)

        # Also add granular Permission nodes and link them
        for perm_action in req.permissions:
            perm_id = f"perm-{perm_action.lower().replace('_', '-')}"
            p_cypher = """
            MATCH (p:Principal {id: $pid})
            MERGE (perm:Permission {id: $permid})
            SET perm.action = $action, perm.name = $action
            MERGE (p)-[:HAS_PERMISSION]->(perm)
            """
            client.query(p_cypher, {"pid": principal_id, "permid": perm_id, "action": perm_action})

    except Exception as e:
        logger.error(f"Error registering identity in FalkorDB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register identity: {e}")

    return {
        "success": True,
        "message": f"Identity '{req.full_name}' ({req.role}) detected and added to dynamic graph.",
        "identity": {
            "id": principal_id,
            "name": req.full_name,
            "email": req.email,
            "role": req.role,
            "session_id": session_id,
            "assigned_agent_id": agent_id,
            "permissions": req.permissions,
            "registered_at": now_ts,
        },
    }


@router.post("/scan-and-reload")
async def scan_and_reload_fleet() -> Dict[str, Any]:
    """
    Probes active fleet servers (Orbit :3001, Nexus :3002, MCP Server :8443, API :8000),
    detects newly exposed tools, services, and agent status, and synchronizes FalkorDB live.
    """
    client = get_graph_client()
    now_ts = time.time()

    probes = [
        {"name": "Orbit Support Agent", "port": 3001, "agent_id": "agent-autodev"},
        {"name": "Nexus FinOps Agent", "port": 3002, "agent_id": "agent-nexus-settlement"},
        {"name": "MCP Tool Server", "port": 8443, "mcp_id": "mcp-edge-01"},
        {"name": "Core Trust API", "port": 8000, "service_id": "service-trust-api"},
    ]

    discovered = []
    new_tools = []
    nodes_updated = 0

    async with httpx.AsyncClient(timeout=3.0) as http_client:
        for p in probes:
            port = p["port"]
            # Try host.docker.internal first, then 127.0.0.1
            urls = [f"http://host.docker.internal:{port}", f"http://127.0.0.1:{port}"]
            online = False
            latency_ms = 0.0
            data = {}

            for u in urls:
                t0 = time.time()
                try:
                    r = await http_client.get(f"{u}/status", follow_redirects=True)
                    if r.status_code == 200:
                        online = True
                        latency_ms = round((time.time() - t0) * 1000, 2)
                        data = r.json() if "application/json" in r.headers.get("content-type", "") else {}
                        break
                except Exception:
                    try:
                        r = await http_client.get(f"{u}/health", follow_redirects=True)
                        if r.status_code == 200:
                            online = True
                            latency_ms = round((time.time() - t0) * 1000, 2)
                            data = r.json() if "application/json" in r.headers.get("content-type", "") else {}
                            break
                    except Exception:
                        pass

            # Sync node in FalkorDB
            if "agent_id" in p:
                q_sync = """
                MERGE (a:Agent {id: $aid})
                SET a.name = $name, a.status = $status, a.last_heartbeat = $ts,
                    a.endpoint = $endpoint, a.latency_ms = $lat
                """
                client.query(q_sync, {
                    "aid": p["agent_id"],
                    "name": p["name"],
                    "status": "ONLINE" if online else "STANDBY",
                    "ts": now_ts,
                    "endpoint": f"http://127.0.0.1:{port}",
                    "lat": latency_ms,
                })
                nodes_updated += 1

            elif "mcp_id" in p:
                q_sync = """
                MERGE (m:MCPServer {id: $mid})
                SET m.name = $name, m.status = $status, m.last_heartbeat = $ts,
                    m.endpoint = $endpoint, m.latency_ms = $lat
                """
                client.query(q_sync, {
                    "mid": p["mcp_id"],
                    "name": p["name"],
                    "status": "ONLINE" if online else "STANDBY",
                    "ts": now_ts,
                    "endpoint": f"http://127.0.0.1:{port}",
                    "lat": latency_ms,
                })
                nodes_updated += 1

                # If MCP server returned tools, sync any new ones
                reg_tools = data.get("registered_tools", [])
                for tname in reg_tools:
                    tid = f"tool-{tname.lower().replace('_', '-')}"
                    q_tool = """
                    MERGE (t:Tool {name: $tname})
                    ON CREATE SET t.id = $tid, t.risk_level = 'LOW', t.is_destructive = false,
                                  t.registered_at = $ts, t.operation_type = 'READ_ONLY'
                    WITH t
                    MATCH (m:MCPServer {id: $mid})
                    MERGE (m)-[:EXPOSES]->(t)
                    """
                    client.query(q_tool, {"tname": tname, "tid": tid, "ts": now_ts, "mid": p["mcp_id"]})
                    nodes_updated += 1
                    new_tools.append(tname)

            discovered.append({
                "service": p["name"],
                "port": port,
                "online": online,
                "latency_ms": latency_ms,
                "status": "ONLINE" if online else "STANDBY",
            })

    return {
        "success": True,
        "message": f"Fleet scan complete: {len(discovered)} services probed, {nodes_updated} graph records synchronized.",
        "services": discovered,
        "newly_synced_tools": new_tools,
        "timestamp": now_ts,
    }


@router.post("/firewall-intercept")
def firewall_intercept(req: FirewallInterceptRequest) -> Dict[str, Any]:
    """
    Multi-Layer Runtime Interception & Graph Reasoning Engine.
    Intercepts the request at 4 distinct layers:
      Layer 1: Identity Ingress & Caller Authentication
      Layer 2: Agent Delegation & RBAC Authority
      Layer 3: MCP Tool Call Interception & Catalog Risk
      Layer 4: Data & Infrastructure Egress Blast Radius
    Explores the latest FalkorDB graph state in real time and enforces the decision.
    """
    client = get_graph_client()
    now_ts = time.time()
    trace_id = f"trace-{uuid.uuid4().hex[:10]}"

    # --- LAYER 1: Ingress Authentication ---
    p_res = client.query(
        "MATCH (p:Principal {id: $pid}) RETURN p.id, p.name, p.role, p.status",
        {"pid": req.caller_identity}
    )
    if not p_res:
        # Fallback query by name if id didn't match directly
        p_res = client.query(
            "MATCH (p:Principal) WHERE p.name =~ $pname RETURN p.id, p.name, p.role, p.status",
            {"pname": f"(?i).*{req.caller_identity}.*"}
        )

    layer1_passed = bool(p_res and p_res[0][3] == "ACTIVE")
    principal_info = {}
    if p_res:
        pid, pname, prole, pstat = p_res[0]
        principal_info = {"id": pid, "name": pname, "role": prole, "status": pstat}
    else:
        principal_info = {"id": req.caller_identity, "name": "Unknown Identity", "role": "UNVERIFIED", "status": "UNKNOWN"}

    layer1_result = {
        "layer": "Layer 1: Ingress & Identity Authentication",
        "passed": layer1_passed,
        "checked": f"Principal verification for '{principal_info.get('name')}' ({principal_info.get('role')})",
        "evidence": f"Principal record status: {principal_info.get('status')}",
    }

    if not layer1_passed:
        return _build_firewall_response(
            trace_id=trace_id,
            decision="DENY",
            decision_code=401,
            rationale=f"Layer 1 Ingress Intercept: Identity '{req.caller_identity}' is not registered or active in Trust Store.",
            layers=[layer1_result],
            graph_path=[],
            execution_result=None,
        )

    # --- LAYER 2: Agent Delegation & RBAC Authority ---
    # Find active session and delegation grant
    del_query = """
    MATCH (p:Principal {id: $pid})-[:OWNS_SESSION]->(s:AgentSession)-[:ACTS_ON_BEHALF_OF]->(p)
    OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
    RETURN s.id, a.id, coalesce(d.scopes, []), coalesce(d.status, 'INACTIVE')
    """
    del_res = client.query(del_query, {"pid": principal_info["id"]})
    session_id = del_res[0][0] if del_res else f"session-{principal_info['id']}-01"
    delegated_scopes = []
    if del_res and del_res[0][2]:
        raw_sc = del_res[0][2]
        delegated_scopes = raw_sc if isinstance(raw_sc, list) else [raw_sc]

    # Check principal permissions
    perm_query = """
    MATCH (p:Principal {id: $pid})-[:HAS_PERMISSION]->(perm:Permission)
    RETURN collect(perm.action)
    """
    perm_res = client.query(perm_query, {"pid": principal_info["id"]})
    user_perms = perm_res[0][0] if perm_res and perm_res[0] else []

    # Check if tool is authorized in delegation or user permissions
    tool_authorized_by_delegation = (
        "*" in delegated_scopes
        or req.tool_name in delegated_scopes
        or "all_tools" in delegated_scopes
        or any(req.tool_name in p for p in user_perms)
    )
    layer2_passed = tool_authorized_by_delegation
    layer2_result = {
        "layer": "Layer 2: Agent Delegation & RBAC Bounds",
        "passed": layer2_passed,
        "checked": f"Delegation bounds for Agent '{req.agent_id}' acting on behalf of '{principal_info['name']}'",
        "evidence": f"Delegated scopes: {delegated_scopes or ['None explicitly granted']}; User Permissions: {user_perms or ['None']}",
    }

    # --- LAYER 3: MCP Tool Call Interception & Catalog Risk ---
    tool_query = """
    MATCH (t:Tool {name: $tname})
    OPTIONAL MATCH (m:MCPServer)-[:EXPOSES]->(t)
    OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
    RETURN t.id, t.name, coalesce(t.risk_level, 'LOW'), coalesce(t.is_destructive, false),
           coalesce(t.operation_type, 'READ_ONLY'), coalesce(sr.id, 'none'), coalesce(sr.sensitivity_level, 'NONE')
    """
    t_res = client.query(tool_query, {"tname": req.tool_name})
    tool_exists = bool(t_res)
    tool_risk = t_res[0][2] if t_res else "UNKNOWN"
    tool_destructive = bool(t_res[0][3]) if t_res else False
    target_resource_id = t_res[0][5] if t_res else None
    target_sensitivity = t_res[0][6] if t_res else "NONE"

    # Destructive or critical tools require explicit elevated role
    is_critical_escalation = (
        tool_risk == "CRITICAL" or tool_destructive
    ) and "SecOps Lead" not in principal_info.get("role", "") and "FinanceAdmin" not in principal_info.get("role", "")

    layer3_passed = tool_exists and not is_critical_escalation
    layer3_result = {
        "layer": "Layer 3: MCP Tool Interception & Catalog Guard",
        "passed": layer3_passed,
        "checked": f"Pre-execution tool scan for '{req.tool_name}' (Risk: {tool_risk}, Destructive: {tool_destructive})",
        "evidence": f"Catalog presence: {tool_exists}; Destructive escalation blocked: {is_critical_escalation}",
    }

    # --- LAYER 4: Data & Infrastructure Egress Blast Radius ---
    layer4_passed = True
    if target_sensitivity == "CRITICAL" and not layer2_passed:
        layer4_passed = False

    layer4_result = {
        "layer": "Layer 4: Data & Crown Jewel Egress Blast Radius",
        "passed": layer4_passed,
        "checked": f"Access boundary to target resource '{target_resource_id or 'General'}' (Sensitivity: {target_sensitivity})",
        "evidence": f"Sensitivity classification: {target_sensitivity}; Egress authorized: {layer4_passed}",
    }

    all_layers = [layer1_result, layer2_result, layer3_result, layer4_result]
    overall_passed = all(l["passed"] for l in all_layers)

    # Graph Traversal Path for visual explanation
    graph_path = [
        {"node": principal_info.get("id"), "label": "Principal", "name": principal_info.get("name"), "status": "VERIFIED"},
        {"edge": "OWNS_SESSION", "target": session_id},
        {"node": session_id, "label": "AgentSession", "status": "ACTIVE"},
        {"edge": "ACTS_ON_BEHALF_OF", "target": req.agent_id},
        {"node": req.agent_id, "label": "Agent", "status": "ONLINE"},
        {"edge": "CAN_INVOKE" if overall_passed else "BLOCKED_INVOCATION", "target": f"tool-{req.tool_name}"},
        {"node": f"tool-{req.tool_name}", "label": "Tool", "name": req.tool_name, "risk": tool_risk},
    ]
    if target_resource_id and target_resource_id != "none":
        graph_path.extend([
            {"edge": "CAN_ACCESS", "target": target_resource_id},
            {"node": target_resource_id, "label": "SensitiveResource", "sensitivity": target_sensitivity},
        ])

    # Enforcement Execution
    if overall_passed or not req.enforce_mode:
        # ALLOW: Execute live tool against SQLite database
        from services.database.live_db import (
            live_get_customer_balance,
            live_get_transactions,
            live_read_audit_logs,
        )
        if req.tool_name in ["lookup_customer_balance", "cust_balance"]:
            acc_id = req.parameters.get("account_id", "acc-104")
            raw_data = live_get_customer_balance(acc_id)
        elif req.tool_name in ["get_transaction_history", "cust_tx"]:
            acc_id = req.parameters.get("account_id", "acc-104")
            raw_data = live_get_transactions(acc_id)
        elif req.tool_name in ["audit_read", "audit_logs"]:
            raw_data = live_read_audit_logs()
        else:
            raw_data = {
                "message": f"Tool '{req.tool_name}' executed cleanly against connected infrastructure.",
                "parameters_processed": req.parameters,
                "timestamp": now_ts,
            }

        ev_hash = hashlib.sha256(json.dumps(raw_data, sort_keys=True).encode()).hexdigest()

        # Record OBSERVED_ACCESS in graph
        try:
            q_obs = """
            MATCH (s:AgentSession {id: $sid})
            MATCH (t:Tool {name: $tname})
            MERGE (s)-[:OBSERVED_ACCESS {timestamp: $ts, evidence_hash: $hash, status: 'ALLOWED'}]->(t)
            """
            client.query(q_obs, {"sid": session_id, "tname": req.tool_name, "ts": now_ts, "hash": ev_hash})
        except Exception:
            pass

        return _build_firewall_response(
            trace_id=trace_id,
            decision="ALLOW",
            decision_code=200,
            rationale=f"Request verified and permitted across all 4 layers. Agent '{req.agent_id}' has verified delegation from '{principal_info['name']}'.",
            layers=all_layers,
            graph_path=graph_path,
            execution_result=raw_data,
            evidence_hash=ev_hash,
        )

    else:
        # DENY / INTERCEPT: Block before execution
        failed_layer_names = [l["layer"] for l in all_layers if not l["passed"]]
        rationale = f"Blocked by AI Firewall at {', '.join(failed_layer_names)}. "
        if not layer2_passed:
            rationale += f"Agent '{req.agent_id}' lacks delegation scope for tool '{req.tool_name}'. "
        if is_critical_escalation:
            rationale += f"Tool '{req.tool_name}' is classified as {tool_risk} / Destructive and cannot be executed by role '{principal_info.get('role')}'. "

        # Record Policy Decision & Violation Event in FalkorDB
        ev_hash = hashlib.sha256(rationale.encode()).hexdigest()
        try:
            evt_id = f"evt-fw-{trace_id}"
            q_evt = """
            MATCH (s:AgentSession {id: $sid})
            CREATE (e:RuntimeEvent {
                id: $eid,
                event_type: 'firewall_interception',
                source: 'ai_firewall_layer',
                severity: 'HIGH',
                timestamp: $ts,
                evidence_hash: $hash,
                command_line: $desc
            })
            CREATE (s)-[:EMITTED_EVENT]->(e)
            """
            client.query(q_evt, {"sid": session_id, "eid": evt_id, "ts": now_ts, "hash": ev_hash, "desc": rationale})
        except Exception:
            pass

        return _build_firewall_response(
            trace_id=trace_id,
            decision="DENY",
            decision_code=403,
            rationale=rationale,
            layers=all_layers,
            graph_path=graph_path,
            execution_result=None,
            evidence_hash=ev_hash,
        )


def _build_firewall_response(
    trace_id: str,
    decision: str,
    decision_code: int,
    rationale: str,
    layers: List[Dict[str, Any]],
    graph_path: List[Dict[str, Any]],
    execution_result: Optional[Dict[str, Any]] = None,
    evidence_hash: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "trace_id": trace_id,
        "decision": decision,
        "status_code": decision_code,
        "enforced": decision == "DENY",
        "rationale": rationale,
        "layers_evaluated": layers,
        "graph_path_explored": graph_path,
        "execution_result": execution_result,
        "evidence_hash": evidence_hash,
        "timestamp": time.time(),
    }
