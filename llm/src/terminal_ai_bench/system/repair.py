from __future__ import annotations

import time
from typing import Any, Optional

from ..output_parser import parse_response
from .command_parser import parse_command
from .command_validator import validate_command
from .types import (
    DocLookupResult,
    IntentContract,
    IntentStatus,
    IntentValidationResult,
    RepairResult,
    ValidationResult,
    ValidationStatus,
)


def build_repair_prompt(
    user_intent: str,
    candidate_command: str,
    validation: Optional[ValidationResult] = None,
    doc_lookup: Optional[DocLookupResult] = None,
    system_prompt: Optional[str] = None,
    intent_contract: Optional[IntentContract] = None,
    intent_validation: Optional[IntentValidationResult] = None,
) -> str:
    """Construct a clean, single-pass repair prompt incorporating CLI and Intent errors."""
    errors = []
    if validation and validation.status == ValidationStatus.INVALID:
        errors.append(f"CLI validation error: {validation.details or validation.reason}")
    if intent_validation and intent_validation.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH):
        status_label = "Semantic intent incomplete (PARTIAL)" if intent_validation.status == IntentStatus.PARTIAL else "Semantic intent mismatch (MISMATCH)"
        msg = f"{status_label}: {intent_validation.details or 'Command does not satisfy user intent.'}"
        if intent_validation.missing_parameters:
            msg += f" (Missing required: {', '.join(intent_validation.missing_parameters)})"
        errors.append(msg)
    if not errors:
        errors.append(f"Validation error: {validation.details if validation else 'Invalid command'}")

    details = "\n".join(errors)

    suggested = ""
    if intent_validation and intent_validation.suggested_fix:
        suggested = f"\nSuggested fix direction: {intent_validation.suggested_fix}\n"
    elif validation and validation.suggested_fix:
        suggested = f"\nSuggested fix direction: {validation.suggested_fix}\n"

    doc_section = ""
    if doc_lookup and doc_lookup.performed and doc_lookup.content:
        doc_section = f"\nRelevant installed documentation:\n{doc_lookup.content}\n"

    prompt_sys = system_prompt or (
        "You are an embedded local Linux terminal AI assistant for an interactive terminal emulator. "
        "Target environment: Arch Linux / CachyOS with Bash. "
        "Classify risk accurately, warn on elevated operations, and when arguments are missing, output action 'clarify'."
    )

    return (
        f"<|im_start|>system\n{prompt_sys}<|im_end|>\n"
        f"<|im_start|>user\n"
        f"[SYSTEM HOST REPAIR PASS]\n"
        f"Original user intent:\n{user_intent}\n\n"
        f"Original candidate:\n{candidate_command}\n\n"
        f"Validation error:\n{details}\n"
        f"{suggested}"
        f"{doc_section}\n"
        f"Return the corrected cAIman Terminal response.\n"
        f"Do not change the user's intent.\n"
        f"Do not invent identifiers or arguments.\n"
        f"Respond in structured JSON according to the contract:<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


class CommandRepairEngine:
    """
    Single-pass LLM repair engine for cAIman Terminal.
    Ensures at most ONE model repair inference pass occurs without looping.
    """

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt or (
            "You are an embedded local Linux terminal AI assistant for an interactive terminal emulator. "
            "Target environment: Arch Linux / CachyOS with Bash. "
            "Classify risk accurately, warn on elevated operations, and when arguments are missing, output action 'clarify'."
        )

    def attempt_repair(
        self,
        runtime: Any,
        user_intent: str,
        initial_command: str,
        validation: Optional[ValidationResult] = None,
        doc_lookup: Optional[DocLookupResult] = None,
        intent_contract: Optional[IntentContract] = None,
        intent_validation: Optional[IntentValidationResult] = None,
    ) -> tuple[RepairResult, Optional[ValidationResult], Optional[Any]]:
        """
        Executes exactly one repair inference.
        Re-validates the candidate. Never loops.
        """
        if not initial_command:
            return RepairResult(performed=False), None, None

        prompt = build_repair_prompt(
            user_intent=user_intent,
            candidate_command=initial_command,
            validation=validation,
            doc_lookup=doc_lookup,
            system_prompt=self.system_prompt,
            intent_contract=intent_contract,
            intent_validation=intent_validation,
        )

        start_t = time.perf_counter()
        try:
            infer_res = runtime.infer(prompt)
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            parse_res = parse_response(infer_res.text)

            if not parse_res.success or not parse_res.response:
                return (
                    RepairResult(
                        performed=True,
                        attempted=True,
                        success=False,
                        initial_command=initial_command,
                        error="Failed to parse repair response JSON",
                        latency_ms=latency_ms,
                    ),
                    None,
                    None,
                )

            repaired_cmd = parse_res.response.command
            if not repaired_cmd:
                # Model may have opted to clarify or explain
                return (
                    RepairResult(
                        performed=True,
                        attempted=True,
                        success=True,
                        initial_command=initial_command,
                        repaired_command=None,
                        repaired_response=parse_res.response,
                        latency_ms=latency_ms,
                    ),
                    ValidationResult(status=ValidationStatus.VALID),
                    parse_res.response,
                )

            # Re-validate the repaired command
            repaired_ast = parse_command(repaired_cmd)
            reval = validate_command(repaired_ast)
            is_success = reval.status != ValidationStatus.INVALID

            if intent_contract:
                from .intent_validator import IntentContractValidator
                val_intent = IntentContractValidator().evaluate(repaired_ast, intent_contract)
                if val_intent.status in (IntentStatus.PARTIAL, IntentStatus.MISMATCH):
                    is_success = False

            return (
                RepairResult(
                    performed=True,
                    attempted=True,
                    success=is_success,
                    initial_command=initial_command,
                    repaired_command=repaired_cmd,
                    repaired_response=parse_res.response,
                    latency_ms=latency_ms,
                ),
                reval,
                parse_res.response,
            )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return (
                RepairResult(
                    performed=True,
                    attempted=True,
                    success=False,
                    initial_command=initial_command,
                    error=str(exc),
                    latency_ms=latency_ms,
                ),
                None,
                None,
            )
