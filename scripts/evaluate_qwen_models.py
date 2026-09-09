#!/usr/bin/env python3
"""Run evaluation on Qwen 2.5 models against the new 100-scenario benchmark suite."""

import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from terminal_ai_bench.runner import BenchmarkRunner

MODELS = [
    ("qwen2.5-0.5b", "Qwen 2.5 0.5B (Base)"),
    ("qwen2.5-0.5b-sft", "Qwen 2.5 0.5B (SFT v1)"),
    ("qwen2.5-0.5b-sft-v2", "Qwen 2.5 0.5B (SFT v2)"),
    ("qwen2.5-0.5b-sft-v3", "Qwen 2.5 0.5B (SFT v3)"),
]

SCENARIOS_DIR = "scenarios_v2"

def main():
    runner = BenchmarkRunner(scenarios_dir=SCENARIOS_DIR)
    results = {}

    print(f"================================================================")
    print(f"Benchmarking Qwen 2.5 models against '{SCENARIOS_DIR}' (100 scenarios)")
    print(f"================================================================\n")

    for model_key, label in MODELS:
        print(f"\n{'='*60}")
        print(f"▶ Running: {label} [{model_key}]")
        print(f"{'='*60}\n")
        start_t = time.time()
        
        try:
            summary = runner.run(model_name=model_key)
            elapsed = time.time() - start_t
            results[model_key] = {
                "label": label,
                "overall_score": summary.overall_score,
                "safety_passed": summary.safety_passed,
                "passed_count": summary.passed_count,
                "scenario_count": summary.scenario_count,
                "domain_scores": summary.domain_scores,
                "capability_scores": summary.capability_scores,
                "results_path": summary.results_path,
                "elapsed_sec": elapsed,
            }
            print(f"\n✔ Finished {label} in {elapsed:.1f}s — Overall: {summary.overall_score:.1f}%")
        except Exception as exc:
            print(f"\n✖ Failed {label}: {exc}")
            import traceback
            traceback.print_exc()

    # Save aggregated comparison
    out_file = Path("results/qwen_comparison_v2_suite.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAggregated comparison saved to {out_file}")

if __name__ == "__main__":
    main()
