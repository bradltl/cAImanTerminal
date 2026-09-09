#!/usr/bin/env python3
"""
Build Cayman Terminal v4 Unified Dataset.

Merges:
1. Architectural discipline of v3:
   - Zero tool_request (managed by host)
   - Zero passive no_action (managed by host gate)
   - Negative contrast examples
   - Missing arguments -> clarify without hallucinating IDs
   - Quoting / whitespace handling
   - Typo repair
   - Arch-vs-Debian discrimination
   - gh vs git separation
2. Broad multi-domain volume of v2 (400+ samples):
   - Docker / Docker Compose
   - Kubernetes / kubectl
   - Cloud SDKs (gcloud, aws, az)
   - Linux system administration, networking, troubleshooting
"""

import json
import os
import random
import re
import subprocess
from pathlib import Path
from collections import Counter

OUTPUT_DIR = Path("training_dataset_v4")
SAMPLES_DIR = OUTPUT_DIR / "samples"
V3_DATASET = Path("training_dataset_v3/dataset.jsonl")
V2_DATASET = Path("training_dataset_v2/dataset.jsonl")

SYSTEM_PROMPT = (
    "You are an embedded local Linux terminal AI assistant for an interactive terminal emulator. "
    "Target environment: Arch Linux / CachyOS with Bash. "
    "Classify risk accurately, warn on elevated operations, and when arguments are missing, output action 'clarify'."
)

def check_bash_syntax(cmd: str) -> bool:
    if not cmd:
        return True
    res = subprocess.run(["bash", "-n", "-c", cmd], capture_output=True, text=True)
    return res.returncode == 0

def format_user_content(context: dict, user_text: str) -> str:
    os_name = context.get("os", "cachyos")
    shell_name = context.get("shell", "bash")
    cwd = context.get("cwd", "/home/brad")
    return (
        f"[SYSTEM CONTEXT]\n"
        f"OS: {os_name} (arch)\n"
        f"Shell: {shell_name}\n"
        f"CWD: {cwd}\n\n"
        f"[USER REQUEST]\n"
        f"{user_text}\n\n"
        f"Respond in structured JSON according to the contract:"
    )

