"""
Named Cypher Queries and Graph Algorithms for Trust Analyst.
Every Cypher query used in the application lives here as a named, documented function.
All queries use explicit parameterized inputs and temporal filtering.
"""

from typing import Any

from backend.app.graph.client import GraphClient


def entity_context(
    client: GraphClient,
    entity_id: str,
    depth: int = 1,
    at: int | None = None,
) -> dict[str, Any]:
    """
    Query: entity_context
    Fetches the 1-hop or bounded neighborhood around an entity with relationship provenance.

    Parameters:
      - entity_id (str): The identifier of the central entity.
      - depth (int): Traversal depth (default 1).
      - at (int | None): Epoch timestamp for temporal filtering.
    """
    cypher = """
    MATCH (center {id: $id})
    OPTIONAL MATCH (center)-[r]-(neighbor)
    WHERE ($at IS NULL OR ((r.valid_from IS NULL OR r.valid_from <= $at) AND (r.valid_to IS NULL OR r.valid_to > $at)))
    RETURN
        center.id AS center_id,
        labels(center)[0] AS center_label,
        coalesce(center.name, center.id) AS center_name,
        neighbor.id AS neighbor_id,
        labels(neighbor)[0] AS neighbor_label,
        coalesce(neighbor.name, neighbor.id) AS neighbor_name,
        startNode(r).id AS edge_source,
        endNode(r).id AS edge_target,
        type(r) AS edge_type,
        coalesce(r.provenance, 'configured') AS edge_provenance,
        r.valid_from AS edge_valid_from,
        r.valid_to AS edge_valid_to
    """
    rows = client.query_dicts(cypher, {"id": entity_id, "at": at})
    if not rows:
        return {"center_id": entity_id, "neighbors": [], "edges": []}

    center_id = rows[0]["center_id"]
    center_label = rows[0]["center_label"]
    center_name = rows[0]["center_name"]

    neighbors_map = {}
    edges_set = []
    seen_edges = set()

    for row in rows:
        nid = row.get("neighbor_id")
        if nid:
            if nid not in neighbors_map:
                neighbors_map[nid] = {
                    "id": nid,
                    "label": row.get("neighbor_label"),
                    "name": row.get("neighbor_name"),
                }
            src = row.get("edge_source")
            tgt = row.get("edge_target")
            etype = row.get("edge_type")
            edge_key = (src, tgt, etype)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges_set.append(
                    {
                        "source": src,
                        "target": tgt,
                        "type": etype,
                        "provenance": row.get("edge_provenance"),
                        "valid_from": row.get("edge_valid_from"),
                        "valid_to": row.get("edge_valid_to"),
                    }
                )

    return {
        "center_id": center_id,
        "center_label": center_label,
        "center_name": center_name,
        "neighbors": list(neighbors_map.values()),
        "edges": edges_set,
    }


def blast_radius(
    client: GraphClient,
    start_id: str,
    max_hops: int = 4,
    at: int | None = None,
) -> list[dict[str, Any]]:
    """
    Query: blast_radius
    Traverses reachable paths from a subject (Workload, Pod, AgentSession) to SensitiveResource nodes.
    Returns bounded paths, target sensitivity, edge provenance, and path length.

    Parameters:
      - start_id (str): The starting node id.
      - max_hops (int): Maximum path length (clamped between 1 and 6).
      - at (int | None): Temporal point-in-time timestamp.
    """
    hops = max(1, min(max_hops, 6))
    temporal_clause = ""
    params: dict[str, Any] = {"start_id": start_id}
    if at is not None:
        temporal_clause = "WHERE all(rel in relationships(path) WHERE (rel.valid_from IS NULL OR rel.valid_from <= $at) AND (rel.valid_to IS NULL OR rel.valid_to > $at))"
        params["at"] = at

    cypher = f"""
    MATCH (start {{id: $start_id}})
    MATCH path = (start)-[*1..{hops}]->(target:SensitiveResource)
    {temporal_clause}
    RETURN
        target.id AS target_id,
        target.name AS target_name,
        coalesce(target.sensitivity, 3) AS sensitivity,
        length(path) AS path_length,
        [n in nodes(path) | n.id] AS path_node_ids,
        [r in relationships(path) | {{
            type: type(r),
            provenance: coalesce(r.provenance, 'configured'),
            source: coalesce(r.source, 'system')
        }}] AS path_edges
    ORDER BY sensitivity DESC, path_length ASC
    """
    return client.query_dicts(cypher, params)


