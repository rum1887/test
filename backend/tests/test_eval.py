"""
Tests for Milestone 8: Evaluation Harness, Baselines, Metrics, and Benchmark Reporting.
"""

from pathlib import Path

from backend.app.eval.baselines import (
    AblatedAgentB2,
    GraphHeuristicBaselineB1,
    RuleBaselineB0,
)
from backend.app.eval.harness import run_benchmark
from backend.app.eval.metrics import BaselineResult, compute_metrics
from backend.app.sim.scenarios import load_all_scenarios, load_scenario


def test_baselines_execution():
    """Verify B0, B1, and B2 ablated evaluators execute and return valid results."""
    sc_benign = load_scenario("pair1_shell_metadata_benign")
    sc_malicious = load_scenario("pair1_shell_metadata_malicious")

    # 1. B0 Rule baseline: always flags malicious
    b0 = RuleBaselineB0()
    res0_ben = b0.evaluate(sc_benign)
    res0_mal = b0.evaluate(sc_malicious)
    assert res0_ben.verdict == "malicious"
    assert res0_ben.is_correct is False  # False positive on benign
    assert res0_mal.verdict == "malicious"
    assert res0_mal.is_correct is True

    # 2. B1 Graph heuristics
    b1 = GraphHeuristicBaselineB1()
    res1_mal = b1.evaluate(sc_malicious)
    assert res1_mal.verdict in ["benign", "malicious"]

    # 3. B2 Ablated agent (no graph tools)
    b2 = AblatedAgentB2()
    sc_pair4_mal = load_scenario("pair4_dormant_permission_malicious")
    res2_pair4 = b2.evaluate(sc_pair4_mal)
    # Ablated agent lacks graph reachability tools to detect dormant wildcard abuse
    assert res2_pair4.verdict == "benign"
    assert res2_pair4.is_correct is False


def test_metrics_calculation():
    """Verify precision, recall, FPR, FNR, and injection resistance calculation."""
    scenarios = load_all_scenarios()
    sc_map = {s.id: s for s in scenarios}

    # Synthesize results: 1 TP, 1 TN
    dummy_results = [
        BaselineResult(
            evaluator_name="test",
            scenario_id="pair1_shell_metadata_benign",
            verdict="benign",
            confidence=0.9,
            summary="ok",
            evidence_ids=["pod-checkout-1"],
            ground_truth_verdict="benign",
            is_correct=True,
            passed_verification=True,
        ),
        BaselineResult(
            evaluator_name="test",
            scenario_id="pair1_shell_metadata_malicious",
            verdict="malicious",
            confidence=0.9,
            summary="alert",
            evidence_ids=["pod-checkout-1", "sr-customer-vault"],
            ground_truth_verdict="malicious",
            is_correct=True,
            passed_verification=True,
        ),
    ]

    metrics = compute_metrics("test_evaluator", dummy_results, sc_map)
    assert metrics.accuracy == 1.0
    assert metrics.tp == 1
    assert metrics.tn == 1
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.fpr == 0.0
    assert metrics.fnr == 0.0
    assert metrics.injection_resistance_rate == 1.0


def test_full_benchmark_harness(tmp_path: Path):
    """Verify end-to-end benchmark execution and report generation."""
    out_dir = tmp_path / "eval_out"
    docs_file = tmp_path / "RESULTS.md"

    metrics_map = run_benchmark(output_dir=str(out_dir), docs_path=str(docs_file))

    assert "Trust Analyst (Full Agent)" in metrics_map
    assert "Ablated Agent (No Graph)" in metrics_map
    assert "B1: Graph Heuristics" in metrics_map
    assert "B0: Alert Rule Baseline" in metrics_map

    ta_metrics = metrics_map["Trust Analyst (Full Agent)"]
    assert ta_metrics.accuracy == 1.0
    assert ta_metrics.fpr == 0.0
    assert ta_metrics.fnr == 0.0

    b0_metrics = metrics_map["B0: Alert Rule Baseline"]
    assert b0_metrics.fpr == 1.0  # Demonstrates rule alert fatigue

    # Verify output files exist and contain markdown
    assert (out_dir / "results.json").exists()
    assert docs_file.exists()
    content = docs_file.read_text(encoding="utf-8")
    assert "# Trust Analyst: Evaluation & Benchmark Results" in content
    assert "Benchmark Comparison Table" in content
    assert "Ablation Analysis" in content
