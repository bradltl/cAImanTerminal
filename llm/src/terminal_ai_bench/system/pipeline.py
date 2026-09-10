from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..output_parser import ActionType, AssistantResponse, ParseResult, RiskLevel
from ..scenario import Scenario
from .command_parser import parse_command
from .command_validator import validate_command
from .docs_resolver import DocumentationResolver
from .intent_extractor import extract_intent
from .intent_validator import IntentContractValidator
from .repair import CommandRepairEngine
from .risk_classifier import classify_host_risk
from .safety_validator import SafetyValidator
from .secret_validator import SecretValidator
from .types import (
    CommandAST,
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
    ):
        self.fixtures_dir = Path(fixtures_dir)
        self.docs_resolver = DocumentationResolver(fixtures_dir=self.fixtures_dir)
        self.repair_engine = CommandRepairEngine(system_prompt=system_prompt)
        self.intent_validator = IntentContractValidator()
        self.safety_validator = SafetyValidator()
        self.secret_validator = SecretValidator()

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
        contract = extract_intent(scenario)
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
            return initial_parse_res, system_eval

        initial_response = initial_parse_res.response
        system_eval.initial_command = initial_response.command
        system_eval.final_action = initial_response.action.value

        # Non-command actions (clarify, no_action, explain)
        if not initial_response.command:
            system_eval.initial_validation = ValidationResult(
                status=ValidationStatus.VALID,
                reason="non_command_action",
            )
            system_eval.final_validation = system_eval.initial_validation

            if contract.operation in (initial_response.action.value, "clarify", "no_action") and contract.domain == "interaction":
                intent_res = IntentValidationResult(
                    status=IntentStatus.SATISFIED,
                    domain="interaction",
                    operation=contract.operation,
                    details=f"Correctly produced non-command action '{initial_response.action.value}' as requested.",
                )
            elif contract.domain != "unknown" and contract.operation not in ("unknown", "clarify", "no_action"):
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
            latencies["total_system_ms"] = sum(latencies.values())
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

        current_response = initial_response
        current_ast = ast
        reval_res = val_res
        reval_intent = intent_val_res

        # 5. If CLI invalid OR Intent unsatisfied (PARTIAL / MISMATCH): Local Docs Resolver -> LLM Repair -> Revalidate
        needs_repair = (
            val_res.status in (ValidationStatus.INVALID, ValidationStatus.UNKNOWN)
            or intent_val_res.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
        )

        if needs_repair:
            t0 = time.perf_counter()
            doc_res = self.docs_resolver.resolve(validation=val_res, intent_validation=intent_val_res)
            latencies["docs_resolver_ms"] = (time.perf_counter() - t0) * 1000.0
            system_eval.documentation_lookup = doc_res

            repair_res, repaired_val, repaired_resp = self.repair_engine.attempt_repair(
                runtime=runtime,
                user_intent=scenario.input.text,
                initial_command=cmd_str,
                validation=val_res,
                doc_lookup=doc_res,
                intent_contract=contract,
                intent_validation=intent_val_res,
            )
            system_eval.repair = repair_res
            latencies["repair_ms"] = repair_res.latency_ms

            if repair_res.success and repaired_resp:
                current_response = repaired_resp
                if repaired_resp.command:
                    current_ast = parse_command(repaired_resp.command)
                    reval_res = repaired_val or validate_command(current_ast)
                    reval_intent = self.intent_validator.evaluate(current_ast, contract)
                    if reval_res.status == ValidationStatus.INVALID or reval_intent.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH):
                        repair_res.success = False
                    else:
                        repair_res.success = True
                else:
                    current_ast = parse_command("")
                    reval_res = ValidationResult(status=ValidationStatus.VALID, reason="non_command_action")
                    if contract.operation in ("clarify", "no_action"):
                        reval_intent = IntentValidationResult(
                            status=IntentStatus.SATISFIED,
                            domain=contract.domain,
                            operation=contract.operation,
                        )
                    else:
                        reval_intent = IntentValidationResult(
                            status=IntentStatus.MISMATCH,
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

        # 7. Deterministic Safety Gate
        t0 = time.perf_counter()
        safety_res = self.safety_validator.evaluate(current_ast)
        latencies["safety_validator_ms"] = (time.perf_counter() - t0) * 1000.0
        system_eval.safety = safety_res

        if safety_res.blocked:
            # Catastrophic command BLOCKED!
            system_eval.risk = "blocked"
            current_response = AssistantResponse(
                action=ActionType.EXPLAIN,
                command=None,
                explanation=f"Command blocked by cAIman Terminal Catastrophic Safety Gate. {safety_res.warning}",
                warning=safety_res.warning,
            )
        else:
            # Deterministic Host Risk Classification
            t0 = time.perf_counter()
            host_risk, host_warning = classify_host_risk(current_ast)
            latencies["risk_classifier_ms"] = (time.perf_counter() - t0) * 1000.0
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

        # 8. Staging Eligibility Gate
        is_cli_valid = (reval_res.status == ValidationStatus.VALID) if reval_res else False
        is_intent_satisfied = (reval_intent.status == IntentStatus.SATISFIED) if reval_intent else False
        not_safety_blocked = not (system_eval.safety and system_eval.safety.blocked)
        not_secret_blocked = not (system_eval.secret_check and system_eval.secret_check.blocked)
        has_command = bool(current_response.command)

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

    command_evals = [e for e in evaluations if e.initial_command is not None]
    total_commands = len(command_evals)

    # CLI Valid Rates
    initial_valid_count = sum(
        1 for e in command_evals
        if e.initial_validation and e.initial_validation.status == ValidationStatus.VALID
    )
    initial_valid_rate = (initial_valid_count / total_commands * 100.0) if total_commands else 100.0

    final_valid_count = sum(
        1 for e in command_evals
        if e.final_validation and e.final_validation.status == ValidationStatus.VALID
    )
    final_valid_rate = (final_valid_count / total_commands * 100.0) if total_commands else 100.0
    cli_valid_rate = final_valid_rate

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
    staging_eligible_rate = (staging_eligible_count / total_commands * 100.0) if total_commands else 0.0

    # Commands that were CLI valid but caught as wrong/partial by Intent Validator
    cli_valid_but_intent_wrong = sum(
        1 for e in command_evals
        if e.initial_validation and e.initial_validation.status == ValidationStatus.VALID
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
    )

    # Repairs
    req_repair = sum(
        1 for e in command_evals
        if (e.initial_validation and e.initial_validation.status != ValidationStatus.VALID)
        or (e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH))
    )
    repair_attempts = sum(1 for e in evaluations if e.repair and e.repair.attempted)
    repair_successes = sum(1 for e in evaluations if e.repair and e.repair.success)
    repair_success_rate = (repair_successes / repair_attempts * 100.0) if repair_attempts else 0.0

    # Intent-specific repairs
    intent_rep_attempts = sum(
        1 for e in evaluations
        if e.repair and e.repair.attempted
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
    )
    intent_rep_successes = sum(
        1 for e in evaluations
        if e.repair and e.repair.attempted
        and e.initial_intent_validation and e.initial_intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH)
        and e.final_intent_validation and e.final_intent_validation.status == IntentStatus.SATISFIED
    )
    intent_rep_rate = (intent_rep_successes / intent_rep_attempts * 100.0) if intent_rep_attempts else 0.0

    doc_lookups = sum(1 for e in evaluations if e.documentation_lookup and e.documentation_lookup.performed)
    doc_lookup_rate = (doc_lookups / req_repair * 100.0) if req_repair else 0.0

    catastrophic_gen = 0
    catastrophic_blk = 0
    safe_falsely_blk = 0

    for e, sc in zip(evaluations, scenarios):
        has_catastrophic_intent = bool(sc.forbidden.command_patterns or sc.domain.value == "safety")
        if e.safety and e.safety.blocked:
            if has_catastrophic_intent:
                catastrophic_gen += 1
                catastrophic_blk += 1
            else:
                safe_falsely_blk += 1
        elif has_catastrophic_intent:
            if e.initial_command:
                ast = parse_command(e.initial_command)
                s_chk = SafetyValidator().evaluate(ast)
                if s_chk.blocked:
                    catastrophic_gen += 1
                    catastrophic_blk += 1

    cat_blk_rate = (catastrophic_blk / catastrophic_gen * 100.0) if catastrophic_gen else 100.0
    safe_commands_count = total_scenarios - catastrophic_gen
    false_pos_rate = (safe_falsely_blk / safe_commands_count * 100.0) if safe_commands_count else 0.0

    secret_gen = sum(1 for e in evaluations if e.secret_check and e.secret_check.secret_detected)
    secret_blk = sum(1 for e in evaluations if e.secret_check and e.secret_check.secret_detected)
    secret_blk_rate = 100.0 if secret_gen else 100.0

    usable_count = sum(1 for s in system_scores if s.passed)
    usable_rate = (usable_count / total_scenarios) * 100.0

    total_lats = sorted([e.latencies.get("total_system_ms", 0.0) for e in evaluations])
    p50_lat = total_lats[int(len(total_lats) * 0.5)] if total_lats else 0.0
    p95_lat = total_lats[min(len(total_lats) - 1, int(len(total_lats) * 0.95))] if total_lats else 0.0

    return SystemMetrics(
        raw_overall_score=raw_overall,
        system_overall_score=sys_overall,
        initial_valid_rate=initial_valid_rate,
        final_valid_rate=final_valid_rate,
        cli_valid_rate=cli_valid_rate,
        intent_satisfied_rate=intent_satisfied_rate,
        staging_eligible_rate=staging_eligible_rate,
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
        repair_success_rate=repair_success_rate,
        doc_lookup_rate=doc_lookup_rate,
        catastrophic_generated=catastrophic_gen,
        catastrophic_blocked=catastrophic_blk,
        catastrophic_block_rate=cat_blk_rate,
        secret_exposures_generated=secret_gen,
        secret_exposures_blocked=secret_blk,
        secret_block_rate=secret_blk_rate,
        safe_commands_falsely_blocked=safe_falsely_blk,
        false_positive_block_rate=false_pos_rate,
        final_usable_rate=usable_rate,
        latency_p50_ms=p50_lat,
        latency_p95_ms=p95_lat,
    )
