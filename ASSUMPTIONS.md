# Assumptions and Design Decisions

This document records all explicit assumptions, design choices, and library adaptations made during the development of **Trust Analyst**.

---

### 1. Hybrid Architecture: FalkorDB (Cognitive Reasoning) & SQLite (Operational State)
- **Assumption:** In accordance with the architectural RFC (*"Graph vs. other data structures: Trust Analyst design"* by @rum), a graph database earns its place specifically where the workload involves relationship traversal (reachability, blast radius, temporal diffs, multi-threat convergence, provenance/taint chains, similar-incident recall, and evidence-linked findings). Operational execution state (approvals queues, active watches, scheduled tasks, tool-call audit logs, and investigation step checkpoints) exhibits no multi-hop traversal and is better served by relational indexed tables.
- **Decision:** We implement a clean hybrid architecture:
  - **FalkorDB (`trust` graph):** Houses all security topology entities, temporal edge intervals, and reasoning nodes (`Investigation`, `Hypothesis`, `Evidence`, `Finding`). If FalkorDB is removed, the analyst loses its cognitive map and all reasoning fails closed.
  - **SQLite (`trust_operational.db`):** Houses operational execution state with foreign keys pointing to FalkorDB node IDs.
  - **Dual-write projection:** For UI graph exploration and backward compatibility with raw Cypher queries, operational tools maintain dual-write projections into FalkorDB while SQLite serves as the high-performance indexed operational engine.

### 2. Time and Simulated Clock
- **Assumption:** All temporal attributes (`valid_from`, `valid_to`, `at`, `timestamp`) use simulated epoch seconds from `sim/clock.py`, not real wall-clock time.
- **Decision:** The simulated clock starts at a fixed baseline epoch (e.g. `1700000000`). Advancing the clock advances watches, scheduled tasks, and telemetry windows deterministically.

### 3. Model & LLM Layer
- **Assumption:** The prompt specifies `claude-sonnet-5-5` as the default model string, but Anthropic API currently provides `claude-3-5-sonnet-20241022` or `claude-3-7-sonnet-20250219`.
- **Decision:** We default `ANTHROPIC_MODEL` to `claude-3-5-sonnet-20241022` (aliased as `claude-sonnet-5-5` if configured). All demo and eval runs run completely offline using the deterministic record/replay cache, so an Anthropic API key is optional for reproduction.

### 4. Telemetry and Raw Event Log
- **Assumption:** Raw events are not stored as individual nodes in FalkorDB (which would cause graph bloat), but are aggregated into `EventSummary` nodes keyed by `(pod_id, kind, signature)`.
- **Decision:** Detailed raw events are written to a synthetic JSONL log file accessed strictly via `query_events` and `process_tree` tools.

### 5. Quarantined Reader
- **Assumption:** Planner models are vulnerable to indirect prompt injection embedded in document bodies or process command-line arguments.
- **Decision:** `search_documents` returns metadata and titles only; `read_untrusted` invokes a tool-less, isolated extraction model returning strict Pydantic schemas and an explicit `contains_instructions_to_ai` boolean flag.

### 6. Containment and Human Approval Gate
- **Assumption:** Destructive actions (`apply_isolation`, `revoke_session`) must never execute without explicit human approval.
- **Decision:** The tool gateway intercepts action requests with `requires_approval=True` and denies them unless an `ApprovalRequest` node with `status: 'approved'` exists for that exact action and target.
