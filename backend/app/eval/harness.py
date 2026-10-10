"""
Evaluation Harness for Trust Analyst.
Runs all 14 scenarios across Trust Analyst, Ablated Agent, and Baselines.
Generates comprehensive benchmark metrics and exports docs/RESULTS.md.
"""

import argparse
import logging

from backend.app.agent.analyst import AnalystAgent
from backend.app.agent.llm import LLMClient
from backend.app.agent.runner import DurableRunner
from backend.app.agent.verifier import VerdictVerifier
from backend.app.eval.baselines import (
    AblatedAgentB2,
    BaselineResult,
    GraphHeuristicBaselineB1,
    RuleBaselineB0,
)
from backend.app.eval.metrics import AggregateMetrics, compute_metrics
from backend.app.eval.report import save_evaluation_report
from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock
from backend.app.sim.scenarios import apply_scenario, load_all_scenarios
from backend.app.sim.telemetry import reset_telemetry
from backend.app.sim.world import seed_world

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("trust_analyst.eval.harness")


def evaluate_trust_analyst(scenarios: list, client, clock) -> list[BaselineResult]:
    """Evaluates the full Trust Analyst agent with FalkorDB graph traversal and quarantined reader."""
    mock_llm = LLMClient(mode="mock")
    agent = AnalystAgent(llm=mock_llm, verifier=VerdictVerifier(client=mock_llm))
    runner = DurableRunner(agent=agent)

    results: list[BaselineResult] = []

    for sc in scenarios:
        clock.reset(1700000000)
        reset_telemetry()
        seed_world(client, seed=42)

        alert_id = apply_scenario(client, sc, clock=clock)
        state = runner.start_investigation(alert_id=alert_id, client=client, clock=clock)

        verdict = state.verdict.verdict if state.verdict else "needs_human"
        confidence = state.verdict.confidence if state.verdict else 0.5
        summary = state.verdict.summary if state.verdict else "Investigation incomplete."
        actions = [a.type for a in state.verdict.recommended_actions] if state.verdict else []

        gt = sc.ground_truth.verdict
        is_correct = verdict == gt

        results.append(
            BaselineResult(
                evaluator_name="Trust Analyst (Full Agent)",
                scenario_id=sc.id,
                verdict=verdict,
                confidence=confidence,
                summary=summary,
                evidence_ids=list(state.evidence_store.keys()),
                recommended_actions=actions,
                tokens_used=state.input_tokens + state.output_tokens,
                cost_usd=state.cost_usd,
                passed_verification=True,
                ground_truth_verdict=gt,
                is_correct=is_correct,
            )
        )

    return results


def run_benchmark(output_dir: str = "eval_output", docs_path: str = "docs/RESULTS.md") -> dict[str, AggregateMetrics]:
    """Runs the complete benchmark suite across all evaluators and generates reports."""
    client = get_graph_client()
    clock = get_clock()

    scenarios = load_all_scenarios()
    scenarios_by_id = {s.id: s for s in scenarios}

    logger.info(f"Loaded {len(scenarios)} evaluation scenarios (7 matched pairs).")

    # 1. Evaluate Trust Analyst (Full Agent)
    logger.info("Evaluating Trust Analyst (Full Agent with FalkorDB)...")
    ta_results = evaluate_trust_analyst(scenarios, client, clock)
    ta_metrics = compute_metrics("Trust Analyst (Full Agent)", ta_results, scenarios_by_id)

    # 2. Evaluate Ablated Agent (No Graph Tools)
    logger.info("Evaluating Ablated Agent (No Graph Tools)...")
    b2_agent = AblatedAgentB2()
    b2_results = [b2_agent.evaluate(s, client, clock) for s in scenarios]
    b2_metrics = compute_metrics("Ablated Agent (No Graph)", b2_results, scenarios_by_id)

    # 3. Evaluate B1: Graph Heuristic Baseline
    logger.info("Evaluating B1: Graph Heuristics Baseline...")
    b1_agent = GraphHeuristicBaselineB1()
    b1_results = [b1_agent.evaluate(s, client, clock) for s in scenarios]
    b1_metrics = compute_metrics("B1: Graph Heuristics", b1_results, scenarios_by_id)

    # 4. Evaluate B0: Alert Rule Baseline
    logger.info("Evaluating B0: Alert Rule Baseline...")
    b0_agent = RuleBaselineB0()
    b0_results = [b0_agent.evaluate(s, client, clock) for s in scenarios]
    b0_metrics = compute_metrics("B0: Alert Rule Baseline", b0_results, scenarios_by_id)

    metrics_map = {
        "Trust Analyst (Full Agent)": ta_metrics,
        "Ablated Agent (No Graph)": b2_metrics,
        "B1: Graph Heuristics": b1_metrics,
        "B0: Alert Rule Baseline": b0_metrics,
    }

    # Save reports
    save_evaluation_report(metrics_map, output_dir=output_dir, docs_path=docs_path)

    # Print summary table to console
    print("\n" + "=" * 95)
    print("TRUST ANALYST BENCHMARK RESULTS")
    print("=" * 95)
    header = f"{'Evaluator':<28} | {'Accuracy':<8} | {'FPR':<7} | {'FNR':<7} | {'Precision':<9} | {'Ev Recall':<9} | {'Inj Resist':<10}"
    print(header)
    print("-" * 95)
    for name, m in metrics_map.items():
        row = (
            f"{name:<28} | "
            f"{m.accuracy * 100:>6.1f}% | "
            f"{m.fpr * 100:>5.1f}% | "
            f"{m.fnr * 100:>5.1f}% | "
            f"{m.precision * 100:>7.1f}% | "
            f"{m.evidence_recall * 100:>7.1f}% | "
            f"{m.injection_resistance_rate * 100:>8.1f}%"
        )
        print(row)
    print("=" * 95)
    print(f"Results exported to {docs_path} and {output_dir}/results.json\n")

    return metrics_map


def main():
    parser = argparse.ArgumentParser(description="Trust Analyst Evaluation Benchmark Harness")
    parser.add_argument("--output-dir", default="eval_output", help="Directory for JSON results")
    parser.add_argument("--docs-path", default="docs/RESULTS.md", help="Path for Markdown results")
    args = parser.parse_args()

    run_benchmark(output_dir=args.output_dir, docs_path=args.docs_path)


if __name__ == "__main__":
    main()
