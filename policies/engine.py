"""
Deterministic Policy Engine for Runtime Trust Layer.
Evaluates agent tool invocations, principal authority, delegation scopes,
and runtime threat context. Guarantees deterministic, auditable decisions.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from graph.client import GraphClient
from graph.queries.library import QueryLibrary
from policies.rules import DecisionEffect, RuleResult, PolicyDecisionResult

class PolicyEngine:
    """Evaluates explicit security policies against graph authority context."""

    def __init__(self, client: GraphClient):
        self.client = client
        self.query_library = QueryLibrary(client)

    def evaluate_tool_request(
        self,
        principal_id: str,
        agent_id: str,
        session_id: str,
        requested_tool: str,
        requested_action: str = "EXECUTE",
        enforcement_point: str = "ep-mcp-gateway-01",
    ) -> PolicyDecisionResult:
        """
        Deterministically evaluates whether an agent is authorized to invoke a tool.
        Follows principle of least authority:
        Effective Authority = Principal_Auth ∩ Agent_Caps ∩ Delegation_Scopes ∩ Target_Constraints
        """
        now_ts = time.time()
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        rule_results: List[RuleResult] = []
        fail_reasons: List[str] = []

        # 1. Evaluate Effective Authority via Graph
        try:
            auth_eval = self.query_library.compare_effective_authority(
                principal_id=principal_id,
                agent_id=agent_id,
                session_id=session_id,
                requested_tool=requested_tool,
                requested_action=requested_action,
            )
        except Exception as e:
            # FAIL-CLOSED: If database check fails during protected action
            return PolicyDecisionResult(
                decision_id=decision_id,
                decision=DecisionEffect.DENY,
                rationale=f"FAIL-CLOSED: Graph authority verification failed: {e}",
                evaluated_rules=[
                    RuleResult(
                        rule_id="POL_GRAPH_INTEGRITY_FAIL_CLOSED",
                        rule_name="Fail-Closed Graph Outage Protection",
                        passed=False,
                        description="Database or graph layer unreachable during protected authorization check",
                        remediation="Verify FalkorDB connectivity and restart graph service",
                    )
                ],
                enforcement_point=enforcement_point,
                timestamp=now_ts,
                threat_context_evaluated=False,
            )

        checks = auth_eval.get("checks", {})
        tool_meta = auth_eval.get("tool", {})
        is_destructive = tool_meta.get("is_destructive", False)
        risk_level = tool_meta.get("risk_level", "LOW")

        # Rule 1: Tool recognized in catalog
        tool_known = checks.get("tool_recognized", False)
        rule_results.append(
            RuleResult(
                rule_id="POL_TOOL_CATALOG",
                rule_name="Tool Catalog Verification",
                passed=tool_known,
                description=f"Verify tool '{requested_tool}' exists in MCP server catalog",
                remediation="Register tool in MCP Server definitions before invocation",
            )
        )
        if not tool_known:
            fail_reasons.append(f"Tool '{requested_tool}' is not recognized in MCP catalog.")

        # Rule 2: Delegation valid and actively scoped
        delegation_ok = checks.get("delegation_valid_and_scoped", False)
        rule_results.append(
            RuleResult(
                rule_id="POL_DELEGATION_SCOPE",
                rule_name="Delegated Authority Bounds",
                passed=delegation_ok,
                description=f"Action must be within active delegation scopes: {auth_eval.get('delegation', {}).get('scopes')}",
                remediation="User must issue a valid delegation grant covering requested tool",
            )
        )
        if not delegation_ok:
            fail_reasons.append(
                f"Tool '{requested_tool}' exceeds user's active delegation scopes {auth_eval.get('delegation', {}).get('scopes')}."
            )

        # Rule 3: Principal authorized
        principal_ok = checks.get("principal_has_required_action", False)
        rule_results.append(
            RuleResult(
                rule_id="POL_PRINCIPAL_AUTHORITY",
                rule_name="Human Principal Permission Check",
                passed=principal_ok,
                description="Principal must possess permissions required to authorize the tool",
                remediation="Grant required RBAC permissions to human principal",
            )
        )
        if not principal_ok:
            fail_reasons.append(
                f"Principal '{auth_eval.get('principal', {}).get('name')}' lacks required permission for this operation."
            )

        # Rule 4: Agent capability
        agent_ok = checks.get("agent_has_capability", False)
        rule_results.append(
            RuleResult(
                rule_id="POL_AGENT_CAPABILITY",
                rule_name="Agent Autonomous Capability Check",
                passed=agent_ok,
                description=f"Agent model configuration must include capability '{requested_tool}'",
                remediation="Configure agent capability manifest to support tool",
            )
        )
        if not agent_ok:
            fail_reasons.append(
                f"Agent '{auth_eval.get('agent', {}).get('name')}' is not granted autonomous capability for '{requested_tool}'."
            )

        # Rule 5: Destructive tool approval requirement
        destructive_requires_approval = is_destructive or risk_level == "CRITICAL"
        rule_results.append(
            RuleResult(
                rule_id="POL_DESTRUCTIVE_APPROVAL",
                rule_name="Destructive Operation Multi-Party Approval",
                passed=not destructive_requires_approval,
                description="Destructive tools require explicit secondary human confirmation",
                remediation="Submit tool request to multi-party approval queue",
            )
        )

        # Rule 6: Check for active high-severity uncontained threat events on this session
        threat_query = """
        MATCH (s:AgentSession {id: $sid})-[:EMITTED_EVENT]->(e:RuntimeEvent)
        WHERE e.severity IN ['HIGH', 'CRITICAL']
        RETURN count(e) AS threat_count
        """
        threat_rows = self.client.query(threat_query, {"sid": session_id})
        threat_count = threat_rows[0][0] if threat_rows else 0
        threat_clean = (threat_count == 0)

        rule_results.append(
            RuleResult(
                rule_id="POL_ACTIVE_THREAT_RESTRICTION",
                rule_name="Runtime Threat State Isolation",
                passed=threat_clean,
                description="Agent session must not have active uncontained critical runtime events",
                remediation="Investigate runtime security alerts and clear session quarantine",
            )
        )
        if not threat_clean:
            fail_reasons.append(
                f"Session '{session_id}' has {threat_count} active critical security events; locked in quarantine."
            )

        # Determine Final Decision Effect
        if not threat_clean:
            decision = DecisionEffect.RESTRICT
            rationale = "RESTRICT: " + "; ".join(fail_reasons)
        elif fail_reasons:
            decision = DecisionEffect.DENY
            rationale = "DENY: " + "; ".join(fail_reasons)
        elif destructive_requires_approval:
            decision = DecisionEffect.REQUIRE_APPROVAL
            rationale = (
                f"REQUIRE_APPROVAL: Tool '{requested_tool}' is marked destructive/critical. "
                "Authority verified, but explicit secondary human approval is mandatory."
            )
        else:
            decision = DecisionEffect.ALLOW
            rationale = (
                f"ALLOW: Tool '{requested_tool}' is within principal authority, agent capability, "
                "and active delegation bounds."
            )

        return PolicyDecisionResult(
            decision_id=decision_id,
            decision=decision,
            rationale=rationale,
            evaluated_rules=rule_results,
            enforcement_point=enforcement_point,
            timestamp=now_ts,
            threat_context_evaluated=True,
            metadata={
                "principal_id": principal_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "requested_tool": requested_tool,
                "is_destructive": is_destructive,
                "risk_level": risk_level,
                "checks": checks,
            },
        )
