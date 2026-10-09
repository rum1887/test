# Threat Model — Runtime Trust Layer

## 1. Scope & System Boundaries

This threat model analyzes threats across Kubernetes workloads, autonomous AI agents, delegated credentials, and runtime execution boundaries.

---

## 2. Threat Scenarios & Mitigations

### Threat 1: Overprivileged Kubernetes Workload Compromise
- **Vector**: An attacker exploits a vulnerability in a public-facing pod (e.g. `checkout-service`), spawning an interactive shell (`/bin/sh`) and querying the internal cloud metadata service (`169.254.169.254`).
- **Impact**: Attacker leverages the pod's service account to reach cluster secrets and customer databases.
- **Runtime Trust Layer Defense**:
  - Cilium Tetragon eBPF captures `sys_execve` of `/bin/sh` in container `cnt-checkout-main`.
  - Event collector ingests event, correlates it to Pod `pod-checkout-7f89b` and Workload `workload-checkout`.
  - Blast Radius query (Query 1) identifies plausible paths to `customer-vault-secrets` and `payment-records-db`.
  - Containment Simulator (Query 5 & 6) ranks pod isolation via NetworkPolicy (`quarantine-checkout-isolate`), proving 100% exposure reduction.

### Threat 2: AI Agent Privilege Escalation / Confused Deputy
- **Vector**: A user with read-only compliance permissions (Alice) requests an AI agent to execute a destructive database operation (`db_drop_table`).
- **Impact**: If the agent runs with its own broad infrastructure permissions, the user escalates privileges beyond authorized delegated bounds.
- **Runtime Trust Layer Defense**:
  - The MCP Gateway intercepts the tool request **BEFORE** execution.
  - The deterministic policy engine checks effective authority:
    $$\text{Effective Authority} = \text{Principal Auth} \cap \text{Agent Caps} \cap \text{Delegation Scopes} \cap \text{Target Constraints}$$
  - The gateway rejects the invocation with HTTP 403 `DENY`, creates a `VIOLATED_POLICY` record in FalkorDB, and **never executes the tool**.

### Threat 3: Convergence on Shared Sensitive Assets (Multi-Path Attack)
- **Vector**: A compromised proxy workload and an overprivileged administrator agent session have distinct entry points but converge on the same crown jewel (`cloud-iam-secrets`).
- **Impact**: Containing only one path leaves the asset vulnerable through the alternative path.
- **Runtime Trust Layer Defense**:
  - Query 4 identifies all intermediate nodes and common targets across suspicious identities.
  - Transparent risk ranking scores targets by sensitivity, path multiplicity, and source diversity.
  - The Containment Simulator displays remaining alternative paths so security analysts can enforce multi-point quarantine.

### Threat 4: Telemetry Blind Spots & Sensor Outages
- **Vector**: A sensor stops reporting events due to kernel crash, network partition, or intentional evasion.
- **Impact**: Traditional dashboards display false "green" status, misleading SecOps into assuming safety.
- **Runtime Trust Layer Defense**:
  - Query 9 evaluates telemetry heartbeat ages against a strict threshold (default 600s).
  - Workloads without active events transition to `STALE_TELEMETRY` (confidence `DEGRADED`) or `MISSING_TELEMETRY` (confidence `UNKNOWN`).
  - Missing telemetry is never treated as proof of safety.

### Threat 5: Control Plane Outage (FalkorDB / Gateway Down)
- **Vector**: FalkorDB crashes or network connectivity between MCP gateway and graph database is severed.
- **Impact**: Attackers attempt requests during the window of failure.
- **Runtime Trust Layer Defense**:
  - System enforces **Fail-Closed** security: when authorization cannot be verified in the graph, the gateway returns HTTP 503 `DENY`.
