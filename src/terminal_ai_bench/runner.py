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
from .scenario import Domain, HistoryTurn, Scenario, load_all_scenarios
from .scoring import ScenarioScore, score_scenario
from .scoring.interaction import compute_interaction_metrics
from .scoring.performance import PerformanceMetrics
from .tool_runtime import ToolRuntime
from .reports.console import print_console_report
from .reports.json_report import generate_json_report
from .reports.html_report import generate_html_report


class RunSummary(BaseModel):
    run_id: str
    model_name: str
    model_sha256: Optional[str] = None
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
        self.fixtures_dir = Path(fixtures_dir)
        self.results_dir = Path(results_dir)
        self.context_builder = ContextBuilder(prompts_dir=prompts_dir)
        self.tool_runtime = ToolRuntime(fixtures_dir=fixtures_dir, live_mode=False)
        
        # Load benchmark config
        with self.config_path.open("r", encoding="utf-8") as f:
            self.benchmark_config = yaml.safe_load(f)

        # Load models config
        with self.models_config_path.open("r", encoding="utf-8") as f:
            self.models_config = yaml.safe_load(f).get("models", {})

    def _execute_turn(
        self,
        runtime: ModelRuntime,
        scenario: Scenario,
        tools_allowed: bool,
    ):
        """Execute a single scenario turn with optional tool request loop."""
        prompt = self.context_builder.build_prompt(scenario)
        infer_res = runtime.infer(prompt)
        parse_res = parse_response(infer_res.text)

        # Tool request loop: if model returned lookup_help and tools are allowed
        if (
            tools_allowed
            and parse_res.success
            and parse_res.response
            and parse_res.response.action == ActionType.LOOKUP_HELP
            and parse_res.response.tool_request
        ):
            tool_res = self.tool_runtime.execute_request(parse_res.response.tool_request)
            tool_snippet = (
                f"\n\n[DOCUMENTATION RESULT - {tool_res.provider} {parse_res.response.tool_request.command}]\n"
                f"{tool_res.output}\n\nNow provide your final recommendation in structured JSON:"
            )
            second_infer = runtime.infer(prompt + tool_snippet)
            second_parse = parse_response(second_infer.text)
            return second_infer, second_parse

        return infer_res, parse_res

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
        self.tool_runtime.live_mode = live_mode

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
        scenario_response_pairs = []

        for scenario in scenarios:
            if scenario.turns:
                # Multi-turn execution
                session_history = list(scenario.history)
                turn_scores = []
                last_parse_res = None

                for turn in scenario.turns:
                    # Construct single-turn scenario context
                    turn_scenario = Scenario(
                        id=f"{scenario.id}-t{turn.turn_index}",
                        name=f"{scenario.name} (Turn {turn.turn_index})",
                        domain=scenario.domain,
                        difficulty=scenario.difficulty,
                        mode=scenario.mode,
                        context=scenario.context,
                        history=session_history,
                        input=turn.input,
                        typing=turn.typing,
                        expected=turn.expected,
                        forbidden=turn.forbidden,
                        tools=turn.tools,
                    )

                    infer_res, parse_res = self._execute_turn(runtime, turn_scenario, turn.tools.allowed)
                    last_parse_res = parse_res
                    ttft_values.append(infer_res.ttft_ms)
                    if infer_res.tokens_per_second > 0:
                        tps_values.append(infer_res.tokens_per_second)

                    perf = PerformanceMetrics(
                        ttft_ms=infer_res.ttft_ms,
                        total_latency_ms=infer_res.total_latency_ms,
                        tokens_per_second=infer_res.tokens_per_second,
                        prompt_tokens=infer_res.prompt_tokens,
                        completion_tokens=infer_res.completion_tokens,
                    )

                    t_score = score_scenario(turn_scenario, parse_res, perf)
                    turn_scores.append(t_score)
                    scenario_response_pairs.append((turn_scenario, parse_res.response))

                    # Advance simulated session history
                    executed_cmd = turn.simulated_command or (
                        parse_res.response.command
                        if parse_res.response and parse_res.response.command
                        else turn.input.text
                    )
                    session_history.append(
                        HistoryTurn(
                            command=executed_cmd,
                            exit_code=turn.simulated_exit_code,
                            output=turn.simulated_output or "",
                        )
                    )

                # Combine turn scores
                avg_total = sum(ts.total_points for ts in turn_scores) / len(turn_scores)
                avg_pct = round((avg_total / 20.0) * 100.0, 1)
                any_hard_violation = any(ts.hard_safety_violation for ts in turn_scores)
                all_passed = all(ts.passed for ts in turn_scores) and not any_hard_violation

                combined_score = ScenarioScore(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    domain=scenario.domain,
                    command_score=round(sum(ts.command_score for ts in turn_scores) / len(turn_scores), 2),
                    flag_score=round(sum(ts.flag_score for ts in turn_scores) / len(turn_scores), 2),
                    context_score=round(sum(ts.context_score for ts in turn_scores) / len(turn_scores), 2),
                    explanation_score=round(sum(ts.explanation_score for ts in turn_scores) / len(turn_scores), 2),
                    risk_score=round(sum(ts.risk_score for ts in turn_scores) / len(turn_scores), 2),
                    tool_score=round(sum(ts.tool_score for ts in turn_scores) / len(turn_scores), 2),
                    no_hallucination_score=round(sum(ts.no_hallucination_score for ts in turn_scores) / len(turn_scores), 2),
                    format_compliance=round(sum(ts.format_compliance for ts in turn_scores) / len(turn_scores), 2),
                    total_points=round(avg_total, 2),
                    max_points=20.0,
                    percentage=avg_pct,
                    passed=all_passed,
                    hard_safety_violation=any_hard_violation,
                    notes=[f"Turn {i+1}: {'; '.join(ts.notes[:1])}" for i, ts in enumerate(turn_scores) if ts.notes],
                    raw_response=last_parse_res.raw_text if last_parse_res else None,
                    parsed_command=last_parse_res.response.command if last_parse_res and last_parse_res.response else None,
                )
                scores.append(combined_score)

            else:
                # Single turn execution
                infer_res, parse_res = self._execute_turn(runtime, scenario, scenario.tools.allowed)
                ttft_values.append(infer_res.ttft_ms)
                if infer_res.tokens_per_second > 0:
                    tps_values.append(infer_res.tokens_per_second)

                perf = PerformanceMetrics(
                    ttft_ms=infer_res.ttft_ms,
                    total_latency_ms=infer_res.total_latency_ms,
                    tokens_per_second=infer_res.tokens_per_second,
                    prompt_tokens=infer_res.prompt_tokens,
                    completion_tokens=infer_res.completion_tokens,
                )

                score = score_scenario(scenario, parse_res, perf)
                scores.append(score)
                scenario_response_pairs.append((scenario, parse_res.response))

        runtime_perf = runtime.metrics()
        model_sha256 = runtime.model_sha256
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
        cmd_accuracy = (sum(s.command_score for s in scores) / (len(scores) * 4.0)) * 100.0 if scores else 0.0
        flag_accuracy = (sum(s.flag_score for s in scores) / (len(scores) * 3.0)) * 100.0 if scores else 0.0
        json_compliance = (sum(s.format_compliance for s in scores) / len(scores)) * 100.0 if scores else 0.0
        tool_selection = (sum(s.tool_score for s in scores) / (len(scores) * 3.0)) * 100.0 if scores else 0.0

        # Compute NO_ACTION precision and recall using first-class interaction metrics
        interaction_metrics = compute_interaction_metrics(scenario_response_pairs)

        capability_scores = {
            "Command correctness": round(cmd_accuracy, 1),
            "Flag correctness": round(flag_accuracy, 1),
            "JSON compliance": round(json_compliance, 1),
            "Tool selection": round(tool_selection, 1),
            "No-action precision": interaction_metrics["no_action_precision"],
            "No-action recall": interaction_metrics["no_action_recall"],
            "Unnecessary suggestion rate": interaction_metrics["unnecessary_suggestion_rate"],
        }

        # Calculate Performance p50 / p95
        ttft_sorted = sorted(ttft_values) if ttft_values else [0.0]
        p50_idx = int(len(ttft_sorted) * 0.5)
        p95_idx = min(len(ttft_sorted) - 1, int(len(ttft_sorted) * 0.95))

        perf_summary = {
            "load_time_s": runtime_perf.model_load_time_s,
            "ram_mb": runtime_perf.resident_ram_mb,
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
            model_sha256=model_sha256,
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
            model_sha256=model_sha256,
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
            model_sha256=model_sha256,
        )

        return RunSummary(
            run_id=run_id,
            model_name=model_name,
            model_sha256=model_sha256,
            overall_score=overall_score,
            domain_scores=domain_scores,
            capability_scores=capability_scores,
            safety_passed=safety_passed,
            scenario_count=len(scenarios),
            passed_count=sum(1 for s in scores if s.passed),
            results_path=str(json_path),
        )
