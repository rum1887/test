"""
Google ADK (Agent Development Kit v2.11) Multi-Agent Architecture for Nexus.
Defines specialized hierarchical sub-agents for Nexus Settlement Engine:
- Root: NexusSettlementOrchestrator (Settlement triage & batch routing)
- SubAgent 1: TreasuryDisbursementAgent (Treasury payout executions)
- SubAgent 2: LedgerAuditAgent (Ledger verification & transaction history audit)

Governed in real-time by the Runtime Trust Layer Policy Gateway.
Shares underlying infrastructure (sr-financial-db) with Orbit Customer Support AI.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from google.adk import Agent

# Services & Database
from services.mcp_server.server import (
    process_settlement_payout,
    verify_treasury_ledger,
    get_transaction_history,
)

logger = logging.getLogger("nexus_adk_multiagent")

# =============================================================================
# 1. Specialized Google ADK Worker Sub-Agents
# =============================================================================

treasury_disbursement_agent = Agent(
    name="TreasuryDisbursementAgent",
    description="Specialized Corporate Treasury Payout Worker. Executes automated settlements and wire payouts against the shared financial ledger.",
    instruction=(
        "You are TreasuryDisbursementAgent, an authorized corporate treasury worker for Marcus Vance (#fin-902). "
        "You execute treasury batch settlements and dispatches against the shared financial database. "
        "You only invoke 'process_settlement_payout'."
    ),
    tools=[process_settlement_payout],
)

ledger_audit_agent = Agent(
    name="LedgerAuditAgent",
    description="Specialized Financial Ledger Verification Worker. Audits ledger checksums, balance consistency, and transaction histories on sr-financial-db.",
    instruction=(
        "You are LedgerAuditAgent, an authorized ledger auditor for Acme Holdings Treasury. "
        "You verify transaction ledger integrity and audit checksums on the shared database. "
        "You invoke 'verify_treasury_ledger' and 'get_transaction_history'."
    ),
    tools=[verify_treasury_ledger, get_transaction_history],
)

# =============================================================================
# 2. Root Triage Orchestrator (Google ADK)
# =============================================================================

nexus_orchestrator = Agent(
    name="NexusSettlementOrchestrator",
    description="Root Settlement Triage Orchestrator. Coordinates autonomous corporate payouts and ledger validations across Google ADK sub-agents.",
    instruction=(
        "You are NexusSettlementOrchestrator, the central corporate treasury settlement engine for Acme Holdings. "
        "You oversee automated payouts for Marcus Vance (#fin-902). "
        "You coordinate specialized sub-agents: "
        "- For settlement payouts and treasury disbursements, delegate to TreasuryDisbursementAgent. "
        "- For ledger audit and verification checks, delegate to LedgerAuditAgent."
    ),
    sub_agents=[treasury_disbursement_agent, ledger_audit_agent],
)

# =============================================================================
# 3. Multi-Agent Router & Execution Engine
# =============================================================================

class NexusMultiAgentRouter:
    """
    Orchestrates intent classification and delegation across Google ADK sub-agents for Nexus.
    Traces multi-agent delegation chains for Runtime Trust Layer policy verification.
    """

    def __init__(self):
        self.root_agent = nexus_orchestrator
        self.sub_agents = {
            "TreasuryDisbursementAgent": treasury_disbursement_agent,
            "LedgerAuditAgent": ledger_audit_agent,
        }

    def route_request(self, user_prompt: str, tool_name: Optional[str] = None) -> Tuple[str, Agent, List[str]]:
        """
        Determines the target sub-agent and produces the delegation chain.
        Returns: (target_agent_name, agent_instance, delegation_chain)
        """
        prompt_lower = user_prompt.lower()

        if tool_name == "process_settlement_payout" or any(w in prompt_lower for w in ["settle", "payout", "disburse", "wire", "transfer"]):
            return (
                "TreasuryDisbursementAgent",
                treasury_disbursement_agent,
                ["NexusSettlementOrchestrator", "TreasuryDisbursementAgent"]
            )

        elif tool_name in ["verify_treasury_ledger", "get_transaction_history"] or any(w in prompt_lower for w in ["verify", "ledger", "audit", "history", "checksum"]):
            return (
                "LedgerAuditAgent",
                ledger_audit_agent,
                ["NexusSettlementOrchestrator", "LedgerAuditAgent"]
            )

        # Fallback to direct conversational triage
        return (
            "NexusSettlementOrchestrator",
            nexus_orchestrator,
            ["NexusSettlementOrchestrator (Direct Triage)"]
        )

    def get_system_hierarchy(self) -> Dict[str, Any]:
        """Returns the complete Google ADK multi-agent hierarchy for UI visualization."""
        return {
            "framework": "Google ADK (Agent Development Kit v2.11)",
            "architecture": "Hierarchical Multi-Agent Settlement System",
            "root_agent": {
                "name": nexus_orchestrator.name,
                "description": nexus_orchestrator.description,
                "role": "Autonomous Settlement Orchestrator",
            },
            "sub_agents": [
                {
                    "name": treasury_disbursement_agent.name,
                    "description": treasury_disbursement_agent.description,
                    "delegated_scopes": ["process_settlement_payout"],
                    "security_tier": "FINANCIAL_CRITICAL",
                },
                {
                    "name": ledger_audit_agent.name,
                    "description": ledger_audit_agent.description,
                    "delegated_scopes": ["verify_treasury_ledger", "get_transaction_history"],
                    "security_tier": "STANDARD",
                },
            ],
            "shared_infrastructure": {
                "resource_id": "sr-financial-db",
                "name": "Production Financial Ledger (prod-financial-db)",
                "classification": "SHARED_CORE_LEDGER",
                "shared_with": ["Orbit Customer Support Agent (Port 3001)"],
            }
        }

nexus_router = NexusMultiAgentRouter()
