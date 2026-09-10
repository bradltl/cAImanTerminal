#!/usr/bin/env python3
"""
Combines the original v0.1 dataset with the new targeted v0.2 dataset
into a unified, deduplicated, adversarially-verified v2 training corpus.
"""

import json
from pathlib import Path
from training.generate_v02 import format_user_prompt, validate_sample

OUTPUT_DIR = Path("training_dataset_v2")
SAMPLES_DIR = OUTPUT_DIR / "samples"
DATASET_JSONL = OUTPUT_DIR / "dataset.jsonl"
TRAIN_JSONL = OUTPUT_DIR / "trl_train.jsonl"
EVAL_JSONL = OUTPUT_DIR / "trl_eval.jsonl"
SUMMARY_JSON = OUTPUT_DIR / "summary.json"

def load_jsonl(path):
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples

def main():
    print("=== Building Unified v2 Training Dataset ===")
    s1 = load_jsonl("training_dataset/trl_dataset.jsonl")
    s2 = load_jsonl("training_dataset_v02/dataset.jsonl")
    print(f"Loaded original v0.1: {len(s1)} samples")
    print(f"Loaded targeted v0.2: {len(s2)} samples")

    # Priority order: put targeted v0.2 first so refined versions override older ones
    combined_raw = s2 + s1
    seen_prompts = set()
    deduped = []

    for s in combined_raw:
        # Key on prompt + history if continue
        user_text = s.get("user", "")
        hist_str = json.dumps(s.get("history", [])) if user_text.startswith("@ continue") else ""
        key = (user_text, hist_str)

        if key in seen_prompts:
            continue
        seen_prompts.add(key)

        errs = validate_sample(s)
        if errs:
            print(f"Skipping invalid sample: {user_text} -> {errs}")
            continue

        # Format ChatML messages consistently
        converted = dict(s)
        sys_content = s["system"]
        user_content = format_user_prompt(s.get("context", {}), s["user"], s.get("history"))
        asst_content = json.dumps(s["assistant"], indent=2, ensure_ascii=False)

        converted["messages"] = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": asst_content}
        ]
        deduped.append(converted)

    print(f"Unified unique samples: {len(deduped)}")

    # Write files
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(deduped, 1):
        with open(SAMPLES_DIR / f"sample_{i:04d}.json", "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    with open(DATASET_JSONL, "w", encoding="utf-8") as f:
        for s in deduped:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 90/10 Train/Eval split
    eval_samples = [s for idx, s in enumerate(deduped) if (idx % 10) == 0]
    train_samples = [s for idx, s in enumerate(deduped) if (idx % 10) != 0]

    with open(TRAIN_JSONL, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(EVAL_JSONL, "w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    action_counts = {}
    risk_counts = {}
    for s in deduped:
        act = s["assistant"]["action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        r = s["assistant"].get("risk") or "none"
        risk_counts[r] = risk_counts.get(r, 0) + 1

    summary = {
        "dataset_name": "cayman-terminal-v2-master",
        "total_examples": len(deduped),
        "train_examples": len(train_samples),
        "eval_examples": len(eval_samples),
        "action_distribution": action_counts,
        "risk_distribution": risk_counts,
        "output_directory": str(OUTPUT_DIR),
        "jsonl_path": str(DATASET_JSONL),
        "train_path": str(TRAIN_JSONL),
        "eval_path": str(EVAL_JSONL)
    }

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"✔ Successfully created {OUTPUT_DIR} with {len(deduped)} samples ({len(train_samples)} train, {len(eval_samples)} eval)")
    print(f"  Actions: {action_counts}")
    print(f"  Risks:   {risk_counts}")

if __name__ == "__main__":
    main()