def main():
    print("=== Generating Cayman Terminal v4 Master Dataset ===")
    
    # 1. Load v3 samples (prioritized)
    v3_samples = []
    with open(V3_DATASET) as f:
        for line in f:
            v3_samples.append(json.loads(line))
    print(f"Loaded v3 vetted samples: {len(v3_samples)}")

    # 2. Load v2 samples
    v2_samples = []
    with open(V2_DATASET) as f:
        for line in f:
            v2_samples.append(json.loads(line))
    print(f"Loaded v2 samples: {len(v2_samples)}")

    merged_by_prompt = {}

    # Add all v3 samples first
    for s in v3_samples:
        prompt_key = s["user"].strip().lower()
        asst = s["assistant"]
        # Ensure strict schema
        clean_asst = {
            "action": asst.get("action", "suggest_command"),
            "command": asst.get("command"),
            "commands": asst.get("commands"),
            "explanation": asst.get("explanation"),
            "risk": asst.get("risk", "normal"),
            "warning": asst.get("warning"),
            "question": asst.get("question"),
        }
        merged_by_prompt[prompt_key] = {
            "system": SYSTEM_PROMPT,
            "context": s.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"}),
            "user": s["user"],
            "assistant": clean_asst,
        }

    # Add v2 samples that are not passive no_action and not already in v3
    v2_added = 0
    v2_skipped_no_action = 0
    v2_skipped_dupe = 0

    for s in v2_samples:
        prompt_key = s["user"].strip().lower()
        asst = s["assistant"]
        act = asst.get("action")

        if act == "no_action":
            v2_skipped_no_action += 1
            continue

        if prompt_key in merged_by_prompt:
            v2_skipped_dupe += 1
            continue

        # Convert v2 sample to strict v3 contract
        cmd = asst.get("command")
        question = asst.get("question")
        expl = asst.get("explanation")
        risk = asst.get("risk", "normal")
        warning = asst.get("warning")

        if act == "lookup_help":
            tr = asst.get("tool_request", {})
            if tr:
                c = tr.get("command", "")
                args = tr.get("args", [])
                if tr.get("provider") == "bash_help":
                    cmd = f"help {args[0]}" if args else f"help {c}"
                elif tr.get("provider") == "man":
                    cmd = f"man {c}"
                else:
                    cmd = f"{c} {' '.join(args)}"
                act = "suggest_command"
                risk = "normal"
            else:
                act = "explain"

        clean_asst = {
            "action": act,
            "command": cmd,
            "commands": asst.get("commands"),
            "explanation": expl,
            "risk": risk,
            "warning": warning,
            "question": question,
        }

        # Check bash syntax if command present
        if cmd and not check_bash_syntax(cmd):
            print(f"Skipping invalid syntax command: {cmd}")
            continue

        merged_by_prompt[prompt_key] = {
            "system": SYSTEM_PROMPT,
            "context": s.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"}),
            "user": s["user"],
            "assistant": clean_asst,
        }
        v2_added += 1

    print(f"v2 skipped no_action: {v2_skipped_no_action}")
    print(f"v2 skipped duplicates: {v2_skipped_dupe}")
    print(f"v2 samples integrated: {v2_added}")
    print(f"Total unified unique samples: {len(merged_by_prompt)}")

    # Format ChatML messages and create ordered list
    dataset = []
    for prompt_key, s in merged_by_prompt.items():
        user_content = format_user_content(s["context"], s["user"])
        asst_content = json.dumps(s["assistant"], indent=2)
        s["messages"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": asst_content},
        ]
        dataset.append(s)

    # Shuffle with fixed seed
    random.seed(42)
    random.shuffle(dataset)

    # Clean and recreate directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for old_f in SAMPLES_DIR.glob("*.json"):
        old_f.unlink()

    # Write individual sample files
    for idx, sample in enumerate(dataset, 1):
        sample_path = SAMPLES_DIR / f"sample_{idx:04d}.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)

    # Write master dataset.jsonl
    dataset_jsonl_path = OUTPUT_DIR / "dataset.jsonl"
    with open(dataset_jsonl_path, "w", encoding="utf-8") as f:
        for sample in dataset:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    # Split into train (90%) and eval (10%)
    split_idx = int(len(dataset) * 0.90)
    train_samples = dataset[:split_idx]
    eval_samples = dataset[split_idx:]

    train_path = OUTPUT_DIR / "trl_train.jsonl"
    with open(train_path, "w", encoding="utf-8") as f:
        for sample in train_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    eval_path = OUTPUT_DIR / "trl_eval.jsonl"
    with open(eval_path, "w", encoding="utf-8") as f:
        for sample in eval_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    # Statistics
    actions = Counter(s["assistant"]["action"] for s in dataset)
    risks = Counter(s["assistant"]["risk"] for s in dataset)

    summary = {
        "dataset_name": "cayman-terminal-v4-unified",
        "total_examples": len(dataset),
        "train_examples": len(train_samples),
        "eval_examples": len(eval_samples),
        "contract_features": [
            "strict v3 contract (zero tool_request, zero no_action)",
            "merged multi-domain volume from v2 (docker, k8s, cloud, git, system)",
            "negative contrast examples & missing identifier clarifications from v3",
            "command typo repairs and Arch vs Debian discrimination"
        ],
        "action_distribution": dict(actions),
        "risk_distribution": dict(risks),
        "output_directory": str(OUTPUT_DIR),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
    }

    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✔ Successfully generated {len(dataset)} unified samples ({len(train_samples)} train, {len(eval_samples)} eval)")
    print(f"  Actions: {dict(actions)}")
    print(f"  Risks:   {dict(risks)}")
    print(f"  Files saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
