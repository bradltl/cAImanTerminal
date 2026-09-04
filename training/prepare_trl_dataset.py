#!/usr/bin/env python3
"""
Prepares training data for TRL (Transformer Reinforcement Learning) SFTTrainer.
Preserves all original fields (system, context, user, assistant) while adding
the standard ChatML/conversational 'messages' array required by TRL.
"""

import json
from pathlib import Path
from typing import Dict, Any

INPUT_JSONL = Path("training_dataset/dataset.jsonl")
OUTPUT_JSONL = Path("training_dataset/trl_dataset.jsonl")
TRAIN_SPLIT_JSONL = Path("training_dataset/trl_train.jsonl")
EVAL_SPLIT_JSONL = Path("training_dataset/trl_eval.jsonl")

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

def format_user_prompt(context: Dict[str, Any], user_input: str) -> str:
    """Formats the user turn to match Cayman Terminal runtime prompt structure."""
    os_id = context.get("os", "cachyos")
    os_base = OS_BASE_MAP.get(os_id.lower(), "arch")
    shell = context.get("shell", "bash")
    cwd = context.get("cwd", "/home/brad")

    is_passive = not user_input.strip().startswith("@")

    if is_passive:
        return (
            f"[SYSTEM CONTEXT]\n"
            f"OS: {os_id} ({os_base})\n"
            f"Shell: {shell}\n"
            f"CWD: {cwd}\n\n"
            f"[CURRENT TYPING BUFFER]\n"
            f"{user_input}\n\n"
            f'Observe terminal context. If this is an incomplete command with an obvious completion, suggest it. '
            f'If ambiguous, partial, or user is simply typing, respond with "no_action".\n'
            f"Respond in structured JSON according to the contract:"
        )
    else:
        return (
            f"[SYSTEM CONTEXT]\n"
            f"OS: {os_id} ({os_base})\n"
            f"Shell: {shell}\n"
            f"CWD: {cwd}\n\n"
            f"[USER REQUEST]\n"
            f"{user_input}\n\n"
            f"Respond in structured JSON according to the contract:"
        )

def convert_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a sample preserving original fields while injecting 'messages'."""
    # Retain all original keys
    converted = dict(sample)

    sys_content = sample["system"]
    user_content = format_user_prompt(sample.get("context", {}), sample["user"])
    # Format assistant output as JSON string
    asst_content = json.dumps(sample["assistant"], indent=2, ensure_ascii=False)

    converted["messages"] = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": asst_content},
    ]
    return converted

def main():
    if not INPUT_JSONL.exists():
        print(f"Error: {INPUT_JSONL} not found.")
        return

    print(f"Loading original dataset from {INPUT_JSONL}...")
    samples = []
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    print(f"Read {len(samples)} samples. Converting to TRL conversational format...")
    converted_samples = [convert_sample(s) for s in samples]

    # Write full trl_dataset.jsonl
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for item in converted_samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"✔ Saved full TRL dataset to {OUTPUT_JSONL} ({len(converted_samples)} examples)")

    # Create 90/10 train/eval split (deterministic: every 10th example is eval)
    eval_samples = [s for i, s in enumerate(converted_samples) if (i % 10) == 0]
    train_samples = [s for i, s in enumerate(converted_samples) if (i % 10) != 0]

    with open(TRAIN_SPLIT_JSONL, "w", encoding="utf-8") as f:
        for item in train_samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    with open(EVAL_SPLIT_JSONL, "w", encoding="utf-8") as f:
        for item in eval_samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✔ Saved train split to {TRAIN_SPLIT_JSONL} ({len(train_samples)} examples)")
    print(f"✔ Saved eval split to {EVAL_SPLIT_JSONL} ({len(eval_samples)} examples)")

if __name__ == "__main__":
    main()
