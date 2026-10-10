# Trust Analyst: Final Hackathon Project Report

**Graph Hacks: Context for AI Agents (WeMakeDevs x FalkorDB)**

- **Primary Track:** *Agents That Act on Connected Data*
- **Secondary Track:** *Agent Memory and Coordination*
- **Database:** FalkorDB (Graph: `trust`)
- **Repository:** `trustme`
- **Submission Date:** October 2026

---

## 1. Project Overview & Pitch

**Trust Analyst** is an autonomous security analyst that investigates runtime alerts by walking a connected FalkorDB graph, gathering telemetry and context, formulating competing hypotheses, and reaching an evidence-cited verdict. Upon human approval, it executes surgical containment, verifies exposure elimination via fresh telemetry, and registers long-running graph watches and scheduled tasks.

### The Core Problem Solved
Pairs of runtime alerts look identical on the surface but possess opposite ground truths (e.g. an authorized engineer debugging latency vs. a web RCE harvesting IMDS credentials). Static rule baselines flag both, causing severe alert fatigue (**100% False Positive Rate**). Telling them apart requires a chain of relational questions across process trees, temporal ChangeSets, Jira tickets, and reachability paths—a task uniquely suited for an agent operating over a connected graph.

---

## 2. Hybrid Architecture: Load-Bearing Graph + Relational Operational Store

In accordance with our architectural RFC ([docs/DESIGN_GRAPH_VS_RELATIONAL.md](docs/DESIGN_GRAPH_VS_RELATIONAL.md)), Trust Analyst implements a principled **hybrid architecture**:
- **FalkorDB (The Cognitive Map):** The primary graph database powering all relationship-intensive reasoning: topological reachability, temporal path diffs, crown jewel convergence, taint chains, and the full evidence-cited explanation tree (`Investigation`, `Hypothesis`, `Evidence`, `Finding`). If FalkorDB were removed, **Trust Analyst loses its map and fails closed immediately**.
- **SQLite (The Operational Engine):** Handles tabular execution state requiring $O(\log N)$ range and status lookups (`approvals`, `watches`, `scheduled_tasks`, `tool_calls` audit log, `step_states` checkpoints), with foreign keys referencing FalkorDB node IDs.
- **Dual-write Projections:** Operational tools maintain dual-write projections into FalkorDB so that operational state can be seamlessly traversed and visualized alongside security entities in the FalkorDB Browser and Cytoscape explorer.

1. **Security Entity Graph:** `Principal`, `Agent`, `AgentSession`, `Delegation`, `Tool`, `MCPServer`, `Workload`, `Pod`, `ServiceAccount`, `Permission`, `SensitiveResource`, `NetworkEndpoint`.
2. **Temporal Edge Model:** Relationships carry `valid_from`, `valid_to`, `provenance`, and `source`. Querying the past is a first-class operation via temporal parameter `$at`.
3. **Telemetry Summaries:** Tetragon-like eBPF events are aggregated into compact `EventSummary` nodes in FalkorDB.
4. **Investigations & Hypotheses:** Every investigation creates an `Investigation` node linked to competing `Hypothesis` nodes and verified `Claim` records.
5. **Human-in-the-Loop Approvals:** `ApprovalRequest` operational records gate disruptive actions; policy gateways check state before allowing tool execution.
6. **Active Watches & Task Scheduler:** `Watch` monitors and `ScheduledTask` follow-ups are evaluated on simulated clock ticks.
7. **Graph Memory:** `Baseline` profiles, `Finding` records, and `SIMILAR_TO` memory edges persist across investigations.

---

## 3. Milestones Completion Matrix (M0 – M9)

