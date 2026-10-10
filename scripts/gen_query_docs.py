#!/usr/bin/env python3
"""
Generates Markdown documentation of all Cypher queries from docstrings in backend/app/graph/queries.py.
"""

import inspect
import sys
from pathlib import Path

# Ensure repo root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.graph import queries

def generate_query_docs() -> str:
    lines = [
        "# Queries and Graph Algorithms the Product Depends On",
        "",
        "> This document is automatically generated from docstrings and implementations in `backend/app/graph/queries.py`.",
        "",
    ]

    query_functions = [
        queries.entity_context,
        queries.blast_radius,
        queries.path_diff,
        queries.delegation_chain,
        queries.find_convergence,
        queries.simulate_containment,
        queries.recall_similar,
        queries.centrality_rank,
    ]

    for fn in query_functions:
        name = fn.__name__
        doc = inspect.getdoc(fn) or "No docstring provided."
        sig = inspect.signature(fn)

        lines.append(f"## `{name}{sig}`")
        lines.append("")
        lines.append("```text")
        lines.append(doc)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    content = generate_query_docs()
    output_path = ROOT_DIR / "docs" / "QUERIES.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    print(f"Generated query documentation at {output_path}")
