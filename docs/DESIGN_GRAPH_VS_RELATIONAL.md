# Architectural RFC: Graph vs. Relational Data Structures in Trust Analyst

**Author:** @rum  
**Date:** October 10, 2026  
**Status:** Approved & Implemented  
**Target:** Hybrid Architecture Split (FalkorDB + SQLite)

---

## 1. Summary

Use a graph database only where the workload involves relationship traversal. In the initial monolithic prototype of Trust Analyst, job states, follow-up schedules, approval queues, and tool audit logs were stored alongside topological entities in FalkorDB. While this satisfied a maximalist interpretation of graph hackathon rules, engineering merit dictates that plain indexed tables handle operational state significantly better.

This architectural RFC establishes a principled **hybrid architecture**:
- **FalkorDB (The Cognitive Map):** Retains all relationship-intensive reasoning data (the infrastructure and identity entity graph, temporal relationships, provenance/taint chains, and the reasoning chain of `Investigation`, `Hypothesis`, `Evidence`, and `Finding` nodes).
- **SQLite (The Operational Engine):** Houses tabular execution state (approval requests, condition watches, scheduled follow-up tasks, tool-call audit logs, and investigation step checkpoints), with foreign keys referencing FalkorDB node IDs.

Removing FalkorDB genuinely breaks the product: the agent loses its topology map, cannot compute blast radii, cannot evaluate temporal diffs, and cannot trace provenance or convergence. Meanwhile, operational queries execute in $O(\log N)$ indexed time without awkward Cypher map projections.

---

## 2. Where a Graph Earns Its Place

A graph database wins decisively when queries require traversing connections across multiple hops, varying depths, or evolving temporal validity windows:

1. **Reachability and Blast Radius:** Variable-length path traversals (`(p:Pod)-[*1..4]->(sr:SensitiveResource)`) across identities, role bindings, and cloud infrastructure. Computing blast radii in SQL requires recursive CTEs that degrade rapidly in maintainability and performance.
2. **Temporal Path Diffs:** Determining what a workload can reach at time $T_{now}$ that it could not reach at $T_{yesterday}$ by filtering on edge intervals (`valid_from <= $t <= valid_to`).
3. **Convergence Analysis:** Identifying sensitive resources reachable simultaneously from two or more threat vectors (e.g., a compromised pod and an active rogue agent session).
4. **Provenance and Taint Chains:** Tracking untrusted user prompts through text transformations, summarization hand-offs, and tool arguments to detect indirect prompt injections.
5. **Context Assembly:** Assembling a 2-hop topological neighborhood around an alerted entity in a single sub-millisecond query instead of stitching multiple disjoint relational tables.
6. **Similar-Incident Recall & Explainable Findings:** Graph pattern matching that retrieves historical incidents sharing topological neighbors, and links findings directly to cited evidence nodes (`(inv)-[:CITES]->(ev)`).

---

## 3. Where a Graph Adds Friction Without Value

Operational and workflow state exhibits zero traversal behavior. Storing it in a graph adds unnecessary complexity:

| Data Element | Access Pattern | Why Graph is Poor Fit | Optimal Store |
| :--- | :--- | :--- | :--- |
| **Investigation Step State** | Sequential checkpoint buffer | Never traversed; overwritten or appended sequentially | SQLite / Postgres Table |
| **Scheduled Follow-up Tasks** | Range scan on `(status, due_at)` | Cypher requires filtering graph nodes without native B-Tree time index | SQLite Table indexed on `(status, due_at)` |
| **Active Watches** | Range scan on `(status, expires_at)` | Periodic poll by worker loop; zero multi-hop relationships | SQLite Table indexed on `(status, expires_at)` |
| **Approvals Queue** | Queue lookup on `(action, target_id, status)` | Status machine transitions (`pending` $\to$ `approved` $\to$ `rejected`) | SQLite Table indexed on `(status, created_at)` |
| **Tool-Call Audit Log** | Append-only write stream | Write-heavy; queried by timestamp or caller ID | Append-only Log Table / SQLite |
| **Raw Telemetry Events** | High-volume time-series append | Millions of socket/process events | Columnar Store / JSONL log |
| **Engineering Documents** | Keyword & semantic text search | Inverted index required | Full-Text Search / Vector Index |
| **Behavioral Baselines** | Key lookup by entity ID | Point lookups on normal distributions | Key-Value / Time-Series Store |

