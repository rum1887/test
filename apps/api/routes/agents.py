"""
AI Agent, Session, Delegation, and Tool Catalog Routes.
"""

from fastapi import APIRouter
from typing import Dict, Any, List
from graph.client import get_graph_client

router = APIRouter(tags=["Agent Activity & Delegation"])

@router.get("/api/agents")
def list_agents() -> List[Dict[str, Any]]:
    """Returns catalog of AI agents registered in the system."""
    client = get_graph_client()
    query = """
    MATCH (a:Agent)
    OPTIONAL MATCH (s:AgentSession)-[:ACTS_ON_BEHALF_OF]->(a)
    WITH a, count(s) AS session_count
    RETURN
        a.id AS id,
        a.name AS name,
        a.model AS model,
        a.vendor AS vendor,
        a.description AS description,
        a.capabilities AS capabilities,
        a.max_autonomy_level AS autonomy,
        a.status AS status,
        session_count
    """
    rows = client.query(query)
    return [
        {
            "id": r[0],
            "name": r[1],
            "model": r[2],
            "vendor": r[3],
            "description": r[4],
            "capabilities": r[5] if isinstance(r[5], list) else ([r[5]] if r[5] else []),
            "max_autonomy_level": r[6],
            "status": r[7],
            "active_sessions_count": r[8],
        }
        for r in rows
    ]

@router.get("/api/agents/sessions")
def list_sessions() -> List[Dict[str, Any]]:
    """Returns active agent sessions linked to human principals."""
    client = get_graph_client()
    query = """
    MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession)
    OPTIONAL MATCH (s)-[:ACTS_ON_BEHALF_OF]->(a:Agent)
    OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a)
    WHERE d.session_id = s.id OR d.session_id IS NULL
    RETURN
        s.id AS session_id,
        s.status AS status,
        s.created_at AS created_at,
        s.expires_at AS expires_at,
        p.id AS principal_id,
        p.name AS principal_name,
        p.role AS principal_role,
        a.id AS agent_id,
        a.name AS agent_name,
        d.id AS delegation_id,
        d.scopes AS scopes
    """
    rows = client.query(query)
    return [
        {
            "session_id": r[0],
            "status": r[1],
            "created_at": r[2],
            "expires_at": r[3],
            "principal": {"id": r[4], "name": r[5], "role": r[6]},
            "agent": {"id": r[7], "name": r[8]} if r[7] else None,
            "delegation": {
                "id": r[9],
                "scopes": r[10] if isinstance(r[10], list) else ([r[10]] if r[10] else []),
            } if r[9] else None,
        }
        for r in rows
    ]

@router.get("/api/agents/tools")
def list_mcp_tools() -> List[Dict[str, Any]]:
    """Returns tools provided by MCP servers and downstream sensitive resources."""
    client = get_graph_client()
    query = """
    MATCH (m:MCPServer)-[:CONTAINS]->(t:Tool)
    OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
    RETURN
        t.id AS id,
        t.name AS name,
        t.description AS description,
        t.required_permissions AS perms,
        t.risk_level AS risk,
        t.is_destructive AS destructive,
        m.name AS mcp_server_name,
        sr.id AS target_id,
        sr.name AS target_name,
        sr.sensitivity_level AS target_sensitivity
    """
    rows = client.query(query)
    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "required_permissions": r[3] if isinstance(r[3], list) else ([r[3]] if r[3] else []),
            "risk_level": r[4] or "LOW",
            "is_destructive": bool(r[5]),
            "mcp_server": r[6],
            "downstream_target": {
                "id": r[7],
                "name": r[8],
                "sensitivity": r[9],
            } if r[7] else None,
        }
        for r in rows
    ]
