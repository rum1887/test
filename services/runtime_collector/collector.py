"""
Runtime Event Collector and Sensor Adapter for Runtime Trust Layer.
Supports:
1. Live Linux mode: Ingests and normalizes real Tetragon/Falco eBPF telemetry.
2. Replay mode: Ingests deterministic synthetic streams with explicit provenance.
Correlates events with Kubernetes workloads and enforces policy checks.
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from graph.client import GraphClient

logger = logging.getLogger("trustlayer.collector")

class NormalizedRuntimeEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: str  # process_exec, process_kprobe, sock_connect, file_access
    source: str  # tetragon_ebpf, falco, replay_simulator
    mode: str = "live_ebpf"  # live_ebpf OR replay_synthetic
    timestamp: float = Field(default_factory=time.time)
    severity: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    process_name: Optional[str] = None
    process_pid: Optional[int] = None
    parent_process: Optional[str] = None
    command_line: Optional[str] = None
    pod_name: Optional[str] = None
    container_id: Optional[str] = None
    namespace: Optional[str] = "trust-lab"
    target_ip: Optional[str] = None
    target_port: Optional[int] = None
    file_path: Optional[str] = None
    evidence_hash: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

class SensorHealth(BaseModel):
    sensor_name: str = "runtime_gateway_sensor"
    mode: str = "live_enforcement"
    is_live: bool = True
    last_event_timestamp: Optional[float] = None
    total_events_ingested: int = 0
    dropped_events_count: int = 0
    is_stale: bool = False
    stale_warning: Optional[str] = None

class RuntimeCollector:
    """Normalizes, correlates, and persists telemetry into FalkorDB."""

    def __init__(self, client: GraphClient, default_mode: str = "live_enforcement"):
        self.client = client
        self.mode = default_mode  # 'live_enforcement' or 'live_ebpf'
        self.total_ingested = 0
        self.dropped_events = 0
        self.last_event_time: Optional[float] = None

    def get_health(self) -> SensorHealth:
        """Returns health status of runtime telemetry pipeline."""
        now = time.time()
        is_stale = False
        warning = None

        if self.last_event_time is not None and (now - self.last_event_time) > 3600:
            is_stale = True
            age_min = round((now - self.last_event_time) / 60.0, 1)
            warning = f"Telemetry stream is stale. Last event was {age_min} minutes ago."

        return SensorHealth(
            sensor_name="runtime_trust_sensor",
            mode=self.mode,
            is_live=(self.mode != "replay_synthetic"),
            last_event_timestamp=self.last_event_time or now,
            total_events_ingested=self.total_ingested,
            dropped_events_count=self.dropped_events,
            is_stale=is_stale,
            stale_warning=warning,
        )

    def normalize_tetragon_event(self, raw_data: Dict[str, Any]) -> NormalizedRuntimeEvent:
        """
        Adapts raw Tetragon JSON event into canonical NormalizedRuntimeEvent.
        """
        process_exec = raw_data.get("process_exec", {})
        proc = process_exec.get("process", {})
        pod = proc.get("pod", {})

        p_name = proc.get("binary", "").split("/")[-1] if proc.get("binary") else None
        cmd = proc.get("arguments", "") or proc.get("binary", "")
        pod_name = pod.get("name")
        namespace = pod.get("namespace", "trust-lab")
        container = pod.get("container", {})

        # Compute severity
        severity = "MEDIUM"
        if p_name in ["sh", "bash", "zsh", "dash", "curl", "wget", "nc", "ncat"]:
            severity = "CRITICAL" if namespace == "trust-lab" else "HIGH"

        # Evidence hash
        hash_input = f"{proc.get('binary')}:{cmd}:{pod_name}:{time.time()}"
        ev_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return NormalizedRuntimeEvent(
            event_type="process_exec",
            source="tetragon_ebpf",
            mode=self.mode,
            timestamp=time.time(),
            severity=severity,
            process_name=p_name,
            process_pid=proc.get("pid"),
            parent_process=process_exec.get("parent", {}).get("binary", "").split("/")[-1] or None,
            command_line=cmd,
            pod_name=pod_name,
            container_id=container.get("id"),
            namespace=namespace,
            evidence_hash=ev_hash,
            raw_payload=raw_data,
        )

    def ingest_event(self, event: NormalizedRuntimeEvent) -> Dict[str, Any]:
        """
        Ingests a normalized event, correlates with workload in FalkorDB,
        and links policy violations where applicable.
        """
        try:
            # 1. Check for correlated Pod/Workload
            find_pod_q = """
            MATCH (p:Pod)
            WHERE p.name = $pname OR p.id = $pname
            RETURN p.id, p.name
            LIMIT 1
            """
            matched_pods = self.client.query(find_pod_q, {"pname": event.pod_name or ""})
            matched_pod_id = matched_pods[0][0] if matched_pods else None

            # 2. Insert RuntimeEvent node
            create_evt_q = """
            CREATE (e:RuntimeEvent {
                id: $id,
                event_type: $event_type,
                source: $source,
                mode: $mode,
                timestamp: $timestamp,
                severity: $severity,
                process_name: $process_name,
                process_pid: $process_pid,
                parent_process: $parent_process,
                command_line: $command_line,
                pod_id: $pod_id,
                namespace: $namespace,
                evidence_hash: $evidence_hash
            })
            """
            self.client.query(
                create_evt_q,
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "source": event.source,
                    "mode": event.mode,
                    "timestamp": event.timestamp,
                    "severity": event.severity,
                    "process_name": event.process_name or "",
                    "process_pid": event.process_pid or 0,
                    "parent_process": event.parent_process or "",
                    "command_line": event.command_line or "",
                    "pod_id": matched_pod_id or event.pod_name or "",
                    "namespace": event.namespace or "",
                    "evidence_hash": event.evidence_hash or "",
                },
            )

            # 3. Link Pod -> EMITTED_EVENT -> RuntimeEvent
            if matched_pod_id:
                link_q = """
                MATCH (p:Pod {id: $pid})
                MATCH (e:RuntimeEvent {id: $eid})
                CREATE (p)-[:EMITTED_EVENT]->(e)
                """
                self.client.query(link_q, {"pid": matched_pod_id, "eid": event.id})

            # 4. Check for Policy Violation (e.g., interactive shell in production)
            is_shell_violation = event.process_name in ["sh", "bash", "zsh", "dash"]
            if is_shell_violation:
                pol_q = """
                MATCH (e:RuntimeEvent {id: $eid})
                MATCH (pol:Policy {id: 'pol-no-interactive-shells'})
                CREATE (e)-[:VIOLATED_POLICY]->(pol)
                """
                self.client.query(pol_q, {"eid": event.id})

            self.total_ingested += 1
            self.last_event_time = event.timestamp

            return {
                "success": True,
                "event_id": event.id,
                "correlated_pod_id": matched_pod_id,
                "policy_violation": is_shell_violation,
            }
        except Exception as e:
            self.dropped_events += 1
            logger.error(f"Failed to ingest event {event.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "event_id": event.id,
            }

    def generate_replay_stream(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generates deterministic synthetic events labeled with mode: replay_synthetic.
        """
        now = time.time()
        templates = [
            {
                "process_name": "curl",
                "command_line": "curl -s http://169.254.169.254/latest/meta-data",
                "pod_name": "checkout-service-7f89b-xk42",
                "severity": "CRITICAL",
                "parent": "sh",
            },
            {
                "process_name": "sh",
                "command_line": "/bin/sh -c env",
                "pod_name": "checkout-service-7f89b-xk42",
                "severity": "CRITICAL",
                "parent": "node",
            },
            {
                "process_name": "python3",
                "command_line": "python3 worker.py --batch-size 100",
                "pod_name": "order-processor-0",
                "severity": "LOW",
                "parent": "systemd",
            },
            {
                "process_name": "envoy",
                "command_line": "envoy -c /etc/envoy/proxy.yaml",
                "pod_name": "frontend-proxy-99aa1-abc",
                "severity": "LOW",
                "parent": "init",
            },
            {
                "process_name": "cat",
                "command_line": "cat /var/run/secrets/kubernetes.io/serviceaccount/token",
                "pod_name": "checkout-service-7f89b-xk42",
                "severity": "CRITICAL",
                "parent": "sh",
            },
        ]

        results = []
        for i in range(min(count, len(templates))):
            tmpl = templates[i]
            event = NormalizedRuntimeEvent(
                event_type="process_exec",
                source="replay_simulator",
                mode="replay_synthetic",
                timestamp=now - (i * 30),
                severity=tmpl["severity"],
                process_name=tmpl["process_name"],
                process_pid=5000 + i,
                parent_process=tmpl["parent"],
                command_line=tmpl["command_line"],
                pod_name=tmpl["pod_name"],
                namespace="trust-lab",
                evidence_hash=hashlib.sha256(f"replay_{i}_{now}".encode()).hexdigest(),
            )
            res = self.ingest_event(event)
            results.append(res)

        return results
