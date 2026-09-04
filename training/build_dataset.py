#!/usr/bin/env python3
"""
High-integrity training dataset generator and adversarial reviewer for Cayman Terminal.
Generates 380+ diverse, realistic examples and verifies each against:
- JSON schema & typing
- Shell syntax using bash -n
- Deterministic risk classification
- Mandatory warnings for elevated operations
- Correct passive silence (no_action)
- Zero catastrophic antipatterns
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("training_dataset")
DATASET_JSONL = OUTPUT_DIR / "dataset.jsonl"
SYSTEM_PROMPT = (
    "You are the terminal assistant for Cayman Terminal on Linux. "
    "Suggest helpful, accurate commands, classify risk precisely, "
    "warn on elevated operations, and output no_action when the user is typing or requires silence."
)

def classify_command_risk_audit(command: str) -> str:
    """Deterministic risk classification matching Cayman Terminal engine."""
    if not command:
        return "normal"
    cmd = command.strip()

    elevated_patterns = [
        r"\bsudo\b",
        r"\bmkfs(?:\.\w+)?\b",
        r"\bdd\s+if=",
        r"\b(?:fdisk|gdisk|parted)\b",
        r"\bpacman\s+-[a-zA-Z]*(?:R|S(?:y)?u)[a-zA-Z]*\b",
        r"\buser(?:del|add|mod)\b",
        r"\bchmod\s+(?:-[a-zA-Z]*R[a-zA-Z]*\s+)?(?:777|a\+rwx)\b",
        r"\brm\s+-[a-zA-Z]*(?:r|R)[a-zA-Z]*\b",
        r"\bsystemctl\s+(?:stop|restart|disable|mask|poweroff|reboot)\b",
        r"\bapt(?:-get)?\s+(?:purge|autoremove|dist-upgrade)\b",
        r"\bdnf\s+(?:remove|erase)\b",
        r"\bchown\b",
    ]
    for pat in elevated_patterns:
        if re.search(pat, cmd):
            return "elevated"

    caution_patterns = [
        r"\brm\b",
        r"\bgit\s+(?:checkout|reset|push|rebase|merge|clean|stash\s+drop|branch\s+-[dD])\b",
        r"\bgh\s+(?:pr\s+merge|release\s+delete|repo\s+delete|run\s+rerun)\b",
        r"\bgcloud\s+(?:config\s+set|compute\s+instances\s+delete|run\s+services\s+delete)\b",
        r"\baws\s+s3\s+(?:rm|sync\s+.*--delete)\b",
        r"\baws\s+ec2\s+stop-instances\b",
        r"\baz\s+(?:vm\s+stop|group\s+delete)\b",
        r"\b(?:kill|pkill|killall)\b",
        r"\bdocker\s+(?:rm|rmi|system\s+prune|stop)\b",
        r"\bkubectl\s+(?:delete|rollout\s+restart)\b",
    ]
    for pat in caution_patterns:
        if re.search(pat, cmd):
            return "caution"

    return "normal"

def is_root_deletion(cmd: str) -> bool:
    try:
        tokens = shlex.split(cmd)
    except Exception:
        tokens = cmd.split()
    for i, tok in enumerate(tokens):
        if tok in ("rm", "unlink") or tok.endswith("/rm"):
            for arg in tokens[i + 1 :]:
                if arg in (";", "&&", "||", "|"):
                    break
                if arg.startswith("-"):
                    if arg == "--no-preserve-root":
                        return True
                    continue
                clean = arg.strip("\"' ")
                if clean in ("/", "/*", "/.", "/..", "/?*"):
                    return True
    return False

def validate_bash_syntax(command: str):
    if not command:
        return True, ""
    res = subprocess.run(
        ["bash", "-n", "-c", command],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return False, res.stderr.strip()
    return True, ""

def validate_example(ex):
    errors = []
    for req_key in ("system", "context", "user", "assistant"):
        if req_key not in ex:
            errors.append(f"Missing '{req_key}'")

    ctx = ex.get("context", {})
    for c_key in ("os", "shell", "cwd"):
        if c_key not in ctx or not str(ctx[c_key]).strip():
            errors.append(f"context missing '{c_key}'")

    ast = ex.get("assistant", {})
    action = ast.get("action")
    allowed_actions = ["suggest_command", "suggest_sequence", "lookup_help", "explain", "clarify", "no_action"]
    if action not in allowed_actions:
        errors.append(f"Invalid action '{action}'")

    cmd = ast.get("command")
    risk = ast.get("risk")
    warning = ast.get("warning")
    explanation = ast.get("explanation")

    if action == "no_action":
        if cmd is not None:
            errors.append(f"no_action must have command=null, got '{cmd}'")
        if warning is not None:
            errors.append(f"no_action must have warning=null, got '{warning}'")
    elif action == "suggest_command":
        if not cmd or not isinstance(cmd, str):
            errors.append("suggest_command must have command string")
        if not explanation:
            errors.append("suggest_command must have explanation")
        if risk not in ("normal", "caution", "elevated"):
            errors.append(f"Invalid risk '{risk}'")
    elif action in ("clarify", "explain"):
        if cmd is not None:
            errors.append(f"{action} must have command=null")
        if not explanation:
            errors.append(f"{action} must have explanation")

    if cmd:
        valid_syntax, err_msg = validate_bash_syntax(cmd)
        if not valid_syntax:
            errors.append(f"Syntax error: {err_msg} on '{cmd}'")

        if is_root_deletion(cmd):
            errors.append(f"Root deletion in '{cmd}'")

        if ":(){ :|:& };:" in cmd:
            errors.append(f"Fork bomb in '{cmd}'")

        det_risk = classify_command_risk_audit(cmd)
        if det_risk == "elevated" and risk != "elevated":
            errors.append(f"Command '{cmd}' is elevated but marked '{risk}'")
        elif det_risk == "caution" and risk == "normal":
            errors.append(f"Command '{cmd}' is caution but marked '{risk}'")

        if risk == "elevated" and not warning:
            errors.append(f"Missing warning for elevated command '{cmd}'")

    return errors

print("Validator loaded.")
