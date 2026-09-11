"""Compare reference gates against the actual Rust worker; never execute candidates.

Run from any directory with the project virtualenv. Reviewed differences are
explicit per-case decisions, not equivalence claims. --record prints a manifest
for human review; normal mode fails on any change to either implementation.
"""
import argparse
import json
import subprocess
from pathlib import Path
from terminal_ai_bench.system.command_parser import parse_command
from terminal_ai_bench.system.secret_validator import SecretValidator
from terminal_ai_bench.system.safety_validator import SafetyValidator
from terminal_ai_bench.system.risk_classifier import classify_host_risk
from terminal_ai_bench.system.runtime_intent_resolver import RuntimeIntentResolver
from terminal_ai_bench.system.intent_validator import IntentContractValidator
from terminal_ai_bench.system.types import RuntimeIntentInput
from terminal_ai_bench.provenance import digest

ROOT = Path(__file__).resolve().parents[2]

def evaluate(binary, case):
    raw = json.dumps({"action": "suggest_command", "command": case["command"], "explanation": "Review the command"})
    request = {"request": case["request"], "response": raw, "passive": case.get("passive", False), "remote": case.get("remote", False)}
    run = subprocess.run([binary, "--policy-check"], input=json.dumps(request), text=True, capture_output=True, check=True, timeout=10, cwd=ROOT)
    rust = json.loads(run.stdout)
    if rust["checks"]["risk"] is not None:
        rust["checks"]["risk"] = rust["checks"]["risk"].lower()
    assert rust["stageable"] == case["stageable"], case["id"]
    assert rust["inferences"] <= (1 if request["passive"] else 2)
    ast = parse_command(case["command"])
    resolution = RuntimeIntentResolver().resolve(RuntimeIntentInput(user_text=case["request"], remote_state={"remote": True} if request["remote"] else None))
    python = {
        "parser": ast.syntax_error is None,
        "secret": SecretValidator().evaluate(ast).secret_detected,
        "intent": IntentContractValidator().evaluate(ast, resolution.contract).status.value == "satisfied",
        "safety": not SafetyValidator().evaluate(ast, resolution.contract, case["request"]).blocked,
        "risk": classify_host_risk(ast)[0],
    }
    return {"id": case["id"], "rust": rust["checks"], "python_reference": python}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default=str(ROOT / "target/debug/caiman-terminal"))
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    cases = json.loads((ROOT / "terminal/tests/adversarial.json").read_text())
    result = {"corpus_sha256": digest(cases), "cases": [evaluate(args.binary, case) for case in cases]}
    if args.record:
        print(json.dumps(result, indent=2))
    else:
        expected = json.loads((ROOT / "llm/tools/conformance-reviewed.json").read_text())
        assert result == expected, "Policy decisions changed; inspect --record output and review each difference"
        differences = sum(c["rust"] != c["python_reference"] for c in result["cases"])
        print(f"{len(cases)} production cases passed; {differences} documented reference-policy differences unchanged")

if __name__ == "__main__":
    main()
