"""
Unit and Integration Tests for Runtime Event Collector.
Verifies Tetragon eBPF normalization, pod correlation, and replay stream mode separation.
"""

import pytest
from graph.client import get_graph_client
from graph.fixtures.seeder import seed_scenarios
from services.runtime_collector.collector import (
    RuntimeCollector,
    NormalizedRuntimeEvent,
)

@pytest.fixture(scope="module")
def collector():
    client = get_graph_client()
    seed_scenarios(client)
    return RuntimeCollector(client, default_mode="live_ebpf")

def test_normalize_raw_tetragon_event(collector):
    """Verifies that raw Tetragon process_exec JSON normalizes properly."""
    raw = {
        "process_exec": {
            "process": {
                "binary": "/bin/bash",
                "arguments": "-i",
                "pid": 4120,
                "pod": {
                    "name": "checkout-service-7f89b-xk42",
                    "namespace": "trust-lab",
                    "container": {"id": "cnt-01"},
                },
            },
            "parent": {"binary": "/usr/bin/node"},
        }
    }
    norm = collector.normalize_tetragon_event(raw)
    assert norm.process_name == "bash"
    assert norm.process_pid == 4120
    assert norm.parent_process == "node"
    assert norm.severity == "CRITICAL"
    assert norm.mode == "live_ebpf"
    assert norm.evidence_hash is not None

def test_ingest_event_correlates_with_pod(collector):
    """Verifies that ingested event correlates with existing Pod in FalkorDB."""
    event = NormalizedRuntimeEvent(
        event_type="process_exec",
        source="tetragon_ebpf",
        mode="live_ebpf",
        severity="CRITICAL",
        process_name="sh",
        command_line="/bin/sh",
        pod_name="checkout-service-7f89b-xk42",
        namespace="trust-lab",
    )
    result = collector.ingest_event(event)
    assert result["success"] is True
    assert result["correlated_pod_id"] == "pod-checkout-7f89b"
    assert result["policy_violation"] is True  # Shell execution policy violation!

def test_replay_mode_explicit_labeling():
    """Verifies that Replay Mode events never pretend to be live eBPF."""
    client = get_graph_client()
    replay_collector = RuntimeCollector(client, default_mode="replay_synthetic")
    stream = replay_collector.generate_replay_stream(count=2)
    assert len(stream) == 2

    # Check health reporting
    health = replay_collector.get_health()
    assert health.mode == "replay_synthetic"
    assert health.is_live is False
    assert health.telemetry_provenance == "SYNTHETIC_REPLAY"
    assert health.total_events_ingested >= 2

def test_default_sensor_unattached_reports_fixture_provenance():
    """Verifies that an unattached sensor without a live daemon honestly reports fixture baseline."""
    client = get_graph_client()
    default_collector = RuntimeCollector(client)
    health = default_collector.get_health()
    assert health.is_live is False
    assert health.daemon_attached is False
    assert health.telemetry_provenance == "FIXTURE_BASELINE"
    assert "No live eBPF kernel sensor" in (health.stale_warning or "")

def test_sensor_health_with_live_daemon_env(monkeypatch):
    """Verifies that setting EBPF_SENSOR_ATTACHED=true reports live kernel telemetry."""
    monkeypatch.setenv("EBPF_SENSOR_ATTACHED", "true")
    client = get_graph_client()
    collector = RuntimeCollector(client)
    health = collector.get_health()
    assert health.is_live is True
    assert health.daemon_attached is True
    assert health.telemetry_provenance == "LIVE_KERNEL_TELEMETRY"

def test_seeded_events_have_fixture_baseline_provenance():
    """Verifies that seeded events in FalkorDB do not claim to be live eBPF telemetry."""
    client = get_graph_client()
    seed_scenarios(client)
    rows = client.query("MATCH (e:RuntimeEvent {id: 'evt-ebpf-tetragon-8812'}) RETURN e.mode, e.source")
    assert len(rows) == 1
    assert rows[0][0] == "fixture_baseline"
    assert rows[0][1] == "fixture_tetragon_baseline"
