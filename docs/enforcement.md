# Runtime Enforcement Architecture — Runtime Trust Layer

## 1. Enforcement Philosophy

**Never claim an operation was blocked unless the enforcement point actually rejected it.**
A post-execution log or graph visualization alert does **not** count as enforcement. Runtime Trust Layer places physical enforcement boundaries directly in the execution path.

---

## 2. Enforcement Boundaries

### Boundary 1: Controlled MCP / Tool Gateway
- **Position**: Sits in front of all Model Context Protocol (MCP) servers and tools.
- **Trigger**: An autonomous AI agent requests a tool call (e.g. `POST /api/gateway/invoke`).
- **Enforcement Action**:
  - The gateway evaluates the session, principal permissions, agent capabilities, and delegation scopes **BEFORE** delegating to the tool.
  - If any constraint fails:
    - The request is immediately rejected with HTTP 403 `DENY` or HTTP 428 `REQUIRE_APPROVAL`.
    - **The tool handler is never invoked.**
    - A `PolicyDecision` and `RuntimeEvent` are appended to FalkorDB.
  - Only if `ALLOW`: The tool is invoked, and an `OBSERVED_ACCESS` edge is created with execution output hashes.

### Boundary 2: Kubernetes Network Policy Quarantine
- **Position**: Kubernetes CNI / iptables packet filter in the cluster.
- **Trigger**: SecOps approves containment of a compromised pod (e.g. `pod-checkout-7f89b`).
- **Enforcement Action**:
  - Applies a default-deny `NetworkPolicy` (`quarantine-checkout-isolate`) selecting the compromised pod's labels.
  - Empty ingress and egress blocks all TCP/UDP traffic to and from the pod.
  - Cluster API confirms policy application before transitioning status to `APPLIED`.
  - Connectivity probe verifies traffic rejection before marking `VERIFIED`.

---

## 3. Containment Lifecycle States

Every containment action progresses through a verifiable state machine:

```
[ SIMULATED ]
      |
      v (SecOps Approves Action)
[ REQUESTED ]
      |
      v (Target System Applies Policy)
 [ APPLIED ]
      |
      v (Active Check / Boundary Probe Confirms)
[ VERIFIED ]
```

- **`SIMULATED`**: Traversal performed on a hypothetical graph projection without modifying cluster resources or token stores.
- **`REQUESTED`**: API call or admission payload submitted to cluster controller.
- **`APPLIED`**: Controller confirms object creation or token invalidation.
- **`VERIFIED`**: Post-containment probe validates that network traffic or tool calls are actively rejected.
