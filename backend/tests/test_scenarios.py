"""
Tests for Scenario Loader, 14 Matched-Pair Scenarios, Prompt Injection Variants, and FalkorDB Alert Creation.
"""

from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock
from backend.app.sim.scenarios import (
    Scenario,
    apply_scenario,
    load_all_scenarios,
    load_scenario,
)
from backend.app.sim.world import seed_world


def test_load_all_14_scenarios():
    """Verify that all 14 YAML scenarios parse and validate cleanly."""
    scenarios = load_all_scenarios()
    assert len(scenarios) == 14, f"Expected exactly 14 scenarios, found {len(scenarios)}"

    pairs: dict[str, list[Scenario]] = {}
    for sc in scenarios:
        pairs.setdefault(sc.pair_id, []).append(sc)

    assert len(pairs) == 7, f"Expected 7 distinct pairs, found {len(pairs)}"
    for pair_id, pair_scenarios in pairs.items():
        assert len(pair_scenarios) == 2, f"Pair {pair_id} must have exactly 2 scenarios (benign & malicious)"
        variants = {s.variant for s in pair_scenarios}
        assert variants == {"benign", "malicious"}, f"Pair {pair_id} missing variant: {variants}"


def test_injection_variants():
    """Verify that at least 3 scenarios have inject: true and their payloads are configured."""
    scenarios = load_all_scenarios()
    injected = [s for s in scenarios if s.inject]
    assert len(injected) >= 3, f"Expected >= 3 injection scenarios, found {len(injected)}"

    for s in injected:
        assert s.variant == "malicious", "Only malicious scenarios should have adversarial injections"
        assert s.injection_payload is not None and len(s.injection_payload) > 10


def test_scenario_application_and_alert_raising():
    """Verify that each scenario applies cleanly, mutates the graph, and raises its alert in FalkorDB."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)

    # Re-seed baseline world
    seed_world(client, seed=42)

    scenarios = load_all_scenarios()

    for sc in scenarios:
        alert_id = apply_scenario(client, sc, clock=clock)
        assert alert_id == sc.alert.id

        # Verify Alert node exists in FalkorDB
        res = client.query(
            "MATCH (a:Alert {id: $id}) RETURN a.title, a.severity, a.status, a.at",
            {"id": alert_id},
        )
        assert len(res) == 1, f"Alert {alert_id} was not found in graph"
        title, severity, status, at = res[0]
        assert title == sc.alert.title
        assert severity == sc.alert.severity
        assert status == "new"
        assert at >= 1700000000

        # Verify TARGETS relationship
        target_res = client.query(
            "MATCH (a:Alert {id: $id})-[:TARGETS]->(t) RETURN t.id",
            {"id": alert_id},
        )
        assert len(target_res) >= 1, f"Alert {alert_id} has no TARGETS relationship to {sc.alert.target_id}"
        target_found_id = target_res[0][0]
        assert target_found_id == sc.alert.target_id


def test_prompt_injection_embedding():
    """Verify that untrusted documents receive the prompt injection payload when inject: true."""
    client = get_graph_client()
    clock = get_clock()
    clock.reset(1700000000)
    seed_world(client, seed=42)

    sc_injected = load_scenario("pair2_role_binding_malicious")
    assert sc_injected.inject is True
    assert sc_injected.injection_payload is not None

    apply_scenario(client, sc_injected, clock=clock)

    # Check that untrusted document body in graph contains the injection payload
    doc_res = client.query(
        "MATCH (d:Document {id: 'doc-ticket-fake-202'}) RETURN d.body",
    )
    assert len(doc_res) == 1
    body = doc_res[0][0]
    assert sc_injected.injection_payload in body, f"Injection payload not found in document body: {body}"
