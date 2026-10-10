# Plan: Trust Analyst (Milestones M0 - M9)

This document tracks the end-to-end execution of Trust Analyst for Graph Hacks: Context for AI Agents (WeMakeDevs x FalkorDB).

---

## Milestones Checklist

- [x] **M0: Skeleton**
  - [x] Repository layout established (`backend/app/`, `backend/tests/`, `scenarios/`, `web/`, `docs/`)
  - [x] `docker-compose.yml` with FalkorDB, API, Worker, Web
  - [x] `Makefile` with targets: `up`, `seed`, `demo`, `test`, `eval`, `lint`
  - [x] FastAPI app with `/api/health` checking FalkorDB connectivity
  - [x] CI configuration for lint + tests
  - [x] *Acceptance Gate:* `GET /api/health` reports DB online.

- [ ] **M1: Graph + Schema + Queries**
  - [ ] Graph connection client (`backend/app/graph/client.py`) with parameterized Cypher binding
  - [ ] Schema, node labels, index definitions (`backend/app/graph/schema.py`)
  - [ ] Temporal helpers (`backend/app/graph/temporal.py`) for `valid_from`, `valid_to`, `$at` queries
  - [ ] Core named Cypher queries in `backend/app/graph/queries.py`:
    - `entity_context`
    - `blast_radius`
    - `path_diff`
    - `delegation_chain`
    - `find_convergence`
    - `simulate_containment`
    - `recall_similar`
    - `centrality_rank`
  - [ ] Unit tests for all queries against live FalkorDB container
  - [ ] Query doc generator script (`scripts/gen_query_docs.py`)
  - [ ] *Acceptance Gate:* Query tests pass cleanly against FalkorDB.

- [ ] **M2: Sim World + Clock + Telemetry**
  - [ ] Simulated clock (`backend/app/sim/clock.py`): `now()`, `advance(seconds)`
  - [ ] Deterministic world seeder (`backend/app/sim/world.py`): ~6 workloads, ~14 pods, service accounts, permissions, ~5 sensitive resources, ~12 endpoints, 4 principals, 2 agents, 4 sessions/delegations, MCP server with ~8 tools, ~40 documents, ~200 filler nodes
  - [ ] Telemetry generator & aggregator (`backend/app/sim/telemetry.py`): Tetragon-like normalized events aggregated into `EventSummary` nodes; raw events in JSONL log; reaction to isolation
  - [ ] Determinism test: same RNG seed produces identical graph hash
  - [ ] *Acceptance Gate:* World seed determinism test passes; telemetry aggregates into EventSummary nodes.

- [ ] **M3: Scenarios & Injection Variants**
  - [ ] Scenario spec YAML parser & Pydantic validator (`backend/app/sim/scenarios.py`)
  - [ ] 7 matched pairs (14 YAML scenarios) under `scenarios/`:
    1. Shell + metadata endpoint (benign vs malicious)
    2. New RoleBinding grants secrets:get (benign vs malicious)
    3. Agent session invokes destructive tool (benign vs malicious)
    4. Dormant broad permission (benign vs malicious)
    5. New outbound endpoint (benign vs malicious)
    6. Zombie delegation (benign vs malicious)
    7. Convergence + stubborn containment (benign vs malicious)
  - [ ] `inject: true` variants with prompt injection payload in untrusted text (at least 3 scenarios)
  - [ ] *Acceptance Gate:* Each scenario loads, applies mutations to graph, and raises its alert.

- [ ] **M4: Tools + Gateway + MCP Server**
  - [ ] Typed tool registry (`backend/app/tools/registry.py`) with Pydantic in/out, read-only and requires-approval flags
  - [ ] Graph tools (`graph_tools.py`), Telemetry tools (`telemetry_tools.py`), Context tools (`context_tools.py`), Memory tools (`memory_tools.py`), Control tools (`control_tools.py`), Action tools (`action_tools.py`)
  - [ ] MCP Server (`backend/app/tools/mcp_server.py`) exposing identical registry
  - [ ] Deterministic policy gateway (`backend/app/agent/gateway.py`): fail-closed checks for session, unexpired delegation, scopes, budgets
  - [ ] Audit logging via `ToolCall` graph nodes
  - [ ] *Acceptance Gate:* Tool tests pass; MCP server lists registered tools; gateway denies unauthorized actions.

