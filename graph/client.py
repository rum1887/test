"""
FalkorDB Client and Connection Manager for Runtime Trust Layer.
Provides resilient connection management, health checks, parameterized query execution,
and fail-closed handling during database outages.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional
from falkordb import FalkorDB

logger = logging.getLogger("trustlayer.graph")

class GraphClient:
    """Encapsulates FalkorDB connection and graph operations."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        graph_name: str = "runtime_trust_layer",
    ):
        self.host = host or os.getenv("FALKORDB_HOST", "localhost")
        self.port = port or int(os.getenv("FALKORDB_PORT", "6379"))
        self.password = password or os.getenv("FALKORDB_PASSWORD", None)
        self.graph_name = graph_name or os.getenv("FALKORDB_GRAPH", "runtime_trust_layer")
        self._db: Optional[FalkorDB] = None
        self._graph = None
        self._last_health_check: float = 0
        self._is_healthy: bool = False
        self._last_error: Optional[str] = None

    def connect(self) -> None:
        """Establish connection to FalkorDB."""
        try:
            self._db = FalkorDB(
                host=self.host,
                port=self.port,
                password=self.password,
            )
            self._graph = self._db.select_graph(self.graph_name)
            self._is_healthy = True
            self._last_error = None
            self._last_health_check = time.time()
            logger.info(f"Connected to FalkorDB at {self.host}:{self.port}, graph: '{self.graph_name}'")
        except Exception as e:
            self._is_healthy = False
            self._last_error = str(e)
            logger.error(f"Failed to connect to FalkorDB at {self.host}:{self.port}: {e}")
            raise

    @property
    def graph(self):
        """Return the active graph instance, connecting if necessary."""
        if self._graph is None or not self._is_healthy:
            self.connect()
        return self._graph

    def is_alive(self) -> bool:
        """Check if FalkorDB is reachable."""
        try:
            if self._graph is None:
                self.connect()
            res = self._graph.query("RETURN 1 AS ping")
            self._is_healthy = (len(res.result_set) == 1 and res.result_set[0][0] == 1)
            self._last_error = None
        except Exception as e:
            self._is_healthy = False
            self._last_error = str(e)
        self._last_health_check = time.time()
        return self._is_healthy

    def get_health_status(self) -> Dict[str, Any]:
        """Return structured health diagnostic."""
        alive = self.is_alive()
        return {
            "healthy": alive,
            "host": self.host,
            "port": self.port,
            "graph_name": self.graph_name,
            "last_check_timestamp": self._last_health_check,
            "last_error": self._last_error,
        }

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None, ignore_errors: bool = False) -> List[List[Any]]:
        """
        Execute a parameterized Cypher query.
        Returns the raw result set (rows).
        Fails closed with a clear exception if DB is unreachable.
        """
        try:
            g = self.graph
            res = g.query(cypher, params or {})
            return res.result_set
        except Exception as e:
            if ignore_errors:
                return []
            self._is_healthy = False
            self._last_error = str(e)
            logger.error(f"FalkorDB query failed: {e}\nQuery: {cypher}\nParams: {params}")
            raise RuntimeError(f"FalkorDB query execution error: {e}") from e

    def query_with_headers(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a query and return column headers along with rows."""
        try:
            g = self.graph
            res = g.query(cypher, params or {})
            header = getattr(res, "header", [])
            headers = [h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else str(h) for h in header]
            rows = res.result_set or []
            return {
                "headers": headers,
                "rows": rows,
                "count": len(rows),
            }
        except Exception as e:
            self._is_healthy = False
            self._last_error = str(e)
            raise RuntimeError(f"FalkorDB query execution error: {e}") from e

    def delete_graph(self) -> None:
        """Wipe all nodes and relationships cleanly."""
        try:
            self.query("MATCH (n) DETACH DELETE n")
            logger.info(f"Wiped all nodes in graph '{self.graph_name}'")
        except Exception as e:
            logger.warning(f"Error while wiping graph '{self.graph_name}': {e}")


# Singleton instance
_default_client: Optional[GraphClient] = None

def get_graph_client(host: Optional[str] = None, port: Optional[int] = None) -> GraphClient:
    global _default_client
    if _default_client is None:
        _default_client = GraphClient(host=host, port=port)
    return _default_client
