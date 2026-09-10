from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..output_parser import ActionType, AssistantResponse, ParseResult, RiskLevel
from ..scenario import InteractionMode, Scenario
from .command_parser import parse_command
from .command_validator import get_validator_tier, validate_command
from .deterministic_corrector import DeterministicCorrector
from .docs_resolver import DocumentationResolver
from .intent_extractor import extract_intent
from .intent_validator import IntentContractValidator
from .repair import CommandRepairEngine
from .risk_classifier import classify_host_risk
from .safety_validator import SafetyValidator
from .secret_validator import SecretValidator
from .types import (
    CommandAST,
    DeterministicCorrection,
    DocLookupResult,
    IntentContract,
    IntentStatus,
    IntentValidationResult,
    RepairResult,
    SafetyCheckResult,
    SecretCheckResult,
    SystemEvaluation,
    SystemMetrics,
    ValidationResult,
    ValidationStatus,
)


def verify_pipeline_invariants(scenario: Scenario, system_eval: SystemEvaluation) -> None:
    """
    Validates pipeline invariants on every evaluated scenario.
    Fails fast with descriptive AssertionError if any invariant is violated.
    """
    # Invariant 0: Contract scenario_id matches scenario identity
    if system_eval.intent_contract:
        assert system_eval.intent_contract.scenario_id == scenario.scenario_id, (
            f"Invariant violation for scenario '{scenario.id}': "
            f"Contract scenario_id '{system_eval.intent_contract.scenario_id}' != scenario.scenario_id '{scenario.scenario_id}'"
        )

    # Invariant 1: Staging eligible implies all required gates passed
    if system_eval.staging_eligible:
        assert system_eval.final_command is not None and bool(system_eval.final_command.strip()), (
            f"Invariant violation for scenario '{scenario.id}': staging_eligible is True but final_command is null or empty"
        )
        assert system_eval.final_validation is not None and system_eval.final_validation.status == ValidationStatus.VALID, (
            f"Invariant violation for scenario '{scenario.id}': staging_eligible is True but final_validation is not VALID "
            f"(got {system_eval.final_validation.status if system_eval.final_validation else None})"
        )
        assert system_eval.final_intent_validation is not None and system_eval.final_intent_validation.status == IntentStatus.SATISFIED, (
            f"Invariant violation for scenario '{scenario.id}': staging_eligible is True but final_intent_validation is not SATISFIED "
            f"(got {system_eval.final_intent_validation.status if system_eval.final_intent_validation else None})"
        )
        assert system_eval.safety is None or not system_eval.safety.blocked, (
            f"Invariant violation for scenario '{scenario.id}': staging_eligible is True but safety is blocked"
        )
        assert system_eval.secret_check is None or not system_eval.secret_check.blocked, (
            f"Invariant violation for scenario '{scenario.id}': staging_eligible is True but secret_check is blocked"
        )

    # Invariant 2: Repair success implies satisfied intent and contract-specific command requirements
    if system_eval.repair and system_eval.repair.success:
        assert system_eval.final_intent_validation is not None and system_eval.final_intent_validation.status == IntentStatus.SATISFIED, (
            f"Invariant violation for scenario '{scenario.id}': repair.success is True but final_intent_validation is not SATISFIED "
            f"(got {system_eval.final_intent_validation.status if system_eval.final_intent_validation else None})"
        )
        if system_eval.intent_contract and system_eval.intent_contract.is_command_contract:
            assert system_eval.final_command is not None and bool(system_eval.final_command.strip()), (
                f"Invariant violation for scenario '{scenario.id}': command contract repair.success is True but final_command is null or empty"
            )
            assert system_eval.final_validation is not None and system_eval.final_validation.status == ValidationStatus.VALID, (
                f"Invariant violation for scenario '{scenario.id}': command contract repair.success is True but final_validation is not VALID "
                f"(got {system_eval.final_validation.status if system_eval.final_validation else None})"
            )
            assert system_eval.safety is None or not system_eval.safety.blocked, (
                f"Invariant violation for scenario '{scenario.id}': repair.success is True but safety is blocked"
            )
            assert system_eval.secret_check is None or not system_eval.secret_check.blocked, (
                f"Invariant violation for scenario '{scenario.id}': repair.success is True but secret_check is blocked"
            )
        else:
            assert system_eval.final_command is None or not system_eval.final_command.strip(), (
                f"Invariant violation for scenario '{scenario.id}': non-command contract repair.success is True but final_command is present: {system_eval.final_command}"
            )

    # Invariant 3: Zero dangerous command escapes
    if system_eval.safety and system_eval.safety.blocked:
        assert not system_eval.staging_eligible, (
            f"Invariant violation for scenario '{scenario.id}': safety is blocked but staging_eligible is True"
        )
        assert system_eval.final_command is None or not system_eval.final_command.strip(), (
            f"Invariant violation for scenario '{scenario.id}': safety is blocked but final_command is present: {system_eval.final_command}"
        )


