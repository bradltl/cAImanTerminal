import json
import pytest
from pathlib import Path

from terminal_ai_bench.scenario import load_all_scenarios
from terminal_ai_bench.output_parser import parse_response, ActionType
from terminal_ai_bench.system.types import (
    IntentSource,
    RuntimeIntentInput,
    RuntimeIntentConfidence,
    RuntimeIntentStatus,
    ValidationStatus,
    IntentStatus,
)
from terminal_ai_bench.system.pipeline import SystemEvaluationPipeline
from terminal_ai_bench.system.runtime_intent_resolver import RuntimeIntentResolver
from terminal_ai_bench.model_runtime import MockModelRuntime, ReplayModelRuntime


def test_runtime_pipeline_cannot_access_oracle_contracts():
    """Verify runtime pipeline operates strictly without gold contracts or scenario IDs."""
    scenarios = load_all_scenarios("scenarios_v3")
    pipeline = SystemEvaluationPipeline(
        fixtures_dir="fixtures",
        intent_source=IntentSource.RUNTIME,
        contracts_by_id=None,
    )
    mock_runtime = MockModelRuntime(persona="perfect")
    test_scenario = scenarios[0]

    initial_parse = parse_response('{"action": "suggest_command", "command": "ls -l"}')
    parse_res, eval_res = pipeline.evaluate(test_scenario, initial_parse, mock_runtime)

    assert eval_res.intent_source == "runtime"
    assert pipeline.contracts_by_id is None
    assert eval_res.runtime_intent_resolution is not None


def test_scenario_reordering_does_not_affect_intent():
    """Verify that intent resolution is purely functional and immune to iteration order."""
    resolver = RuntimeIntentResolver()
    inp1 = RuntimeIntentInput(user_text="approve pull request 417")
    inp2 = RuntimeIntentInput(user_text="stop compute instance analytics-worker in zone europe-west1-b")

    # Order A
    res1_a = resolver.resolve(inp1)
    res2_a = resolver.resolve(inp2)

    # Order B
    res2_b = resolver.resolve(inp2)
    res1_b = resolver.resolve(inp1)

    assert res1_a.contract.operation == res1_b.contract.operation
    assert res1_a.contract.parameters == res1_b.contract.parameters
    assert res2_a.contract.operation == res2_b.contract.operation
    assert res2_a.contract.parameters == res2_b.contract.parameters


def test_missing_slots_never_receive_invented_values():
    """Verify missing required slots remain absent or require clarification."""
    resolver = RuntimeIntentResolver()
    # User asks to approve PR without number
    inp = RuntimeIntentInput(user_text="approve the pull request")
    res = resolver.resolve(inp)
    if res.contract and res.contract.parameters:
        assert "pr_number" not in res.contract.parameters or res.contract.parameters["pr_number"] is None


def test_safety_runs_even_when_intent_is_unknown():
    """Verify safety scans and blocks catastrophic commands even when intent is UNKNOWN."""
    pipeline = SystemEvaluationPipeline(
        fixtures_dir="fixtures",
        intent_source=IntentSource.RUNTIME,
        contracts_by_id=None,
    )
    scenarios = load_all_scenarios("scenarios_v3")
    test_scenario = scenarios[0]

    # Model generates catastrophic command on unknown intent
    parse_res = parse_response('{"action": "suggest_command", "command": "mkfs.ext4 /dev/sda"}')
    mock_runtime = MockModelRuntime(persona="perfect")
    _, eval_res = pipeline.evaluate(test_scenario, parse_res, mock_runtime)

    assert eval_res.safety is not None
    assert eval_res.safety.blocked is True
    assert eval_res.staging_eligible is False


def test_staged_command_validity_invariant():
    """Verify staging_eligible == True strictly implies CLI valid, intent satisfied, safety clean, secrets clean."""
    scenarios = load_all_scenarios("scenarios_v3")
    pipeline = SystemEvaluationPipeline(
        fixtures_dir="fixtures",
        intent_source=IntentSource.RUNTIME,
        contracts_by_id=None,
    )
    mock_runtime = MockModelRuntime(persona="perfect")

    for s in scenarios[:15]:
        parse_res = parse_response('{"action": "suggest_command", "command": "wc -l audit.log"}')
        _, eval_res = pipeline.evaluate(s, parse_res, mock_runtime)
        if eval_res.staging_eligible:
            assert eval_res.final_validation.status == ValidationStatus.VALID
            assert eval_res.final_intent_validation.status == IntentStatus.SATISFIED
            assert not (eval_res.safety and eval_res.safety.blocked)
            assert not (eval_res.secret_check and eval_res.secret_check.blocked)
            assert eval_res.final_command is not None


def test_replay_uses_identical_raw_outputs(tmp_path):
    """Verify ReplayModelRuntime reproduces identical recorded text without LLM inference."""
    raw_file = tmp_path / "test_raw.json"
    raw_data = {
        "model": "test-model",
        "inferences": {
            "bash-030": {
                "prompt_sha256": __import__("hashlib").sha256(b"dummy prompt").hexdigest(),
                "text": '{"action": "suggest_command", "command": "wc -l audit.log"}',
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "ttft_ms": 12.5,
                "total_latency_ms": 45.0,
                "tokens_per_second": 35.0,
            }
        }
    }
    with open(raw_file, "w") as f:
        json.dump(raw_data, f)

    replay_runtime = ReplayModelRuntime(raw_file)
    replay_runtime.set_scenario_key("bash-030")
    res = replay_runtime.infer("dummy prompt")
    assert res.text == '{"action": "suggest_command", "command": "wc -l audit.log"}'
    assert res.total_latency_ms == 45.0
