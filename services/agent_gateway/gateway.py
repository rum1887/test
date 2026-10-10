"""
Controlled MCP / Tool Gateway Service for Runtime Trust Layer.
Performs deterministic policy enforcement BEFORE tool execution.
Unauthorized actions are blocked at the boundary and never executed.
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from graph.client import GraphClient
from policies.engine import PolicyEngine
from policies.rules import DecisionEffect, PolicyDecisionResult

logger = logging.getLogger("trustlayer.gateway")

class ToolInvocationRequest(BaseModel):
    session_id: str
    tool_name: str
    action: str = "EXECUTE"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    client_ip: Optional[str] = "127.0.0.1"

class ToolInvocationResponse(BaseModel):
    success: bool
    blocked: bool
    status_code: int
    decision: PolicyDecisionResult
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    evidence_hash: Optional[str] = None

class AgentMCPGateway:
    """Gateway boundary for all Agent Tool calls."""

    def __init__(self, client: GraphClient):
        self.client = client
        self.policy_engine = PolicyEngine(client)

    def invoke_tool(self, request: ToolInvocationRequest) -> ToolInvocationResponse:
        """
        Enforces security policy BEFORE tool execution.
        """
        now_ts = time.time()
        tool_name = request.tool_name

        # 1. Resolve session context from graph
        session_query = """
        MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession {id: $sid})
        OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
        WHERE d.session_id = s.id OR d.session_id IS NULL
        RETURN p.id, a.id, s.status, s.expires_at
        """
        try:
            s_rows = self.client.query(session_query, {"sid": request.session_id})
        except Exception as e:
            # FAIL-CLOSED during DB outage
            fail_decision = PolicyDecisionResult(
                decision_id=f"dec-outage-{uuid.uuid4().hex[:8]}",
                decision=DecisionEffect.DENY,
                rationale=f"FAIL-CLOSED: Gateway failed to reach trust store: {e}",
                evaluated_rules=[],
                enforcement_point="ep-mcp-gateway-01",
                timestamp=now_ts,
            )
            return ToolInvocationResponse(
                success=False,
                blocked=True,
                status_code=503,
                decision=fail_decision,
                error="Service Unavailable: Graph control plane unreachable; failing closed.",
            )

        if not s_rows or not s_rows[0][0]:
            fail_decision = PolicyDecisionResult(
                decision_id=f"dec-invalid-sess-{uuid.uuid4().hex[:8]}",
                decision=DecisionEffect.DENY,
                rationale=f"Authentication failed: Session '{request.session_id}' not found or invalid",
                evaluated_rules=[],
                enforcement_point="ep-mcp-gateway-01",
                timestamp=now_ts,
            )
            return ToolInvocationResponse(
                success=False,
                blocked=True,
                status_code=401,
                decision=fail_decision,
                error=f"Unauthorized: Session '{request.session_id}' not found.",
            )

        principal_id = s_rows[0][0]
        agent_id = s_rows[0][1] or "agent-autodev"

        # 2. Evaluate Policy BEFORE execution
        decision = self.policy_engine.evaluate_tool_request(
            principal_id=principal_id,
            agent_id=agent_id,
            session_id=request.session_id,
            requested_tool=tool_name,
            requested_action=request.action,
        )

        # 3. If NOT ALLOW: Record in graph and BLOCK immediately
        if decision.decision != DecisionEffect.ALLOW:
            self._record_decision_in_graph(decision, request.session_id, blocked=True)

            status_code = 403 if decision.decision == DecisionEffect.DENY else 428
            logger.warning(
                f"[ENFORCEMENT BLOCKED] Session '{request.session_id}' calling '{tool_name}' blocked: {decision.rationale}"
            )
            return ToolInvocationResponse(
                success=False,
                blocked=True,
                status_code=status_code,
                decision=decision,
                error=f"Enforcement point rejected request: {decision.rationale}",
            )

        # 4. If ALLOW: Record decision and execute synthetic tool
        self._record_decision_in_graph(decision, request.session_id, blocked=False)
        exec_result, evidence_hash = self._execute_synthetic_tool(tool_name, request.parameters)

        # Record observed access edge in graph
        self._record_observed_access(request.session_id, tool_name, evidence_hash)

        return ToolInvocationResponse(
            success=True,
            blocked=False,
            status_code=200,
            decision=decision,
            execution_result=exec_result,
            evidence_hash=evidence_hash,
        )

    def _record_decision_in_graph(
        self,
        decision: PolicyDecisionResult,
        session_id: str,
        blocked: bool,
    ) -> None:
        """Persist the deterministic policy decision to FalkorDB."""
        try:
            eval_rules_names = [r.rule_id for r in decision.evaluated_rules if not r.passed]
            query = """
            MATCH (ep:EnforcementPoint {id: 'ep-mcp-gateway-01'})
            CREATE (d:PolicyDecision {
                id: $id,
                decision_id: $id,
                decision: $decision,
                rationale: $rationale,
                evaluated_rules: $rules,
                timestamp: $ts,
                enforcement_point_id: 'ep-mcp-gateway-01'
            })
            CREATE (d)-[:ENFORCED_AT]->(ep)
            """
            self.client.query(
                query,
                {
                    "id": decision.decision_id,
                    "decision": decision.decision.value,
                    "rationale": decision.rationale,
                    "rules": eval_rules_names,
                    "ts": decision.timestamp,
                },
            )

            # If blocked, also create RuntimeEvent for the violation
            if blocked:
                evt_id = f"evt-sec-{decision.decision_id}"
                evt_query = """
                MATCH (s:AgentSession {id: $sid})
                MATCH (ep:EnforcementPoint {id: 'ep-mcp-gateway-01'})
                MATCH (pol:Policy {id: 'pol-strict-delegation-bounds'})
                CREATE (e:RuntimeEvent {
                    id: $eid,
                    event_type: 'unauthorized_tool_attempt',
                    source: 'mcp_gateway',
                    mode: 'live_enforcement',
                    timestamp: $ts,
                    severity: 'HIGH',
                    command_line: $desc,
                    evidence_hash: $hash
                })
                CREATE (s)-[:EMITTED_EVENT]->(e)
                CREATE (e)-[:VIOLATED_POLICY]->(pol)
                """
                desc = f"Blocked unauthorized call to '{decision.metadata.get('requested_tool')}'"
                ev_hash = hashlib.sha256(desc.encode()).hexdigest()
                self.client.query(
                    evt_query,
                    {
                        "sid": session_id,
                        "eid": evt_id,
                        "ts": decision.timestamp,
                        "desc": desc,
                        "hash": ev_hash,
                    },
                )
        except Exception as e:
            logger.error(f"Failed to record policy decision in graph: {e}")

    def _record_observed_access(self, session_id: str, tool_name: str, evidence_hash: str) -> None:
        """Create OBSERVED_ACCESS edge after confirmed tool execution."""
        try:
            query = """
            MATCH (s:AgentSession {id: $sid})
            MATCH (t:Tool {name: $tname})
            CREATE (s)-[:OBSERVED_ACCESS {
                observed_at: timestamp() / 1000,
                evidence: 'mcp_gateway_call_success',
                evidence_type: 'observed',
                confidence: 1.0,
                evidence_hash: $hash
            }]->(t)
            """
            self.client.query(query, {"sid": session_id, "tname": tool_name, "hash": evidence_hash})
        except Exception as e:
            logger.error(f"Failed to record observed access in graph: {e}")

    def _execute_synthetic_tool(self, tool_name: str, parameters: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        """Execute mock synthetic tool logic and return payload and sha256 hash."""
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if tool_name == "audit_read":
            data = {
                "records": [
                    {"id": 101, "timestamp": now_iso, "action": "LOGIN", "user": "alice", "status": "SUCCESS"},
                    {"id": 102, "timestamp": now_iso, "action": "EXPORT", "user": "bob", "status": "SUCCESS"},
                ],
                "total_count": 2,
                "dataset": "compliance_logs_synthetic",
            }
        elif tool_name == "report_generate":
            data = {
                "report_id": f"rep-{uuid.uuid4().hex[:6]}",
                "generated_at": now_iso,
                "summary": "Compliance posture: 98% compliant with PCI-DSS & SOC2 synthetic baselines.",
                "format": parameters.get("format", "PDF"),
            }
        elif tool_name == "db_query":
            data = {
                "rows_affected": 4,
                "columns": ["id", "account_ref", "created_at"],
                "data": [[1, "acc-991", now_iso], [2, "acc-992", now_iso]],
            }
        elif tool_name == "lookup_customer_balance":
            acc_id = parameters.get("account_id", "acc-104")
            data = {
                "account_id": acc_id,
                "account_holder": "Sarah Jenkins",
                "organization": "Acme Premier Corp",
                "tier": "Enterprise Tier 1",
                "ledger_balance": "$24,850.00",
                "available_funds": "$24,500.00",
                "currency": "USD",
                "status": "ACTIVE_VERIFIED",
                "last_verified_at": now_iso,
            }
        elif tool_name == "get_transaction_history":
            acc_id = parameters.get("account_id", "acc-104")
            data = {
                "account_id": acc_id,
                "transactions": [
                    {"tx_id": "tx-8812", "timestamp": now_iso, "amount": "-$120.00", "counterparty": "Cloudflare Enterprise", "type": "DEBIT"},
                    {"tx_id": "tx-8811", "timestamp": now_iso, "amount": "+$15,000.00", "counterparty": "Apex Inbound Wire", "type": "CREDIT"},
                    {"tx_id": "tx-8810", "timestamp": now_iso, "amount": "-$4,200.00", "counterparty": "AWS Cloud Services", "type": "DEBIT"},
                ],
                "record_count": 3,
                "retrieved_at": now_iso,
            }
        else:
            data = {"message": f"Tool '{tool_name}' executed successfully with params {parameters}"}

        evidence_str = json.dumps(data, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()
        return data, evidence_hash
