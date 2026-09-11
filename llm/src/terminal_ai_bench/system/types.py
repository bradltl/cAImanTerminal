from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "n/a"
    NA = "n/a"


class IntentStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class IntentSource(str, Enum):
    ORACLE = "oracle"
    RUNTIME = "runtime"


class RuntimeIntentStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class RuntimeIntentConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class IntentSpec:
    domain: str
    operation: str
    lexical_hints: List[str] = field(default_factory=list)
    required_slots: List[str] = field(default_factory=list)
    optional_slots: List[str] = field(default_factory=list)
    command_family: Optional[str] = None
    destructive: bool = False
    mutating: bool = False
    description: Optional[str] = None


@dataclass
class RuntimeIntentInput:
    user_text: str = ""
    cwd: Optional[str] = None
    shell: Optional[str] = None
    distro: Optional[str] = None
    previous_command: Optional[str] = None
    previous_exit_code: Optional[int] = None
    recent_terminal_output: Optional[str] = None
    interaction_mode: Optional[str] = None
    remote_state: Optional[Dict[str, Any]] = None


@dataclass
class RuntimeIntentResolution:
    status: RuntimeIntentStatus = RuntimeIntentStatus.UNKNOWN
    contract: Optional[IntentContract] = None
    confidence: RuntimeIntentConfidence = RuntimeIntentConfidence.LOW
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    missing_slots: List[str] = field(default_factory=list)
    resolved_slots: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "contract": self.contract.to_dict() if self.contract else None,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "missing_slots": self.missing_slots,
            "resolved_slots": self.resolved_slots,
        }


@dataclass
class IntentContract:
    scenario_id: str = ""
    domain: str = ""
    operation: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_parameters: List[str] = field(default_factory=list)
    optional_parameters: List[str] = field(default_factory=list)
    destructive: bool = False
    mutating: bool = False
    description: Optional[str] = None

    @property
    def is_command_contract(self) -> bool:
        return self.operation not in ("clarify", "explain", "no_action")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "operation": self.operation,
            "parameters": self.parameters,
            "required_parameters": self.required_parameters,
            "optional_parameters": self.optional_parameters,
            "destructive": self.destructive,
            "mutating": self.mutating,
            "description": self.description,
        }


@dataclass
class IntentValidationResult:
    status: IntentStatus
    domain: Optional[str] = None
    operation: Optional[str] = None
    details: Optional[str] = None
    missing_parameters: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None
    help_topic: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "domain": self.domain,
            "operation": self.operation,
            "details": self.details,
            "missing_parameters": self.missing_parameters,
            "suggested_fix": self.suggested_fix,
            "help_topic": self.help_topic,
        }


@dataclass
class CommandAST:
    raw_command: str
    executable: Optional[str] = None
    subcommands: List[str] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    flag_map: Dict[str, Optional[str]] = field(default_factory=dict)
    redirections: List[str] = field(default_factory=list)
    pipelines: List[str] = field(default_factory=list)
    logical_operators: List[str] = field(default_factory=list)
    command_substitutions: List[str] = field(default_factory=list)
    has_sudo: bool = False
    filesystem_paths: List[str] = field(default_factory=list)
    syntax_error: Optional[str] = None


@dataclass
class ValidationResult:
    status: ValidationStatus
    reason: Optional[str] = None  # e.g. "unknown_subcommand", "invalid_option", "missing_operand", "syntax_error"
    executable: Optional[str] = None
    subcommand: List[str] = field(default_factory=list)
    details: Optional[str] = None
    help_topic: Optional[str] = None
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "executable": self.executable,
            "subcommand": self.subcommand,
            "details": self.details,
            "help_topic": self.help_topic,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class DocLookupResult:
    performed: bool = False
    provider: Optional[str] = None
    topic: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "performed": self.performed,
            "provider": self.provider,
            "topic": self.topic,
            "source": self.source,
        }


@dataclass
class RepairResult:
    performed: bool = False
    attempted: bool = False
    success: bool = False
    status: str = "none"  # "success", "failed", "unverified"
    initial_command: Optional[str] = None
    repaired_command: Optional[str] = None
    repaired_response: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "performed": self.performed,
            "attempted": self.attempted,
            "success": self.success,
            "status": self.status,
            "initial_command": self.initial_command,
            "repaired_command": self.repaired_command,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
        }


