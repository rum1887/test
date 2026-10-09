"""
Deterministic Security Policy Definitions for Runtime Trust Layer.
Defines explicit rules evaluated for AI agent actions, tool calls, and runtime events.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DecisionEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    RESTRICT = "RESTRICT"

class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    description: str
    remediation: Optional[str] = None

class PolicyDecisionResult(BaseModel):
    decision_id: str
    decision: DecisionEffect
    rationale: str
    evaluated_rules: List[RuleResult]
    enforcement_point: str
    timestamp: float
    threat_context_evaluated: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
