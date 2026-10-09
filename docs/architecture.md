# Runtime Trust Layer — Architecture Specification

## 1. System Overview

**Runtime Trust Layer** is a graph-native runtime security platform uniting three previously siloed cloud security domains into a single unified control plane:

1. **Workload Trust**: Kubernetes workloads, pods, service accounts, RBAC permissions, and container runtime telemetry.
2. **Agent Trust**: Human principals, autonomous AI agent sessions, delegated authority scopes, and Model Context Protocol (MCP) tool servers.
3. **Runtime Enforcement**: Deterministic boundary enforcement points (MCP Gateway, Kubernetes Network Policies, RBAC constraints), bounded blast-radius traversals, and containment simulations.

```
                           +----------------------------------------+
                           |          Human Principal               |
                           |   (Alice: Compliance / Bob: Admin)     |
                           +-------------------+--------------------+
                                               |
                                     DELEGATES_TO (Scopes, Expiry)
                                               v
+------------------------+        +----------------------------+
|  Kubernetes Workloads  |        |      AI Agent Session      |
|  (Pods, SAs, RBAC)     |        |   (AutoDev / Model Identity)
+-----------+------------+        +-------------+--------------+
            |                                   |
    EMITTED_EVENT (eBPF)                   CAN_INVOKE
            |                                   |
            v                                   v
+--------------------------------------------------------------+
|            FalkorDB Graph Control Plane & Query Layer        |
|  - 10 Versioned Cypher Graph Traversal Algorithms            |
|  - Real-time Blast Radius & Shared Attack Path Traversal     |
|  - Hypothetical Read-Only Containment Simulation             |
+------------------------------+-------------------------------+
                               |
                               v
+--------------------------------------------------------------+
|             Deterministic Boundary Enforcement Points        |
|  - MCP Tool Gateway: Pre-Execution Blocking (HTTP 403 / 428) |
|  - Kubernetes Lab: Dynamic Network Policy Pod Quarantine     |
+--------------------------------------------------------------+
```

---

## 2. Core Subsystems

### A. FalkorDB Graph Layer (`graph/`)
- Canonical graph database storing identities, workloads, runtime events, policies, and evidence.
- High-performance Cypher query execution with parameterized queries, schema versioning, and index optimization.
- **Fail-Closed Resilience**: If FalkorDB becomes unreachable during a protected operation, the system fails closed (HTTP 503 / DENY) rather than allowing unauthorized access.

### B. Controlled MCP / Tool Gateway (`services/agent-gateway/`)
- Sits in front of all AI agent tool executions.
- Validates sessions, human delegators, expiration timestamps, and permissions.
- Evaluates the deterministic policy engine **BEFORE** executing any tool.
- Unauthorized calls are blocked at the boundary and never executed. Evidence is saved to FalkorDB.

### C. Runtime Event Collector (`services/runtime-collector/`)
- Dual-mode architecture:
  - **Live Linux Mode**: Ingests real eBPF telemetry from Cilium Tetragon (`sys_execve`, `sys_openat`, socket connects).
  - **Replay Mode**: Ingests deterministic synthetic streams with explicit provenance markings (`mode: replay_synthetic`).
- Correlates events with Kubernetes pods and workloads using pod names and namespaces.
- Checks for policy violations (e.g. interactive shells `/bin/sh` or `/bin/bash` in production pods).

### D. FastAPI Backend (`apps/api/`)
- Asynchronous Python REST API exposing health, graph traversal, workload/agent inventory, blast-radius queries, containment simulations, and scenario management.

### E. Web Console (`apps/web/`)
- React 19, TypeScript, Vite, and Cytoscape.js security operations interface.
- Dark navy palette with restrained ocean-blue accents and distinct visual styling for configured, inferred, observed, and simulated edges.
