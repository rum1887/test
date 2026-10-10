# Technical Limitations & Boundary Disclosures

Trust Analyst is designed as a rigorous autonomous security analyst operating over FalkorDB. In the spirit of honest engineering and transparency, this document details the current boundaries, trade-offs, and technical limitations of the implementation.

---

## 1. Synthetic Environment & Zero Real Infrastructure
- **All Data is Synthetic:** Every principal, pod, workload, session, document, and telemetry event in Trust Analyst is synthetically generated.
- **Zero Real Hosts Contacted:** The system does not scan, probe, or connect to external networks, live Kubernetes clusters, cloud provider APIs, or real company systems.
- **No Private or Personal Data:** All usernames (e.g. `user-alice`, `user-bob`), IP addresses (e.g. `169.254.169.254`, `198.51.100.25`), and document contents are synthetic artifacts.

---

## 2. Telemetry Ingestion Granularity
- **Signature-Based Aggregation:** Tetragon-like eBPF events (`exec`, `connect`, `file_read`, `secret_read`) are collapsed into `EventSummary` nodes in FalkorDB using composite signature hashes (`binary:args:dest`). While this prevents graph explosion and enables sub-second blast radius queries, it collapses sub-second event micro-timings.
- **Raw Telemetry Storage:** Raw events are stored in append-only JSONL files (`telemetry.jsonl`). In high-throughput production environments (e.g. 50,000+ events/sec), raw event streaming would require Kafka or ClickHouse paired with FalkorDB graph summarization.

---

## 3. LLM Record/Replay vs. Live Execution
- **Deterministic Replay Guarantee:** To guarantee 100% offline reproducibility for hackathon judges and evaluation harnesses, Trust Analyst defaults to `LLM_MODE=replay` / `mock`.
- **Live Mode API Key:** Running in `live` mode requires setting an `ANTHROPIC_API_KEY`. Live completions are automatically cached to disk via SHA-256 hashed prompt payloads.
- **Model Specificity:** Prompts are optimized for Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`). Using smaller or less capable reasoning models without structured output enforcement may require prompt recalibration.

---

## 4. FalkorDB OpenCypher Dialect
- **FalkorDB Compatibility:** All Cypher queries in `backend/app/graph/queries.py` are explicitly tailored to FalkorDB OpenCypher.
- **Unsupported Syntax Avoided:** Neo4j 5-specific subqueries (e.g., `EXISTS { MATCH ... }`) and multi-argument `round()` functions are deliberately avoided in favor of clean OpenCypher constructs and Python-side rounding.

---

## 5. Intentional Human-in-the-Loop Gates
- **Disruptive Actions Fail Closed:** Disruptive containment actions (`apply_isolation`, `revoke_session`, `revoke_permission`, `block_endpoint`) strictly require prior human operator approval via an approved `ApprovalRequest` node in FalkorDB.
- **Not a Lights-Out Auto-Pilot:** Trust Analyst will not autonomously sever production network connections without human confirmation. The system is designed as an autonomous force multiplier for SecOps, maintaining accountability and safety.

---

## 6. Graph Scalability Bounds
- **Current Test Graph:** The default synthetic world seeds ~311 nodes and ~289 temporal edges, executing blast radius traversals in 1–5 milliseconds.
- **Large-Scale Deployments:** For hyper-scale enterprise graphs exceeding 100 million nodes, bounded traversal parameters (`max_depth=3` to `4`) and indexed temporal filtering (`valid_from`, `valid_to`) must be preserved to prevent unbounded combinatorial graph expansion.
