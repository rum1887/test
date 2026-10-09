# Unified Graph Data Model — Runtime Trust Layer

## 1. Schema Overview

The FalkorDB graph schema captures the relationship between cloud infrastructure, Kubernetes entities, AI agents, identities, permissions, runtime events, policies, and containment actions.

Schema version: `1.0.0`

---

## 2. Canonical Node Labels

| Node Label | Key Properties | Description |
| :--- | :--- | :--- |
| **`Principal`** | `id`, `name`, `email`, `role`, `auth_provider`, `status` | Human identity authorizing agent sessions |
| **`Agent`** | `id`, `name`, `model`, `vendor`, `capabilities`, `max_autonomy_level` | AI autonomous agent definition |
| **`AgentSession`** | `id`, `principal_id`, `agent_id`, `created_at`, `expires_at`, `status` | Ephemeral runtime delegation session |
| **`Delegation`** | `id`, `scopes`, `constraints`, `issued_at`, `expires_at`, `status` | Explicit grant of authority from principal to agent |
| **`Workload`** | `id`, `name`, `namespace`, `kind`, `cluster`, `replicas`, `status` | Kubernetes Deployment, StatefulSet, DaemonSet |
| **`Pod`** | `id`, `name`, `namespace`, `node_name`, `ip`, `status`, `created_at` | Kubernetes pod runtime instance |
| **`Container`** | `id`, `name`, `image`, `privileged`, `read_only_root_fs` | Container running inside a Pod |
| **`ServiceAccount`**| `id`, `name`, `namespace`, `cluster` | Kubernetes workload identity |
| **`Permission`** | `id`, `action`, `resource_pattern`, `effect`, `description` | RBAC or tool authorization grant |
| **`MCPServer`** | `id`, `name`, `endpoint`, `protocol`, `transport`, `status` | Model Context Protocol server |
| **`Tool`** | `id`, `name`, `description`, `required_permissions`, `risk_level`, `is_destructive` | Tool callable by an AI agent |
| **`SensitiveResource`** | `id`, `name`, `type`, `sensitivity_level`, `encryption_status` | Crown jewel (KeyVault, DB, KMS) |
| **`NetworkEndpoint`**| `id`, `cidr_or_dns`, `port`, `protocol`, `direction` | Egress network target |
| **`RuntimeEvent`** | `id`, `event_type`, `source`, `mode`, `timestamp`, `severity`, `command_line` | Tetragon eBPF or replay telemetry |
| **`Policy`** | `id`, `name`, `version`, `effect`, `enforcement_point`, `description` | Deterministic security rule |
| **`EnforcementPoint`** | `id`, `name`, `type`, `status`, `mode`, `location` | Physical enforcement boundary |
| **`PolicyDecision`** | `id`, `decision_id`, `decision`, `rationale`, `evaluated_rules`, `timestamp` | Recorded authorization decision |
| **`ContainmentAction`**| `id`, `target_id`, `action_type`, `status`, `enforcement_mechanism` | Isolation or revocation operation |

---

## 3. Relationship Types & Semantics

| Relationship Type | Source &rarr; Target | Semantics & Edge Properties |
| :--- | :--- | :--- |
| `OWNS_SESSION` | `Principal` &rarr; `AgentSession` | Identifies human principal who authenticated session. |
| `ACTS_ON_BEHALF_OF` | `AgentSession` &rarr; `Principal` | Proves session operates under user's delegated identity. |
| `DELEGATES_TO` | `Principal` &rarr; `Delegation` &rarr; `Agent` | Attaches explicit scopes, constraints, and expiration. |
| `CONTAINS` | `Workload` &rarr; `Pod` &rarr; `Container` | Container runtime hierarchy. |
| `RUNS_AS` | `Pod` &rarr; `ServiceAccount` | Workload Kubernetes identity. |
| `HAS_PERMISSION` | `ServiceAccount` or `Principal` &rarr; `Permission` | Configured RBAC grant. |
| `CAN_ACCESS` | `Permission` or `Tool` &rarr; `SensitiveResource` | Derived or configured capability. Carries `evidence_type: 'configured'`. |
| `CAN_REACH` | `Pod` &rarr; `NetworkEndpoint` | Inferred network connectivity. Carries `evidence_type: 'inferred'`. |
| `CAN_INVOKE` | `AgentSession` &rarr; `Tool` | Permitted tool invocation based on active delegation. |
| `OBSERVED_ACCESS` | `Pod` or `AgentSession` &rarr; `Target` | Confirmed access observed in telemetry. Carries `evidence_type: 'observed'`. |
| `EMITTED_EVENT` | `Pod` or `AgentSession` &rarr; `RuntimeEvent` | Links telemetry event to emitting workload or session. |
| `VIOLATED_POLICY` | `RuntimeEvent` or `PolicyDecision` &rarr; `Policy` | Direct correlation of violation to security policy. |
| `ENFORCED_AT` | `Policy` or `PolicyDecision` &rarr; `EnforcementPoint` | Boundary where decision was enforced. |

---

## 4. Evidence Classification

Edges carry an `evidence_type` property to prevent confusing configuration with confirmed compromise:
- **`configured`**: Established through explicit Kubernetes manifests, RBAC roles, or MCP catalog configurations.
- **`inferred`**: Established via network reachability models (e.g. Calico default-allow, DNS routes). Does not represent proof of access.
- **`observed`**: Established via cryptographically hashed runtime telemetry (Tetragon kprobe execve or confirmed socket connect).
- **`simulated`**: Used only during read-only containment simulations.
