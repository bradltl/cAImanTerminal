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


def check_semantic_equivalence(actual_cmd: str, expected_target: str) -> bool:
    """Check deterministic semantic equivalence between commands (e.g. ss vs lsof, curl vs wget)."""
    if not actual_cmd or not expected_target:
        return False
    a = normalize_command(actual_cmd)
    e = normalize_command(expected_target)
    if a == e:
        return True

    # 1. Flag ordering for common commands (e.g. ls -la vs ls -al, rm -rf vs rm -fr)
    try:
        a_tokens = shlex.split(a)
        e_tokens = shlex.split(e)
        if a_tokens and e_tokens and a_tokens[0] == e_tokens[0]:
            a_flags, a_args = set(), []
            for t in a_tokens[1:]:
                if t.startswith("--"):
                    a_flags.add(t)
                elif t.startswith("-") and len(t) > 1:
                    for char in t[1:]:
                        a_flags.add(f"-{char}")
                else:
                    a_args.append(t)
            e_flags, e_args = set(), []
            for t in e_tokens[1:]:
                if t.startswith("--"):
                    e_flags.add(t)
                elif t.startswith("-") and len(t) > 1:
                    for char in t[1:]:
                        e_flags.add(f"-{char}")
                else:
                    e_args.append(t)
            if a_flags == e_flags and a_args == e_args:
                return True
    except Exception:
        pass

    # 2. Listening sockets / open ports (ss vs netstat vs lsof)
    is_a_socket = any(s in a for s in ("ss -tul", "ss -tlpn", "ss -tulpn", "netstat -tul", "lsof -i"))
    is_e_socket = any(s in e for s in ("ss -tul", "ss -tlpn", "ss -tulpn", "netstat -tul", "lsof -i"))
    if is_a_socket and is_e_socket:
        return True

    # 3. Git branch switch vs checkout
    m_a = re.match(r"^git\s+(?:switch|checkout)\s+([a-zA-Z0-9_\-\./]+)$", a)
    m_e = re.match(r"^git\s+(?:switch|checkout)\s+([a-zA-Z0-9_\-\./]+)$", e)
    if m_a and m_e and m_a.group(1) == m_e.group(1):
        return True

    # 4. Downloads: curl vs wget
    if ("curl" in a and "wget" in e) or ("wget" in a and "curl" in e):
        url_pat = r"https?://[^\s\"']+"
        a_urls = re.findall(url_pat, a)
        e_urls = re.findall(url_pat, e)
        if a_urls and e_urls and a_urls == e_urls:
            return True

    # 5. Pacman system sync: pacman -Syu vs pacman -Syyu (with optional sudo)
    a_clean = a.removeprefix("sudo ").strip()
    e_clean = e.removeprefix("sudo ").strip()
    if a_clean in ("pacman -Syu", "pacman -Syyu") and e_clean in ("pacman -Syu", "pacman -Syyu"):
        return True

    # 6. Diff: diff -u f1 f2 vs diff f1 f2 vs git diff --no-index f1 f2
    m_diff_a = re.search(r"diff\s+(?:-u\s+)?([^\s]+)\s+([^\s]+)", a)
    m_diff_e = re.search(r"diff\s+(?:-u\s+)?([^\s]+)\s+([^\s]+)", e)
    if m_diff_a and m_diff_e and m_diff_a.groups() == m_diff_e.groups():
        return True

    return False


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
            if check_semantic_equivalence(actual_cmd, rule.value):
                return 4.0, 3.0, [f"Semantic equivalence matched with '{rule.value}'"]
            # Partial credit if command core matches
            if rule.value in actual_cmd:
                best_cmd_score = max(best_cmd_score, 2.0)
                best_flag_score = max(best_flag_score, 1.5)

        elif rule_type == "regex" and rule.value:
            if re.search(rule.value, actual_cmd, re.IGNORECASE):
                return 4.0, 3.0, [f"Command regex matched: {rule.value}"]
            elif check_semantic_equivalence(actual_cmd, rule.value):
                return 4.0, 3.0, [f"Semantic equivalence matched regex target: {rule.value}"]
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