| Milestone | Scope | Status | Acceptance Gate Passed |
| :--- | :--- | :---: | :--- |
| **M0: Skeleton** | Repo layout, config, Docker Compose, fail-closed `/api/health` | **Done** | FalkorDB online/offline health tests pass |
| **M1: Graph & Schema** | FalkorDB client, 26 labels, 27 edge types, temporal queries | **Done** | `test_graph.py` verifies all Cypher algorithms |
| **M2: Sim World & Clock** | `SimulatedClock`, Tetragon telemetry aggregator, world seeder | **Done** | World seeder produces identical hash (311 nodes) |
| **M3: Scenarios** | 14 matched-pair YAML scenarios, 3 prompt injection variants | **Done** | All 14 scenarios parse, validate, and mutate graph |
| **M4: Tools & Gateway** | 27 typed security tools, policy gateway, official MCP server | **Done** | Policy gateway denies unapproved disruptive actions |
| **M5: LLM Layer** | Anthropic SDK wrapper, disk SHA-256 replay cache, MockLLM | **Done** | Replay mode serves pre-recorded runs deterministically |
| **M6: Analyst Core** | Quarantined reader, verifier, planner, durability runner | **Done** | Kill/resume mid-investigation state test passes |
| **M7: Act-Verify-Watch** | Human approvals, post-action verification, Pair 7 escalation | **Done** | Pair 7 stubborn exposure escalates to session revocation |
| **M8: Eval Harness** | Benchmarks across Trust Analyst vs B0, B1, and B2 ablated | **Done** | `make eval` generates `docs/RESULTS.md` |
| **M9: UI & Demo** | React + Vite + Cytoscape UI, 3-minute offline demo, full docs | **Done** | `make demo` runs clean 3-minute offline runbook |

---

## 4. Benchmark & Measured Results

Evaluated across **14 realistic matched-pair scenarios** (7 pairs, benign vs. malicious):

```
===============================================================================================
TRUST ANALYST BENCHMARK RESULTS
===============================================================================================
Evaluator                    | Accuracy | FPR     | FNR     | Precision | Ev Recall | Inj Resist
-----------------------------------------------------------------------------------------------
Trust Analyst (Full Agent)   |  100.0% |   0.0% |   0.0% |   100.0% |    67.9% |    100.0%
Ablated Agent (No Graph)     |   85.7% |   0.0% |  28.6% |   100.0% |    22.6% |    100.0%
B1: Graph Heuristics         |   50.0% | 100.0% |   0.0% |    50.0% |     0.0% |    100.0%
B0: Alert Rule Baseline      |   50.0% | 100.0% |   0.0% |    50.0% |     0.0% |    100.0%
===============================================================================================
```

### Measured Value
- **Zero Alert Fatigue:** Trust Analyst achieves **0.0% FPR**, eliminating false positive alerts on legitimate debugging.
- **Graph Ablation Impact:** Stripping graph topology tools causes the ablated agent to fail on Pair 4 (dormant wildcard) and Pair 7 (stubborn convergence), dropping accuracy to 85.7%.
- **Adversarial Robustness:** The Quarantined Reader delivers **100% Prompt Injection Resistance** against attacker override instructions.

---

## 5. Local Setup & Quick Commands

```bash
# 1. Start FalkorDB and services
make up

# 2. Seed synthetic environment
make seed

# 3. Run all unit and integration tests (45 tests)
make test

# 4. Run full evaluation benchmark across all 14 scenarios
make eval

# 5. Run 3-minute offline interactive demonstration
make demo

# 6. Check code formatting and lints
make lint
```

- **Web Dashboard:** `http://localhost:5173`
- **FastAPI Control Plane:** `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)
- **FalkorDB Web Browser:** `http://localhost:3000`

---

## 6. AI-Assistance Disclosure

In accordance with hackathon submission guidelines:
- **AI Coding Assistant:** This project was developed with assistance from Google Antigravity / Gemini code assistants.
- **Human Guidance & Authorship:** All architectural specifications, security threat models, temporal graph schemas, Cypher query designs, and benchmark metrics were authored, validated, reviewed, and iteratively refined by human engineers.
- **Deterministic Replay Guarantee:** All evaluation benchmarks and demo scripts operate deterministically via replay and mock harnesses, guaranteeing 100% offline reproducibility without external AI API dependencies.