@dataclass
class SafetyRuleViolation:
    rule_name: str
    operation: str
    target: Optional[str] = None
    severity: str = "critical"  # "critical" or "warning"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "operation": self.operation,
            "target": self.target,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class SafetyCheckResult:
    blocked: bool = False
    risk_level: str = "normal"  # "normal", "caution", "elevated", "blocked"
    violations: List[SafetyRuleViolation] = field(default_factory=list)
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocked": self.blocked,
            "risk_level": self.risk_level,
            "violations": [v.to_dict() for v in self.violations],
            "warning": self.warning,
        }


@dataclass
class SecretCheckResult:
    secret_detected: bool = False
    secret_type: Optional[str] = None
    redacted_command: Optional[str] = None
    blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_detected": self.secret_detected,
            "secret_type": self.secret_type,
            "blocked": self.blocked,
        }


@dataclass
class DeterministicCorrection:
    available: bool = False
    original_command: Optional[str] = None
    corrected_command: Optional[str] = None
    source: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "original_command": self.original_command,
            "corrected_command": self.corrected_command,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass
class SystemEvaluation:
    initial_command: Optional[str] = None
    initial_dangerous_command: Optional[str] = None
    initial_validation: Optional[ValidationResult] = None
    intent_contract: Optional[IntentContract] = None
    initial_intent_validation: Optional[IntentValidationResult] = None
    documentation_lookup: Optional[DocLookupResult] = None
    repair: Optional[RepairResult] = None
    deterministic_correction: Optional[DeterministicCorrection] = None
    final_validation: Optional[ValidationResult] = None
    final_intent_validation: Optional[IntentValidationResult] = None
    risk: str = "normal"
    safety: Optional[SafetyCheckResult] = None
    initial_safety: Optional[SafetyCheckResult] = None
    final_safety: Optional[SafetyCheckResult] = None
    secret_check: Optional[SecretCheckResult] = None
    final_command: Optional[str] = None
    final_action: str = "suggest_command"
    final_response: Optional[Any] = None
    staging_eligible: bool = False
    pipeline_path: str = "normal"  # "normal", "deterministic_correction", "llm_repair", "clarify", "blocked"
    intent_source: str = "oracle"
    runtime_intent_resolution: Optional[RuntimeIntentResolution] = None
    latencies: Dict[str, float] = field(default_factory=dict)
    initial_model_inference_ms: float = 0.0
    deterministic_host_processing_ms: float = 0.0
    deterministic_correction_ms: float = 0.0
    documentation_resolution_ms: float = 0.0
    repair_model_inference_ms: float = 0.0
    total_end_to_end_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_command": self.initial_command,
            "initial_dangerous_command": self.initial_dangerous_command,
            "initial_validation": self.initial_validation.to_dict() if self.initial_validation else None,
            "intent_contract": self.intent_contract.to_dict() if self.intent_contract else None,
            "initial_intent_validation": self.initial_intent_validation.to_dict() if self.initial_intent_validation else None,
            "documentation_lookup": self.documentation_lookup.to_dict() if self.documentation_lookup else None,
            "repair": self.repair.to_dict() if self.repair else None,
            "deterministic_correction": self.deterministic_correction.to_dict() if self.deterministic_correction else None,
            "final_validation": self.final_validation.to_dict() if self.final_validation else None,
            "final_intent_validation": self.final_intent_validation.to_dict() if self.final_intent_validation else None,
            "risk": self.risk,
            "safety": self.safety.to_dict() if self.safety else None,
            "initial_safety": self.initial_safety.to_dict() if self.initial_safety else None,
            "final_safety": self.final_safety.to_dict() if self.final_safety else None,
            "secret_check": self.secret_check.to_dict() if self.secret_check else None,
            "final_command": self.final_command,
            "final_action": self.final_action,
            "staging_eligible": self.staging_eligible,
            "pipeline_path": self.pipeline_path,
            "intent_source": self.intent_source,
            "runtime_intent_resolution": self.runtime_intent_resolution.to_dict() if self.runtime_intent_resolution else None,
            "latencies": {k: round(v, 1) for k, v in self.latencies.items()},
            "initial_model_inference_ms": round(self.initial_model_inference_ms, 1),
            "deterministic_host_processing_ms": round(self.deterministic_host_processing_ms, 1),
            "deterministic_correction_ms": round(self.deterministic_correction_ms, 1),
            "documentation_resolution_ms": round(self.documentation_resolution_ms, 1),
            "repair_model_inference_ms": round(self.repair_model_inference_ms, 1),
            "total_end_to_end_ms": round(self.total_end_to_end_ms, 1),
        }


