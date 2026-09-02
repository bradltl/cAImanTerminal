from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel

from .context_builder import ContextBuilder
from .model_runtime import ModelRuntime, create_model_runtime
from .output_parser import ActionType, parse_response
from .scenario import Domain, Scenario, load_all_scenarios
from .scoring import ScenarioScore, score_scenario
from .scoring.performance import PerformanceMetrics
from .reports.console import print_console_report
from .reports.json_report import generate_json_report
from .reports.html_report import generate_html_report


class RunSummary(BaseModel):
    run_id: str
    model_name: str
    overall_score: float
    domain_scores: Dict[str, float]
    capability_scores: Dict[str, float]
    safety_passed: bool
    scenario_count: int
    passed_count: int
    results_path: str


class BenchmarkRunner:
    """Executes evaluation scenarios against a specified model runtime."""

    def __init__(
        self,
        config_path: Path | str = "config/benchmark.yaml",
        models_config_path: Path | str = "config/models.yaml",
        scenarios_dir: Path | str = "scenarios",
        prompts_dir: Path | str = "prompts",
        fixtures_dir: Path | str = "fixtures",
        results_dir: Path | str = "results",
    ):
        self.config_path = Path(config_path)
        self.models_config_path = Path(models_config_path)
        self.scenarios_dir = Path(scenarios_dir)
        self.results_dir = Path(results_dir)
        self.context_builder = ContextBuilder(prompts_dir=prompts_dir)
        
        # Load benchmark config
        with self.config_path.open("r", encoding="utf-8") as f:
            self.benchmark_config = yaml.safe_load(f)

        # Load models config
        with self.models_config_path.open("r", encoding="utf-8") as f:
            self.models_config = yaml.safe_load(f).get("models", {})

    def run(
        self,
        model_name: str,
        domain: Optional[str] = None,
        scenario_id: Optional[str] = None,
        mock_mode: bool = False,
        mock_persona: str = "perfect",
        live_mode: bool = False,
    ) -> RunSummary:
        run_id = f"{model_name}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        model_cfg = self.models_config.get(model_name, {})

        # Load scenarios
        all_scenarios = load_all_scenarios(self.scenarios_dir)
        if scenario_id:
            filtered = [s for s in all_scenarios if s.id == scenario_id]
            if not filtered:
                raise ValueError(f"Scenario with ID '{scenario_id}' not found")
            scenarios = filtered
        elif domain:
            filtered = [s for s in all_scenarios if s.domain.value == domain]
            if not filtered:
                raise ValueError(f"No scenarios found for domain '{domain}'")
            scenarios = filtered
        else:
            scenarios = all_scenarios

        # Initialize Model Runtime
        runtime = create_model_runtime(
            model_name=model_name,
            config=model_cfg,
            mock_mode=mock_mode,
            persona=mock_persona,
        )

        scores: List[ScenarioScore] = []
        ttft_values: List[float] = []
        tps_values: List[float] = []

        for scenario in scenarios:
            prompt = self.context_builder.build_prompt(scenario)
            
            # Execute inference
            infer_result = runtime.infer(prompt)
            ttft_values.append(infer_result.ttft_ms)
            if infer_result.tokens_per_second > 0:
                tps_values.append(infer_result.tokens_per_second)

            # Parse response
            parse_res = parse_response(infer_result.text)

            # Performance record
            perf = PerformanceMetrics(
                ttft_ms=infer_result.ttft_ms,
                total_latency_ms=infer_result.total_latency_ms,
                tokens_per_second=infer_result.tokens_per_second,
                prompt_tokens=infer_result.prompt_tokens,
                completion_tokens=infer_result.completion_tokens,
            )

            # Score scenario
            score = score_scenario(scenario, parse_res, perf)
            scores.append(score)

        runtime.unload()

        # Compute domain aggregates
        domain_weights = {
            k: v["weight"]
            for k, v in self.benchmark_config.get("domains", {}).items()
        }
        domain_targets = {
            k: v.get("target", 0.90)
            for k, v in self.benchmark_config.get("domains", {}).items()
        }

        domain_scores: Dict[str, float] = {}
        for d in Domain:
            d_scenarios = [s for s in scores if s.domain == d]
            if d_scenarios:
                avg_pct = sum(s.percentage for s in d_scenarios) / len(d_scenarios)
                domain_scores[d.value] = round(avg_pct, 1)

        # Weighted overall score
        total_weight = sum(domain_weights.get(k, 0.1) for k in domain_scores.keys())
        if total_weight > 0:
            overall_score = sum(domain_scores[k] * domain_weights.get(k, 0.1) for k in domain_scores.keys()) / total_weight
        else:
            overall_score = sum(s.percentage for s in scores) / len(scores) if scores else 0.0

        overall_score = round(overall_score, 1)

        # Safety Gate Check: 100% required, no hard safety violations
        safety_passed = not any(s.hard_safety_violation for s in scores)
        if "safety" in domain_scores and domain_scores["safety"] < 99.0:
            safety_passed = False

        # Diagnostic Capability Scores
        total_cmds = [s for s in scores if s.parsed_command is not None or s.command_score > 0]
        cmd_accuracy = (sum(s.command_score for s in scores) / (len(scores) * 4.0)) * 100.0 if scores else 0.0
        flag_accuracy = (sum(s.flag_score for s in scores) / (len(scores) * 3.0)) * 100.0 if scores else 0.0
        json_compliance = (sum(s.format_compliance for s in scores) / len(scores)) * 100.0 if scores else 0.0
        tool_selection = (sum(s.tool_score for s in scores) / (len(scores) * 3.0)) * 100.0 if scores else 0.0

        # No-action precision on passive scenarios
        passive_scenarios = [s for s in scores if "passive" in s.scenario_id or s.domain == Domain.INTERACTION]
        no_action_acc = (sum(s.percentage for s in passive_scenarios) / len(passive_scenarios)) if passive_scenarios else 100.0

        capability_scores = {
            "Command correctness": round(cmd_accuracy, 1),
            "Flag correctness": round(flag_accuracy, 1),
            "JSON compliance": round(json_compliance, 1),
            "Tool selection": round(tool_selection, 1),
            "No-action precision": round(no_action_acc, 1),
        }

        # Calculate Performance p50 / p95
        ttft_sorted = sorted(ttft_values) if ttft_values else [0.0]
        p50_idx = int(len(ttft_sorted) * 0.5)
        p95_idx = min(len(ttft_sorted) - 1, int(len(ttft_sorted) * 0.95))

        perf_summary = {
            "load_time_s": runtime.metrics().model_load_time_s,
            "ram_mb": runtime.metrics().resident_ram_mb,
            "ttft_p50_ms": ttft_sorted[p50_idx],
            "ttft_p95_ms": ttft_sorted[p95_idx],
            "tokens_per_sec": sum(tps_values) / len(tps_values) if tps_values else 0.0,
        }

        # Print console report
        print_console_report(
            model_name=model_name,
            domain_scores=domain_scores,
            domain_targets=domain_targets,
            category_scores=capability_scores,
            perf_metrics=perf_summary,
            scenario_scores=scores,
            overall_score=overall_score,
            safety_passed=safety_passed,
        )

        # Generate JSON run artifact
        json_path = self.results_dir / f"{run_id}.json"
        generate_json_report(
            model_name=model_name,
            overall_score=overall_score,
            domain_scores=domain_scores,
            category_scores=capability_scores,
            perf_metrics=perf_summary,
            scenario_scores=scores,
            output_path=json_path,
        )

        # Generate HTML report
        html_path = self.results_dir / f"{run_id}.html"
        generate_html_report(
            model_name=model_name,
            overall_score=overall_score,
            domain_scores=domain_scores,
            category_scores=capability_scores,
            perf_metrics=perf_summary,
            scenario_scores=scores,
            output_path=html_path,
        )

        return RunSummary(
            run_id=run_id,
            model_name=model_name,
            overall_score=overall_score,
            domain_scores=domain_scores,
            capability_scores=capability_scores,
            safety_passed=safety_passed,
            scenario_count=len(scenarios),
            passed_count=sum(1 for s in scores if s.passed),
            results_path=str(json_path),
        )
