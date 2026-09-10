from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class IntentStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


@dataclass
class IntentContract:
    domain: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_parameters: List[str] = field(default_factory=list)
    optional_parameters: List[str] = field(default_factory=list)
    destructive: bool = False
    mutating: bool = False
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
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
class SystemEvaluation:
    initial_command: Optional[str] = None
    initial_validation: Optional[ValidationResult] = None
    intent_contract: Optional[IntentContract] = None
    initial_intent_validation: Optional[IntentValidationResult] = None
    documentation_lookup: Optional[DocLookupResult] = None
    repair: Optional[RepairResult] = None
    final_validation: Optional[ValidationResult] = None
    final_intent_validation: Optional[IntentValidationResult] = None
    risk: str = "normal"
    safety: Optional[SafetyCheckResult] = None
    secret_check: Optional[SecretCheckResult] = None
    final_command: Optional[str] = None
    final_action: str = "suggest_command"
    final_response: Optional[Any] = None
    staging_eligible: bool = False
    latencies: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_command": self.initial_command,
            "initial_validation": self.initial_validation.to_dict() if self.initial_validation else None,
            "intent_contract": self.intent_contract.to_dict() if self.intent_contract else None,
            "initial_intent_validation": self.initial_intent_validation.to_dict() if self.initial_intent_validation else None,
            "documentation_lookup": self.documentation_lookup.to_dict() if self.documentation_lookup else None,
            "repair": self.repair.to_dict() if self.repair else None,
            "final_validation": self.final_validation.to_dict() if self.final_validation else None,
            "final_intent_validation": self.final_intent_validation.to_dict() if self.final_intent_validation else None,
            "risk": self.risk,
            "safety": self.safety.to_dict() if self.safety else None,
            "secret_check": self.secret_check.to_dict() if self.secret_check else None,
            "final_command": self.final_command,
            "final_action": self.final_action,
            "staging_eligible": self.staging_eligible,
            "latencies": {k: round(v, 1) for k, v in self.latencies.items()},
        }


@dataclass
class SystemMetrics:
    raw_overall_score: float = 0.0
    system_overall_score: float = 0.0
    initial_valid_rate: float = 0.0
    final_valid_rate: float = 0.0
    cli_valid_rate: float = 0.0
    intent_satisfied_rate: float = 0.0
    staging_eligible_rate: float = 0.0
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
    repair_success_rate: float = 0.0
    doc_lookup_rate: float = 0.0
    catastrophic_generated: int = 0
    catastrophic_blocked: int = 0
    catastrophic_block_rate: float = 0.0
    secret_exposures_generated: int = 0
    secret_exposures_blocked: int = 0
    secret_block_rate: float = 0.0
    safe_commands_falsely_blocked: int = 0
    false_positive_block_rate: float = 0.0
    final_usable_rate: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_overall_score": round(self.raw_overall_score, 1),
            "system_overall_score": round(self.system_overall_score, 1),
            "initial_valid_rate": round(self.initial_valid_rate, 1),
            "final_valid_rate": round(self.final_valid_rate, 1),
            "cli_valid_rate": round(self.cli_valid_rate, 1),
            "intent_satisfied_rate": round(self.intent_satisfied_rate, 1),
            "staging_eligible_rate": round(self.staging_eligible_rate, 1),
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
            "repair_success_rate": round(self.repair_success_rate, 1),
            "doc_lookup_rate": round(self.doc_lookup_rate, 1),
            "catastrophic_generated": self.catastrophic_generated,
            "catastrophic_blocked": self.catastrophic_blocked,
            "catastrophic_block_rate": round(self.catastrophic_block_rate, 1),
            "secret_exposures_generated": self.secret_exposures_generated,
            "secret_exposures_blocked": self.secret_exposures_blocked,
            "secret_block_rate": round(self.secret_block_rate, 1),
            "safe_commands_falsely_blocked": self.safe_commands_falsely_blocked,
            "false_positive_block_rate": round(self.false_positive_block_rate, 1),
            "final_usable_rate": round(self.final_usable_rate, 1),
            "latency_p50_ms": round(self.latency_p50_ms, 1),
            "latency_p95_ms": round(self.latency_p95_ms, 1),
        }
