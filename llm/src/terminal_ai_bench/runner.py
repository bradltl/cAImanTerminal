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
from .system import IntentSource, SystemEvaluationPipeline, compute_system_metrics, generate_contracts_by_id


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
    evaluation_mode: str = "raw"
    system_metrics: Optional[Dict[str, Any]] = None


class BenchmarkRunner:
    """Executes evaluation scenarios against a specified model runtime."""

    def __init__(
        self,
        config_path: Path | str = "config/benchmark.yaml",
        models_config_path: Path | str = "config/models.yaml",
        scenarios_dir: Path | str = "scenarios",
        prompts_dir: Path | str = "prompts",
        fixtures_dir: Path | str = "fixtures",
        results_dir: Path | str = "../artifacts/results",
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
        system_mode: bool = False,
        intent_source: str = "oracle",
    ) -> RunSummary:
        alias_map = {
            "gemma3-1b": "gemma-3-1b",
            "gemma3": "gemma-3-1b",
            "qwen3": "qwen3-0.6b",
            "qwen3-0.6": "qwen3-0.6b",
            "phi1.5": "phi-1.5",
            "phi-1_5": "phi-1.5",
            "phi": "phi-1.5",
            "lfm2": "lfm2-1.2b",
            "lfm": "lfm2-1.2b",
            "lfm-1.2b": "lfm2-1.2b",
            "qwen-sft": "qwen2.5-0.5b-sft",
            "qwen2.5-sft": "qwen2.5-0.5b-sft",
            "qwen-0.5b-sft": "qwen2.5-0.5b-sft",
            "qwen-sft-v2": "qwen2.5-0.5b-sft-v2",
            "qwen2.5-sft-v2": "qwen2.5-0.5b-sft-v2",
            "qwen-v2": "qwen2.5-0.5b-sft-v2",
            "qwen2.5-v2": "qwen2.5-0.5b-sft-v2",
            "v2": "qwen2.5-0.5b-sft-v2",
            "qwen-sft-v3": "qwen2.5-0.5b-sft-v3",
            "qwen2.5-sft-v3": "qwen2.5-0.5b-sft-v3",
            "qwen-v3": "qwen2.5-0.5b-sft-v3",
            "qwen2.5-v3": "qwen2.5-0.5b-sft-v3",
            "v3": "qwen2.5-0.5b-sft-v3",
            "qwen-sft-v4": "qwen2.5-0.5b-sft-v4",
            "qwen2.5-sft-v4": "qwen2.5-0.5b-sft-v4",
            "qwen-v4": "qwen2.5-0.5b-sft-v4",
            "qwen2.5-v4": "qwen2.5-0.5b-sft-v4",
            "v4": "qwen2.5-0.5b-sft-v4",
            "qwen-sft-v5": "qwen2.5-0.5b-sft-v5",
            "qwen2.5-sft-v5": "qwen2.5-0.5b-sft-v5",
            "qwen-v5": "qwen2.5-0.5b-sft-v5",
            "qwen2.5-v5": "qwen2.5-0.5b-sft-v5",
            "v5": "qwen2.5-0.5b-sft-v5",
            "deepseek": "deepseek-coder-1.3b-base",
            "deepseek-coder": "deepseek-coder-1.3b-base",
            "deepseek-coder-1.3b": "deepseek-coder-1.3b-base",
            "deepseek-1.3b": "deepseek-coder-1.3b-base",
        }
        canonical_model = alias_map.get(model_name.lower(), model_name)
        mode_prefix = f"{canonical_model}-system" if system_mode else canonical_model
        run_id = f"{mode_prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}"

        # Load configuration
        with open(self.models_config_path, "r", encoding="utf-8") as f:
            models_data = yaml.safe_load(f).get("models", {})

        model_cfg = models_data.get(canonical_model)
        if not model_cfg and not mock_mode and model_name != "mock":
            raise ValueError(f"Model '{model_name}' not configured in {self.models_config_path}")

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
        raw_scores: List[ScenarioScore] = []
        system_evaluations: List[Any] = []
        ttft_values: List[float] = []
        tps_values: List[float] = []
        scenario_response_pairs = []

        intent_src_enum = IntentSource.RUNTIME if intent_source == "runtime" else IntentSource.ORACLE
        contracts_by_id = generate_contracts_by_id(all_scenarios) if (system_mode and intent_src_enum == IntentSource.ORACLE) else None
        system_pipeline = (
            SystemEvaluationPipeline(
                fixtures_dir=self.fixtures_dir,
                intent_source=intent_src_enum,
                contracts_by_id=contracts_by_id,
            )
            if system_mode
            else None
        )

        for scenario in scenarios:
            if scenario.turns:
                # Multi-turn execution
                session_history = list(scenario.history)
                turn_scores = []
                turn_raw_scores = []
                last_parse_res = None
                last_sys_eval = None

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

                    if system_mode and system_pipeline:
                        prompt = self.context_builder.build_prompt(turn_scenario)
                        infer_res = runtime.infer(prompt)
                        initial_parse_res = parse_response(infer_res.text)
                        parse_res, sys_eval = system_pipeline.evaluate(
                            turn_scenario,
                            initial_parse_res,
                            runtime,
                            initial_latency_ms=infer_res.total_latency_ms,
                        )
                        last_sys_eval = sys_eval
                    else:
                        infer_res, parse_res = self._execute_turn(runtime, turn_scenario, turn.tools.allowed)
                        initial_parse_res = parse_res
                        sys_eval = None

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
                    if system_mode:
                        raw_t_score = score_scenario(turn_scenario, initial_parse_res, perf)
                        turn_raw_scores.append(raw_t_score)
                        t_score.system_evaluation = sys_eval.to_dict() if sys_eval else None
                        t_score.raw_command = initial_parse_res.response.command if initial_parse_res and initial_parse_res.response else None
                        t_score.raw_score = raw_t_score.percentage

                    turn_scores.append(t_score)
                    scenario_response_pairs.append((turn_scenario, parse_res.response))

                    # Advance simulated session history
                    staged_cmd = (sys_eval.final_command if sys_eval else None) or (
                        parse_res.response.command
                        if parse_res.response and parse_res.response.command
                        else turn.input.text
                    )
                    executed_cmd = turn.simulated_command or staged_cmd
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
                    system_evaluation=last_sys_eval.to_dict() if last_sys_eval else None,
                )
                scores.append(combined_score)
                if system_mode:
                    if last_sys_eval:
                        system_evaluations.append(last_sys_eval)
                    raw_avg = sum(r.percentage for r in turn_raw_scores) / len(turn_raw_scores) if turn_raw_scores else 0.0
                    raw_scores.append(ScenarioScore(
                        scenario_id=scenario.id,
                        scenario_name=scenario.name,
                        domain=scenario.domain,
                        percentage=raw_avg,
                        passed=all(r.passed for r in turn_raw_scores),
                    ))

            else:
                # Single turn execution
                if system_mode and system_pipeline:
                    prompt = self.context_builder.build_prompt(scenario)
                    infer_res = runtime.infer(prompt)
                    initial_parse_res = parse_response(infer_res.text)
                    parse_res, sys_eval = system_pipeline.evaluate(
                        scenario,
                        initial_parse_res,
                        runtime,
                        initial_latency_ms=infer_res.total_latency_ms,
                    )
                    system_evaluations.append(sys_eval)
                else:
                    infer_res, parse_res = self._execute_turn(runtime, scenario, scenario.tools.allowed)
                    initial_parse_res = parse_res
                    sys_eval = None

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
                if system_mode:
                    raw_score = score_scenario(scenario, initial_parse_res, perf)
                    raw_scores.append(raw_score)
                    score.system_evaluation = sys_eval.to_dict() if sys_eval else None
                    score.raw_command = initial_parse_res.response.command if initial_parse_res and initial_parse_res.response else None
                    score.raw_score = raw_score.percentage

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

        # Compute System Metrics if running in system mode
        system_metrics_dict = None
        if system_mode:
            sys_metrics_obj = compute_system_metrics(
                evaluations=system_evaluations,
                raw_scores=raw_scores,
                system_scores=scores,
                scenarios=scenarios,
            )
            system_metrics_dict = sys_metrics_obj.to_dict()

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
            evaluation_mode="system" if system_mode else "raw",
            system_metrics=system_metrics_dict,
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
            evaluation_mode="system" if system_mode else "raw",
            system_metrics=system_metrics_dict,
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
            evaluation_mode="system" if system_mode else "raw",
            system_metrics=system_metrics_dict,
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
            evaluation_mode="system" if system_mode else "raw",
            system_metrics=system_metrics_dict,
        )
