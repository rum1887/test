# Queries and Graph Algorithms the Product Depends On

> This document is automatically generated from docstrings and implementations in `backend/app/graph/queries.py`.

## `entity_context(client: backend.app.graph.client.GraphClient, entity_id: str, depth: int = 1, at: int | None = None) -> dict[str, typing.Any]`

```text
Query: entity_context
Fetches the 1-hop or bounded neighborhood around an entity with relationship provenance.

Parameters:
  - entity_id (str): The identifier of the central entity.
  - depth (int): Traversal depth (default 1).
  - at (int | None): Epoch timestamp for temporal filtering.
```

## `blast_radius(client: backend.app.graph.client.GraphClient, start_id: str, max_hops: int = 4, at: int | None = None) -> list[dict[str, typing.Any]]`

```text
Query: blast_radius
Traverses reachable paths from a subject (Workload, Pod, AgentSession) to SensitiveResource nodes.
Returns bounded paths, target sensitivity, edge provenance, and path length.

Parameters:
  - start_id (str): The starting node id.
  - max_hops (int): Maximum path length (clamped between 1 and 6).
  - at (int | None): Temporal point-in-time timestamp.
```

## `path_diff(client: backend.app.graph.client.GraphClient, start_id: str, t_before: int, t_after: int) -> dict[str, typing.Any]`

```text
Query: path_diff
Identifies targets reachable after t_after that were NOT reachable at t_before.
Uses temporal edge validity (valid_from / valid_to) to detect newly emerged security paths.

Parameters:
  - start_id (str): Starting entity identifier.
  - t_before (int): Prior epoch time.
  - t_after (int): Later epoch time.
```

## `delegation_chain(client: backend.app.graph.client.GraphClient, session_id: str, requested_tool: str | None = None, at: int | None = None) -> dict[str, typing.Any]`

```text
Query: delegation_chain
Traces: Principal -> Delegation -> AgentSession -> Agent -> Tool -> SensitiveResource.
Detects scope-vs-requested-tool mismatch and authority boundary violations.

Parameters:
  - session_id (str): The AgentSession identifier.
  - requested_tool (str | None): Optional tool name to check against delegation scopes.
  - at (int | None): Temporal evaluation time.
```

## `find_convergence(client: backend.app.graph.client.GraphClient, source_ids: list[str], at: int | None = None) -> list[dict[str, typing.Any]]`

```text
Query: find_convergence
Finds SensitiveResource nodes reachable from 2 or more distinct sources.
Calculates transparent risk score: sensitivity * (1 + 0.5 * (sources - 1)) * (1 + 0.1 * paths).

Parameters:
  - source_ids (list[str]): List of starting node IDs (e.g. compromised Pod and rogue AgentSession).
  - at (int | None): Temporal evaluation time.
```

## `simulate_containment(client: backend.app.graph.client.GraphClient, node_id: str, at: int | None = None) -> dict[str, typing.Any]`

```text
Query: simulate_containment
Hypothetically simulates the security impact of isolating a node.
Read-only calculation comparing exposure before vs after excluding node_id.
Returns exposure reduction % and remaining reachable paths.

Parameters:
  - node_id (str): The node to hypothetically isolate (e.g. Pod or AgentSession).
  - at (int | None): Temporal evaluation time.
```

## `recall_similar(client: backend.app.graph.client.GraphClient, alert_kind: str, subject_ids: list[str] | None = None) -> list[dict[str, typing.Any]]`

```text
Query: recall_similar
Recalls prior findings, baselines, and investigations about the same alert kind or subjects.
Provides semantic and episodic memory for the analyst agent.

Parameters:
  - alert_kind (str): The alert type (e.g. 'shell_metadata_access', 'destructive_tool_call').
  - subject_ids (list[str] | None): Subject node IDs.
```

## `centrality_rank(client: backend.app.graph.client.GraphClient, label: str = 'Pod') -> list[dict[str, typing.Any]]`

```text
Query: centrality_rank
Ranks nodes of a given label by topological degree connectivity and choke point reach.

Parameters:
  - label (str): Node label to rank (e.g. 'Pod', 'Workload', 'Tool').
```