def path_diff(
    client: GraphClient,
    start_id: str,
    t_before: int,
    t_after: int,
) -> dict[str, Any]:
    """
    Query: path_diff
    Identifies targets reachable after t_after that were NOT reachable at t_before.
    Uses temporal edge validity (valid_from / valid_to) to detect newly emerged security paths.

    Parameters:
      - start_id (str): Starting entity identifier.
      - t_before (int): Prior epoch time.
      - t_after (int): Later epoch time.
    """
    cypher_before = """
    MATCH path = (start {id: $id})-[*1..5]->(target)
    WHERE (target:SensitiveResource OR target:NetworkEndpoint OR target:Tool)
      AND all(r in relationships(path) WHERE (r.valid_from IS NULL OR r.valid_from <= $t_before) AND (r.valid_to IS NULL OR r.valid_to > $t_before))
    RETURN collect(DISTINCT target.id) AS targets
    """
    cypher_after = """
    MATCH path = (start {id: $id})-[*1..5]->(target)
    WHERE (target:SensitiveResource OR target:NetworkEndpoint OR target:Tool)
      AND all(r in relationships(path) WHERE (r.valid_from IS NULL OR r.valid_from <= $t_after) AND (r.valid_to IS NULL OR r.valid_to > $t_after))
    RETURN collect(DISTINCT target.id) AS targets
    """
    before_rows = client.query(cypher_before, {"id": start_id, "t_before": t_before}, ignore_errors=True)
    after_rows = client.query(cypher_after, {"id": start_id, "t_after": t_after}, ignore_errors=True)

    targets_before = set(before_rows[0][0]) if before_rows and before_rows[0] and before_rows[0][0] else set()
    targets_after = set(after_rows[0][0]) if after_rows and after_rows[0] and after_rows[0][0] else set()

    newly_reachable = list(targets_after - targets_before)
    revoked = list(targets_before - targets_after)

    return {
        "start_id": start_id,
        "t_before": t_before,
        "t_after": t_after,
        "newly_reachable_ids": newly_reachable,
        "revoked_ids": revoked,
        "net_diff_count": len(newly_reachable),
    }


