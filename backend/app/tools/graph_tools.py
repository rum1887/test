"""
Graph Tools: Cypher-backed topological exploration and analysis tools for Trust Analyst.
Every tool returns structured data and evidence_id strings citing graph nodes and edges.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.app.graph.client import GraphClient, get_graph_client
from backend.app.graph.queries import (
    blast_radius as q_blast_radius,
)
from backend.app.graph.queries import (
    centrality_rank as q_centrality_rank,
)
from backend.app.graph.queries import (
    delegation_chain as q_delegation_chain,
)
from backend.app.graph.queries import (
    entity_context as q_entity_context,
)
from backend.app.graph.queries import (
    find_convergence as q_find_convergence,
)
from backend.app.graph.queries import (
    path_diff as q_path_diff,
)
from backend.app.graph.queries import (
    shortest_path as q_shortest_path,
)
from backend.app.graph.queries import (
    simulate_containment as q_simulate_containment,
)
from backend.app.tools.registry import ToolContext, ToolResult, registry

# 1. Entity Context


class EntityContextInput(BaseModel):
    entity_id: str = Field(description="Unique ID of the entity node in FalkorDB")
    depth: int = Field(default=1, description="Hop depth for neighborhood expansion")
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class EntityContextOutput(BaseModel):
    center_id: str
    neighbors: list[dict[str, Any]]
    edges: list[dict[str, Any]]


@registry.register(
    name="get_entity_context",
    description="Fetches 1-hop or bounded neighborhood around an entity with relationship provenance.",
    input_schema=EntityContextInput,
    output_schema=EntityContextOutput,
    read_only=True,
    requires_approval=False,
)
def get_entity_context(
    entity_id: str,
    depth: int = 1,
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_entity_context(c, entity_id=entity_id, depth=depth, at=at)
    evidence_ids = [f"ev:node:{entity_id}"]
    for n in data.get("neighbors", []):
        evidence_ids.append(f"ev:node:{n['id']}")
    for e in data.get("edges", []):
        evidence_ids.append(f"ev:edge:{e['source']}->{e['target']}")
    return ToolResult(tool="get_entity_context", success=True, data=data, evidence_ids=evidence_ids)


# 2. Blast Radius


class BlastRadiusInput(BaseModel):
    start_id: str = Field(description="Starting entity ID (e.g. compromised pod or workload)")
    max_depth: int = Field(default=3, description="Maximum traversal depth")
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class BlastRadiusOutput(BaseModel):
    total_reachable: int
    sensitive_resources_count: int
    sensitive_resources: list[dict[str, Any]]
    reachable_nodes: list[dict[str, Any]]


@registry.register(
    name="blast_radius",
    description="Traverses outbound paths to compute all reachable entities and sensitive assets.",
    input_schema=BlastRadiusInput,
    output_schema=BlastRadiusOutput,
    read_only=True,
    requires_approval=False,
)
def blast_radius(
    start_id: str,
    max_depth: int = 3,
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    paths = q_blast_radius(c, start_id=start_id, max_hops=max_depth, at=at)

    seen_nodes = set()
    reachable_nodes = []
    seen_sr = set()
    sensitive_resources = []
    for p in paths:
        for nid in p.get("path_node_ids", []):
            if nid not in seen_nodes:
                seen_nodes.add(nid)
                reachable_nodes.append({"id": nid})
        tid = p.get("target_id")
        if tid and tid not in seen_sr:
            seen_sr.add(tid)
            sensitive_resources.append({"id": tid, "name": p.get("target_name"), "sensitivity": p.get("sensitivity")})

    data = {
        "total_reachable": len(reachable_nodes),
        "sensitive_resources_count": len(sensitive_resources),
        "sensitive_resources": sensitive_resources,
        "reachable_nodes": reachable_nodes,
    }
    evidence_ids = [f"ev:node:{start_id}"]
    for sr in sensitive_resources:
        evidence_ids.append(f"ev:node:{sr['id']}")
    for rn in reachable_nodes:
        evidence_ids.append(f"ev:node:{rn['id']}")
    return ToolResult(tool="blast_radius", success=True, data=data, evidence_ids=evidence_ids)


# 3. Path Diff


class PathDiffInput(BaseModel):
    workload_id: str = Field(description="Workload ID to compare access paths for")
    at_t1: int = Field(description="Prior epoch timestamp (e.g. before change)")
    at_t2: int = Field(description="Later epoch timestamp (e.g. after change)")


class PathDiffOutput(BaseModel):
    workload_id: str
    new_paths: list[dict[str, Any]]
    removed_paths: list[dict[str, Any]]


@registry.register(
    name="path_diff",
    description="Calculates delta of reachability paths to sensitive assets between two timestamps.",
    input_schema=PathDiffInput,
    output_schema=PathDiffOutput,
    read_only=True,
    requires_approval=False,
)
def path_diff(
    workload_id: str,
    at_t1: int,
    at_t2: int,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_path_diff(c, workload_id=workload_id, at_t1=at_t1, at_t2=at_t2)
    evidence_ids = [f"ev:node:{workload_id}"]
    for p in data.get("new_paths", []):
        evidence_ids.append(f"ev:path:{p.get('target_id')}")
    return ToolResult(tool="path_diff", success=True, data=data, evidence_ids=evidence_ids)


# 4. Delegation Chain


class DelegationChainInput(BaseModel):
    session_id: str = Field(description="AgentSession ID")
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class DelegationChainOutput(BaseModel):
    session_id: str
    status: str
    principal: dict[str, Any] | None
    agent: dict[str, Any] | None
    delegation: dict[str, Any] | None
    permitted_tools: list[dict[str, Any]]


@registry.register(
    name="delegation_chain",
    description="Resolves full authorization provenance from AgentSession back to human Principal and scopes.",
    input_schema=DelegationChainInput,
    output_schema=DelegationChainOutput,
    read_only=True,
    requires_approval=False,
)
def delegation_chain(
    session_id: str,
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_delegation_chain(c, session_id=session_id, at=at)
    evidence_ids = [f"ev:node:{session_id}"]
    if data.get("principal"):
        evidence_ids.append(f"ev:node:{data['principal']['id']}")
    if data.get("delegation"):
        evidence_ids.append(f"ev:node:{data['delegation']['id']}")
    return ToolResult(tool="delegation_chain", success=True, data=data, evidence_ids=evidence_ids)


# 5. Find Convergence


class FindConvergenceInput(BaseModel):
    source_ids: list[str] = Field(default_factory=list, description="Optional starting node IDs")
    max_depth: int = Field(default=4, description="Maximum traversal depth")
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class FindConvergenceOutput(BaseModel):
    convergences: list[dict[str, Any]]


@registry.register(
    name="find_convergence",
    description="Identifies sensitive resources reachable from multiple distinct entry points (choke points).",
    input_schema=FindConvergenceInput,
    output_schema=FindConvergenceOutput,
    read_only=True,
    requires_approval=False,
)
def find_convergence(
    source_ids: list[str] = [],
    max_depth: int = 4,
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    sources = source_ids or ["pod-ci-1", "sess-bob-data", "pod-checkout-1"]
    data = q_find_convergence(c, source_ids=sources, at=at)
    evidence_ids = []
    for item in data:
        evidence_ids.append(f"ev:node:{item['resource_id']}")
    return ToolResult(tool="find_convergence", success=True, data={"convergences": data}, evidence_ids=evidence_ids)


# 6. Shortest Path


class ShortestPathInput(BaseModel):
    start_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Destination entity ID")
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class ShortestPathOutput(BaseModel):
    found: bool
    node_ids: list[str]
    edge_types: list[str]
    length: int


@registry.register(
    name="shortest_path",
    description="Finds the shortest directed path connecting two entities in the security graph.",
    input_schema=ShortestPathInput,
    output_schema=ShortestPathOutput,
    read_only=True,
    requires_approval=False,
)
def shortest_path(
    start_id: str,
    target_id: str,
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_shortest_path(c, start_id=start_id, target_id=target_id, at=at)
    evidence_ids = [f"ev:node:{nid}" for nid in data.get("node_ids", [])]
    return ToolResult(tool="shortest_path", success=True, data=data, evidence_ids=evidence_ids)


# 7. Simulate Containment


class SimulateContainmentInput(BaseModel):
    isolate_nodes: list[str] = Field(default_factory=list, description="List of node IDs to hypothetically isolate")
    revoke_edges: list[dict[str, Any]] = Field(
        default_factory=list, description="List of edges to hypothetically revoke"
    )
    at: int | None = Field(default=None, description="Simulated epoch timestamp filter")


class SimulateContainmentOutput(BaseModel):
    isolated_nodes: list[str]
    remaining_paths_count: int
    exposure_eliminated: bool


@registry.register(
    name="simulate_containment",
    description="Simulates effect of isolating nodes or revoking edges to evaluate remaining blast radius.",
    input_schema=SimulateContainmentInput,
    output_schema=SimulateContainmentOutput,
    read_only=True,
    requires_approval=False,
)
def simulate_containment(
    isolate_nodes: list[str] = [],
    revoke_edges: list[dict[str, Any]] = [],
    at: int | None = None,
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_simulate_containment(c, isolate_nodes=isolate_nodes, revoke_edges=revoke_edges, at=at)
    evidence_ids = [f"ev:node:{nid}" for nid in isolate_nodes]
    return ToolResult(tool="simulate_containment", success=True, data=data, evidence_ids=evidence_ids)


# 8. Centrality Rank


class CentralityRankInput(BaseModel):
    label: str = Field(default="Pod", description="Node label to analyze (Pod, Workload, Tool)")


class CentralityRankOutput(BaseModel):
    ranks: list[dict[str, Any]]


@registry.register(
    name="centrality_rank",
    description="Ranks nodes of a given label by topological degree connectivity and choke point reach.",
    input_schema=CentralityRankInput,
    output_schema=CentralityRankOutput,
    read_only=True,
    requires_approval=False,
)
def centrality_rank(
    label: str = "Pod",
    client: GraphClient | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    c = client or get_graph_client()
    data = q_centrality_rank(c, label=label)
    evidence_ids = [f"ev:node:{r['id']}" for r in data]
    return ToolResult(tool="centrality_rank", success=True, data={"ranks": data}, evidence_ids=evidence_ids)
