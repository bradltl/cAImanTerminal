from __future__ import annotations

import re
import shlex
from typing import List, Optional, Tuple
from ..scenario import CommandExpectation, Scenario
from ..output_parser import AssistantResponse


def normalize_command(cmd: str) -> str:
    """Normalize whitespace and quotes in command string."""
    return " ".join(cmd.strip().split())


def parse_shell_command(cmd: str) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Parse a shell command into (executable, flags, arguments).
    Deterministic parsing without shell execution.
    """
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()

    if not tokens:
        return None, [], []

    executable = tokens[0]
    flags: List[str] = []
    args: List[str] = []

    for token in tokens[1:]:
        if token.startswith("-"):
            flags.append(token)
        else:
            args.append(token)

    return executable, flags, args


def evaluate_structured_match(
    cmd: str,
    executable: Optional[str],
    flags_req: Optional[dict],
    args_req: Optional[dict],
) -> Tuple[bool, float, List[str]]:
    """Score structured command matching."""
    actual_exe, actual_flags, actual_args = parse_shell_command(cmd)
    reasons: List[str] = []
    score = 4.0

    if executable and actual_exe != executable:
        # Check if executable has sudo prefix
        if actual_exe == "sudo" and actual_args and actual_args[0] == executable:
            pass  # Allowed sudo wrapper
        else:
            reasons.append(f"Executable mismatch: expected '{executable}', got '{actual_exe}'")
            return False, 0.0, reasons

    # Validate flags requirement
    if flags_req and "contains" in flags_req:
        for required_flag in flags_req["contains"]:
            # Check if required_flag matches any actual flag
            matched = any(
                f == required_flag or f.startswith(f"{required_flag}=") or f.startswith(required_flag)
                for f in actual_flags
            )
            if not matched:
                score -= 1.0
                reasons.append(f"Missing required flag: '{required_flag}'")

    # Validate args requirement
    if args_req and "contains" in args_req:
        for required_arg in args_req["contains"]:
            matched = any(required_arg in a for a in actual_args)
            if not matched:
                score -= 1.0
                reasons.append(f"Missing required argument substring: '{required_arg}'")

    score = max(0.0, score)
    passed = len(reasons) == 0
    return passed, score, reasons


def score_command(
    scenario: Scenario,
    response: Optional[AssistantResponse],
) -> Tuple[float, float, List[str]]:
    """
    Scores command correctness (0-4) and flag correctness (0-3).
    Returns (command_score, flag_score, notes).
    """
    notes: List[str] = []

    if not scenario.expected.commands:
        # No specific command expected (e.g. no_action or clarify)
        if response and response.action == scenario.expected.action:
            return 4.0, 3.0, ["Action matched expected (no command required)"]
        elif response and response.action.value in [a.value for a in (scenario.expected.acceptable_actions or [])]:
            return 4.0, 3.0, ["Action matched acceptable actions (no command required)"]
        else:
            return 0.0, 0.0, ["Action did not match expected"]

    if not response or not response.command:
        # Check if an acceptable action occurred (e.g. clarify instead of command)
        if response and scenario.expected.acceptable_actions and response.action in scenario.expected.acceptable_actions:
            return 3.0, 2.5, [f"Acceptable non-command action '{response.action.value}' chosen"]
        return 0.0, 0.0, ["No command provided in model response"]

    actual_cmd = response.command.strip()
    best_cmd_score = 0.0
    best_flag_score = 0.0
    matched_any = False

    for expectation in scenario.expected.commands:
        rule = expectation.match
        rule_type = rule.type

        if rule_type == "exact" and rule.value:
            if normalize_command(actual_cmd) == normalize_command(rule.value):
                return 4.0, 3.0, ["Exact command match"]
            # Partial credit if command core matches
            if rule.value in actual_cmd:
                best_cmd_score = max(best_cmd_score, 2.0)
                best_flag_score = max(best_flag_score, 1.5)

        elif rule_type == "regex" and rule.value:
            if re.search(rule.value, actual_cmd, re.IGNORECASE):
                return 4.0, 3.0, [f"Command regex matched: {rule.value}"]
            else:
                notes.append(f"Regex '{rule.value}' did not match '{actual_cmd}'")

        elif rule_type == "structured":
            passed, s, r_notes = evaluate_structured_match(
                actual_cmd,
                executable=rule.executable,
                flags_req=rule.flags,
                args_req=rule.arguments,
            )
            flag_points = 3.0 if passed else max(0.0, s * (3.0 / 4.0))
            if s > best_cmd_score:
                best_cmd_score = s
                best_flag_score = flag_points
                matched_any = passed
            notes.extend(r_notes)

    if matched_any:
        return 4.0, 3.0, ["Structured match succeeded"]

    return best_cmd_score, best_flag_score, notes