At lab scale (hundreds of nodes), in-memory libraries such as NetworkX can also evaluate static graphs. A persistent graph database like FalkorDB earns its place on dynamic persistence, low-latency graph traversals, Cypher expressiveness, and enterprise scale. A production implementation is naturally polyglot: a relational or columnar engine for operational execution state, and a graph database for relational topological reasoning.

---

## 4. The Hybrid Architecture Design

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                      Trust Analyst                      │
                     │                 Autonomous Security Agent               │
                     └──────────┬───────────────────────────────────┬──────────┘
                                │                                   │
               Operational State│                                   │Relationship
                  Lookups & CRUD│                                   │Reasoning Traversals
                                ▼                                   ▼
             ┌───────────────────────────────────┐ ┌───────────────────────────────────┐
             │       SQLite Operational Store    │ │       FalkorDB Cognitive Graph    │
             ├───────────────────────────────────┤ ├───────────────────────────────────┤
             │ • approvals                       │ │ • Entity Topology (Workload, Pod, │
             │ • watches                         │ │   ServiceAccount, Principal, SR)  │
             │ • scheduled_tasks                 │ │ • Temporal Edges (valid_from/to)  │
             │ • tool_calls (audit log)          │ │ • Investigation, Hypothesis,      │
             │ • step_states (checkpoints)       │ │   Evidence, Finding nodes         │
             │                                   │ │ • Provenance & Taint Chains       │
             │ Foreign Keys:                     │ │ • Blast Radius & Convergence      │
             │   target_id, investigation_id     │ │ • Similar-Incident Recall         │
             └───────────────────────────────────┘ └───────────────────────────────────┘
```

### Foreign Key Linkage
Rows in SQLite maintain referential integrity with FalkorDB entities via immutable string identifiers:
- `approvals.target_id` $\to$ FalkorDB node `Pod.id` or `AgentSession.id`
- `approvals.investigation_id` $\to$ FalkorDB node `Investigation.id`
- `watches.investigation_id` $\to$ FalkorDB node `Investigation.id`
- `scheduled_tasks.investigation_id` $\to$ FalkorDB node `Investigation.id`
- `tool_calls.investigation_id` $\to$ FalkorDB node `Investigation.id`
- `tool_calls.evidence_ids` $\to$ JSON list of FalkorDB `Evidence.id`

---

## 5. Load-Bearing Verification: Why the Graph is Indispensable

A key hackathon criteria is ensuring the graph database is **load-bearing**, not cosmetic decoration.

If FalkorDB is severed or removed from Trust Analyst:
1. **The Policy Gateway Fails Closed:** Cannot verify agent delegation validity windows or session scopes in the graph topology.
2. **The Analyst Loses Spatial Context:** Cannot compute blast radius, cannot discover upstream service accounts, and cannot locate downstream crown jewels.
3. **Temporal Diff Reasoning Collapses:** Cannot distinguish between a historical authorized maintenance window and an unauthorized runtime privilege escalation.
4. **Evidence-Cited Verifier Fails:** Cannot verify claims against graph evidence nodes (`(inv)-[:CITES]->(ev)`), preventing any verdict from passing the verifier gate.
5. **Multi-Vector Escalation Fails:** The stubborn convergence escalation in Pair 7 cannot find parallel rogue paths without multi-hop graph traversal.

Thus, moving operational execution state to SQLite sharpens the architectural boundary without diminishing FalkorDB's load-bearing primacy.

---

## 6. Implementation Summary

1. **`backend/app/config.py`**: Added `SQLITE_DB_PATH: str = "trust_operational.db"`.
2. **`backend/app/db/sqlite.py`**: Created thread-safe SQLite engine with WAL mode, foreign keys, schema migrations, and CRUD helpers for approvals, watches, tasks, tool calls, and step states.
3. **`backend/app/tools/control_tools.py`**: Persists watches, tasks, and approvals to SQLite with dual-write to FalkorDB for visual graph inspection.
4. **`backend/app/agent/gateway.py`**: Validates approvals and checks tool-call budgets against SQLite in $O(1)$ indexed lookups.
5. **`backend/app/agent/watcher.py` & `backend/app/agent/scheduler.py`**: Poll active watches and due tasks from SQLite indexed tables while evaluating graph patterns against FalkorDB.
6. **`backend/app/agent/analyst.py` & `backend/app/agent/runner.py`**: Stores step checkpoints in SQLite, updating live investigation state seamlessly.
7. **`backend/app/main.py`**: Serves `/api/approvals`, `/api/watches`, and `/api/tasks` directly from SQLite.
8. **`backend/tests/test_sqlite_operational.py`**: Dedicated 5-suite test harness validating the SQLite operational store.