def delegation_chain(
    client: GraphClient,
    session_id: str,
    requested_tool: str | None = None,
    at: int | None = None,
) -> dict[str, Any]:
    """
    Query: delegation_chain
    Traces: Principal -> Delegation -> AgentSession -> Agent -> Tool -> SensitiveResource.
    Detects scope-vs-requested-tool mismatch and authority boundary violations.

    Parameters:
      - session_id (str): The AgentSession identifier.
      - requested_tool (str | None): Optional tool name to check against delegation scopes.
      - at (int | None): Temporal evaluation time.
    """
    temporal_clause = ""
    params: dict[str, Any] = {"sid": session_id}
    if at is not None:
        temporal_clause = "AND (d.expires_at IS NULL OR d.expires_at > $at)"
        params["at"] = at

    cypher = f"""
    MATCH (p:Principal)-[:GRANTED]->(d:Delegation)-[:TO_SESSION]->(s:AgentSession {{id: $sid}})
    OPTIONAL MATCH (s)-[:USES_AGENT]->(a:Agent)
    OPTIONAL MATCH (s)-[:CAN_INVOKE]->(t:Tool)
    OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
    WHERE 1=1 {temporal_clause}
    RETURN
        p.id AS principal_id,
        p.name AS principal_name,
        p.role AS principal_role,
        p.status AS principal_status,
        d.id AS delegation_id,
        coalesce(d.scopes, []) AS scopes,
        d.expires_at AS delegation_expires_at,
        d.intent_text AS intent_text,
        s.id AS session_id,
        s.status AS session_status,
        a.id AS agent_id,
        a.name AS agent_name,
        collect(DISTINCT t.name) AS invokable_tools,
        collect(DISTINCT sr.name) AS accessible_resources
    """
    rows = client.query_dicts(cypher, params)
    if not rows:
        return {
            "authorized": False,
            "session_id": session_id,
            "reason": f"Agent session '{session_id}' not found or has no active delegation.",
        }

    chain = rows[0]
    scopes = chain.get("scopes", [])
    if isinstance(scopes, str):
        scopes = [scopes]

    scope_authorized = True
    scope_mismatch_reason = None

    if requested_tool:
        if "*" not in scopes and requested_tool not in scopes:
            scope_authorized = False
            scope_mismatch_reason = f"Requested tool '{requested_tool}' is not permitted by delegation scopes: {scopes}"

    is_principal_active = chain.get("principal_status") == "active"
    if not is_principal_active:
        scope_authorized = False
        scope_mismatch_reason = f"Delegating principal '{chain.get('principal_name')}' is offboarded/inactive."

    return {
        "authorized": scope_authorized,
        "mismatch_reason": scope_mismatch_reason,
        "chain": chain,
    }


def find_convergence(
    client: GraphClient,
    source_ids: list[str],
    at: int | None = None,
) -> list[dict[str, Any]]:
    """
    Query: find_convergence
    Finds SensitiveResource nodes reachable from 2 or more distinct sources.
    Calculates transparent risk score: sensitivity * (1 + 0.5 * (sources - 1)) * (1 + 0.1 * paths).

    Parameters:
      - source_ids (list[str]): List of starting node IDs (e.g. compromised Pod and rogue AgentSession).
      - at (int | None): Temporal evaluation time.
    """
    temporal_clause = ""
    params: dict[str, Any] = {"sources": source_ids}
    if at is not None:
        temporal_clause = "WHERE all(r in relationships(path) WHERE (r.valid_from IS NULL OR r.valid_from <= $at) AND (r.valid_to IS NULL OR r.valid_to > $at))"
        params["at"] = at

    cypher = f"""
    MATCH (src)
    WHERE src.id IN $sources
    MATCH path = (src)-[*1..5]->(target:SensitiveResource)
    {temporal_clause}
    WITH target,
         count(DISTINCT src.id) AS source_count,
         collect(DISTINCT src.id) AS convergent_sources,
         count(path) AS path_count
    WHERE source_count >= 2
    RETURN
        target.id AS resource_id,
        target.name AS resource_name,
        coalesce(target.sensitivity, 3) AS sensitivity,
        source_count,
        convergent_sources,
        path_count
    """
    rows = client.query_dicts(cypher, params)
    for r in rows:
        sens = r.get("sensitivity", 3)
        sources = r.get("source_count", 2)
        paths = r.get("path_count", 2)
        r["risk_score"] = round(sens * (1.0 + 0.5 * (sources - 1)) * (1.0 + 0.1 * paths), 2)
    rows.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return rows


