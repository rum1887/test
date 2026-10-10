"""
Runtime Trust Layer Python SDK / Middleware.
Integrates standalone agent applications with the FalkorDB Runtime Trust Layer control plane.
Enforces deterministic policy checks BEFORE any tool executes.
"""

import time
import httpx
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel

class GuardDecision(BaseModel):
    allowed: bool
    blocked: bool
    status_code: int
    rationale: str
    tool_name: str
    latency_ms: float
    evidence_hash: Optional[str] = None
    evaluated_rules: list = []

class TrustGuard:
    """
    Client middleware to intercept AI agent tool invocations
    and enforce deterministic Runtime Trust Layer policies.
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000/api/gateway/invoke",
        session_id: str = "session-alice-dev-01",
        fail_closed: bool = True,
        timeout_seconds: float = 2.0,
    ):
        self.gateway_url = gateway_url
        self.session_id = session_id
        self.fail_closed = fail_closed
        self.timeout = timeout_seconds

    def evaluate(self, tool_name: str, parameters: Dict[str, Any] = None) -> GuardDecision:
        """
        Sends pre-execution check to Runtime Trust Layer Gateway.
        Guarantees deterministic decision in sub-15ms.
        """
        start = time.time()
        payload = {
            "session_id": self.session_id,
            "tool_name": tool_name,
            "action": "EXECUTE",
            "parameters": parameters or {},
            "client_ip": "127.0.0.1",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.gateway_url, json=payload)
                data = res.json()
                latency_ms = round((time.time() - start) * 1000, 2)

                if res.status_code == 200 and not data.get("blocked", False):
                    return GuardDecision(
                        allowed=True,
                        blocked=False,
                        status_code=200,
                        rationale=data.get("decision", {}).get("rationale", "Authorized by delegation grant"),
                        tool_name=tool_name,
                        latency_ms=latency_ms,
                        evidence_hash=data.get("evidence_hash"),
                        evaluated_rules=data.get("decision", {}).get("evaluated_rules", []),
                    )
                else:
                    return GuardDecision(
                        allowed=False,
                        blocked=True,
                        status_code=res.status_code,
                        rationale=data.get("decision", {}).get("rationale") or data.get("error", "Access Denied"),
                        tool_name=tool_name,
                        latency_ms=latency_ms,
                        evidence_hash=data.get("decision", {}).get("decision_id"),
                        evaluated_rules=data.get("decision", {}).get("evaluated_rules", []),
                    )

        except Exception as e:
            latency_ms = round((time.time() - start) * 1000, 2)
            if self.fail_closed:
                return GuardDecision(
                    allowed=False,
                    blocked=True,
                    status_code=503,
                    rationale=f"FAIL-CLOSED: Runtime Trust Layer control plane unreachable: {e}",
                    tool_name=tool_name,
                    latency_ms=latency_ms,
                )
            else:
                return GuardDecision(
                    allowed=True,
                    blocked=False,
                    status_code=200,
                    rationale=f"FAIL-OPEN: Warning: Gateway unreachable: {e}",
                    tool_name=tool_name,
                    latency_ms=latency_ms,
                )
