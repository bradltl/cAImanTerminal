"""Detect exact normalized request overlap; never label examined data unseen.

Default: audit existing regression suites (overlap is reported, not hidden).
--candidate-dir PATH --expected-sha256 HASH: gate an independently supplied,
previously frozen holdout against all checked-in training requests. Exact-match
disjointness does not establish semantic independence or absence from pretraining.
"""
import argparse
import json
import re
from pathlib import Path
import yaml
from terminal_ai_bench.provenance import digest

ROOT = Path(__file__).resolve().parents[2]

def normalize(text):
    return re.sub(r"\s+", " ", text.strip().lstrip("@").strip().casefold())

def requests(folder):
    result = []
    for path in sorted(folder.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict) or "id" not in data:
            continue
        for turn in data.get("turns") or [data]:
            text = turn.get("input", {}).get("text", "")
            if text:
                result.append((str(path.relative_to(folder)), data["id"], normalize(text)))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    training = {}
    for path in sorted((ROOT / "llm").glob("training_dataset*/dataset.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            text = row.get("user", "")
            if text:
                training.setdefault(normalize(text), set()).add(path.parent.name)
    folders = [args.candidate_dir] if args.candidate_dir else sorted((ROOT / "llm").glob("scenarios*"))
    reports = []
    for folder in folders:
        cases = requests(folder)
        overlaps = [{"scenario": id_, "file": file, "training_sets": sorted(training[text])} for file, id_, text in cases if text in training]
        identity = digest([(str(p.relative_to(folder)), p.read_text()) for p in sorted(folder.rglob("*.yaml"))])
        reports.append({"suite": folder.name, "status": "candidate-disjointness-only" if args.candidate_dir else "examined-regression-not-holdout", "sha256": identity, "requests": len(cases), "exact_overlaps": overlaps})
        if args.candidate_dir:
            assert cases, "Empty holdout"
            assert args.expected_sha256 == identity, "Frozen holdout hash missing or changed"
            assert not overlaps, "Holdout overlaps training requests"
    print(json.dumps(reports, indent=2))

if __name__ == "__main__":
    main()
