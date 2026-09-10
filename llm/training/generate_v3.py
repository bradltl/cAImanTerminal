#!/usr/bin/env python3
"""
v3 Training Dataset Generator for cAIman Terminal.
Implements the refined model contract:
- Removed tool_request from model output contract (host software owns documentation eligibility)
- Removed passive no_action from training data (host eligibility gate owns debounce)
- High concentration of:
  * Negative contrast examples (e.g. '@ delete the old release' -> clarify, NEVER rm -rf)
  * Missing information & identifiers -> clarify (NEVER invent regions, instances, titles, IDs)
  * Command typo & flag repairs
  * Quoting / whitespace preservation
  * Multi-turn @ continue sequences with context
  * Arch vs Debian discrimination
  * gh vs git discrimination
  * Context-sensitive troubleshooting
  * Catastrophic command recognition & refusal
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
from training.data_v3_core import (
    SYSTEM_PROMPT,
    get_negative_contrast_data,
    get_missing_info_clarify_data,
    get_typo_repair_data,
    get_quoting_whitespace_data,
    get_multi_turn_continue_data,
    get_arch_vs_debian_data,
    get_gh_vs_git_data,
    get_troubleshooting_data,
    get_catastrophic_safety_data,
)

OUTPUT_DIR = Path("training_dataset_v3")
SAMPLES_DIR = OUTPUT_DIR / "samples"
DATASET_JSONL = OUTPUT_DIR / "dataset.jsonl"
TRAIN_JSONL = OUTPUT_DIR / "trl_train.jsonl"
EVAL_JSONL = OUTPUT_DIR / "trl_eval.jsonl"
SUMMARY_JSON = OUTPUT_DIR / "summary.json"

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
    res = subprocess.run(["bash", "-n", "-c", command], capture_output=True, text=True)
    return res.returncode == 0, res.stderr.strip()

def is_root_deletion(cmd: str) -> bool:
    try:
        tokens = shlex.split(cmd)
    except Exception:
        tokens = cmd.split()
    for i, tok in enumerate(tokens):
        if tok in ("rm", "unlink") or tok.endswith("/rm"):
            for arg in tokens[i + 1:]:
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

def clean_assistant_response(ast: Dict[str, Any]) -> Dict[str, Any]:
    """Strictly formats assistant response removing tool_request completely."""
    return {
        "action": ast["action"],
        "command": ast.get("command"),
        "commands": ast.get("commands"),
        "explanation": ast.get("explanation"),
        "risk": ast.get("risk"),
        "warning": ast.get("warning"),
        "question": ast.get("question"),
    }

def main():
    print("=== Generating cAIman Terminal v3 Training Corpus ===")
    raw_samples = []

    # 1. v3 Targeted Core
    v3_categories = [
        ("negative_contrast", get_negative_contrast_data()),
        ("missing_info_clarify", get_missing_info_clarify_data()),
        ("typo_repair", get_typo_repair_data()),
        ("quoting_whitespace", get_quoting_whitespace_data()),
        ("multi_turn_continue", get_multi_turn_continue_data()),
        ("arch_vs_debian", get_arch_vs_debian_data()),
        ("gh_vs_git", get_gh_vs_git_data()),
        ("troubleshooting", get_troubleshooting_data()),
        ("catastrophic_safety", get_catastrophic_safety_data()),
    ]

    for cat_name, items in v3_categories:
        print(f"  + [{cat_name}]: {len(items)} samples")
        raw_samples.extend(items)

    # 2. Add high quality baseline command data (skipping any no_action)
    baseline_modules = [
        get_bash_linux_data(SYSTEM_PROMPT),
        get_arch_aur_data(SYSTEM_PROMPT),
        get_debian_fedora_data(SYSTEM_PROMPT),
        get_gcloud_data(SYSTEM_PROMPT),
        get_aws_data(SYSTEM_PROMPT),
        get_azure_data(SYSTEM_PROMPT),
        get_git_gh_data(SYSTEM_PROMPT),
        get_containers_k8s_data(SYSTEM_PROMPT),
    ]

    for mod_data in baseline_modules:
        for ex in mod_data:
            if ex.get("assistant", {}).get("action") == "no_action":
                continue
            raw_samples.append(ex)

    print(f"\nTotal raw samples gathered: {len(raw_samples)}")

    # 3. Deduplication and Cleaning
    seen_prompts = set()
    cleaned_samples = []
    errors = 0

    for i, ex in enumerate(raw_samples, 1):
        ast = ex.get("assistant", {})
        action = ast.get("action")
        if action == "no_action":
            continue

        cmd = ast.get("command")
        if cmd:
            ok, err = validate_bash_syntax(cmd)
            if not ok:
                print(f"Error in sample {i} bash syntax: {err} -> '{cmd}'")
                errors += 1
                continue
            if is_root_deletion(cmd):
                print(f"Catastrophic root deletion in sample {i}: '{cmd}'")
                errors += 1
                continue

        u_text = ex["user"].strip()
        hist_str = json.dumps(ex.get("history", [])) if u_text.startswith("@ continue") else ""
        key = (u_text, hist_str)

        if key in seen_prompts:
            continue
        seen_prompts.add(key)

        cleaned_ast = clean_assistant_response(ast)
        cleaned_ex = {
            "system": SYSTEM_PROMPT,
            "context": ex.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"}),
            "user": ex["user"],
            "assistant": cleaned_ast,
        }
        if "history" in ex:
            cleaned_ex["history"] = ex["history"]

        # Create ChatML messages
        user_formatted = format_user_prompt(cleaned_ex["context"], cleaned_ex["user"], cleaned_ex.get("history"))
        asst_json = json.dumps(cleaned_ast, indent=2, ensure_ascii=False)

        cleaned_ex["messages"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_formatted},
            {"role": "assistant", "content": asst_json},
        ]
        cleaned_samples.append(cleaned_ex)

    if errors > 0:
        print(f"Validation failed with {errors} errors!")
        exit(1)

    print(f"✔ Final vetted and deduplicated v3 samples: {len(cleaned_samples)}")

    # 4. Save to training_dataset_v3/
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for idx, s in enumerate(cleaned_samples, 1):
        with open(SAMPLES_DIR / f"sample_{idx:04d}.json", "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    with open(DATASET_JSONL, "w", encoding="utf-8") as f:
        for s in cleaned_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 90/10 split
    eval_samples = [s for idx, s in enumerate(cleaned_samples) if (idx % 10) == 0]
    train_samples = [s for idx, s in enumerate(cleaned_samples) if (idx % 10) != 0]

    with open(TRAIN_JSONL, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(EVAL_JSONL, "w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    action_counts = {}
    risk_counts = {}
    for s in cleaned_samples:
        act = s["assistant"]["action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        r = s["assistant"].get("risk") or "none"
        risk_counts[r] = risk_counts.get(r, 0) + 1

    summary = {
        "dataset_name": "cayman-terminal-v3",
        "total_examples": len(cleaned_samples),
        "train_examples": len(train_samples),
        "eval_examples": len(eval_samples),
        "contract_changes": [
            "tool_request removed from assistant response schema",
            "passive no_action removed (owned by host eligibility gate)",
            "mandatory clarify questions without hallucinating identifiers",
            "negative contrast examples added"
        ],
        "action_distribution": action_counts,
        "risk_distribution": risk_counts,
        "output_directory": str(OUTPUT_DIR),
        "jsonl_path": str(DATASET_JSONL),
        "train_path": str(TRAIN_JSONL),
        "eval_path": str(EVAL_JSONL),
    }

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✔ Successfully generated v3 dataset in '{OUTPUT_DIR}':")
    print(f"  - Total samples: {len(cleaned_samples)}")
    print(f"  - Train split:   {len(train_samples)}")
    print(f"  - Eval split:    {len(eval_samples)}")
    print(f"  - Actions:       {action_counts}")
    print(f"  - Risks:         {risk_counts}")

if __name__ == "__main__":
    main()