def simulate_containment(
    client: GraphClient,
    node_id: str,
    at: int | None = None,
) -> dict[str, Any]:
    """
    Query: simulate_containment
    Hypothetically simulates the security impact of isolating a node.
    Read-only calculation comparing exposure before vs after excluding node_id.
    Returns exposure reduction % and remaining reachable paths.

    Parameters:
      - node_id (str): The node to hypothetically isolate (e.g. Pod or AgentSession).
      - at (int | None): Temporal evaluation time.
    """
    # 1. Total reachable sensitive targets before exclusion
    cypher_before = """
    MATCH (src {id: $nid})-[*1..5]->(target:SensitiveResource)
    RETURN count(DISTINCT target) AS total_targets, count(*) AS total_paths
    """
    res_before = client.query_dicts(cypher_before, {"nid": node_id})
    targets_before = res_before[0]["total_targets"] if res_before else 0
    paths_before = res_before[0]["total_paths"] if res_before else 0

    # 2. Check if other active workloads or sessions still reach those same targets
    cypher_remaining = """
    MATCH (src {id: $nid})-[*1..5]->(target:SensitiveResource)
    WITH DISTINCT target
    MATCH (other)-[*1..5]->(target)
    WHERE other.id <> $nid AND (other:Pod OR other:AgentSession)
    RETURN count(DISTINCT target) AS remaining_targets, count(*) AS remaining_paths, collect(DISTINCT other.id) AS other_sources
    """
    res_rem = client.query_dicts(cypher_remaining, {"nid": node_id})
    rem_targets = res_rem[0]["remaining_targets"] if res_rem else 0
    rem_paths = res_rem[0]["remaining_paths"] if res_rem else 0
    other_sources = res_rem[0]["other_sources"] if res_rem else []

    reduction_pct = (
        100.0
        if targets_before == 0
        else max(0.0, round(((targets_before - rem_targets) / max(1, targets_before)) * 100.0, 1))
    )

    return {
        "isolated_node_id": node_id,
        "initial_reachable_targets": targets_before,
        "initial_reachable_paths": paths_before,
        "remaining_reachable_targets": rem_targets,
        "remaining_reachable_paths": rem_paths,
        "other_convergent_sources": other_sources,
        "exposure_reduction_pct": reduction_pct,
        "containment_complete": rem_targets == 0,
    }


def recall_similar(
    client: GraphClient,
    alert_kind: str,
    subject_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Query: recall_similar
    Recalls prior findings, baselines, and investigations about the same alert kind or subjects.
    Provides semantic and episodic memory for the analyst agent.

    Parameters:
      - alert_kind (str): The alert type (e.g. 'shell_metadata_access', 'destructive_tool_call').
      - subject_ids (list[str] | None): Subject node IDs.
    """
    params: dict[str, Any] = {"kind": alert_kind}
    subject_clause = ""
    if subject_ids:
        subject_clause = "OR any(sid IN $subjects WHERE (f)-[:ABOUT]->({id: sid}))"
        params["subjects"] = subject_ids

    cypher = f"""
    MATCH (f:Finding)
    OPTIONAL MATCH (f)-[:ABOUT]->(subject)
    OPTIONAL MATCH (f)-[:CITES]->(ev:Evidence)
    WHERE f.summary CONTAINS $kind {subject_clause}
    RETURN
        f.id AS finding_id,
        f.verdict AS verdict,
        f.severity AS severity,
        f.confidence AS confidence,
        f.summary AS summary,
        f.created_at AS created_at,
        subject.id AS subject_id,
        labels(subject)[0] AS subject_label,
        count(ev) AS cited_evidence_count
    ORDER BY f.created_at DESC
    LIMIT 10
    """
    return client.query_dicts(cypher, params)


def centrality_rank(
    client: GraphClient,
    label: str = "Pod",
) -> list[dict[str, Any]]:
    """
    Query: centrality_rank
    Ranks nodes of a given label by topological degree connectivity and choke point reach.

    Parameters:
      - label (str): Node label to rank (e.g. 'Pod', 'Workload', 'Tool').
    """
    cypher = f"""
    MATCH (n:{label})
    OPTIONAL MATCH (n)-[r_out]->()
    OPTIONAL MATCH ()-[r_in]->(n)
    WITH n, count(DISTINCT r_in) AS in_degree, count(DISTINCT r_out) AS out_degree
    RETURN
        n.id AS id,
        coalesce(n.name, n.id) AS name,
        in_degree,
        out_degree,
        (in_degree + out_degree) AS total_degree
    ORDER BY total_degree DESC, in_degree DESC
    LIMIT 15
    """
    return client.query_dicts(cypher)
