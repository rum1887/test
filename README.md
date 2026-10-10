# Trust Analyst
### Autonomous Graph-Native Security Analyst on FalkorDB

[![FalkorDB](https://img.shields.io/badge/Graph_Database-FalkorDB_v4-blue.svg)](https://www.falkordb.com/)
[![Protocol](https://img.shields.io/badge/Protocol-Model_Context_Protocol_(MCP)-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![Sensor](https://img.shields.io/badge/Sensor-Cilium_Tetragon_eBPF-brightgreen.svg)](https://tetragon.io/)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Trust Analyst** is an autonomous security analyst built for **Graph Hacks: Context for AI Agents (WeMakeDevs x FalkorDB)**. It receives runtime security alerts about workloads and AI-agent sessions, investigates them by walking a **FalkorDB** graph, gathers telemetry and context, reaches an evidence-cited verdict, proposes containment that a human approves, verifies that containment succeeded, and registers long-running watches and scheduled tasks.

---

## 🏆 Hackathon Tracks
- **Primary Track:** *Agents That Act on Connected Data* (Autonomous agent investigation, tool-driven graph walks, MCP gateways, real-time path traversal).
- **Secondary Track:** *Agent Memory and Coordination* (Graph-backed incident memory, verified findings, baseline comparisons, temporal state tracking).

---

## 📚 Documentation Directory
| Document | Description |
| :--- | :--- |
| **[3-Minute Demo Runbook](docs/DEMO.md)** | Step-by-step walkthrough of the offline demo matching `make demo` and the web UI |
| **[Evaluation & Benchmark Results](docs/RESULTS.md)** | Full benchmark tables across 14 scenarios comparing Trust Analyst against B0, B1, and B2 ablated |
| **[Cypher Queries & Algorithms](docs/QUERIES.md)** | Complete documentation of all 8 Cypher graph algorithms used in production |
| **[Draft Blog Post](docs/BLOG.md)** | Comprehensive technical blog post on graph-native agentic security |
| **[Technical Limitations](docs/LIMITATIONS.md)** | Honest engineering disclosures regarding synthetic boundaries and fail-closed gates |
| **[Final Project Report](FINAL_REPORT.md)** | Executive hackathon summary and verification checklist |

---

## ⚡ Quick Start (60 Seconds)

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (or Node 20+ for web UI)

```bash
# 1. Start FalkorDB and all container services
make up

# 2. Seed the synthetic security world in FalkorDB (~311 nodes, seed=42)
make seed

# 3. Run the automated 3-minute offline demo
make demo

# 4. Run the 14-scenario evaluation benchmark
make eval

# 5. Run all 40 unit and integration tests
make test
```

- **Web Dashboard:** `http://localhost:5173`
- **FastAPI Control Plane:** `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)
- **FalkorDB Browser:** `http://localhost:3000`

---

## 1. Product Vision & The Alert Fatigue Dilemma

In modern cloud and AI environments, pairs of alerts look **identical on the surface** but have **opposite ground truths**:
- **Scenario A (Benign):** An engineer runs `kubectl exec` to debug an active latency incident during an approved change window.
- **Scenario B (Malicious):** A web server process suffers an RCE, spawns `/bin/sh`, queries cloud metadata (`169.254.169.254`), and accesses customer vault secrets.

Both emit identical eBPF telemetry signatures: `/bin/sh` connecting to `169.254.169.254`.

A traditional static rule baseline (*"flag every alert of this type"*) achieves a **100.0% False Positive Rate (FPR)** on benign operational activities, crippling engineering velocity. Distinguishing between them requires a chain of relational questions across connected data:
1. *Who launched this process?* (PID $\to$ PPID ancestry)
2. *Does the user have an approved ticket or ChangeSet?* (Temporal graph lookup)
3. *What sensitive resources can this entity reach right now?* (Outbound reachability)
4. *Are parallel active attack vectors targeting the same secret?* (Choke-point convergence)

The graph computes **what is possible** (paths, reachability, diffs). The agent decides **what is justified** (intent, authorization, explanation).

---

## 2. Architecture Diagram

```
                              RUNTIME INCIDENT EVENT
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │      Simulated Clock (sim)    │
                        │   Unified epoch time source   │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │                     AUTONOMOUS ANALYST CORE LOOP                      │
    │                                                                       │
    │   1. Alert Ingestion & Target Resolution                              │
    │   2. Autonomous Triage & Neighborhood Context                         │
    │   3. Competing Hypotheses Formulation (e.g. Authorized vs Compromise) │
    │   4. Quarantined Reader (Neutralizes adversarial prompt injections)   │
    │   5. Forensic Graph Walk (Cypher queries & Tetragon telemetry)        │
    │   6. Two-Stage Verification (Deterministic existence + Entailment)    │
    │   7. Policy Gateway Enforcement (Fail-closed authorization check)     │
    └───────────────────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │                     FALKORDB LOAD-BEARING GRAPH                       │
    │                                                                       │
    │   • Security Entities: Workloads, Pods, SAs, Sessions, Tools, Secrets │
    │   • Temporal Validity: valid_from, valid_to, provenance, source       │
    │   • Telemetry Nodes: EventSummary signatures (exec, connect, reads)   │
    │   • Operational State: Investigations, Hypotheses, Claims, Findings   │
    │   • Durable Controls: Active Watches & Scheduled Follow-up Tasks      │
    └───────────────────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │                 HUMAN-IN-THE-LOOP & VERIFICATION                      │
    │                                                                       │
    │   1. Human Operator Approval (ApprovalRequest node review)            │
    │   2. Surgical Remediation (apply_isolation / revoke_session)          │
    │   3. Post-Action Telemetry Verification (Zero egress check)           │
    │   4. Stubborn Exposure Escalation (Detects multi-path convergence)    │
    │   5. Durable Watch Activation (24h condition monitoring in FalkorDB)  │
    └───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Why FalkorDB is Load-Bearing

If FalkorDB were removed, **Trust Analyst would immediately fail closed and stop working**. All core state lives inside FalkorDB:
- **No SQLite / Postgres / Redis queues:** All entities, telemetry summaries, change records, investigations, hypotheses, evidence, findings, memory baselines, watches, schedules, approvals, and tool-call audit logs live directly in FalkorDB.
- **Temporal Convention:** Every relationship carrying world state possesses `valid_from` and `valid_to` epoch integers. Queries take an `$at` parameter to query point-in-time past states.
- **Fail-Closed Policy Gateway:** The agent's own actions are mediated by a deterministic gateway that inspects FalkorDB before executing any disruptive tool.

### Node Labels (26 Labels)
`Principal`, `Agent`, `AgentSession`, `Delegation`, `Tool`, `MCPServer`, `Workload`, `Pod`, `ServiceAccount`, `Permission`, `SensitiveResource`, `NetworkEndpoint`, `ChangeSet`, `Document`, `EventSummary`, `Baseline`, `Alert`, `Investigation`, `Hypothesis`, `Evidence`, `Claim`, `Finding`, `ApprovalRequest`, `Watch`, `ScheduledTask`, `ToolCall`.

---

## 4. Key Cypher Queries & Graph Algorithms

All production queries are centralized in `backend/app/graph/queries.py`:

1. **Blast Radius (`blast_radius`):** Traverses outbound directed paths from a compromised entity to all reachable `SensitiveResource` nodes up to 4 hops.
2. **Temporal Path Diff (`path_diff`):** Compares topological reachability between two timestamps (`$t_before` vs `$t_after`) to detect privilege escalation.
3. **Delegation Chain (`delegation_chain`):** Validates authority lineages: `(Principal)-[:OWNS_SESSION]->(Session)-[:DELEGATES]->(Agent)-[:CAN_INVOKE]->(Tool)`.
4. **Choke Point Convergence (`find_convergence`):** Identifies where multiple independent attack paths (e.g. pod + rogue agent session) converge on the same crown jewel secret.
5. **Simulated Containment (`simulate_containment`):** Evaluates hypothetically severing edges before applying physical isolation.
6. **Incident Memory Recall (`recall_similar_incidents`):** Performs semantic graph search over past `Finding` nodes to reuse proven remediation strategies.
7. **Shortest Attack Path (`shortest_path`):** Computes shortest paths between any source entity and targeted sensitive asset.
8. **Watch Evaluator Patterns (`watcher.py`):** Runs allowlisted Cypher patterns on clock ticks to awaken paused investigations.

---

## 5. Measured Benchmark Results

Trust Analyst was evaluated across **14 realistic matched-pair scenarios** (7 benign operational events, 7 malicious attacks including 3 prompt-injection variants):

| Evaluator | Accuracy | False Positive Rate (FPR) | False Negative Rate (FNR) | Precision | Evidence Recall | Injection Resistance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Trust Analyst (Full Agent)** | **100.0%** | **0.0%** | **0.0%** | **100.0%** | **67.9%** | **100.0%** |
| **Ablated Agent (No Graph)** | 85.7% | 0.0% | 28.6% | 100.0% | 22.6% | 100.0% |
| **B1: Graph Heuristics** | 50.0% | 100.0% | 0.0% | 50.0% | 0.0% | 100.0% |
| **B0: Alert Rule Baseline** | 50.0% | 100.0% | 0.0% | 50.0% | 0.0% | 100.0% |

### Key Benchmark Findings:
- **Zero False Positives:** While static SIEM rules flag 100% of benign events (alert fatigue), Trust Analyst achieves **0.0% FPR**.
- **FalkorDB is Load-Bearing:** The ablated agent (no graph tools) failed on Pair 4 (dormant wildcard permission) and Pair 7 (stubborn multi-path convergence), proving that raw telemetry without graph topology cannot detect lateral reachability.
- **Adversarial Robustness:** Quarantined schema extraction delivered a **100% Prompt Injection Resistance Rate** against embedded override payloads.

---

## 6. Repository Layout

```
trustme/
  README.md                     # Main documentation & architecture guide
  PLAN.md                       # Milestones M0-M9 checklist & acceptance gates
  ASSUMPTIONS.md                # Recorded engineering assumptions
  FINAL_REPORT.md               # Final hackathon summary report
  Makefile                      # make up, seed, test, eval, demo, lint
  docker-compose.yml            # Container definitions (falkordb, api, worker, web)
  .env.example                  # Environment configuration template
  backend/
    app/
      main.py                   # FastAPI REST API & Cytoscape endpoints
      config.py                 # Pydantic settings
      graph/
        client.py               # Thread-safe FalkorDB client
        schema.py               # 26 labels, 27 relationship types, indexes
        queries.py              # Centralized Cypher algorithms
        temporal.py             # valid_from / valid_to temporal helpers
      sim/
        clock.py                # SimulatedClock single source of time
        world.py                # Deterministic synthetic world seeder (seed=42)
        telemetry.py            # Tetragon-like telemetry generator & EventSummary
        scenarios.py            # 14 matched-pair scenario loader & runner
      tools/
        registry.py             # Typed Pydantic tool registry (27 tools)
        graph_tools.py          # Cypher graph traversal tools
        telemetry_tools.py      # Telemetry & process tree tools
        context_tools.py        # Audit logs & document search
        memory_tools.py         # Memory baselines & findings
        control_tools.py        # Watches, schedules, and approvals
        action_tools.py         # Disruptive containment actions & verification
        mcp_server.py           # Official Model Context Protocol (MCP) server
      agent/
        llm.py                  # Anthropic SDK, SHA-256 disk cache, MockLLM
        analyst.py              # Core autonomous investigation loop
        prompts.py              # Planner, reader, and verifier system prompts
        reader.py               # Quarantined reader for untrusted text
        verifier.py             # Two-stage verdict verifier
        gateway.py              # Deterministic policy gateway
        runner.py               # Durable investigation runner & state persistence
        watcher.py              # Active watch evaluator on clock ticks
        scheduler.py            # Scheduled task dispatcher
        worker.py               # Background daemon loop
      eval/
        baselines.py            # B0, B1, and B2 ablated evaluators
        harness.py              # Evaluation benchmark runner
        metrics.py              # Accuracy, FPR, FNR, recall, cost calculator
        report.py               # Markdown and JSON report generator
        demo.py                 # 3-minute offline demo script
    tests/                      # 40 unit and integration tests (100% passing)
  scenarios/                    # 14 YAML scenario specifications
  web/                          # React + Vite + TypeScript + Cytoscape web UI
  docs/                         # DEMO.md, RESULTS.md, QUERIES.md, BLOG.md, LIMITATIONS.md
```

---

## 7. AI-Assistance Disclosure

In compliance with WeMakeDevs x FalkorDB submission guidelines:
- **AI Coding Assistant:** This project was developed with assistance from Google Antigravity / Gemini code assistants for scaffolding, typing, and refactoring.
- **Engineering Authorship:** All threat models, security scenarios, temporal graph schemas, Cypher graph algorithms, quarantined reader architectures, and benchmark metrics were authored, validated, and refined by human developers.
- **Deterministic Replay Guarantee:** All evaluation benchmarks and demo scripts operate deterministically via replay and mock harnesses, guaranteeing 100% offline reproducibility without external AI API dependencies.