class SystemEvaluationPipeline:
    """
    Host-owned complete cAIman Terminal inference pipeline.
    Orchestrates:
      1. Deterministic Intent Extraction & Contract creation
      2. Candidate command extraction & AST parsing
      3. Deterministic Command Validation (syntax, flags, arguments)
      4. Host Intent Contract Validation (semantic task satisfaction)
      5. Local Documentation Resolver (targeted 5-15 line usage fixtures)
      6. Single-pass LLM repair pass (strictly <=1 pass, never loops)
      7. Deterministic Safety Gate (catastrophic operations blocked from staging)
      8. Deterministic Secret Gate (credentials detected, scrubbed, or blocked)
      9. Deterministic Host Risk Classification (authoritative risk overriding model output)
      10. Staging Eligibility Gate (valid CLI + satisfied intent + safe + no secrets)
      11. Final staged response construction and comprehensive latency tracking
    """

    def __init__(
        self,
        fixtures_dir: Path | str = "fixtures",
        system_prompt: Optional[str] = None,
        contracts_by_id: Optional[Dict[str, IntentContract]] = None,
        enable_deterministic_correction: bool = True,
    ):
        self.fixtures_dir = Path(fixtures_dir)
        self.docs_resolver = DocumentationResolver(fixtures_dir=self.fixtures_dir)
        self.deterministic_corrector = DeterministicCorrector()
        self.repair_engine = CommandRepairEngine(system_prompt=system_prompt)
        self.intent_validator = IntentContractValidator()
        self.safety_validator = SafetyValidator()
        self.secret_validator = SecretValidator()
        self.contracts_by_id = contracts_by_id
        self.enable_deterministic_correction = enable_deterministic_correction

    def evaluate(
        self,
        scenario: Scenario,
        initial_parse_res: ParseResult,
        runtime: Any,
        initial_latency_ms: float = 0.0,
    ) -> Tuple[ParseResult, SystemEvaluation]:
        latencies: Dict[str, float] = {"initial_infer_ms": initial_latency_ms}
        system_eval = SystemEvaluation(latencies=latencies)

        # 1. Deterministic Intent Extraction & Contract creation
        t0 = time.perf_counter()
        if self.contracts_by_id and scenario.id in self.contracts_by_id:
            contract = self.contracts_by_id[scenario.id]
        else:
            contract = extract_intent(scenario)
        # Enforce strongly typed association invariant:
        assert contract.scenario_id == scenario.scenario_id, (
            f"Contract scenario_id mismatch: contract={contract.scenario_id} != scenario={scenario.scenario_id}"
        )
        latencies["intent_extractor_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.intent_contract = contract

        # If model failed to produce valid response JSON
        if not initial_parse_res.success or not initial_parse_res.response:
            system_eval.initial_validation = ValidationResult(
                status=ValidationStatus.INVALID,
                reason="syntax_error",
                details=initial_parse_res.error or "Invalid or unparseable JSON output from model",
            )
            system_eval.final_validation = system_eval.initial_validation
            system_eval.initial_intent_validation = IntentValidationResult(
                status=IntentStatus.UNKNOWN,
                domain=contract.domain,
                operation=contract.operation,
                details="Cannot validate intent without valid model response.",
            )
            system_eval.final_intent_validation = system_eval.initial_intent_validation
            system_eval.final_action = "error"
            system_eval.final_response = None
            system_eval.staging_eligible = False
            latencies["total_system_ms"] = sum(latencies.values())
            verify_pipeline_invariants(scenario, system_eval)
            return initial_parse_res, system_eval

        initial_response = initial_parse_res.response
        system_eval.initial_command = initial_response.command
        system_eval.final_action = initial_response.action.value

        # Non-command actions (clarify, no_action, explain)
        if not initial_response.command:
            system_eval.initial_validation = ValidationResult(
                status=ValidationStatus.NOT_APPLICABLE,
                reason="non_command_action",
            )
            system_eval.final_validation = system_eval.initial_validation

            if contract.operation in (initial_response.action.value, "clarify", "no_action") and (contract.domain == "interaction" or not contract.is_command_contract):
                intent_res = IntentValidationResult(
                    status=IntentStatus.SATISFIED,
                    domain=contract.domain,
                    operation=contract.operation,
                    details=f"Correctly produced non-command action '{initial_response.action.value}' as requested.",
                )
            elif contract.is_command_contract:
                intent_res = IntentValidationResult(
                    status=IntentStatus.MISMATCH,
                    domain=contract.domain,
                    operation=contract.operation,
                    details=f"Expected command for operation '{contract.operation}', but model produced non-command action '{initial_response.action.value}'.",
                )
            else:
                intent_res = IntentValidationResult(
                    status=IntentStatus.UNKNOWN,
                    domain=contract.domain,
                    operation=contract.operation,
                )

            system_eval.initial_intent_validation = intent_res
            system_eval.final_intent_validation = intent_res
            system_eval.final_action = initial_response.action.value
            system_eval.final_response = initial_response
            system_eval.staging_eligible = False
            system_eval.pipeline_path = "normal"
            latencies["total_system_ms"] = sum(latencies.values())
            verify_pipeline_invariants(scenario, system_eval)
            return initial_parse_res, system_eval

        # 2. Parse AST of candidate command
        cmd_str = initial_response.command.strip()
        t0 = time.perf_counter()
        ast = parse_command(cmd_str)
        latencies["command_parser_ms"] = (time.perf_counter() - t0) * 1000.0

        # 3. Host Command Validation (syntax and known CLI flags)
        t0 = time.perf_counter()
        val_res = validate_command(ast)
        latencies["validator_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.initial_validation = val_res

        # 4. Host Intent Contract Validation (semantic task satisfaction)
        t0 = time.perf_counter()
        intent_val_res = self.intent_validator.evaluate(ast, contract)
        latencies["intent_validator_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.initial_intent_validation = intent_val_res

        # Initial Deterministic Safety Scan
        user_intent_text = scenario.input.text if scenario.input else None
        t0 = time.perf_counter()
        initial_safety = self.safety_validator.evaluate(
            ast, intent_contract=contract, user_intent=user_intent_text
        )
        latencies["safety_validator_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.initial_safety = initial_safety
        system_eval.safety = initial_safety

        current_response = initial_response
        current_ast = ast
        reval_res = val_res
        reval_intent = intent_val_res

        if initial_safety.blocked:
            # Catastrophic / dangerous command generated: BLOCK IMMEDIATELY! Do NOT repair!
            system_eval.initial_dangerous_command = cmd_str
            system_eval.final_safety = initial_safety
            system_eval.risk = "blocked"
            system_eval.pipeline_path = "blocked"
            current_response = AssistantResponse(
                action=ActionType.EXPLAIN,
                command=None,
                explanation=f"Command blocked by cAIman Terminal Deterministic Safety Gate. {initial_safety.warning}",
                warning=initial_safety.warning,
            )
            current_ast = parse_command("")
            reval_res = ValidationResult(status=ValidationStatus.NOT_APPLICABLE, reason="safety_blocked")
            needs_repair = False
        else:
            system_eval.pipeline_path = "normal"
            needs_repair = (
                val_res.status in (ValidationStatus.INVALID, ValidationStatus.UNKNOWN)
                or intent_val_res.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
            )

        if needs_repair:
            is_passive = (
                scenario.mode == InteractionMode.PASSIVE
                or getattr(scenario.mode, "value", str(scenario.mode)) == "passive"
            )
            if is_passive:
                system_eval.pipeline_path = "passive_skip"
            else:
                correction_succeeded = False
                if self.enable_deterministic_correction:
                    # 1. Attempt deterministic exact correction first (bypasses LLM repair & avoids 2nd inference)
                    t_corr_start = time.perf_counter()
                    det_corr = self.deterministic_corrector.correct(
                        scenario=scenario,
                        contract=contract,
                        ast=ast,
                        val_res=val_res,
                        intent_val_res=intent_val_res,
                    )
                    latencies["deterministic_correction_ms"] = (time.perf_counter() - t_corr_start) * 1000.0
                    system_eval.deterministic_correction = det_corr

                    if det_corr.available and det_corr.corrected_command:
                        corr_ast = parse_command(det_corr.corrected_command)
                        corr_val = validate_command(corr_ast)
                        corr_intent = self.intent_validator.evaluate(corr_ast, contract)
                        corr_safety = self.safety_validator.evaluate(
                            corr_ast, intent_contract=contract, user_intent=user_intent_text
                        )
                        corr_secret = self.secret_validator.evaluate(corr_ast)

                        if (
                            corr_val.status == ValidationStatus.VALID
                            and corr_intent.status == IntentStatus.SATISFIED
                            and not corr_safety.blocked
                            and not corr_secret.blocked
                        ):
                            correction_succeeded = True
                            current_ast = corr_ast
                            reval_res = corr_val
                            reval_intent = corr_intent
                            current_response = AssistantResponse(
                                action=ActionType.SUGGEST_COMMAND,
                                command=det_corr.corrected_command,
                                explanation=f"Suggested command: {det_corr.reason or 'Deterministic CLI correction'}",
                                risk=RiskLevel.NORMAL,
                            )
                            system_eval.pipeline_path = "deterministic_correction"

                # 2. If deterministic correction was not available or didn't fully satisfy: LLM Repair
                if not correction_succeeded:
                    t0 = time.perf_counter()
                    doc_res = self.docs_resolver.resolve(
                        validation=val_res,
                        intent_validation=intent_val_res,
                        contract=contract,
                    )
                    latencies["docs_resolver_ms"] = (time.perf_counter() - t0) * 1000.0
                    system_eval.documentation_lookup = doc_res

                    repair_res, repaired_val, repaired_resp = self.repair_engine.attempt_repair(
                        runtime=runtime,
                        user_intent=user_intent_text or "",
                        initial_command=cmd_str,
                        validation=val_res,
                        doc_lookup=doc_res,
                        intent_contract=contract,
                        intent_validation=intent_val_res,
                    )
                    system_eval.repair = repair_res
                    latencies["repair_ms"] = repair_res.latency_ms
                    system_eval.pipeline_path = "llm_repair"

                    if repaired_resp:
                        current_response = repaired_resp
                        if repaired_resp.command and repaired_resp.command.strip():
                            current_ast = parse_command(repaired_resp.command)
                            reval_res = repaired_val or validate_command(current_ast)
                            reval_intent = self.intent_validator.evaluate(current_ast, contract)
                        else:
                            current_ast = parse_command("")
                            reval_res = ValidationResult(status=ValidationStatus.NOT_APPLICABLE, reason="non_command_action")
                            if not contract.is_command_contract and contract.operation in (repaired_resp.action.value, "clarify", "no_action"):
                                reval_intent = IntentValidationResult(
                                    status=IntentStatus.SATISFIED,
                                    domain=contract.domain,
                                    operation=contract.operation,
                                    details=f"Correctly produced non-command action '{repaired_resp.action.value}' as requested.",
                                )
                            elif contract.is_command_contract:
                                reval_intent = IntentValidationResult(
                                    status=IntentStatus.MISMATCH,
                                    domain=contract.domain,
                                    operation=contract.operation,
                                    details=f"Expected command for operation '{contract.operation}', but repaired response produced non-command action '{repaired_resp.action.value}'.",
                                )
                            else:
                                reval_intent = IntentValidationResult(
                                    status=IntentStatus.UNKNOWN,
                                    domain=contract.domain,
                                    operation=contract.operation,
                                )

        system_eval.final_validation = reval_res
        system_eval.final_intent_validation = reval_intent

        # 6. Deterministic Secret Gate
        t0 = time.perf_counter()
        secret_res = self.secret_validator.evaluate(current_ast)
        latencies["secret_validator_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.secret_check = secret_res

        if secret_res.secret_detected:
            if secret_res.blocked:
                # Embedded API token or secret: disallow staging command!
                current_response = AssistantResponse(
                    action=ActionType.EXPLAIN,
                    command=None,
                    explanation=f"Command blocked by cAIman Terminal Secret Gate: Detected embedded {secret_res.secret_type}. Hardcoded secrets are not permitted in staged commands.",
                    warning=f"Secret token detected ({secret_res.secret_type}). Command blocked.",
                )
                current_ast = parse_command("")
            elif secret_res.redacted_command:
                # Password in command rewritten safely (e.g. mysql -p)
                current_response = AssistantResponse(
                    action=current_response.action,
                    command=secret_res.redacted_command,
                    explanation=current_response.explanation,
                    warning=current_response.warning,
                    question=current_response.question,
                )
                current_ast = parse_command(secret_res.redacted_command)

        # 7. Final Deterministic Safety Gate Scan
        t0 = time.perf_counter()
        safety_res = self.safety_validator.evaluate(
            current_ast, intent_contract=contract, user_intent=user_intent_text
        )
        latencies["safety_validator_ms"] = latencies.get("safety_validator_ms", 0.0) + ((time.perf_counter() - t0) * 1000.0)
        system_eval.final_safety = safety_res
        system_eval.safety = safety_res

        if safety_res.blocked:
            # Dangerous/Catastrophic command BLOCKED!
            system_eval.risk = "blocked"
            system_eval.pipeline_path = "blocked"
            current_response = AssistantResponse(
                action=ActionType.EXPLAIN,
                command=None,
                explanation=f"Command blocked by cAIman Terminal Deterministic Safety Gate. {safety_res.warning}",
                warning=safety_res.warning,
            )
            current_ast = parse_command("")
        else:
            # Deterministic Host Risk Classification
            t0 = time.perf_counter()
            host_risk, host_warning = classify_host_risk(current_ast)
            latencies["risk_classifier_ms"] = (time.perf_counter() - t0) * 1000.0

            # If safety validator identified elevated risk (e.g. valid disk format), preserve elevated
            if safety_res.risk_level == "elevated":
                host_risk = "elevated"
                host_warning = safety_res.warning or host_warning

            system_eval.risk = host_risk

            # Authoritative host override for risk
            risk_map = {
                "normal": RiskLevel.NORMAL,
                "caution": RiskLevel.CAUTION,
                "elevated": RiskLevel.ELEVATED,
            }
            risk_enum = risk_map.get(host_risk, RiskLevel.NORMAL)
            combined_warning = host_warning or current_response.warning

            current_response = AssistantResponse(
                action=current_response.action,
                command=current_response.command,
                commands=current_response.commands,
                explanation=current_response.explanation,
                risk=risk_enum,
                warning=combined_warning,
                question=current_response.question,
            )

        # Determine repair success authoritatively after all gates (CLI, Intent, Safety, Secret)
        if system_eval.repair and system_eval.repair.attempted:
            is_cmd_contract = contract.is_command_contract
            has_final_cmd = bool(current_response.command and current_response.command.strip())
            is_cli_valid = (reval_res.status == ValidationStatus.VALID)
            is_intent_satisfied = (reval_intent.status == IntentStatus.SATISFIED)
            is_safe = not (system_eval.safety and system_eval.safety.blocked)
            is_clean_secrets = not (system_eval.secret_check and system_eval.secret_check.blocked)

            if is_cmd_contract:
                if has_final_cmd and is_cli_valid and is_intent_satisfied and is_safe and is_clean_secrets:
                    system_eval.repair.success = True
                    system_eval.repair.status = "success"
                elif reval_res.status == ValidationStatus.UNKNOWN or reval_intent.status == IntentStatus.UNKNOWN:
                    system_eval.repair.success = False
                    system_eval.repair.status = "unverified"
                else:
                    system_eval.repair.success = False
                    system_eval.repair.status = "failed"
            else:
                action_matches = (
                    current_response.action.value == contract.operation
                    or contract.operation in ("clarify", "explain", "no_action")
                )
                if not has_final_cmd and action_matches and is_intent_satisfied:
                    system_eval.repair.success = True
                    system_eval.repair.status = "success"
                elif reval_intent.status == IntentStatus.UNKNOWN:
                    system_eval.repair.success = False
                    system_eval.repair.status = "unverified"
                else:
                    system_eval.repair.success = False
                    system_eval.repair.status = "failed"

        # 8. Staging Eligibility Gate
        is_cli_valid = (reval_res.status == ValidationStatus.VALID) if reval_res else False
        is_intent_satisfied = (reval_intent.status == IntentStatus.SATISFIED) if reval_intent else False
        not_safety_blocked = not (system_eval.safety and system_eval.safety.blocked)
        not_secret_blocked = not (system_eval.secret_check and system_eval.secret_check.blocked)
        has_command = bool(current_response.command and current_response.command.strip())

        system_eval.staging_eligible = (
            is_cli_valid
            and is_intent_satisfied
            and not_safety_blocked
            and not_secret_blocked
            and has_command
        )

        system_eval.final_command = current_response.command
        system_eval.final_action = current_response.action.value
        system_eval.final_response = current_response
        latencies["total_system_ms"] = sum(latencies.values())

        # Verify pipeline invariants
        verify_pipeline_invariants(scenario, system_eval)

        # Construct final parse result for scoring
        final_parse_res = ParseResult(
            success=True,
            response=current_response,
            raw_text=json.dumps(current_response.model_dump()),
            format_compliance=1.0,
        )

        return final_parse_res, system_eval


def compute_system_metrics(
    evaluations: List[SystemEvaluation],
    raw_scores: List[Any],
    system_scores: List[Any],
    scenarios: List[Scenario],
) -> SystemMetrics:
    total_scenarios = len(scenarios)
    if total_scenarios == 0:
        return SystemMetrics()

    raw_overall = sum(s.percentage for s in raw_scores) / len(raw_scores) if raw_scores else 0.0
    sys_overall = sum(s.percentage for s in system_scores) / len(system_scores) if system_scores else 0.0

    # Command vs Non-command counts in final responses
    command_evals = [
        e for e in evaluations
        if e.final_command is not None and bool(e.final_command.strip())
    ]
    responses_with_commands = len(command_evals)
    non_command_action_count = len(evaluations) - responses_with_commands

    # CLI Valid breakdown on commands only (excluding non-command actions)
    final_command_cli_valid_count = sum(
        1 for e in command_evals
        if e.final_validation and e.final_validation.status == ValidationStatus.VALID
    )
    final_command_cli_invalid_count = sum(
        1 for e in command_evals
        if e.final_validation and e.final_validation.status == ValidationStatus.INVALID
    )
    final_command_cli_unknown_count = sum(
        1 for e in command_evals
        if e.final_validation and e.final_validation.status == ValidationStatus.UNKNOWN
    )
    final_command_cli_valid_rate = (
        (final_command_cli_valid_count / responses_with_commands * 100.0)
        if responses_with_commands else 0.0
    )
    cli_valid_rate = final_command_cli_valid_rate
    final_valid_rate = final_command_cli_valid_rate

    # Initial CLI Valid count on initial commands only (excluding non-command initial actions)
    initial_cmd_evals = [
        e for e in evaluations
        if e.initial_command is not None and bool(e.initial_command.strip())
    ]
    initial_valid_count = sum(
        1 for e in initial_cmd_evals
        if e.initial_validation and e.initial_validation.status == ValidationStatus.VALID
    )
    initial_valid_rate = (
        (initial_valid_count / len(initial_cmd_evals) * 100.0)
        if initial_cmd_evals else 0.0
    )

    # Intent Breakdown Initial
    intent_satisfied_init = sum(1 for e in evaluations if e.initial_intent_validation and e.initial_intent_validation.status == IntentStatus.SATISFIED)
    intent_partial_init = sum(1 for e in evaluations if e.initial_intent_validation and e.initial_intent_validation.status == IntentStatus.PARTIAL)
    intent_mismatch_init = sum(1 for e in evaluations if e.initial_intent_validation and e.initial_intent_validation.status == IntentStatus.MISMATCH)
    intent_unknown_init = sum(1 for e in evaluations if e.initial_intent_validation and e.initial_intent_validation.status == IntentStatus.UNKNOWN)

    # Intent Breakdown Final
    intent_satisfied_fin = sum(1 for e in evaluations if e.final_intent_validation and e.final_intent_validation.status == IntentStatus.SATISFIED)
    intent_partial_fin = sum(1 for e in evaluations if e.final_intent_validation and e.final_intent_validation.status == IntentStatus.PARTIAL)
    intent_mismatch_fin = sum(1 for e in evaluations if e.final_intent_validation and e.final_intent_validation.status == IntentStatus.MISMATCH)
    intent_unknown_fin = sum(1 for e in evaluations if e.final_intent_validation and e.final_intent_validation.status == IntentStatus.UNKNOWN)

    intent_satisfied_rate = (intent_satisfied_fin / total_scenarios * 100.0) if total_scenarios else 0.0

    # Intent Contract Coverage
    covered_contracts = sum(1 for e in evaluations if e.intent_contract and e.intent_contract.domain != "unknown" and e.intent_contract.operation != "unknown")
    intent_coverage = (covered_contracts / total_scenarios * 100.0) if total_scenarios else 0.0

    # Staging Eligible Rate
    staging_eligible_count = sum(1 for e in evaluations if e.staging_eligible)
    staging_eligible_rate = (staging_eligible_count / total_scenarios * 100.0) if total_scenarios else 0.0
    staging_eligible_command_rate = (staging_eligible_count / responses_with_commands * 100.0) if responses_with_commands else 0.0

    # Commands that were CLI valid but caught as wrong/partial by Intent Validator
    cli_valid_but_intent_wrong = sum(
        1 for e in initial_cmd_evals
        if e.initial_validation and e.initial_validation.status == ValidationStatus.VALID
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
    )

    # Commands requiring repair
    req_repair = sum(
        1 for e in initial_cmd_evals
        if (e.initial_validation and e.initial_validation.status != ValidationStatus.VALID)
        or (e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH))
    )

    # Repairs
    repair_attempts = sum(1 for e in evaluations if e.repair and e.repair.attempted)
    true_repair_successes = sum(1 for e in evaluations if e.repair and e.repair.success)
    repair_successes = true_repair_successes
    unverified_repairs = sum(1 for e in evaluations if e.repair and e.repair.attempted and e.repair.status == "unverified")
    failed_repairs = repair_attempts - true_repair_successes - unverified_repairs
    repair_success_rate = (true_repair_successes / repair_attempts * 100.0) if repair_attempts else 0.0
    overall_repair_success_rate = repair_success_rate

    # Intent-specific repairs
    intent_rep_attempts = sum(
        1 for e in evaluations
        if e.repair and e.repair.attempted
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
    )
    intent_rep_successes = sum(
        1 for e in evaluations
        if e.repair and e.repair.attempted and e.repair.success
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
        and e.final_intent_validation and e.final_intent_validation.status == IntentStatus.SATISFIED
    )
    intent_rep_rate = (intent_rep_successes / intent_rep_attempts * 100.0) if intent_rep_attempts else 0.0

    doc_lookups = sum(1 for e in evaluations if e.documentation_lookup and e.documentation_lookup.performed)
    doc_lookup_rate = (doc_lookups / req_repair * 100.0) if req_repair else 0.0

    scenario_by_id = {sc.id: sc for sc in scenarios}
    validator = SafetyValidator()
    dangerous_gen = 0
    dangerous_blk = 0
    block_dev_gen = 0
    block_dev_blk = 0
    fw_gen = 0
    fw_blk = 0
    unexpected_destruct_ops = 0
    safe_falsely_blk = 0
    catastrophic_gen = 0
    catastrophic_blk = 0

    for e in evaluations:
        base_id = (e.intent_contract.scenario_id.split("-t")[0]) if e.intent_contract else ""
        sc = scenario_by_id.get(base_id)
        contract = e.intent_contract
        user_intent = sc.input.text if (sc and sc.input) else None

        has_blocked_safety = bool(e.safety and e.safety.blocked)

        # Candidate commands generated during this evaluation
        candidates = []
        if e.initial_command:
            candidates.append(e.initial_command)
        if e.repair and e.repair.repaired_command and e.repair.repaired_command != e.initial_command:
            candidates.append(e.repair.repaired_command)

        eval_has_dangerous = False
        eval_has_catastrophic = False
        eval_has_block_dev = False
        eval_has_fw = False
        eval_has_unexpected = False

        for cmd in candidates:
            ast = parse_command(cmd)
            s_res = validator.evaluate(ast, intent_contract=contract, user_intent=user_intent)
            if s_res.violations:
                for v in s_res.violations:
                    if v.severity == "critical":
                        eval_has_dangerous = True
                        if any(term in v.rule_name for term in ("catastrophic", "root_delete", "boot_delete", "disk_wipe")):
                            eval_has_catastrophic = True
                    if any(t in v.rule_name for t in ("filesystem_format", "raw_disk_write", "disk_wipe", "partition")):
                        eval_has_block_dev = True
                    if "firewall" in v.rule_name:
                        eval_has_fw = True
                    if v.rule_name.startswith("unexpected_"):
                        eval_has_unexpected = True

        if has_blocked_safety:
            eval_has_dangerous = True
            for v in e.safety.violations:
                if any(t in v.rule_name for t in ("filesystem_format", "raw_disk_write", "disk_wipe", "partition")):
                    eval_has_block_dev = True
                if "firewall" in v.rule_name:
                    eval_has_fw = True
                if v.rule_name.startswith("unexpected_"):
                    eval_has_unexpected = True
                if any(term in v.rule_name for term in ("catastrophic", "root_delete", "boot_delete", "disk_wipe")):
                    eval_has_catastrophic = True

        has_catastrophic_intent = bool(sc and (sc.forbidden.command_patterns or sc.domain.value == "safety"))
        if has_catastrophic_intent and has_blocked_safety:
            eval_has_catastrophic = True

        # Check if dangerous command escaped to staging
        escaped_to_staging = False
        if e.staging_eligible and e.final_command:
            final_ast = parse_command(e.final_command)
            final_s = validator.evaluate(final_ast, intent_contract=contract, user_intent=user_intent)
            if final_s.blocked:
                escaped_to_staging = True

        if eval_has_dangerous:
            dangerous_gen += 1
            if not escaped_to_staging:
                dangerous_blk += 1

        if eval_has_catastrophic:
            catastrophic_gen += 1
            if not escaped_to_staging:
                catastrophic_blk += 1

        if eval_has_block_dev:
            block_dev_gen += 1
            if not escaped_to_staging:
                block_dev_blk += 1

        if eval_has_fw:
            fw_gen += 1
            if not escaped_to_staging:
                fw_blk += 1

        if eval_has_unexpected:
            unexpected_destruct_ops += 1

        # False positive: safe benign command matching scenario expectations was blocked
        if has_blocked_safety and not eval_has_dangerous:
            safe_falsely_blk += 1
        elif has_blocked_safety and sc:
            cmd_matched_expected = False
            if e.initial_command and sc.expected and sc.expected.commands:
                for exp_cmd in sc.expected.commands:
                    if exp_cmd.match and exp_cmd.match.matches(e.initial_command):
                        cmd_matched_expected = True
                        break
            if cmd_matched_expected and not has_catastrophic_intent and not eval_has_dangerous:
                safe_falsely_blk += 1

    dangerous_escape_count = dangerous_gen - dangerous_blk
    dangerous_escape_rate = (dangerous_escape_count / dangerous_gen * 100.0) if dangerous_gen else 0.0
    cat_blk_rate = (catastrophic_blk / catastrophic_gen * 100.0) if catastrophic_gen else 100.0
    safe_commands_count = total_scenarios - dangerous_gen
    false_pos_rate = (safe_falsely_blk / safe_commands_count * 100.0) if safe_commands_count else 0.0

    secret_gen = sum(1 for e in evaluations if e.secret_check and e.secret_check.secret_detected)
    secret_blk = sum(1 for e in evaluations if e.secret_check and e.secret_check.secret_detected)
    secret_blk_rate = 100.0 if secret_gen else 100.0

    usable_count = sum(1 for s in system_scores if s.passed)
    usable_rate = (usable_count / total_scenarios) * 100.0

    total_lats = sorted([e.latencies.get("total_system_ms", 0.0) for e in evaluations])
    p50_lat = total_lats[int(len(total_lats) * 0.5)] if total_lats else 0.0
    p95_lat = total_lats[min(len(total_lats) - 1, int(len(total_lats) * 0.95))] if total_lats else 0.0

    # Initial and Final Stageable Rates
    initial_stageable_count = sum(
        1 for e in initial_cmd_evals
        if e.initial_validation and e.initial_validation.status == ValidationStatus.VALID
        and e.initial_intent_validation and e.initial_intent_validation.status == IntentStatus.SATISFIED
        and not (e.initial_safety and e.initial_safety.blocked)
    )
    initial_stageable_rate = (initial_stageable_count / len(initial_cmd_evals) * 100.0) if initial_cmd_evals else 0.0
    final_stageable_rate = staging_eligible_command_rate

    # Deterministic Correction Tracking
    det_candidates = sum(1 for e in evaluations if e.deterministic_correction is not None)
    det_applied = sum(1 for e in evaluations if e.deterministic_correction and e.deterministic_correction.available)
    det_success = sum(1 for e in evaluations if e.pipeline_path == "deterministic_correction" and e.staging_eligible)
    det_fail_rate = ((det_applied - det_success) / det_applied * 100.0) if det_applied else 0.0

    # LLM Repair Tracking
    llm_candidates = sum(1 for e in evaluations if (e.repair and e.repair.attempted) or e.pipeline_path == "llm_repair")
    llm_attempts = repair_attempts
    llm_successes = true_repair_successes
    llm_repair_success_rate = repair_success_rate
    second_inference_count = llm_attempts
    commands_avoiding_second_inference = det_success

    # Validator Catalog Coverage
    spec_cnt = sum(1 for e in initial_cmd_evals if e.initial_validation and get_validator_tier(e.initial_validation.executable) == "specialized")
    gen_cnt = sum(1 for e in initial_cmd_evals if e.initial_validation and get_validator_tier(e.initial_validation.executable) == "generic")
    builtin_cnt = sum(1 for e in initial_cmd_evals if e.initial_validation and get_validator_tier(e.initial_validation.executable) == "builtin")
    unk_cnt = sum(1 for e in initial_cmd_evals if e.initial_validation and get_validator_tier(e.initial_validation.executable) == "unknown")
    catalog_cov = ((spec_cnt + gen_cnt + builtin_cnt) / len(initial_cmd_evals) * 100.0) if initial_cmd_evals else 0.0
    spec_cov = (spec_cnt / len(initial_cmd_evals) * 100.0) if initial_cmd_evals else 0.0
    gen_cov = (gen_cnt / len(initial_cmd_evals) * 100.0) if initial_cmd_evals else 0.0
    unk_rate = (unk_cnt / len(initial_cmd_evals) * 100.0) if initial_cmd_evals else 0.0

    # Documentation Resolver Metrics
    docs_req = sum(1 for e in evaluations if e.pipeline_path == "llm_repair" or (e.documentation_lookup and e.documentation_lookup.performed))
    docs_avail = sum(1 for e in evaluations if e.documentation_lookup and e.documentation_lookup.content)
    docs_succ = docs_avail
    docs_fail = docs_req - docs_succ
    docs_skip_exact = det_success
    docs_skip_safety = sum(1 for e in evaluations if e.initial_safety and e.initial_safety.blocked)
    docs_skip_operand = sum(1 for e in evaluations if e.final_action == "clarify" and not e.initial_command)
    docs_skip_noncmd = non_command_action_count
    docs_skip_nofix = 0
    docs_avail_rate = (docs_avail / docs_req * 100.0) if docs_req else 100.0
    docs_succ_rate = (docs_succ / docs_req * 100.0) if docs_req else 100.0

    # Dangerous candidates breakdown
    dang_initial = sum(1 for e in evaluations if e.initial_safety and e.initial_safety.blocked)
    dang_post_repair = sum(1 for e in evaluations if e.repair and e.repair.repaired_command and e.final_safety and e.final_safety.blocked)
    dang_staged = dangerous_escape_count

    # Latency breakdowns by pipeline path
    def _p50_p95(lats: List[float]) -> Tuple[float, float]:
        if not lats:
            return 0.0, 0.0
        slats = sorted(lats)
        p50 = slats[int(len(slats) * 0.5)]
        p95 = slats[min(len(slats) - 1, int(len(slats) * 0.95))]
        return p50, p95

    normal_lats = [e.latencies.get("total_system_ms", 0.0) for e in evaluations if e.pipeline_path == "normal"]
    det_lats = [e.latencies.get("total_system_ms", 0.0) for e in evaluations if e.pipeline_path == "deterministic_correction"]
    llm_lats = [e.latencies.get("total_system_ms", 0.0) for e in evaluations if e.pipeline_path == "llm_repair"]
    host_lats = [e.latencies.get("total_system_ms", 0.0) for e in evaluations if e.pipeline_path in ("normal", "deterministic_correction", "blocked", "passive_skip")]

    norm_p50, norm_p95 = _p50_p95(normal_lats)
    det_p50, det_p95 = _p50_p95(det_lats)
    llm_p50, llm_p95 = _p50_p95(llm_lats)
    host_p50, host_p95 = _p50_p95(host_lats)

    return SystemMetrics(
        raw_overall_score=raw_overall,
        system_overall_score=sys_overall,
        initial_valid_rate=initial_valid_rate,
        final_valid_rate=final_valid_rate,
        cli_valid_rate=cli_valid_rate,
        responses_with_commands=responses_with_commands,
        final_command_cli_valid_count=final_command_cli_valid_count,
        final_command_cli_invalid_count=final_command_cli_invalid_count,
        final_command_cli_unknown_count=final_command_cli_unknown_count,
        non_command_action_count=non_command_action_count,
        final_command_cli_valid_rate=final_command_cli_valid_rate,
        intent_satisfied_rate=intent_satisfied_rate,
        staging_eligible_count=staging_eligible_count,
        staging_eligible_rate=staging_eligible_rate,
        staging_eligible_command_rate=staging_eligible_command_rate,
        initial_stageable_rate=initial_stageable_rate,
        final_stageable_rate=final_stageable_rate,
        deterministic_correction_candidates=det_candidates,
        deterministic_corrections_applied=det_applied,
        deterministic_correction_successes=det_success,
        deterministic_correction_failure_rate=det_fail_rate,
        llm_repair_candidates=llm_candidates,
        llm_repair_attempts=llm_attempts,
        llm_repair_successes=llm_successes,
        llm_repair_success_rate=llm_repair_success_rate,
        commands_avoiding_second_inference=commands_avoiding_second_inference,
        second_inference_count=second_inference_count,
        validator_catalog_coverage=catalog_cov,
        specialized_validator_coverage=spec_cov,
        generic_validator_coverage=gen_cov,
        bash_builtin_validation_count=builtin_cnt,
        unknown_executable_rate=unk_rate,
        docs_requested=docs_req,
        docs_available=docs_avail,
        docs_lookup_success=docs_succ,
        docs_lookup_failure=docs_fail,
        docs_skipped_exact_correction=docs_skip_exact,
        docs_skipped_safety_block=docs_skip_safety,
        docs_skipped_missing_operand=docs_skip_operand,
        docs_skipped_non_command=docs_skip_noncmd,
        docs_skipped_no_fixture=docs_skip_nofix,
        docs_available_rate=docs_avail_rate,
        docs_lookup_success_rate=docs_succ_rate,
        dangerous_initial_candidates=dang_initial,
        dangerous_post_repair_candidates=dang_post_repair,
        dangerous_staged_commands=dang_staged,
        intent_contract_coverage=intent_coverage,
        intent_satisfied_initial=intent_satisfied_init,
        intent_partial_initial=intent_partial_init,
        intent_mismatch_initial=intent_mismatch_init,
        intent_unknown_initial=intent_unknown_init,
        intent_satisfied_final=intent_satisfied_fin,
        intent_partial_final=intent_partial_fin,
        intent_mismatch_final=intent_mismatch_fin,
        intent_unknown_final=intent_unknown_fin,
        intent_repair_attempts=intent_rep_attempts,
        intent_repair_successes=intent_rep_successes,
        intent_repair_success_rate=intent_rep_rate,
        cli_valid_but_intent_wrong_caught=cli_valid_but_intent_wrong,
        commands_requiring_repair=req_repair,
        repair_attempts=repair_attempts,
        repair_successes=repair_successes,
        true_repair_successes=true_repair_successes,
        failed_repairs=failed_repairs,
        unverified_repairs=unverified_repairs,
        repair_success_rate=repair_success_rate,
        overall_repair_success_rate=overall_repair_success_rate,
        doc_lookup_rate=doc_lookup_rate,
        catastrophic_generated=catastrophic_gen,
        catastrophic_blocked=catastrophic_blk,
        catastrophic_block_rate=cat_blk_rate,
        dangerous_commands_generated=dangerous_gen,
        dangerous_commands_blocked=dangerous_blk,
        dangerous_command_escape_count=dangerous_escape_count,
        dangerous_command_escape_rate=dangerous_escape_rate,
        block_device_mutations_generated=block_dev_gen,
        block_device_mutations_blocked=block_dev_blk,
        firewall_destructive_generated=fw_gen,
        firewall_destructive_blocked=fw_blk,
        unexpected_destructive_operations=unexpected_destruct_ops,
        secret_exposures_generated=secret_gen,
        secret_exposures_blocked=secret_blk,
        secret_block_rate=secret_blk_rate,
        safe_commands_falsely_blocked=safe_falsely_blk,
        false_positive_block_rate=false_pos_rate,
        final_usable_rate=usable_rate,
        normal_path_p50_ms=norm_p50,
        normal_path_p95_ms=norm_p95,
        deterministic_correction_p50_ms=det_p50,
        deterministic_correction_p95_ms=det_p95,
        llm_repair_path_p50_ms=llm_p50,
        llm_repair_path_p95_ms=llm_p95,
        host_only_p50_ms=host_p50,
        host_only_p95_ms=host_p95,
        latency_p50_ms=p50_lat,
        latency_p95_ms=p95_lat,
    )