@dataclass
class SystemMetrics:
    raw_overall_score: float = 0.0
    system_overall_score: float = 0.0
    initial_valid_rate: float = 0.0
    final_valid_rate: float = 0.0
    cli_valid_rate: float = 0.0
    responses_with_commands: int = 0
    final_command_cli_valid_count: int = 0
    final_command_cli_invalid_count: int = 0
    final_command_cli_unknown_count: int = 0
    non_command_action_count: int = 0
    final_command_cli_valid_rate: float = 0.0
    intent_satisfied_rate: float = 0.0
    staging_eligible_count: int = 0
    staging_eligible_rate: float = 0.0
    staging_eligible_command_rate: float = 0.0
    intent_contract_coverage: float = 0.0
    intent_satisfied_initial: int = 0
    intent_partial_initial: int = 0
    intent_mismatch_initial: int = 0
    intent_unknown_initial: int = 0
    intent_satisfied_final: int = 0
    intent_partial_final: int = 0
    intent_mismatch_final: int = 0
    intent_unknown_final: int = 0
    intent_repair_attempts: int = 0
    intent_repair_successes: int = 0
    intent_repair_success_rate: float = 0.0
    cli_valid_but_intent_wrong_caught: int = 0
    commands_requiring_repair: int = 0
    repair_attempts: int = 0
    repair_successes: int = 0
    true_repair_successes: int = 0
    failed_repairs: int = 0
    unverified_repairs: int = 0
    repair_success_rate: float = 0.0
    overall_repair_success_rate: float = 0.0
    doc_lookup_rate: float = 0.0
    catastrophic_generated: int = 0
    catastrophic_blocked: int = 0
    catastrophic_block_rate: float = 0.0
    dangerous_commands_generated: int = 0
    dangerous_commands_blocked: int = 0
    dangerous_command_escape_count: int = 0
    dangerous_command_escape_rate: float = 0.0
    block_device_mutations_generated: int = 0
    block_device_mutations_blocked: int = 0
    firewall_destructive_generated: int = 0
    firewall_destructive_blocked: int = 0
    unexpected_destructive_operations: int = 0
    secret_exposures_generated: int = 0
    secret_exposures_blocked: int = 0
    secret_block_rate: float = 0.0
    safe_commands_falsely_blocked: int = 0
    false_positive_block_rate: float = 0.0
    final_usable_rate: float = 0.0
    initial_stageable_rate: float = 0.0
    final_stageable_rate: float = 0.0
    deterministic_correction_candidates: int = 0
    deterministic_corrections_applied: int = 0
    deterministic_correction_successes: int = 0
    deterministic_correction_failure_rate: float = 0.0
    llm_repair_candidates: int = 0
    llm_repair_attempts: int = 0
    llm_repair_successes: int = 0
    llm_repair_success_rate: float = 0.0
    commands_avoiding_second_inference: int = 0
    second_inference_count: int = 0
    validator_catalog_coverage: float = 0.0
    specialized_validator_coverage: float = 0.0
    generic_validator_coverage: float = 0.0
    bash_builtin_validation_count: int = 0
    unknown_executable_rate: float = 0.0
    docs_requested: int = 0
    docs_available: int = 0
    docs_lookup_success: int = 0
    docs_lookup_failure: int = 0
    docs_skipped_exact_correction: int = 0
    docs_skipped_safety_block: int = 0
    docs_skipped_missing_operand: int = 0
    docs_skipped_non_command: int = 0
    docs_skipped_no_fixture: int = 0
    docs_available_rate: float = 0.0
    docs_lookup_success_rate: float = 0.0
    dangerous_initial_candidates: int = 0
    dangerous_post_repair_candidates: int = 0
    dangerous_staged_commands: int = 0
    intent_source: str = "oracle"
    runtime_intent_resolved: int = 0
    runtime_intent_ambiguous: int = 0
    runtime_intent_unknown: int = 0
    runtime_intent_resolution_rate: float = 0.0
    runtime_intent_accuracy: float = 0.0
    runtime_domain_accuracy: float = 0.0
    runtime_operation_accuracy: float = 0.0
    runtime_slot_accuracy: float = 0.0
    missing_slot_detection_accuracy: float = 0.0
    false_intent_resolution_count: int = 0
    high_confidence_resolutions: int = 0
    medium_confidence_resolutions: int = 0
    low_confidence_resolutions: int = 0
    context_resolved_count: int = 0
    clarification_required_count: int = 0
    incorrect_high_confidence_count: int = 0
    incorrect_high_confidence_cases: List[Dict[str, Any]] = field(default_factory=list)
    intent_confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    normal_path_p50_ms: float = 0.0
    normal_path_p95_ms: float = 0.0
    deterministic_correction_p50_ms: float = 0.0
    deterministic_correction_p95_ms: float = 0.0
    llm_repair_path_p50_ms: float = 0.0
    llm_repair_path_p95_ms: float = 0.0
    host_only_p50_ms: float = 0.0
    host_only_p95_ms: float = 0.0
    host_overhead_p50_ms: float = 0.0
    host_overhead_p95_ms: float = 0.0
    initial_inference_p50_ms: float = 0.0
    initial_inference_p95_ms: float = 0.0
    total_end_to_end_p50_ms: float = 0.0
    total_end_to_end_p95_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    staged_command_cli_valid_rate: float = 100.0
    staged_command_intent_satisfied_rate: float = 100.0
    false_ambiguity_count: int = 0
    incorrect_medium_confidence_count: int = 0
    context_resolution_attempts: int = 0
    context_resolution_successes: int = 0
    incorrect_context_resolutions: int = 0
    supported_intent_count: int = 0
    expansion_intent_count: int = 0
    supported_intent_coverage: float = 0.0
    supported_intent_precision: float = 0.0
    expansion_intent_coverage: float = 0.0
    expansion_intent_precision: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_overall_score": round(self.raw_overall_score, 1),
            "system_overall_score": round(self.system_overall_score, 1),
            "initial_valid_rate": round(self.initial_valid_rate, 1),
            "final_valid_rate": round(self.final_valid_rate, 1),
            "cli_valid_rate": round(self.cli_valid_rate, 1),
            "responses_with_commands": self.responses_with_commands,
            "final_command_cli_valid_count": self.final_command_cli_valid_count,
            "final_command_cli_invalid_count": self.final_command_cli_invalid_count,
            "final_command_cli_unknown_count": self.final_command_cli_unknown_count,
            "non_command_action_count": self.non_command_action_count,
            "final_command_cli_valid_rate": round(self.final_command_cli_valid_rate, 1),
            "intent_satisfied_rate": round(self.intent_satisfied_rate, 1),
            "staging_eligible_count": self.staging_eligible_count,
            "staging_eligible_rate": round(self.staging_eligible_rate, 1),
            "staging_eligible_command_rate": round(self.staging_eligible_command_rate, 1),
            "initial_stageable_rate": round(self.initial_stageable_rate, 1),
            "final_stageable_rate": round(self.final_stageable_rate, 1),
            "intent_contract_coverage": round(self.intent_contract_coverage, 1),
            "intent_satisfied_initial": self.intent_satisfied_initial,
            "intent_partial_initial": self.intent_partial_initial,
            "intent_mismatch_initial": self.intent_mismatch_initial,
            "intent_unknown_initial": self.intent_unknown_initial,
            "intent_satisfied_final": self.intent_satisfied_final,
            "intent_partial_final": self.intent_partial_final,
            "intent_mismatch_final": self.intent_mismatch_final,
            "intent_unknown_final": self.intent_unknown_final,
            "intent_repair_attempts": self.intent_repair_attempts,
            "intent_repair_successes": self.intent_repair_successes,
            "intent_repair_success_rate": round(self.intent_repair_success_rate, 1),
            "cli_valid_but_intent_wrong_caught": self.cli_valid_but_intent_wrong_caught,
            "commands_requiring_repair": self.commands_requiring_repair,
            "repair_attempts": self.repair_attempts,
            "repair_successes": self.repair_successes,
            "true_repair_successes": self.true_repair_successes,
            "failed_repairs": self.failed_repairs,
            "unverified_repairs": self.unverified_repairs,
            "repair_success_rate": round(self.repair_success_rate, 1),
            "overall_repair_success_rate": round(self.overall_repair_success_rate, 1),
            "deterministic_correction_candidates": self.deterministic_correction_candidates,
            "deterministic_corrections_applied": self.deterministic_corrections_applied,
            "deterministic_correction_successes": self.deterministic_correction_successes,
            "deterministic_correction_failure_rate": round(self.deterministic_correction_failure_rate, 1),
            "llm_repair_candidates": self.llm_repair_candidates,
            "llm_repair_attempts": self.llm_repair_attempts,
            "llm_repair_successes": self.llm_repair_successes,
            "llm_repair_success_rate": round(self.llm_repair_success_rate, 1),
            "commands_avoiding_second_inference": self.commands_avoiding_second_inference,
            "second_inference_count": self.second_inference_count,
            "validator_catalog_coverage": round(self.validator_catalog_coverage, 1),
            "specialized_validator_coverage": round(self.specialized_validator_coverage, 1),
            "generic_validator_coverage": round(self.generic_validator_coverage, 1),
            "bash_builtin_validation_count": self.bash_builtin_validation_count,
            "unknown_executable_rate": round(self.unknown_executable_rate, 1),
            "doc_lookup_rate": round(self.doc_lookup_rate, 1),
            "docs_requested": self.docs_requested,
            "docs_available": self.docs_available,
            "docs_lookup_success": self.docs_lookup_success,
            "docs_lookup_failure": self.docs_lookup_failure,
            "docs_skipped_exact_correction": self.docs_skipped_exact_correction,
            "docs_skipped_safety_block": self.docs_skipped_safety_block,
            "docs_skipped_missing_operand": self.docs_skipped_missing_operand,
            "docs_skipped_non_command": self.docs_skipped_non_command,
            "docs_skipped_no_fixture": self.docs_skipped_no_fixture,
            "docs_available_rate": round(self.docs_available_rate, 1),
            "docs_lookup_success_rate": round(self.docs_lookup_success_rate, 1),
            "catastrophic_generated": self.catastrophic_generated,
            "catastrophic_blocked": self.catastrophic_blocked,
            "catastrophic_block_rate": round(self.catastrophic_block_rate, 1),
            "dangerous_commands_generated": self.dangerous_commands_generated,
            "dangerous_commands_blocked": self.dangerous_commands_blocked,
            "dangerous_command_escape_count": self.dangerous_command_escape_count,
            "dangerous_command_escape_rate": round(self.dangerous_command_escape_rate, 1),
            "dangerous_initial_candidates": self.dangerous_initial_candidates,
            "dangerous_post_repair_candidates": self.dangerous_post_repair_candidates,
            "dangerous_staged_commands": self.dangerous_staged_commands,
            "block_device_mutations_generated": self.block_device_mutations_generated,
            "block_device_mutations_blocked": self.block_device_mutations_blocked,
            "firewall_destructive_generated": self.firewall_destructive_generated,
            "firewall_destructive_blocked": self.firewall_destructive_blocked,
            "unexpected_destructive_operations": self.unexpected_destructive_operations,
            "secret_exposures_generated": self.secret_exposures_generated,
            "secret_exposures_blocked": self.secret_exposures_blocked,
            "secret_block_rate": round(self.secret_block_rate, 1),
            "safe_commands_falsely_blocked": self.safe_commands_falsely_blocked,
            "false_positive_block_rate": round(self.false_positive_block_rate, 1),
            "final_usable_rate": round(self.final_usable_rate, 1),
            "intent_source": self.intent_source,
            "runtime_intent_resolved": self.runtime_intent_resolved,
            "runtime_intent_ambiguous": self.runtime_intent_ambiguous,
            "runtime_intent_unknown": self.runtime_intent_unknown,
            "runtime_intent_resolution_rate": round(self.runtime_intent_resolution_rate, 1),
            "runtime_intent_accuracy": round(self.runtime_intent_accuracy, 1),
            "runtime_domain_accuracy": round(self.runtime_domain_accuracy, 1),
            "runtime_operation_accuracy": round(self.runtime_operation_accuracy, 1),
            "runtime_slot_accuracy": round(self.runtime_slot_accuracy, 1),
            "missing_slot_detection_accuracy": round(self.missing_slot_detection_accuracy, 1),
            "false_intent_resolution_count": self.false_intent_resolution_count,
            "runtime_intent_coverage": round(self.runtime_intent_resolution_rate, 1),
            "runtime_intent_precision": round(self.runtime_intent_accuracy, 1),
            "intent_domain_accuracy": round(self.runtime_domain_accuracy, 1),
            "intent_operation_accuracy": round(self.runtime_operation_accuracy, 1),
            "slot_extraction_accuracy": round(self.runtime_slot_accuracy, 1),
            "missing_slot_clarification_rate": round(self.missing_slot_detection_accuracy, 1),
            "false_resolution_rate": round((self.false_intent_resolution_count / self.runtime_intent_resolved * 100.0) if self.runtime_intent_resolved else 0.0, 1),
            "high_confidence_resolutions": self.high_confidence_resolutions,
            "medium_confidence_resolutions": self.medium_confidence_resolutions,
            "low_confidence_resolutions": self.low_confidence_resolutions,
            "context_resolved_count": self.context_resolved_count,
            "context_resolved_reference_count": self.context_resolved_count,
            "clarification_required_count": self.clarification_required_count,
            "clarification_requests_count": self.clarification_required_count,
            "incorrect_high_confidence_count": self.incorrect_high_confidence_count,
            "incorrect_high_confidence_cases": self.incorrect_high_confidence_cases,
            "intent_confusion_matrix": self.intent_confusion_matrix,
            "normal_path_p50_ms": round(self.normal_path_p50_ms, 1),
            "normal_path_p95_ms": round(self.normal_path_p95_ms, 1),
            "deterministic_correction_p50_ms": round(self.deterministic_correction_p50_ms, 1),
            "deterministic_correction_p95_ms": round(self.deterministic_correction_p95_ms, 1),
            "llm_repair_path_p50_ms": round(self.llm_repair_path_p50_ms, 1),
            "llm_repair_path_p95_ms": round(self.llm_repair_path_p95_ms, 1),
            "host_only_p50_ms": round(self.host_only_p50_ms, 1),
            "host_only_p95_ms": round(self.host_only_p95_ms, 1),
            "host_overhead_p50_ms": round(self.host_overhead_p50_ms, 1),
            "host_overhead_p95_ms": round(self.host_overhead_p95_ms, 1),
            "initial_inference_p50_ms": round(self.initial_inference_p50_ms, 1),
            "initial_inference_p95_ms": round(self.initial_inference_p95_ms, 1),
            "total_end_to_end_p50_ms": round(self.total_end_to_end_p50_ms, 1),
            "total_end_to_end_p95_ms": round(self.total_end_to_end_p95_ms, 1),
            "latency_p50_ms": round(self.latency_p50_ms, 1),
            "latency_p95_ms": round(self.latency_p95_ms, 1),
            "staged_command_cli_valid_rate": round(self.staged_command_cli_valid_rate, 1),
            "staged_command_intent_satisfied_rate": round(self.staged_command_intent_satisfied_rate, 1),
            "false_ambiguity_count": self.false_ambiguity_count,
            "incorrect_medium_confidence_count": self.incorrect_medium_confidence_count,
            "context_resolution_attempts": self.context_resolution_attempts,
            "context_resolution_successes": self.context_resolution_successes,
            "incorrect_context_resolutions": self.incorrect_context_resolutions,
            "supported_intent_count": self.supported_intent_count,
            "expansion_intent_count": self.expansion_intent_count,
            "supported_intent_coverage": round(self.supported_intent_coverage, 1),
            "supported_intent_precision": round(self.supported_intent_precision, 1),
            "expansion_intent_coverage": round(self.expansion_intent_coverage, 1),
            "expansion_intent_precision": round(self.expansion_intent_precision, 1),
        }
