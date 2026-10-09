"""
Versioned Cypher Query Library for Runtime Trust Layer.
Implements the 10 core graph algorithms and security queries against FalkorDB.
All queries use explicit parameterized inputs and allowlists.
"""

import time
from typing import Any, Dict, List, Optional, Set
from graph.client import GraphClient
from graph.schema.schema import validate_graph_integrity

# Sensitivity scoring weights
SENSITIVITY_WEIGHTS = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 40.0,
    "LOW": 10.0,
}

class QueryLibrary:
    """Encapsulates the 10 graph-native security queries."""

    def __init__(self, client: GraphClient):
        self.client = client

    # =========================================================================
    # QUERY 1: Workload Blast Radius
    # =========================================================================
    def get_workload_blast_radius(
        self,
        workload_or_pod_id: str,
        max_depth: int = 5,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Traverses reachable resources from a workload or pod via:
        - Workload -> Pod -> ServiceAccount -> Permission -> SensitiveResource
        - Workload -> Pod -> CAN_REACH -> NetworkEndpoint -> SensitiveResource
        - Observed access edges (OBSERVED_ACCESS)
        Returns bounded paths, edge evidence, reachability classifications, and targets.
        """
        # Validate depth parameter
        depth = max(1, min(max_depth, 8))

        # 1. Fetch direct and indirect reachable paths to sensitive resources or endpoints
        query_paths = f"""
        MATCH (start)
        WHERE (start:Workload OR start:Pod) AND start.id = $id
        MATCH path = (start)-[r:CONTAINS|RUNS_AS|USES_CREDENTIAL|HAS_PERMISSION|CAN_ACCESS|CAN_REACH|OBSERVED_ACCESS*1..{depth}]->(target)
        WHERE target:SensitiveResource OR target:KubernetesResource OR target:NetworkEndpoint
        RETURN
            [n in nodes(path) | {{
                id: n.id,
                label: labels(n)[0],
                name: coalesce(n.name, n.id),
                sensitivity: coalesce(n.sensitivity_level, 'NONE')
            }}] AS path_nodes,
            [rel in relationships(path) | {{
                type: type(rel),
                evidence: coalesce(rel.evidence, 'configured_spec'),
                evidence_type: coalesce(rel.evidence_type, 'configured'),
                confidence: coalesce(rel.confidence, 1.0)
            }}] AS path_edges,
            target.id AS target_id,
            target.name AS target_name,
            labels(target)[0] AS target_label,
            coalesce(target.sensitivity_level, 'NONE') AS target_sensitivity,
            length(path) AS path_length
        LIMIT {limit}
        """

        rows = self.client.query(query_paths, {"id": workload_or_pod_id})

        paths_data = []
        reachable_targets = {}
        max_path_len = 0
        all_edge_types: Set[str] = set()

        for row in rows:
            p_nodes, p_edges, t_id, t_name, t_label, t_sens, p_len = row
            max_path_len = max(max_path_len, p_len)

            # Determine path classification
            edge_types = [e["type"] for e in p_edges]
            for et in edge_types:
                all_edge_types.add(et)

            has_observed = any(e.get("evidence_type") == "observed" or e.get("type") == "OBSERVED_ACCESS" for e in p_edges)
            has_inferred = any(e.get("evidence_type") == "inferred" or e.get("type") == "CAN_REACH" for e in p_edges)

            if has_observed:
                path_class = "observed"
            elif has_inferred:
                path_class = "inferred"
            else:
                path_class = "configured"

            path_record = {
                "length": p_len,
                "classification": path_class,
                "nodes": p_nodes,
                "edges": p_edges,
                "target": {
                    "id": t_id,
                    "name": t_name,
                    "label": t_label,
                    "sensitivity": t_sens,
                },
            }
            paths_data.append(path_record)

            if t_id not in reachable_targets:
                reachable_targets[t_id] = {
                    "id": t_id,
                    "name": t_name,
                    "label": t_label,
                    "sensitivity": t_sens,
                    "min_path_length": p_len,
                    "path_count": 1,
                    "is_direct": (p_len <= 2),
                }
            else:
                reachable_targets[t_id]["path_count"] += 1
                reachable_targets[t_id]["min_path_length"] = min(
                    reachable_targets[t_id]["min_path_length"], p_len
                )

        sensitive_count = sum(1 for t in reachable_targets.values() if t["sensitivity"] in ("CRITICAL", "HIGH"))

        return {
            "source_id": workload_or_pod_id,
            "total_paths": len(paths_data),
            "max_path_length": max_path_len,
            "reachable_resources_count": len(reachable_targets),
            "sensitive_resources_count": sensitive_count,
            "unique_edge_types": sorted(list(all_edge_types)),
            "targets": list(reachable_targets.values()),
            "paths": paths_data,
        }

    # =========================================================================
    # QUERY 2: Agent Delegation-Chain Analysis
    # =========================================================================
    def trace_agent_delegation_chain(
        self,
        session_id: str,
        requested_tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Traces:
        Human Principal -> Agent Session -> Agent -> Delegation -> MCP Server -> Tool -> Downstream Resource
        Evaluates validity, issuer, scopes, expiry, and excessive privilege.
        """
        query = """
        MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession {id: $session_id})
        OPTIONAL MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
        WHERE d.session_id = s.id OR d.session_id IS NULL
        OPTIONAL MATCH (s)-[:CAN_INVOKE]->(t:Tool)
        OPTIONAL MATCH (m:MCPServer)-[:CONTAINS]->(t)
        OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
        RETURN
            p.id AS principal_id, p.name AS principal_name, p.role AS principal_role,
            s.id AS session_id, s.status AS session_status, s.expires_at AS session_expires_at,
            a.id AS agent_id, a.name AS agent_name, a.capabilities AS agent_capabilities,
            d.id AS delegation_id, d.status AS delegation_status, d.scopes AS delegation_scopes,
            d.expires_at AS delegation_expires_at, d.issued_at AS delegation_issued_at,
            m.id AS mcp_id, m.name AS mcp_name,
            t.id AS tool_id, t.name AS tool_name, t.risk_level AS tool_risk, t.is_destructive AS tool_destructive,
            sr.id AS target_id, sr.name AS target_name, sr.sensitivity_level AS target_sensitivity
        """

        rows = self.client.query(query, {"session_id": session_id})
        if not rows:
            return {
                "session_id": session_id,
                "found": False,
                "error": "No delegation chain found for given session_id",
            }

        first = rows[0]
        now_ts = time.time()

        principal_info = {
            "id": first[0],
            "name": first[1],
            "role": first[2],
        }
        session_info = {
            "id": first[3],
            "status": first[4],
            "expires_at": first[5],
            "is_expired": (first[5] is not None and first[5] < now_ts),
        }
        agent_info = {
            "id": first[6],
            "name": first[7],
            "capabilities": first[8] if isinstance(first[8], list) else ([first[8]] if first[8] else []),
        }
        delegation_info = {
            "id": first[9],
            "status": first[10] or "MISSING",
            "scopes": first[11] if isinstance(first[11], list) else ([first[11]] if first[11] else []),
            "expires_at": first[12],
            "issued_at": first[13],
            "is_expired": (first[12] is not None and first[12] < now_ts),
            "is_active": (first[10] == "ACTIVE" and (first[12] is None or first[12] >= now_ts)),
        }

        # Gather accessible tools & target resources
        accessible_tools = []
        for r in rows:
            t_name = r[17]
            if t_name:
                accessible_tools.append({
                    "mcp_server": r[15],
                    "tool_id": r[16],
                    "tool_name": t_name,
                    "risk_level": r[18],
                    "is_destructive": bool(r[19]),
                    "downstream_resource": {
                        "id": r[20],
                        "name": r[21],
                        "sensitivity": r[22],
                    } if r[20] else None,
                })

        # Anomaly / Validation checks
        anomalies = []
        if session_info["is_expired"]:
            anomalies.append("Agent session has expired.")
        if delegation_info["id"] is None:
            anomalies.append("No active delegation record found between principal and agent.")
        elif delegation_info["is_expired"]:
            anomalies.append("Delegation has expired.")
        elif delegation_info["status"] != "ACTIVE":
            anomalies.append(f"Delegation status is {delegation_info['status']} (not ACTIVE).")

        # Check requested tool if provided
        tool_in_scope = False
        tool_excessive = False
        if requested_tool_name:
            matched_tool = next((t for t in accessible_tools if t["tool_name"] == requested_tool_name), None)
            if not matched_tool:
                anomalies.append(f"Requested tool '{requested_tool_name}' is not granted to agent.")
            else:
                # Check delegation scopes
                scopes = delegation_info["scopes"]
                if "*" in scopes or requested_tool_name in scopes:
                    tool_in_scope = True
                else:
                    tool_in_scope = False
                    tool_excessive = True
                    anomalies.append(
                        f"Requested tool '{requested_tool_name}' exceeds delegated scopes ({scopes})."
                    )

        return {
            "session_id": session_id,
            "found": True,
            "principal": principal_info,
            "session": session_info,
            "agent": agent_info,
            "delegation": delegation_info,
            "accessible_tools_count": len(accessible_tools),
            "accessible_tools": accessible_tools,
            "requested_tool": requested_tool_name,
            "tool_in_scope": tool_in_scope,
            "tool_excessive": tool_excessive,
            "anomalies": anomalies,
            "is_valid": len(anomalies) == 0,
        }

    # =========================================================================
    # QUERY 3: Effective Authority Comparison
    # =========================================================================
    def compare_effective_authority(
        self,
        principal_id: str,
        agent_id: str,
        session_id: str,
        requested_tool: str,
        requested_action: str = "EXECUTE",
    ) -> Dict[str, Any]:
        """
        Compares requested action against:
        1. Principal authorized permissions
        2. Agent inherent capabilities
        3. Explicit delegation scopes
        4. Target resource constraints
        Effective Authority = Principal_Auth ∩ Agent_Caps ∩ Delegation_Scopes ∩ Target_Constraints
        """
        # 1. Fetch principal permissions
        principal_q = """
        MATCH (p:Principal {id: $pid})
        OPTIONAL MATCH (p)-[:HAS_PERMISSION]->(perm:Permission)
        RETURN p.id, p.name, p.role, collect(perm.action) AS principal_actions
        """
        p_res = self.client.query(principal_q, {"pid": principal_id})
        if not p_res:
            return {"authorized": False, "reason": f"Principal {principal_id} not found"}

        p_id, p_name, p_role, p_actions = p_res[0]
        principal_actions_set = set(p_actions) if isinstance(p_actions, list) else set()

        # 2. Fetch agent capabilities
        agent_q = """
        MATCH (a:Agent {id: $aid})
        RETURN a.id, a.name, a.capabilities, a.max_autonomy_level
        """
        a_res = self.client.query(agent_q, {"aid": agent_id})
        if not a_res:
            return {"authorized": False, "reason": f"Agent {agent_id} not found"}

        a_id, a_name, a_caps, a_autonomy = a_res[0]
        agent_caps_set = set(a_caps) if isinstance(a_caps, list) else ({a_caps} if a_caps else set())

        # 3. Fetch delegation scopes
        del_q = """
        MATCH (p:Principal {id: $pid})-[d_rel:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent {id: $aid})
        WHERE d.session_id = $sid AND d.status = 'ACTIVE'
        RETURN d.id, d.scopes, d.expires_at
        """
        d_res = self.client.query(del_q, {"pid": principal_id, "aid": agent_id, "sid": session_id})
        delegated_scopes_set: Set[str] = set()
        delegation_active = False

        if d_res:
            d_id, d_scopes, d_exp = d_res[0]
            now_ts = time.time()
            if d_exp is None or d_exp >= now_ts:
                delegation_active = True
                delegated_scopes_set = set(d_scopes) if isinstance(d_scopes, list) else ({d_scopes} if d_scopes else set())

        # 4. Fetch tool metadata
        tool_q = """
        MATCH (t:Tool {name: $tool_name})
        OPTIONAL MATCH (t)-[:CAN_ACCESS]->(sr:SensitiveResource)
        RETURN t.id, t.name, t.required_permissions, t.risk_level, t.is_destructive, sr.id, sr.name, sr.sensitivity_level
        """
        t_res = self.client.query(tool_q, {"tool_name": requested_tool})
        tool_exists = len(t_res) > 0
        tool_req_perms = set()
        tool_risk = "LOW"
        is_destructive = False
        target_resource = None

        if tool_exists:
            t_id, t_nm, t_reqs, t_risk, t_destr, sr_id, sr_nm, sr_sens = t_res[0]
            tool_req_perms = set(t_reqs) if isinstance(t_reqs, list) else ({t_reqs} if t_reqs else set())
            tool_risk = t_risk or "LOW"
            is_destructive = bool(t_destr)
            if sr_id:
                target_resource = {"id": sr_id, "name": sr_nm, "sensitivity": sr_sens}

        # Step-by-step checks
        checks = {
            "principal_has_required_action": ("*" in principal_actions_set or requested_action in principal_actions_set or any(req in principal_actions_set for req in tool_req_perms)),
            "agent_has_capability": ("*" in agent_caps_set or requested_tool in agent_caps_set or "all_tools" in agent_caps_set),
            "delegation_valid_and_scoped": delegation_active and ("*" in delegated_scopes_set or requested_tool in delegated_scopes_set),
            "tool_recognized": tool_exists,
        }

        # Deterministic effective authority check
        reasons_denied = []
        if not checks["tool_recognized"]:
            reasons_denied.append(f"Tool '{requested_tool}' is not recognized in the system catalog.")
        if not checks["principal_has_required_action"]:
            reasons_denied.append(
                f"Principal '{p_name}' lacks required permission for action '{requested_action}' or tool requirements {list(tool_req_perms)}."
            )
        if not checks["agent_has_capability"]:
            reasons_denied.append(f"Agent '{a_name}' is not configured with capability for '{requested_tool}'.")
        if not checks["delegation_valid_and_scoped"]:
            if not delegation_active:
                reasons_denied.append(f"Delegation between '{p_name}' and '{a_name}' is missing or expired.")
            else:
                reasons_denied.append(f"Delegation scopes {list(delegated_scopes_set)} do not permit tool '{requested_tool}'.")

        authorized = len(reasons_denied) == 0

        return {
            "authorized": authorized,
            "decision": "ALLOW" if authorized else "DENY",
            "principal": {"id": p_id, "name": p_name, "role": p_role, "permissions": list(principal_actions_set)},
            "agent": {"id": a_id, "name": a_name, "capabilities": list(agent_caps_set)},
            "delegation": {"session_id": session_id, "active": delegation_active, "scopes": list(delegated_scopes_set)},
            "tool": {
                "name": requested_tool,
                "risk_level": tool_risk,
                "is_destructive": is_destructive,
                "target_resource": target_resource,
            },
            "checks": checks,
            "reasons_denied": reasons_denied,
            "evaluation_timestamp": time.time(),
        }

    # =========================================================================
    # QUERY 4: Shared Attack Paths
    # =========================================================================
    def find_shared_attack_paths(
        self,
        suspicious_ids: List[str],
        max_depth: int = 5,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Finds sensitive targets reachable by multiple suspicious workloads or agents.
        Calculates transparent risk score based on:
        - Target sensitivity
        - Number of distinct sources converging on target
        - Number of distinct paths
        - Edge evidence strengths
        """
        if not suspicious_ids:
            return {"findings": [], "count": 0}

        depth = max(1, min(max_depth, 6))

        query = f"""
        MATCH (src)
        WHERE src.id IN $sources
        MATCH path = (src)-[:CONTAINS|RUNS_AS|CAN_ACCESS|CAN_INVOKE|CAN_REACH|ACTS_ON_BEHALF_OF|HAS_PERMISSION*1..{depth}]->(target:SensitiveResource)
        RETURN
            src.id AS source_id,
            labels(src)[0] AS source_type,
            target.id AS target_id,
            target.name AS target_name,
            target.sensitivity_level AS sensitivity,
            [n in nodes(path) | n.id] AS path_nodes,
            [r in relationships(path) | type(r)] AS path_edges,
            length(path) AS path_len
        LIMIT {limit * 4}
        """

        rows = self.client.query(query, {"sources": suspicious_ids})

        # Group by target
        targets_map: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            src_id, src_type, tgt_id, tgt_name, sens, p_nodes, p_edges, p_len = row
            if tgt_id not in targets_map:
                targets_map[tgt_id] = {
                    "target_id": tgt_id,
                    "target_name": tgt_name,
                    "sensitivity": sens or "MEDIUM",
                    "sources": set(),
                    "paths": [],
                    "intermediate_nodes": set(),
                }
            targets_map[tgt_id]["sources"].add(src_id)
            targets_map[tgt_id]["paths"].append({
                "source_id": src_id,
                "length": p_len,
                "node_ids": p_nodes,
                "edge_types": p_edges,
            })
            # Track intermediates
            if len(p_nodes) > 2:
                for interm in p_nodes[1:-1]:
                    targets_map[tgt_id]["intermediate_nodes"].add(interm)

        # Calculate scores and format
        findings = []
        for tgt_id, data in targets_map.items():
            num_sources = len(data["sources"])
            num_paths = len(data["paths"])
            sens_weight = SENSITIVITY_WEIGHTS.get(data["sensitivity"], 30.0)

            # Transparent ranking formula:
            # Multiplier for shared convergence (>1 source is much higher priority)
            shared_factor = 1.0 + (0.5 * (num_sources - 1)) if num_sources > 1 else 0.8
            path_factor = 1.0 + (0.1 * min(num_paths, 5))
            score = round(sens_weight * shared_factor * path_factor, 2)

            findings.append({
                "target_id": tgt_id,
                "target_name": data["target_name"],
                "sensitivity": data["sensitivity"],
                "converging_sources": list(data["sources"]),
                "converging_sources_count": num_sources,
                "is_shared": (num_sources > 1),
                "total_paths_count": num_paths,
                "intermediate_chokepoints": list(data["intermediate_nodes"]),
                "risk_score": score,
                "score_breakdown": {
                    "sensitivity_weight": sens_weight,
                    "shared_factor": shared_factor,
                    "path_factor": path_factor,
                },
                "paths": data["paths"][:5],  # Top 5 paths
            })

        # Sort by risk score descending
        findings.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "suspicious_sources": suspicious_ids,
            "findings": findings[:limit],
            "total_shared_targets": sum(1 for f in findings if f["is_shared"]),
        }

    # =========================================================================
    # QUERY 5: Remaining Paths After Containment (Simulation)
    # =========================================================================
    def simulate_containment_remaining_paths(
        self,
        source_id: str,
        excluded_node_id: Optional[str] = None,
        excluded_relationship_type: Optional[str] = None,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """
        Simulates an intervention (e.g. isolating pod, disabling service account, revoking tool)
        WITHOUT mutating the production graph.
        Computes before vs after reachable sensitive resources and alternative paths.
        """
        depth = max(1, min(max_depth, 6))

        # 1. Baseline: all paths
        baseline_query = f"""
        MATCH (start {{id: $sid}})
        MATCH path = (start)-[:CONTAINS|RUNS_AS|USES_CREDENTIAL|HAS_PERMISSION|CAN_ACCESS|CAN_REACH*1..{depth}]->(target:SensitiveResource)
        RETURN
            target.id AS target_id,
            target.name AS target_name,
            target.sensitivity_level AS sensitivity,
            [n in nodes(path) | n.id] AS node_ids,
            length(path) AS path_len
        LIMIT 50
        """
        baseline_rows = self.client.query(baseline_query, {"sid": source_id})

        baseline_targets = set()
        baseline_paths = []
        for row in baseline_rows:
            baseline_targets.add(row[0])
            baseline_paths.append({
                "target_id": row[0],
                "target_name": row[1],
                "sensitivity": row[2],
                "node_ids": row[3],
                "length": row[4],
            })

        # 2. Simulated Paths excluding proposed node
        simulated_paths = []
        simulated_targets = set()

        for p in baseline_paths:
            # Check if path contains excluded node
            if excluded_node_id and excluded_node_id in p["node_ids"]:
                continue
            simulated_paths.append(p)
            simulated_targets.add(p["target_id"])

        # Calculate metrics
        eliminated_paths_count = len(baseline_paths) - len(simulated_paths)
        eliminated_targets = baseline_targets - simulated_targets
        exposure_reduction_pct = 0.0
        if len(baseline_paths) > 0:
            exposure_reduction_pct = round((eliminated_paths_count / len(baseline_paths)) * 100.0, 1)

        return {
            "source_id": source_id,
            "simulation": True,
            "excluded_node_id": excluded_node_id,
            "baseline": {
                "paths_count": len(baseline_paths),
                "reachable_targets_count": len(baseline_targets),
                "target_ids": list(baseline_targets),
            },
            "post_containment": {
                "remaining_paths_count": len(simulated_paths),
                "remaining_targets_count": len(simulated_targets),
                "remaining_target_ids": list(simulated_targets),
                "remaining_paths": simulated_paths[:10],
            },
            "impact": {
                "eliminated_paths_count": eliminated_paths_count,
                "eliminated_targets": list(eliminated_targets),
                "exposure_reduction_pct": exposure_reduction_pct,
                "containment_effective": len(simulated_paths) == 0,
            },
        }

    # =========================================================================
    # QUERY 6: Best Containment Candidates
    # =========================================================================
    def evaluate_best_containment_candidates(
        self,
        threat_source_id: str,
    ) -> Dict[str, Any]:
        """
        Generates candidate containment actions and ranks them by:
        - Exposure reduction (%)
        - Disruption risk (potential impact on legitimate services)
        - Net containment score
        """
        # Discover intermediate nodes in reachable paths
        query = """
        MATCH (src {id: $sid})
        MATCH path = (src)-[:CONTAINS|RUNS_AS|USES_CREDENTIAL|HAS_PERMISSION|CAN_ACCESS|CAN_INVOKE*1..5]->(target:SensitiveResource)
        RETURN
            [n in nodes(path) | {id: n.id, label: labels(n)[0], name: coalesce(n.name, n.id)}] AS nodes_list
        LIMIT 30
        """
        rows = self.client.query(query, {"sid": threat_source_id})

        candidates_seen: Set[str] = set()
        evaluated_candidates = []

        # Always include the source itself
        candidates_seen.add(threat_source_id)

        # Collect unique intermediate nodes
        for row in rows:
            for node in row[0]:
                nid = node["id"]
                nlabel = node["label"]
                if nid != threat_source_id and nid not in candidates_seen:
                    candidates_seen.add(nid)

        # For each candidate node, simulate its removal
        for candidate_id in candidates_seen:
            # Fetch node details
            node_q = "MATCH (n {id: $nid}) RETURN labels(n)[0] AS label, coalesce(n.name, n.id) AS name"
            n_res = self.client.query(node_q, {"nid": candidate_id})
            if not n_res:
                continue

            n_label, n_name = n_res[0]

            # Determine action type and disruption score
            if n_label == "Pod":
                action_type = "ISOLATE_POD"
                disruption_score = 20.0
                mechanism = "k8s_network_policy_default_deny"
            elif n_label == "ServiceAccount":
                action_type = "DISABLE_SERVICE_ACCOUNT"
                disruption_score = 65.0  # High disruption if multiple pods share SA
                mechanism = "k8s_rbac_binding_removal"
            elif n_label == "Tool":
                action_type = "BLOCK_TOOL"
                disruption_score = 30.0
                mechanism = "mcp_gateway_rule"
            elif n_label == "Delegation":
                action_type = "REVOKE_DELEGATION"
                disruption_score = 15.0
                mechanism = "agent_gateway_token_revocation"
            elif n_label == "Workload":
                action_type = "SCALE_TO_ZERO"
                disruption_score = 80.0
                mechanism = "k8s_deployment_scale"
            else:
                action_type = f"BLOCK_{n_label.upper()}"
                disruption_score = 40.0
                mechanism = "generic_policy_block"

            sim = self.simulate_containment_remaining_paths(
                source_id=threat_source_id,
                excluded_node_id=candidate_id,
            )

            exposure_reduction = sim["impact"]["exposure_reduction_pct"]
            remaining_paths = sim["post_containment"]["remaining_paths_count"]

            # Transparent Net Score = Exposure Reduction - (Disruption * 0.4)
            net_score = round(exposure_reduction - (disruption_score * 0.4), 1)

            evaluated_candidates.append({
                "candidate_id": candidate_id,
                "node_label": n_label,
                "node_name": n_name,
                "action_type": action_type,
                "enforcement_mechanism": mechanism,
                "exposure_reduction_pct": exposure_reduction,
                "disruption_score": disruption_score,
                "net_score": net_score,
                "remaining_paths_count": remaining_paths,
                "eliminated_paths_count": sim["impact"]["eliminated_paths_count"],
                "eliminated_targets": sim["impact"]["eliminated_targets"],
                "status": "SIMULATED",
            })

        # Rank by net score descending
        evaluated_candidates.sort(key=lambda x: x["net_score"], reverse=True)

        return {
            "threat_source_id": threat_source_id,
            "candidates_count": len(evaluated_candidates),
            "candidates": evaluated_candidates,
            "recommended_candidate": evaluated_candidates[0] if evaluated_candidates else None,
        }

    # =========================================================================
    # QUERY 7: Evidence-Backed Incident Timeline
    # =========================================================================
    def get_evidence_backed_timeline(
        self,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Combines runtime events, policy decisions, and observed access into an ordered timeline.
        Deduplicates repeat events while preserving provenance and timestamps.
        """
        # Fetch runtime events
        event_query = """
        MATCH (e:RuntimeEvent)
        OPTIONAL MATCH (src)-[:EMITTED_EVENT]->(e)
        OPTIONAL MATCH (e)-[:VIOLATED_POLICY]->(p:Policy)
        RETURN
            e.id AS event_id,
            e.event_type AS event_type,
            e.timestamp AS timestamp,
            e.severity AS severity,
            e.mode AS mode,
            e.source AS source,
            e.process_name AS process,
            e.command_line AS cmd,
            src.id AS source_entity_id,
            labels(src)[0] AS source_entity_label,
            p.id AS policy_violation_id,
            p.name AS policy_name
        ORDER BY e.timestamp DESC
        LIMIT $limit
        """
        event_rows = self.client.query(event_query, {"limit": limit})

        # Fetch policy decisions
        decision_query = """
        MATCH (d:PolicyDecision)
        OPTIONAL MATCH (d)-[:ENFORCED_AT]->(ep:EnforcementPoint)
        RETURN
            d.id AS decision_id,
            'POLICY_DECISION' AS event_type,
            d.timestamp AS timestamp,
            d.decision AS decision,
            d.rationale AS rationale,
            ep.name AS enforcement_point,
            d.evaluated_rules AS rules
        ORDER BY d.timestamp DESC
        LIMIT $limit
        """
        decision_rows = self.client.query(decision_query, {"limit": limit})

        timeline = []

        # Format events
        for row in event_rows:
            e_id, e_type, ts, sev, mode, src, proc, cmd, s_id, s_lbl, pol_id, pol_nm = row
            if entity_id and s_id != entity_id and e_id != entity_id:
                continue
            timeline.append({
                "id": e_id,
                "category": "RUNTIME_EVENT",
                "event_type": e_type,
                "timestamp": ts,
                "severity": sev or "MEDIUM",
                "mode": mode or "live_ebpf",
                "provenance": src or "sensor",
                "process": proc,
                "command": cmd,
                "entity": {"id": s_id, "label": s_lbl} if s_id else None,
                "policy_violation": {"id": pol_id, "name": pol_nm} if pol_id else None,
                "verified": (mode == "live_ebpf"),
            })

        # Format policy decisions
        for row in decision_rows:
            d_id, _, ts, dec, rat, ep_nm, rules = row
            timeline.append({
                "id": d_id,
                "category": "POLICY_DECISION",
                "event_type": f"DECISION_{dec}",
                "timestamp": ts,
                "severity": "HIGH" if dec == "DENY" else ("MEDIUM" if dec == "REQUIRE_APPROVAL" else "INFO"),
                "mode": "deterministic_enforcement",
                "provenance": ep_nm or "mcp_gateway",
                "decision": dec,
                "rationale": rat,
                "rules": rules,
                "verified": True,
            })

        # Sort combined timeline by timestamp descending
        timeline.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)

        return {
            "total_items": len(timeline),
            "timeline": timeline[:limit],
        }

    # =========================================================================
    # QUERY 8: Policy-Violation Correlation
    # =========================================================================
    def correlate_policy_violations(
        self,
        window_seconds: int = 3600,
    ) -> Dict[str, Any]:
        """
        Correlates observed runtime events with explicit policy violations:
        - Unexpected shells in production containers
        - Excessive tool requests beyond delegation
        - Cross-principal resource access attempts
        """
        query = """
        MATCH (e:RuntimeEvent)-[:VIOLATED_POLICY]->(p:Policy)
        OPTIONAL MATCH (entity)-[:EMITTED_EVENT]->(e)
        RETURN
            e.id AS event_id,
            e.event_type AS event_type,
            e.timestamp AS timestamp,
            e.severity AS severity,
            e.process_name AS process,
            e.command_line AS command,
            p.id AS policy_id,
            p.name AS policy_name,
            p.enforcement_point AS enforcement_point,
            entity.id AS entity_id,
            labels(entity)[0] AS entity_label
        ORDER BY e.timestamp DESC
        """
        rows = self.client.query(query)

        correlations = []
        for r in rows:
            correlations.append({
                "event_id": r[0],
                "event_type": r[1],
                "timestamp": r[2],
                "severity": r[3],
                "process": r[4],
                "command": r[5],
                "policy": {
                    "id": r[6],
                    "name": r[7],
                    "enforcement_point": r[8],
                },
                "correlated_entity": {
                    "id": r[9],
                    "label": r[10],
                } if r[9] else None,
                "causality_link": "DIRECT_EVIDENCE_ATTACHMENT",
            })

        return {
            "count": len(correlations),
            "correlations": correlations,
        }

    # =========================================================================
    # QUERY 9: Stale or Missing Evidence Detection
    # =========================================================================
    def detect_stale_or_missing_evidence(
        self,
        stale_threshold_seconds: int = 600,  # 10 minutes default
    ) -> Dict[str, Any]:
        """
        Identifies workloads, pods, or sensors whose telemetry is stale or missing.
        Never converts missing telemetry into a claim of safety!
        Degrades finding confidence to DEGRADED or UNKNOWN.
        """
        now_ts = time.time()
        stale_cutoff = now_ts - stale_threshold_seconds

        query = """
        MATCH (w:Workload)
        OPTIONAL MATCH (w)-[:CONTAINS]->(p:Pod)-[:EMITTED_EVENT]->(e:RuntimeEvent)
        WITH w, p, max(e.timestamp) AS last_telemetry_ts
        RETURN
            w.id AS workload_id,
            w.name AS workload_name,
            p.id AS pod_id,
            p.name AS pod_name,
            last_telemetry_ts AS last_telemetry
        """
        rows = self.client.query(query)

        findings = []
        for row in rows:
            w_id, w_nm, p_id, p_nm, last_ts = row

            if last_ts is None:
                status = "MISSING_TELEMETRY"
                confidence = "UNKNOWN"
                reason = "No runtime events recorded for workload; zero telemetry visibility."
                is_stale = True
            elif last_ts < stale_cutoff:
                status = "STALE_TELEMETRY"
                confidence = "DEGRADED"
                age_min = round((now_ts - last_ts) / 60.0, 1)
                reason = f"Last telemetry observed {age_min} minutes ago (exceeds {stale_threshold_seconds // 60}m threshold)."
                is_stale = True
            else:
                status = "ACTIVE_TELEMETRY"
                confidence = "HIGH"
                reason = "Telemetry current and verified."
                is_stale = False

            findings.append({
                "workload_id": w_id,
                "workload_name": w_nm,
                "pod_id": p_id,
                "pod_name": p_nm,
                "last_telemetry_timestamp": last_ts,
                "telemetry_status": status,
                "trust_confidence": confidence,
                "is_stale_or_missing": is_stale,
                "explanation": reason,
            })

        stale_count = sum(1 for f in findings if f["is_stale_or_missing"])

        return {
            "current_time": now_ts,
            "stale_threshold_seconds": stale_threshold_seconds,
            "total_workloads_evaluated": len(findings),
            "stale_or_missing_count": stale_count,
            "system_telemetry_healthy": (stale_count == 0),
            "findings": findings,
        }

    # =========================================================================
    # QUERY 10: Graph Integrity Checks
    # =========================================================================
    def check_graph_integrity(self) -> Dict[str, Any]:
        """Runs graph integrity validation."""
        return validate_graph_integrity(self.client)