- [ ] **M5: LLM Layer & Record/Replay**
  - [ ] Anthropic client wrapper (`backend/app/agent/llm.py`) with `claude-sonnet-5-5` (or latest supported Anthropic model)
  - [ ] Record/replay cache keyed by hash of model, prompt, messages, tools, temp
  - [ ] `MockLLM` for unit tests and deterministic replay mode
  - [ ] Token usage and approximate cost tracking per investigation
  - [ ] *Acceptance Gate:* Replay mode runs a scripted dummy investigation deterministically without external API calls.

- [ ] **M6: Analyst Core**
  - [ ] System prompts (`backend/app/agent/prompts.py`) for planner, reader, and verifier
  - [ ] Quarantined reader (`backend/app/agent/reader.py`): typed schema extraction, never exposes raw untrusted text, detects injection signals
  - [ ] Investigation loop (`backend/app/agent/analyst.py`): triage, hypothesis generation, tool use loop, evidence collection, verdict generation
  - [ ] Verifier (`backend/app/agent/verifier.py`): deterministic evidence existence check + LLM entailment verification
  - [ ] Durability runner (`backend/app/agent/runner.py`): state persistence in FalkorDB `Investigation` node; resume from graph state
  - [ ] Kill/resume mid-investigation test
  - [ ] *Acceptance Gate:* Scenarios Pair 1 and Pair 3 reach correct ground-truth verdicts; cache recorded; kill/resume test passes.

- [ ] **M7: Act-Verify-Watch-Schedule & Memory**
  - [ ] Human approval workflow: `ApprovalRequest` nodes, pending/approved/rejected states
  - [ ] Action execution: `apply_isolation`, `revoke_session`
  - [ ] Verification with escalation: fresh telemetry check; triggers second action on stubborn convergence (Pair 7)
  - [ ] Watch evaluator (`backend/app/agent/watcher.py`): graph pattern and telemetry watches evaluated on clock ticks
  - [ ] Scheduler (`backend/app/agent/scheduler.py`): `ScheduledTask` nodes evaluated on clock ticks
  - [ ] Semantic & procedural memory: `Baseline` updates, `Finding` records, `SIMILAR_TO` links
  - [ ] *Acceptance Gate:* Pair 7 escalates correctly; a watch wakes an investigation on clock advance.

- [ ] **M8: Evaluation Harness & Benchmarks**
  - [ ] Baselines (`backend/app/eval/baselines.py`): B0 rule-based, B1 deterministic graph rules, B2 forensic tracer
  - [ ] Eval harness (`backend/app/eval/harness.py`): 14 scenarios x k=3 runs in replay mode
  - [ ] Metrics calculator (`backend/app/eval/metrics.py`): accuracy, FPR, FNR, evidence recall/precision, verification pass rate, injection resistance, tokens, cost
  - [ ] Graph ablation test: agent without graph tools vs full agent
  - [ ] Results generator (`backend/app/eval/report.py`): `eval/results.json` and `docs/RESULTS.md`
  - [ ] *Acceptance Gate:* `make eval` completes in replay mode and generates full comparison tables.

- [ ] **M9: UI, Docs, and Demo Path**
  - [ ] React + Vite + TypeScript web interface under `web/`:
    - Inbox view with scenario runner and world reset
    - Investigation hero screen with live trace timeline, verifier results, and Cytoscape evidence subgraph
    - Approvals panel with exposure reduction preview
    - Watches & schedule panel with simulated clock fast-forward
    - Eval results table view
    - Graph explorer with "as of" time toggle and honest synthetic/replay mode badge
  - [ ] Documentation deliverables:
    - `README.md` with architecture diagram, query docs, setup, honest limitations, AI disclosure
    - `docs/DEMO.md` with 3-minute script
    - `docs/RESULTS.md` with eval tables
    - `docs/BLOG.md` draft post
    - `docs/LIMITATIONS.md`
    - `FINAL_REPORT.md`
  - [ ] *Acceptance Gate:* `make demo` runs clean 3-minute runbook offline in replay mode; all tests pass.
