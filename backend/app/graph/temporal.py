"""
Temporal graph helpers and edge validity utilities.
Enforces valid_from, valid_to, provenance, and point-in-time ($at) query semantics.
"""

from typing import Any

from backend.app.graph.client import GraphClient


def temporal_predicate(rel_var: str = "r", at_param: str = "$at") -> str:
    """
    Returns Cypher snippet asserting relationship validity at a given epoch timestamp.
    Handles null valid_from (valid from dawn of time) and null valid_to (currently valid).
    """
    return (
        f"({rel_var}.valid_from IS NULL OR {rel_var}.valid_from <= {at_param}) AND "
        f"({rel_var}.valid_to IS NULL OR {rel_var}.valid_to > {at_param})"
    )


def invalidate_edge(
    client: GraphClient,
    from_id: str,
    to_id: str,
    rel_type: str,
    invalid_at: int,
) -> int:
    """
    Sets valid_to = invalid_at on active matching relationships.
    'Deleting' an edge in Trust Analyst means marking its expiration in history.
    """
    cypher = f"""
    MATCH (a {{id: $from_id}})-[r:{rel_type}]->(b {{id: $to_id}})
    WHERE r.valid_to IS NULL OR r.valid_to > $invalid_at
    SET r.valid_to = $invalid_at
    RETURN count(r) AS updated_count
    """
    res = client.query(cypher, {"from_id": from_id, "to_id": to_id, "invalid_at": invalid_at})
    return res[0][0] if res and res[0] else 0


def create_temporal_edge(
    client: GraphClient,
    from_id: str,
    to_id: str,
    rel_type: str,
    valid_from: int,
    valid_to: int | None = None,
    provenance: str = "configured",
    source: str = "system",
    extra_props: dict[str, Any] | None = None,
) -> None:
    """
    Creates a temporal relationship with explicit provenance and lifetime validity.
    Provenance must be in {'configured', 'observed', 'inferred'}.
    """
    if provenance not in {"configured", "observed", "inferred"}:
        provenance = "configured"

    props = {
        "valid_from": valid_from,
        "valid_to": valid_to,
        "provenance": provenance,
        "source": source,
    }
    if extra_props:
        props.update(extra_props)

    props_str = ", ".join([f"{k}: ${k}" for k in props])
    cypher = f"""
    MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
    CREATE (a)-[r:{rel_type} {{{props_str}}}]->(b)
    RETURN count(r)
    """
    params = {"from_id": from_id, "to_id": to_id, **props}
    client.query(cypher, params)
