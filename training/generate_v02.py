#!/usr/bin/env python3
"""
Targeted v0.2 Training Dataset Generator & Adversarial Reviewer for Cayman Terminal.
Combines comprehensive baseline coverage with targeted failure cluster fixes:
1. clarify instead of inventing missing arguments
2. no_action / restraint during passive typing and comments
3. Arch vs Debian package-management contrast
4. gh vs git disambiguation
5. gcloud vs other cloud providers
6. unknown/obscure command -> documentation lookup (lookup_help)
7. multi-turn @ continue with contextual history
8. quoting and whitespace preservation
9. catastrophic command recognition and refusal
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from training.data_bash_pkg import get_bash_linux_data, get_arch_aur_data, get_debian_fedora_data
from training.data_cloud import get_gcloud_data, get_aws_data, get_azure_data
from training.data_dev_containers import get_git_gh_data, get_containers_k8s_data
from training.data_passive_interaction import get_passive_data
from training.data_v02_targeted import (
    get_clarify_missing_args_data,
    get_no_action_restraint_data,
    get_arch_vs_debian_contrast_data,
    get_gh_vs_git_data,
    get_cloud_disambiguation_data,
    get_doc_lookup_help_data,
    get_multi_turn_continue_data,
    get_quoting_whitespace_data,
    get_catastrophic_safety_data
)

OUTPUT_DIR = Path("training_dataset_v02")
SAMPLES_DIR = OUTPUT_DIR / "samples"
DATASET_JSONL = OUTPUT_DIR / "dataset.jsonl"
TRAIN_JSONL = OUTPUT_DIR / "trl_train.jsonl"
EVAL_JSONL = OUTPUT_DIR / "trl_eval.jsonl"
SUMMARY_JSON = OUTPUT_DIR / "summary.json"

SYSTEM_PROMPT = (
    "You are the terminal assistant for Cayman Terminal on Linux. "
    "Suggest helpful, accurate commands, classify risk precisely, "
    "warn on elevated operations, and output no_action when the user is typing or requires silence."
)

OS_BASE_MAP = {
    "cachyos": "arch",
    "arch": "arch",
    "ubuntu": "debian",
    "debian": "debian",
    "fedora": "fedora",
    "rhel": "fedora",
    "centos": "fedora",
    "manjaro": "arch"
}

def format_user_prompt(context: Dict[str, Any], user_input: str, history: List[Dict[str, Any]] = None) -> str:
    """Formats the user turn to match Cayman Terminal runtime prompt structure."""
    os_id = context.get("os", "cachyos")
    os_base = OS_BASE_MAP.get(os_id.lower(), "arch")
    shell = context.get("shell", "bash")
    cwd = context.get("cwd", "/home/brad")

    history_str = ""
    if history:
        for entry in history:
            cmd = entry.get("command", "")
            out = entry.get("output", "").strip()
            history_str += f"$ {cmd}\n{out}\n"
        history_str = history_str.strip()

    is_passive = not user_input.strip().startswith("@")

    if is_passive:
        hist_block = f"\n\n[RECENT TERMINAL HISTORY]\n{history_str}" if history_str else ""
        return (
            f"[SYSTEM CONTEXT]\n"
            f"OS: {os_id} ({os_base})\n"
            f"Shell: {shell}\n"
            f"CWD: {cwd}{hist_block}\n\n"
            f"[CURRENT TYPING BUFFER]\n"
            f"{user_input}\n\n"
            f'Observe terminal context. If this is an incomplete command with an obvious completion, suggest it. '
            f'If ambiguous, partial, or user is simply typing, respond with "no_action".\n'
            f"Respond in structured JSON according to the contract:"
        )
    else:
        hist_block = f"\n\n[RECENT TERMINAL HISTORY]\n{history_str}" if history_str else ""
        return (
            f"[SYSTEM CONTEXT]\n"
            f"OS: {os_id} ({os_base})\n"
            f"Shell: {shell}\n"
            f"CWD: {cwd}{hist_block}\n\n"
            f"[USER REQUEST]\n"
            f"{user_input}\n\n"
            f"Respond in structured JSON according to the contract:"
        )

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

def validate_sample(ex: Dict[str, Any]) -> List[str]:
    errors = []
    for req in ("system", "context", "user", "assistant"):
        if req not in ex:
            errors.append(f"Missing '{req}'")

    ctx = ex.get("context", {})
    for k in ("os", "shell", "cwd"):
        if k not in ctx or not str(ctx[k]).strip():
            errors.append(f"context missing '{k}'")

    ast = ex.get("assistant", {})
    action = ast.get("action")
    allowed = ["suggest_command", "suggest_sequence", "lookup_help", "explain", "clarify", "no_action"]
    if action not in allowed:
        errors.append(f"Invalid action '{action}'")

    cmd = ast.get("command")
    risk = ast.get("risk")
    warning = ast.get("warning")
    explanation = ast.get("explanation")
    user = ex.get("user", "")

    if action == "no_action":
        if cmd is not None:
            errors.append(f"no_action must have command=null, got '{cmd}'")
        if warning is not None:
            errors.append(f"no_action must have warning=null")
        if user.startswith("@"):
            errors.append(f"user with @ prefix should not be no_action: '{user}'")
    elif action == "suggest_command":
        if not cmd:
            errors.append("suggest_command must have command string")
        if not explanation:
            errors.append("suggest_command must have explanation")
        if risk not in ("normal", "caution", "elevated"):
            errors.append(f"Invalid risk '{risk}'")
        if risk == "elevated" and not warning:
            errors.append(f"Elevated command '{cmd}' missing warning")
    elif action in ("clarify", "explain"):
        if cmd is not None:
            errors.append(f"{action} must have command=null, got '{cmd}'")
        if not explanation:
            errors.append(f"{action} must have explanation")
    elif action == "lookup_help":
        if cmd is not None:
            errors.append(f"lookup_help must have command=null")
        tool_req = ast.get("tool_request")
        if not tool_req or not isinstance(tool_req, dict):
            errors.append("lookup_help must include tool_request dict")
        else:
            if "provider" not in tool_req or "command" not in tool_req:
                errors.append("tool_request missing provider or command")

    if cmd:
        ok, err = validate_bash_syntax(cmd)
        if not ok:
            errors.append(f"Bash syntax error: {err} in '{cmd}'")
        if is_root_deletion(cmd):
            errors.append(f"Root deletion detected in '{cmd}'")
        if ":(){ :|:& };:" in cmd:
            errors.append(f"Fork bomb detected in '{cmd}'")

    return errors

def main():
    print("=== Cayman Terminal Targeted v0.2 Dataset Generator ===")
    all_raw = []

    # 1. Baseline sources
    all_raw.extend(get_bash_linux_data(SYSTEM_PROMPT))
    all_raw.extend(get_arch_aur_data(SYSTEM_PROMPT))
    all_raw.extend(get_debian_fedora_data(SYSTEM_PROMPT))
    all_raw.extend(get_gcloud_data(SYSTEM_PROMPT))
    all_raw.extend(get_aws_data(SYSTEM_PROMPT))
    all_raw.extend(get_azure_data(SYSTEM_PROMPT))
    all_raw.extend(get_git_gh_data(SYSTEM_PROMPT))
    all_raw.extend(get_containers_k8s_data(SYSTEM_PROMPT))
    all_raw.extend(get_passive_data(SYSTEM_PROMPT))

    # 2. Targeted failure-cluster sources
    targeted_clusters = {
        "clarify_missing_args": get_clarify_missing_args_data(SYSTEM_PROMPT),
        "no_action_restraint": get_no_action_restraint_data(SYSTEM_PROMPT),
        "arch_vs_debian_contrast": get_arch_vs_debian_contrast_data(SYSTEM_PROMPT),
        "gh_vs_git": get_gh_vs_git_data(SYSTEM_PROMPT),
        "cloud_disambiguation": get_cloud_disambiguation_data(SYSTEM_PROMPT),
        "doc_lookup_help": get_doc_lookup_help_data(SYSTEM_PROMPT),
        "multi_turn_continue": get_multi_turn_continue_data(SYSTEM_PROMPT),
        "quoting_whitespace": get_quoting_whitespace_data(SYSTEM_PROMPT),
        "catastrophic_safety": get_catastrophic_safety_data(SYSTEM_PROMPT)
    }

    print(f"Loaded baseline examples: {len(all_raw)}")
    for name, items in targeted_clusters.items():
        print(f"  + Cluster [{name}]: {len(items)} examples")
        all_raw.extend(items)

    print(f"\nTotal gathered raw examples: {len(all_raw)}")

    # 3. Validation Pass
    print("\nRunning strict adversarial review on all candidates...")
    valid_samples = []
    errors_found = 0

    seen_prompts = set()
    for i, ex in enumerate(all_raw, 1):
        errs = validate_sample(ex)
        # Duplicate prompt check (allow multi-turn '@ continue' with distinct history)
        prompt_key = ex["user"]
        if prompt_key == "@ continue":
            prompt_key = f"@ continue {json.dumps(ex.get('history', []))}"
        
        if prompt_key in seen_prompts:
            # Skip exact duplicate prompts gracefully
            continue
        seen_prompts.add(prompt_key)

        if errs:
            errors_found += 1
            print(f"[FAIL] Sample #{i}: {'; '.join(errs)}")
        else:
            valid_samples.append(ex)

    if errors_found > 0:
        print(f"\nCRITICAL: {errors_found} samples failed validation! Aborting.")
        exit(1)

    print(f"✔ ALL {len(valid_samples)} CANDIDATES PASSED ADVERSARIAL VALIDATION!")

    # 4. Prepare Directories and Dual Format
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    full_converted = []

    for i, ex in enumerate(valid_samples, 1):
        # Retain original fields
        converted = dict(ex)

        # Generate ChatML messages
        sys_content = ex["system"]
        user_content = format_user_prompt(ex.get("context", {}), ex["user"], ex.get("history"))
        asst_content = json.dumps(ex["assistant"], indent=2, ensure_ascii=False)

        converted["messages"] = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": asst_content}
        ]
        full_converted.append(converted)

        # Save individual sample JSON
        sample_path = SAMPLES_DIR / f"sample_{i:04d}.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(converted, f, indent=2, ensure_ascii=False)

    # 5. Write JSONL Files
    with open(DATASET_JSONL, "w", encoding="utf-8") as f:
        for s in full_converted:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 90/10 Train/Eval split
    eval_samples = [s for idx, s in enumerate(full_converted) if (idx % 10) == 0]
    train_samples = [s for idx, s in enumerate(full_converted) if (idx % 10) != 0]

    with open(TRAIN_JSONL, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(EVAL_JSONL, "w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 6. Generate Summary Metadata
    action_counts = {}
    risk_counts = {}
    os_counts = {}

    for s in full_converted:
        act = s["assistant"]["action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        r = s["assistant"].get("risk") or "none"
        risk_counts[r] = risk_counts.get(r, 0) + 1
        os_id = s.get("context", {}).get("os", "unknown")
        os_counts[os_id] = os_counts.get(os_id, 0) + 1

    summary = {
        "dataset_name": "cayman-terminal-targeted-v02",
        "total_examples": len(full_converted),
        "train_examples": len(train_samples),
        "eval_examples": len(eval_samples),
        "validation_passed": True,
        "action_distribution": action_counts,
        "risk_distribution": risk_counts,
        "os_distribution": os_counts,
        "failure_clusters_covered": [
            "clarify_missing_args",
            "no_action_restraint",
            "arch_vs_debian_contrast",
            "gh_vs_git",
            "cloud_disambiguation",
            "doc_lookup_help",
            "multi_turn_continue",
            "quoting_whitespace",
            "catastrophic_safety"
        ],
        "output_directory": str(OUTPUT_DIR),
        "jsonl_path": str(DATASET_JSONL),
        "train_path": str(TRAIN_JSONL),
        "eval_path": str(EVAL_JSONL)
    }

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✔ Target v0.2 dataset built successfully in '{OUTPUT_DIR}':")
    print(f"  - Total samples: {len(full_converted)}")
    print(f"  - Train split:   {len(train_samples)}")
    print(f"  - Eval split:    {len(eval_samples)}")
    print(f"  - Actions:       {action_counts}")
    print(f"  - Risks:         {risk_counts}")
    print(f"  - Summary:       {SUMMARY_JSON}")

if __name__ == "__main__":
    main()
