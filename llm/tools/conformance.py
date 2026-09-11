"""Exact alpha-v1 candidate-pipeline conformance; no baseline exceptions."""
import argparse
import copy
import json
import subprocess
from pathlib import Path
from terminal_ai_bench.system.pipeline import AlphaEvaluationPipeline
from terminal_ai_bench.system.alpha_policy import POLICY
from terminal_ai_bench.provenance import digest

ROOT = Path(__file__).resolve().parents[2]

def fixture(case):
    context = dict(id=1, request_id=1, prompt_generation=1, revision=0, cwd="/fixture", input="", remote=case.get("remote", False), at_prompt=True, terminal_text="", running_command=None, intent=None, journal=[], conversation=[])
    context.update(case.get("context", {}))
    host = dict(package_manager="pacman", root=False, installed=list(POLICY["commands"]) + ["sudo"], documentation={})
    host.update(case.get("host", {}))
    return dict(policy="alpha-v1", request=case["request"], candidate=case["command"], context=context, host=host, passive=case.get("passive", False), cancelled=case.get("cancelled", False))

def cases():
    corpus = json.loads((ROOT / "terminal/tests/adversarial.json").read_text())
    corpus += json.loads((ROOT / "terminal/tests/alpha-conformance.json").read_text())
    base = dict(request="show disk usage", command="df -h", stageable=False)
    corpus += [dict(base, id="not-at-prompt", context={"at_prompt": False}), dict(base, id="cancelled", cancelled=True)]
    return corpus

def evaluate(binary, case):
    request = fixture(case)
    run = subprocess.run([binary, "--policy-check"], input=json.dumps(request), text=True, capture_output=True, check=True, timeout=10, cwd=ROOT)
    rust = json.loads(run.stdout)
    reference = AlphaEvaluationPipeline().evaluate(copy.deepcopy(request))
    assert rust == reference, f"{case['id']}: deterministic mismatch\nRust: {rust}\nPython: {reference}"
    assert rust["stageable"] == case["stageable"], (case["id"], rust)
    return rust

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default=str(ROOT / "target/debug/caiman-terminal"))
    args = parser.parse_args()
    corpus = cases()
    for case in corpus:
        evaluate(args.binary, case)
    print(json.dumps(dict(policy="alpha-v1", corpus_sha256=digest(corpus), cases=len(corpus), discrepancies=0, exceptions=0)))

if __name__ == "__main__":
    main()
