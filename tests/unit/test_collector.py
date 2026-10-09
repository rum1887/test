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
    assert health.total_events_ingested >= 2
