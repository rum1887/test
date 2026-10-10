"""
Tests for simulated clock, deterministic world seeder, and Tetragon telemetry aggregation.
"""

from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock
from backend.app.sim.telemetry import (
    TelemetryEvent,
    emit_event,
    isolate_pod,
    telemetry_source,
    unisolate_pod,
)
from backend.app.sim.world import seed_world


def test_clock_advance():
    """Verify simulated clock progresses strictly forward."""
    clock = get_clock()
    clock.reset(1700000000)
    assert clock.now() == 1700000000

    t1 = clock.advance(3600)
    assert t1 == 1700003600
    assert clock.now() == 1700003600


def test_world_determinism():
    """Verify that seeding with the same seed produces identical graph state and hash."""
    client = get_graph_client()

    # Seed run 1
    res1 = seed_world(client, seed=42)
    hash1 = res1["hash"]
    nodes1 = res1["nodes"]
    edges1 = res1["edges"]

    assert nodes1 > 280, f"Expected dense graph, got {nodes1}"
    assert edges1 > 280, f"Expected dense graph, got {edges1}"

    # Seed run 2 with same seed
    res2 = seed_world(client, seed=42)
    hash2 = res2["hash"]
    nodes2 = res2["nodes"]
    edges2 = res2["edges"]

    assert nodes1 == nodes2
    assert edges1 == edges2
    assert hash1 == hash2, "World seeder must be 100% deterministic with fixed seed"


def test_telemetry_aggregation_and_isolation():
    """Verify Tetragon event aggregation into EventSummary and isolation behavior."""
    client = get_graph_client()
    seed_world(client, seed=42)
    unisolate_pod("pod-checkout-1")

    # 1. Emit exec event
    ev1 = TelemetryEvent(
        ts=1700000100,
        pod_id="pod-checkout-1",
        pid=1001,
        ppid=1,
        binary="/bin/sh",
        args=["-c", "whoami"],
        kind="exec",
    )
    sum_id1 = emit_event(client, ev1)
    assert sum_id1.startswith("evsum-pod-checkout-1-exec-")

    # 2. Emit identical exec event -> should aggregate and increment count
    ev2 = TelemetryEvent(
        ts=1700000120,
        pod_id="pod-checkout-1",
        pid=1002,
        ppid=1,
        binary="/bin/sh",
        args=["-c", "whoami"],
        kind="exec",
    )
    sum_id2 = emit_event(client, ev2)
    assert sum_id1 == sum_id2

    res = client.query(
        "MATCH (es:EventSummary {id: $id}) RETURN es.count, es.first_seen, es.last_seen", {"id": sum_id1}
    )
    assert len(res) == 1
    count, first_seen, last_seen = res[0]
    assert count == 2
    assert first_seen == 1700000100
    assert last_seen == 1700000120

    # 3. Test raw log query
    raw_events = telemetry_source.get_events(pod_id="pod-checkout-1", kind="exec")
    assert len(raw_events) >= 2

    # 4. Test isolation reaction on egress connect event
    ev_connect = TelemetryEvent(
        ts=1700000150,
        pod_id="pod-checkout-1",
        pid=1005,
        ppid=1001,
        binary="/bin/nc",
        args=["169.254.169.254", "80"],
        kind="connect",
        dest="169.254.169.254",
    )
    # Before isolation: emitted successfully
    sum_conn = emit_event(client, ev_connect)
    assert sum_conn != ""

    # Apply isolation
    isolate_pod("pod-checkout-1")

    # After isolation: connect events must be suppressed
    sum_conn_blocked = emit_event(client, ev_connect)
    assert sum_conn_blocked == ""

    # Clean up isolation
    unisolate_pod("pod-checkout-1")
