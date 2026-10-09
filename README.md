# Runtime Trust Layer
### Graph-Native Runtime Security Platform for AI Agents & Kubernetes

[![CI](https://github.com/red-teaming/trustme/actions/workflows/ci.yml/badge.svg)](https://github.com/red-teaming/trustme/actions)
[![FalkorDB](https://img.shields.io/badge/Graph_Database-FalkorDB_v4-blue.svg)](https://www.falkordb.com/)
[![Tetragon](https://img.shields.io/badge/Runtime_Sensor-Cilium_Tetragon_eBPF-brightgreen.svg)](https://tetragon.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Runtime Trust Layer** is a graph-native security control plane connecting **Workload Trust** (Kubernetes, RBAC, eBPF), **Agent Trust** (human principals, AI agent sessions, delegated authority, MCP servers), and **Runtime Enforcement** (deterministic policy blocking and hypothetical containment simulation) into a single unified platform powered by **FalkorDB**.

---

## 1. Executive Summary & Product Vision

Modern cloud applications increasingly delegate sensitive tasks to autonomous AI agents running inside Kubernetes clusters. However:
- **Static permissions** show only what a workload or agent *may* be authorized to do.
- **Runtime telemetry** shows what actions were *observed* at the kernel level.
- **Identity & delegation** explain *on whose behalf* an action was performed.

Until now, these signals lived in three disconnected silos. **Runtime Trust Layer** combines them in **FalkorDB** to answer the critical questions:
- *Who initiated this action, and which identity authorized it?*
- *Is the AI agent acting within the human user's explicitly delegated authority?*
- *Which sensitive crown jewels could the compromised workload or agent reach?*
- *Which suspicious actions were observed in real eBPF kernel telemetry?*
- *What is the plausible blast radius, and which containment action eliminates exposure with minimum service disruption?*
- *Was the unauthorized operation actually blocked before execution at the physical boundary?*

**Hackathon Tracks**:
- **Primary**: *Agents That Act on Connected Data* (Autonomous agent delegation, MCP gateways, real-time graph path traversal).
- **Secondary**: *Agent Memory and Coordination* (Graph-backed incident memory, correlated policy violations, auditable containment).

---

## 2. Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                 HUMAN PRINCIPALS                                  |
|            Alice Henderson (Compliance)       Bob Martinez (DevOps Admin)         |
+----------------------------------------+------------------------------------------+
                                         |
                               DELEGATES_TO (Scopes, Expiry)
                                         v
+------------------------+      +----------------------------+
|  Kubernetes Workloads  |      |      AI Agent Session      |
|  - checkout-service    |      |   - session-alice-dev-01   |
|  - frontend-proxy      |      |   - session-bob-02         |
|  - order-processor     |      |   Agent: AutoDev-Agent     |
+-----------+------------+      +-------------+--------------+
            |                                 |
    EMITTED_EVENT (eBPF)                 CAN_INVOKE
            |                                 |
            v                                 v
+-----------------------------------------------------------------------------------+
|                        FALKORDB GRAPH CONTROL PLANE                                |
|  - Bounded Workload Blast Radius Traversal                                        |
|  - Delegated Authority & Expiry Evaluation                                        |
|  - Multi-Source Converged Attack Paths                                            |
|  - Read-Only Hypothetical Containment Simulations                                 |
|  - Automated Graph Integrity Validations                                          |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       DETERMINISTIC ENFORCEMENT POINTS                            |
|                                                                                   |
|   1. MCP Tool Gateway (`ep-mcp-gateway-01`)                                       |
|      - Pre-Execution Evaluation: BLOCKS unauthorized calls (HTTP 403 / 428)       |
|      - Prevents execution BEFORE tool handler runs. Records proof in FalkorDB.    |
|                                                                                   |
|   2. Kubernetes Lab Quarantine Controller (`ep-k8s-admission-01`)                 |
|      - Applies Default-Deny Network Policies isolating compromised pods           |
|      - Confirms applied status before transitioning: Applied -> Verified          |
+-----------------------------------------------------------------------------------+
```

---

## 3. Unified Graph Data Model

The FalkorDB graph schema captures the relationships between infrastructure, identity, runtime events, and enforcement:

```
(Principal)-[:OWNS_SESSION]->(AgentSession)-[:ACTS_ON_BEHALF_OF]->(Principal)
     |                             |
     +-[:DELEGATES_TO]->(Delegation)-[:DELEGATES_TO]->(Agent)
                                   |
                             CAN_INVOKE
                                   v
(MCPServer)-[:CONTAINS]->(Tool)-[:CAN_ACCESS]->(SensitiveResource)
                                                      ^
                                                      | CAN_ACCESS
(Workload)-[:CONTAINS]->(Pod)-[:RUNS_AS]->(ServiceAccount)-[:HAS_PERMISSION]->(Permission)
                          |
                  EMITTED_EVENT
                          v
(RuntimeEvent: eBPF)-[:VIOLATED_POLICY]->(Policy)-[:ENFORCED_AT]->(EnforcementPoint)
```

### Node Labels & Edge Types

| Node Label | Key Properties | Relationship | Semantics |
| :--- | :--- | :--- | :--- |
| **`Principal`** | `id`, `name`, `email`, `role`, `status` | `OWNS_SESSION` | Authenticated human initiating agent sessions |
| **`Agent`** | `id`, `name`, `model`, `capabilities` | `DELEGATES_TO` | Autonomous agent definition |
| **`AgentSession`** | `id`, `status`, `expires_at`, `audience` | `CAN_INVOKE` | Ephemeral execution session |
| **`Delegation`** | `id`, `scopes`, `constraints`, `expires_at`| `ACTS_ON_BEHALF_OF`| Explicit user-authorized scope bounds |
| **`Workload`** | `id`, `name`, `namespace`, `kind`, `replicas` | `CONTAINS` | Kubernetes Deployment / StatefulSet |
| **`Pod`** | `id`, `name`, `node_name`, `ip`, `status` | `RUNS_AS` | Running pod correlated to eBPF events |
| **`ServiceAccount`**| `id`, `name`, `namespace`, `cluster` | `HAS_PERMISSION` | Workload identity |
| **`Tool`** | `id`, `name`, `risk_level`, `is_destructive`| `CAN_ACCESS` | MCP tool capability |
| **`SensitiveResource`**| `id`, `name`, `sensitivity_level` | `PROTECTED_BY` | High-value database, vault, or key |
| **`RuntimeEvent`** | `id`, `event_type`, `mode`, `command_line` | `EMITTED_EVENT` | Tetragon eBPF kernel telemetry |
| **`Policy`** | `id`, `name`, `effect`, `enforcement_point`| `ENFORCED_AT` | Deterministic security rule |
| **`PolicyDecision`** | `id`, `decision`, `rationale`, `timestamp` | `VIOLATED_POLICY` | Auditable decision record |

---

## 4. Real FalkorDB Cypher Queries & Security Algorithms

All queries execute directly against FalkorDB with explicit parameterized inputs:

### Query 1: Workload Blast Radius Traversal
```cypher
MATCH (start)
WHERE (start:Workload OR start:Pod) AND start.id = $id
MATCH path = (start)-[:CONTAINS|RUNS_AS|USES_CREDENTIAL|HAS_PERMISSION|CAN_ACCESS|CAN_REACH|OBSERVED_ACCESS*1..5]->(target)
WHERE target:SensitiveResource OR target:KubernetesResource OR target:NetworkEndpoint
RETURN
    [n in nodes(path) | {id: n.id, label: labels(n)[0], name: coalesce(n.name, n.id)}] AS path_nodes,
    [rel in relationships(path) | {type: type(rel), evidence_type: rel.evidence_type}] AS path_edges,
    target.name AS target_name,
    target.sensitivity_level AS target_sensitivity,
    length(path) AS path_length
LIMIT 50
```
*How it works*: Traverses bounded paths from a pod through service accounts, permissions, and egress endpoints to discover crown jewels. Distinguishes `configured`, `inferred`, and `observed` edges.

---

### Query 2: Agent Delegation-Chain Analysis
```cypher
MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession {id: $session_id})
OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
WHERE d.session_id = s.id OR d.session_id IS NULL
OPTIONAL MATCH (s)-[:CAN_INVOKE]->(t:Tool)
OPTIONAL MATCH (m:MCPServer)-[:CONTAINS]->(t)
OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
RETURN
    p.name AS principal_name,
    s.status AS session_status,
    s.expires_at AS session_expires_at,
    a.name AS agent_name,
    d.scopes AS delegation_scopes,
    t.name AS tool_name,
    t.is_destructive AS tool_destructive,
    sr.name AS downstream_target
```
*How it works*: Traces `Human Principal -> Agent Session -> Agent -> Delegation -> MCP Tool -> Downstream Resource`. Detects expired sessions, missing delegations, or requested tools exceeding granted scopes.

---

### Query 3: Effective Authority Comparison
The policy engine computes:
$$\text{Effective Authority} = \text{Principal Auth} \cap \text{Agent Capabilities} \cap \text{Delegation Scopes} \cap \text{Target Constraints}$$
- **Principal Authorization**: Human user must possess RBAC permissions for the underlying action.
- **Agent Capability**: Agent model manifest must support the tool.
- **Delegation Scope**: Tool must be within the active session delegation scopes (`*` or explicit tool name).
- **Destructive Approval**: High-risk or destructive tools (`is_destructive: true`) require multi-party human confirmation (`REQUIRE_APPROVAL`).

---

### Query 4: Shared Attack Paths Convergence
```cypher
MATCH (src)
WHERE src.id IN $sources
MATCH path = (src)-[:CONTAINS|RUNS_AS|CAN_ACCESS|CAN_INVOKE|CAN_REACH|ACTS_ON_BEHALF_OF|HAS_PERMISSION*1..5]->(target:SensitiveResource)
RETURN
    src.id AS source_id,
    target.name AS target_name,
    target.sensitivity_level AS sensitivity,
    [n in nodes(path) | n.id] AS path_nodes,
    length(path) AS path_len
```
*How it works*: Detects when distinct threat sources (e.g. compromised pod and rogue agent session) converge on the same sensitive resource. Scores targets using transparent formula:
$$\text{Risk Score} = \text{Sensitivity Weight} \times (1.0 + 0.5 \times (\text{Sources} - 1)) \times (1.0 + 0.1 \times \text{Paths})$$

---

### Query 5: Hypothetical Containment Simulation (Zero Graph Mutation)
```cypher
MATCH (start {id: $sid})
MATCH path = (start)-[:CONTAINS|RUNS_AS|USES_CREDENTIAL|HAS_PERMISSION|CAN_ACCESS|CAN_REACH*1..5]->(target:SensitiveResource)
RETURN
    target.name AS target_name,
    [n in nodes(path) | n.id] AS node_ids,
    length(path) AS path_len
```
*How it works*: Computes reachable targets before and after excluding a candidate node (e.g. `pod-checkout-7f89b`). Calculates **Exposure Reduction %**, identifies eliminated targets, and alerts if alternative paths remain—**without mutating the production graph**.

---

## 5. Live Linux eBPF vs. Replay Mode

To ensure full transparency and avoid misleading claims:

| Feature | Live Linux Mode (`live_ebpf`) | Replay Mode (`replay_synthetic`) |
| :--- | :--- | :--- |
| **Environment** | Linux kernel &ge; 5.4, Docker/Kind, `CAP_SYS_ADMIN` | Any OS, Mac, Windows, Cloudflare, Render |
| **Telemetry Driver** | Cilium Tetragon (`sys_execve`, `sys_openat`, kprobes) | Deterministic synthetic generator |
| **Provenance Tag** | `mode: "live_ebpf"`, `source: "tetragon_ebpf"` | `mode: "replay_synthetic"`, `source: "replay_simulator"` |
| **Stale Detection** | Degrades confidence to `DEGRADED` if heartbeat &gt; 10m | Heartbeats refreshed deterministically |
| **Dashboard Badge** | Green glowing **LIVE eBPF** badge | Amber **REPLAY MODE** badge |

---

## 6. Demonstration Scenarios (Scenarios A through E)

The system includes 5 built-in, reproducible scenarios with 1-click reset:

- **Scenario A: Compromised Kubernetes Workload**
  - Worker pod `checkout-service-7f89b` runs unexpected `/bin/sh` and curls AWS metadata IP (`169.254.169.254`).
  - Tetragon captures event; correlated in FalkorDB to service account with overprivileged secret permissions.
  - Blast Radius reveals paths to `customer-vault-secrets`. Simulation proves pod isolation cuts exposure by 100%.

- **Scenario B: AI-Agent Delegation Violation**
  - User Alice (Compliance Officer, read-only scopes `["audit_read", "report_generate"]`) asks Agent AutoDev to execute `db_drop_table`.
  - MCP Tool Gateway evaluates policy **BEFORE** execution: rejected with HTTP 403 `DENY`.
  - Tool handler is **never invoked**. Decision recorded in FalkorDB audit log.

- **Scenario C: Shared Attack Path**
  - Suspicious workload `frontend-proxy` and compromised session `session-bob-compromised-02` both converge on `cloud-iam-secrets`.
  - Query 4 identifies the common target and flags that isolating only the workload leaves the agent path exposed.

- **Scenario D: Stale & Missing Telemetry Detection**
  - Workload `order-processor` telemetry stops (&gt; 20m ago); workload `analytics-worker` has zero events.
  - System flags `STALE_TELEMETRY` (confidence `DEGRADED`) and `MISSING_TELEMETRY` (confidence `UNKNOWN`).

- **Scenario E: Control Plane Outage & Fail-Closed Behavior**
  - When FalkorDB is unreachable, protected tool invocations fail closed with HTTP 503 `DENY`. System never permits unverified access.

---

## 7. Feature Implementation Status

| Capability | Status | Implementation Details |
| :--- | :--- | :--- |
| FalkorDB Unified Graph Model | **Implemented** | 20 node types, 17 edge types, indexes, schema v1.0.0 (`graph/schema/`) |
| 10 Real Cypher Security Queries | **Implemented** | Tested against live FalkorDB instance (`graph/queries/library.py`) |
| Pre-Execution MCP Tool Gateway | **Implemented** | Blocks unauthorized calls before execution (`services/agent-gateway/`) |
| Deterministic Policy Engine | **Implemented** | Evaluates effective authority & destructive approval (`policies/engine.py`) |
| Cilium Tetragon eBPF Normalizer | **Implemented** | Normalizes `sys_execve` & kprobe JSON events (`services/runtime-collector/`) |
| Deterministic Replay Mode | **Implemented** | Explicitly labeled synthetic generator for hosted demos |
| Kind Local Kubernetes Lab | **Implemented** | Manifests for workloads, RBAC, network policies, Tetragon policy |
| React & Cytoscape.js Web Console | **Implemented** | Interactive graph canvas, search, filters, drawer (`apps/web/`) |
| Before/After Containment Simulator| **Implemented** | Zero-mutation exposure reduction calculation (`POST /api/containment/simulate`)|
| Automated Test Suite | **Implemented** | 32/32 tests passing across unit, integration, and e2e (`tests/`) |
| CI Pipeline & Smoke Test | **Implemented** | GitHub Actions workflow + standalone `scripts/smoke_test.py` |

---

## 8. Quickstart & Installation

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/red-teaming/trustme.git
cd trustme

# Copy environment template
cp .env.example .env

# Start FalkorDB, API backend, and Web console
docker compose -f deploy/docker/docker-compose.yml up --build
```
Access the dashboard at `http://localhost:5173` and API docs at `http://localhost:8000/docs`.

---

### Option 2: Local Development Setup

#### 1. Start FalkorDB in Docker
```bash
docker run -d --name trust-falkordb -p 6379:6379 falkordb/falkordb:latest
```

#### 2. Set Up Python Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run deployment smoke test
python scripts/smoke_test.py

# Start FastAPI backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Set Up React Dashboard
```bash
cd apps/web
npm install
npm run dev
```

---

## 9. Running Tests

```bash
# Run the complete test suite (Unit, Integration against real FalkorDB, E2E)
pytest tests/ -v

# Run the deployment smoke test
python scripts/smoke_test.py

# Run frontend build check
cd apps/web && npm run build
```

---

## 10. Demo Script (Walkthrough)

1. Open Web Console at `http://localhost:5173`.
2. Observe the **Overview Dashboard**: FalkorDB status is `ONLINE`, Sensor reports `REPLAY MODE` (or `LIVE eBPF` on Linux).
3. Click **Trust Graph**: Explore the Cytoscape canvas. Notice that sensitive resources (`customer-vault-secrets`, `payment-records-db`) glow red.
4. Click **Workload Explorer**: Select `checkout-service`. Observe the overprivileged `secrets:get` RBAC permission. Click **Blast Radius** to trace the 8 plausible paths.
5. Click **Agent Trust**:
   - In the live test console, select session `Alice Henderson` and tool `db_drop_table`.
   - Click **Invoke via MCP Gateway**.
   - Notice the instant **HTTP 403 DENY**: The call is blocked *before* execution. The rationale cites that Alice's scopes are restricted to `[audit_read, report_generate]`.
6. Click **Policy Engine**: View the audit entry generated by the rejected call, complete with rule evaluations.
7. Click **Containment**:
   - Select threat source `checkout-service`.
   - Click **Simulate** on candidate `ISOLATE_POD`. Notice **Net Exposure Reduction: -100%**.
   - Click **Apply Containment**: State transitions to `APPLIED` and confirms `VERIFIED`.
8. Click **Reset** in the top navbar to return to the canonical baseline instantly.

---

## 11. Known Limitations & Trade-Offs

1. **eBPF Privileges**: Live eBPF kernel tracing requires a Linux host kernel and root/`CAP_SYS_ADMIN` privileges. On macOS development machines and serverless static hosting tiers, the platform falls back to **Replay Mode** with clear provenance labels.
2. **Cold Starts on Free Tiers**: On free hosting tiers like Render, the backend service may sleep after 15 minutes of inactivity; allow ~30 seconds for initial wakeup.
3. **FalkorDB Persistence**: In local Docker Compose, data persists via `falkordb_data` volume. In ephemeral test environments, running `reset` re-seeds the canonical state in &lt;1 second.

---

## 12. AI-Assistance Disclosure

In accordance with hackathon rules, this project utilized agentic pairing with Google DeepMind's Antigravity system for architectural prototyping, Cypher traversal optimization, and React/Cytoscape interface construction. All authorization rules, graph algorithms, policy evaluations, and boundary enforcement mechanisms were verified through real integration tests.

---

## 13. License

MIT License. See [LICENSE](LICENSE) for details.
