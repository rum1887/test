"""
FalkorDB Client Wrapper.
Manages connection, parameterized Cypher queries, and graph lifecycle.
"""

import logging
from typing import Any, Dict, List, Optional

from falkordb import FalkorDB

from backend.app.config import settings

logger = logging.getLogger("trust_analyst.graph_client")


class GraphClient:
    """Thread-safe FalkorDB client wrapper with parameterized Cypher queries."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, graph_name: Optional[str] = None):
        self.host = host or settings.FALKORDB_HOST
        self.port = port or settings.FALKORDB_PORT
        self.graph_name = graph_name or settings.FALKORDB_GRAPH
        self._db: Optional[FalkorDB] = None
        self._graph = None

    def _connect(self):
        if self._db is None:
            self._db = FalkorDB(host=self.host, port=self.port)
            self._graph = self._db.select_graph(self.graph_name)

    def is_alive(self) -> bool:
        """Returns True if FalkorDB is reachable and responsive."""
        try:
            self._connect()
            res = self._graph.query("RETURN 1")
            return bool(res and len(res.result_set) > 0)
        except Exception as e:
            logger.warning(f"FalkorDB connectivity check failed: {e}")
            return False

    def query(
        self, cypher: str, params: Optional[Dict[str, Any]] = None, ignore_errors: bool = False
    ) -> List[List[Any]]:
        """
        Executes parameterized Cypher query and returns result rows as list of lists.
        Fails closed on connection error if ignore_errors is False.
        """
        self._connect()
        try:
            # FalkorDB expects params dictionary as second positional argument or keyword
            if params:
                result = self._graph.query(cypher, params)
            else:
                result = self._graph.query(cypher)
            return result.result_set if hasattr(result, "result_set") else []
        except Exception as e:
            if ignore_errors:
                logger.debug(f"Query ignored error: {e} for query: {cypher}")
                return []
            logger.error(f"FalkorDB query error: {e} | Cypher: {cypher} | Params: {params}")
            raise

    def query_dicts(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes Cypher query and maps columns into dictionary records."""
        self._connect()
        result = self._graph.query(cypher, params) if params else self._graph.query(cypher)
        if not hasattr(result, "header") or not hasattr(result, "result_set"):
            return []
        headers = [col[1] if isinstance(col, (list, tuple)) else str(col) for col in result.header]
        return [dict(zip(headers, row)) for row in result.result_set]

    def reset_graph(self) -> None:
        """Deletes the graph and re-initializes an empty graph."""
        try:
            self._connect()
            self._graph.delete()
        except Exception as e:
            logger.warning(f"Reset graph notice: {e}")
        self._db = None
        self._graph = None
        self._connect()


_client_instance: Optional[GraphClient] = None


def get_graph_client() -> GraphClient:
    """Returns singleton GraphClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GraphClient()
    return _client_instance
