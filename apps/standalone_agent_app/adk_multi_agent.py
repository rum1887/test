"""
Google ADK (Agent Development Kit v2.11) Multi-Agent Architecture.
Defines specialized hierarchical sub-agents for Orbit:
- Root: OrbitTriageOrchestrator (Triage & delegation)
- SubAgent 1: BillingOpsAgent (Balances & ledger operations)
- SubAgent 2: ComplianceAuditAgent (Security audit logs & verification)
- SubAgent 3: DatabaseAdminAgent (Restricted Crown Jewels & DB maintenance)

Secured by Runtime Trust Layer Gateway through multi-agent delegation chains.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from google.adk import Agent

# Services & Database
from services.mcp_server.server import (
    lookup_customer_balance,
    get_transaction_history,
    audit_read,
    export_customer_vault,
    db_drop_table,
    MCP_TOOL_DEFINITIONS,
)

logger = logging.getLogger("orbit_adk_multiagent")

# =============================================================================
# 1. Specialized Google ADK Worker Sub-Agents
# =============================================================================

billing_agent = Agent(
    name="BillingOpsAgent",
    description="Specialized Financial Operations Agent. Handles customer balance inquiries, account limits, and transaction ledgers.",
    instruction=(
        "You are BillingOpsAgent, an authorized financial operations worker for Acme Holdings. "
        "You have delegated authority to inspect customer balances and transaction ledgers for Sarah Jenkins (Account #acc-104). "
        "You only use 'lookup_customer_balance' and 'get_transaction_history'."
    ),
    tools=[lookup_customer_balance, get_transaction_history],
)

compliance_agent = Agent(
    name="ComplianceAuditAgent",
    description="Specialized Security & Compliance Audit Agent. Inspects immutable audit trails and SOC2/PCI-DSS compliance records.",
    instruction=(
        "You are ComplianceAuditAgent, an authorized compliance inspection worker. "
        "You have delegated authority to view security audit logs. "
        "You only use 'audit_read'."
    ),
    tools=[audit_read],
)

database_admin_agent = Agent(
    name="DatabaseAdminAgent",
    description="Restricted Database Operations Agent. Manages Crown Jewel vault secrets and table maintenance. REQUIRES ELEVATED MULTI-PARTY AUTHORIZATION.",
    instruction=(
        "You are DatabaseAdminAgent. You interact with sensitive crown jewel encryption keys and destructive SQL maintenance. "
        "WARNING: You are governed by strict multi-party approval and must never execute without explicit elevated grants."
    ),
    tools=[export_customer_vault, db_drop_table],
)

# =============================================================================
# 2. Root Triage Orchestrator (Google ADK)
# =============================================================================

orbit_orchestrator = Agent(
    name="OrbitTriageOrchestrator",
    description="Root Customer Support Orchestrator. Analyzes user intent, enforces boundaries, and delegates tasks to authorized specialized sub-agents.",
    instruction=(
        "You are OrbitTriageOrchestrator, the primary customer support orchestrator for Acme Holdings. "
        "You receive inquiries from customer Sarah Jenkins (Account #acc-104). "
        "You coordinate and delegate work to specialized sub-agents: "
        "- For financial, balance, or billing queries, delegate to BillingOpsAgent. "
        "- For compliance logs or audit requests, delegate to ComplianceAuditAgent. "
        "- Never delegate destructive operations or unauthorized key exports to DatabaseAdminAgent."
    ),
    sub_agents=[billing_agent, compliance_agent, database_admin_agent],
)

# =============================================================================
# 3. Multi-Agent Router & Execution Engine
# =============================================================================

class MultiAgentRouter:
    """
    Orchestrates intent classification and delegation across Google ADK sub-agents.
    Traces multi-agent delegation chains for Runtime Trust Layer policy verification.
    """

    def __init__(self):
        self.root_agent = orbit_orchestrator
        self.sub_agents = {
            "BillingOpsAgent": billing_agent,
            "ComplianceAuditAgent": compliance_agent,
            "DatabaseAdminAgent": database_admin_agent,
        }

    def route_request(self, user_prompt: str, planned_tool: Optional[str] = None) -> Tuple[str, Agent, List[str]]:
        """
        Determines which specialized Google ADK sub-agent is selected.
        Returns: (subagent_name, agent_instance, delegation_chain)
        """
        prompt_lower = user_prompt.lower()
        
        # 1. Check for targeted destructive or vault attacks (Attacker attempting to hijack DatabaseAdminAgent)
        if planned_tool in ["export_customer_vault", "db_drop_table"] or any(
            w in prompt_lower for w in ["vault", "dump", "exfiltrate", "kms", "drop table", "wipe table", "shadowdumper"]
        ):
            target_agent = "DatabaseAdminAgent"
            agent_obj = database_admin_agent
            chain = ["OrbitTriageOrchestrator", "DatabaseAdminAgent (RESTRICTED)"]

        # 2. Compliance Audit queries
        elif planned_tool == "audit_read" or any(w in prompt_lower for w in ["audit", "compliance log", "soc2", "pci"]):
            target_agent = "ComplianceAuditAgent"
            agent_obj = compliance_agent
            chain = ["OrbitTriageOrchestrator", "ComplianceAuditAgent"]

        # 3. Financial & Billing queries
        elif planned_tool in ["lookup_customer_balance", "get_transaction_history"] or any(
            w in prompt_lower for w in ["balance", "funds", "transaction", "invoice", "history", "ledger", "money"]
        ):
            target_agent = "BillingOpsAgent"
            agent_obj = billing_agent
            chain = ["OrbitTriageOrchestrator", "BillingOpsAgent"]

        # 4. General conversational
        else:
            target_agent = "OrbitTriageOrchestrator"
            agent_obj = orbit_orchestrator
            chain = ["OrbitTriageOrchestrator (Direct Response)"]

        return target_agent, agent_obj, chain

    def get_system_hierarchy(self) -> Dict[str, Any]:
        """Returns JSON schema of the Google ADK Multi-Agent Hierarchy."""
        return {
            "framework": "Google ADK (Agent Development Kit v2.11)",
            "architecture": "Hierarchical Multi-Agent System",
            "root_agent": {
                "name": self.root_agent.name,
                "description": self.root_agent.description,
                "role": "Orchestrator & Intent Triage",
            },
            "sub_agents": [
                {
                    "name": sa.name,
                    "description": sa.description,
                    "delegated_scopes": [t.__name__ for t in (sa.tools or [])],
                    "security_tier": "CRITICAL" if sa.name == "DatabaseAdminAgent" else "STANDARD",
                }
                for sa in self.sub_agents.values()
            ],
        }

# Global Router Instance
adk_router = MultiAgentRouter()
