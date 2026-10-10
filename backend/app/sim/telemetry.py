"""
Tetragon-like Telemetry Generator, JSONL Logger, and Graph Aggregator.
Aggregates high-volume runtime events into compact EventSummary nodes in FalkorDB.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.graph.client import GraphClient

logger = logging.getLogger("trust_analyst.telemetry")


class TelemetryEvent(BaseModel):
    """Normalized runtime security event matching Cilium Tetragon eBPF telemetry."""

    ts: int
    pod_id: str
    pid: int
    ppid: int
    binary: str
    args: list[str] = Field(default_factory=list)
    kind: str  # exec, connect, file_read, secret_read
    dest: str | None = None
    mode: str = "replay_synthetic"


class TelemetrySource(Protocol):
    """Adapter interface for telemetry sources."""

    def get_events(
        self,
        pod_id: str | None = None,
        kind: str | None = None,
        window_start: int | None = None,
        window_end: int | None = None,
    ) -> list[TelemetryEvent]: ...


# In-memory isolation tracking (environment reactions)
_ISOLATED_PODS: set[str] = set()


def is_pod_isolated(pod_id: str) -> bool:
    """Returns True if pod is currently quarantined/isolated."""
    return pod_id in _ISOLATED_PODS


def isolate_pod(pod_id: str) -> None:
    """Applies network isolation to pod, stopping future egress events."""
    _ISOLATED_PODS.add(pod_id)


def unisolate_pod(pod_id: str) -> None:
    """Removes isolation from pod."""
    _ISOLATED_PODS.discard(pod_id)


def clear_isolations() -> None:
    """Clears all isolation states."""
    _ISOLATED_PODS.clear()


class RecordedJsonlTelemetrySource:
    """Reads telemetry events from JSONL log files."""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path or settings.TELEMETRY_LOG_PATH)

    def clear(self) -> None:
        """Clears the JSONL log file."""
        if self.log_path.exists():
            self.log_path.unlink()

    def append_event(self, event: TelemetryEvent) -> None:
        """Appends a raw event to the JSONL log file (evidence source)."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def get_events(
        self,
        pod_id: str | None = None,
        kind: str | None = None,
        window_start: int | None = None,
        window_end: int | None = None,
    ) -> list[TelemetryEvent]:
        """Queries recorded raw events within time and attribute filters."""
        if not self.log_path.exists():
            return []

        results: list[TelemetryEvent] = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    ev = TelemetryEvent(**data)
                    if pod_id and ev.pod_id != pod_id:
                        continue
                    if kind and ev.kind != kind:
                        continue
                    if window_start is not None and ev.ts < window_start:
                        continue
                    if window_end is not None and ev.ts > window_end:
                        continue
                    results.append(ev)
                except Exception as e:
                    logger.debug(f"Skipping malformed telemetry line: {e}")
        return results

    def get_process_tree(self, pod_id: str, pid: int) -> list[dict[str, Any]]:
        """Walks process ancestry (PID -> PPID) from the raw log for a given pod."""
        events = self.get_events(pod_id=pod_id, kind="exec")
        pid_map: dict[int, TelemetryEvent] = {ev.pid: ev for ev in events}

        tree: list[dict[str, Any]] = []
        curr_pid = pid
        visited = set()

        while curr_pid in pid_map and curr_pid not in visited:
            visited.add(curr_pid)
            ev = pid_map[curr_pid]
            tree.append(
                {
                    "pid": ev.pid,
                    "ppid": ev.ppid,
                    "binary": ev.binary,
                    "args": ev.args,
                    "ts": ev.ts,
                }
            )
            curr_pid = ev.ppid

        return tree


# Default singleton telemetry logger
telemetry_source = RecordedJsonlTelemetrySource()


def reset_telemetry() -> None:
    """Resets in-memory pod isolations and clears recorded JSONL log."""
    clear_isolations()
    telemetry_source.clear()


def emit_event(client: GraphClient, event: TelemetryEvent) -> str:
    """
    Emits a telemetry event:
    1. Checks if pod is isolated (suppresses egress connect events if isolated).
    2. Writes raw event to the JSONL log file.
    3. Aggregates event into an EventSummary node in FalkorDB.
    Returns the EventSummary id.
    """
    # Environment reaction: isolated pods cannot emit egress connect events
    if is_pod_isolated(event.pod_id) and event.kind == "connect":
        logger.info(f"Suppressed connect event from isolated pod: {event.pod_id}")
        return ""

    # 1. Append raw event to JSONL log
    telemetry_source.append_event(event)

    # 2. Compute signature for aggregation: (pod_id, kind, binary, dest)
    sig_raw = f"{event.binary}:{' '.join(event.args)}:{event.dest or ''}"
    sig_hash = hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:8]
    summary_id = f"evsum-{event.pod_id}-{event.kind}-{sig_hash}"

    detail_json = json.dumps(
        {
            "binary": event.binary,
            "args": event.args,
            "dest": event.dest,
            "mode": event.mode,
        }
    )

    # 3. Update or create EventSummary in FalkorDB
    cypher = """
    MATCH (p:Pod {id: $pod_id})
    MERGE (es:EventSummary {id: $summary_id})
    ON CREATE SET
        es.pod_id = $pod_id,
        es.kind = $kind,
        es.first_seen = $ts,
        es.last_seen = $ts,
        es.count = 1,
        es.detail = $detail
    ON MATCH SET
        es.last_seen = $ts,
        es.count = es.count + 1
    MERGE (p)-[r:CONNECTED_TO {valid_from: $ts, provenance: 'observed', source: 'tetragon'}]->(es)
    RETURN es.id
    """
    params = {
        "pod_id": event.pod_id,
        "summary_id": summary_id,
        "kind": event.kind,
        "ts": event.ts,
        "detail": detail_json,
    }
    client.query(cypher, params, ignore_errors=True)

    # If it is a connect event to a known NetworkEndpoint, also maintain direct graph edge
    if event.kind == "connect" and event.dest:
        cypher_net = """
        MATCH (p:Pod {id: $pod_id}), (ne:NetworkEndpoint {id: $dest})
        MERGE (p)-[r:CONNECTED_TO {valid_from: $ts, provenance: 'observed', source: 'tetragon'}]->(ne)
        """
        client.query(cypher_net, {"pod_id": event.pod_id, "dest": event.dest, "ts": event.ts}, ignore_errors=True)

    return summary_id
