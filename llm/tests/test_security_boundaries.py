import json
import pytest
from pathlib import Path
from terminal_ai_bench.model_runtime import ReplayModelRuntime
from terminal_ai_bench.provenance import prompt_digest
from terminal_ai_bench.privacy import redact, sanitize
from terminal_ai_bench.output_parser import ToolRequest, parse_response
from terminal_ai_bench.tool_runtime import ToolRuntime
from terminal_ai_bench.system.secret_validator import SecretValidator
from terminal_ai_bench.system.command_parser import parse_command

@pytest.mark.parametrize("text", ["glpat-fake123", "xoxb-fake123", "Basic YWJjOmRlZg==", "postgres://user:fake@host/db", "--password=fiction", "mysql -pfiction", "-----BEGIN\nPRIVATE KEY-----\nfake"])
def test_secrets_are_blocked_not_semantically_rewritten(text):
    command = text if text.startswith("mysql") else f"echo '{text}'"
    assert SecretValidator().evaluate(parse_command(command)).blocked
    assert text not in redact(text)
    assert text not in json.dumps(sanitize({"command": text, "nested": [text]}))

def test_reference_tools_cannot_execute_or_escape_fixtures(tmp_path):
    with pytest.raises(ValueError):
        ToolRuntime(live_mode=True)
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "x-help.txt").write_text("must not read")
    request = ToolRequest(provider="command_help", command=str(outside), args=["x"])
    assert not ToolRuntime(fixtures).execute_request(request).success

def test_replay_rejects_missing_changed_reused_or_sanitized_input(tmp_path):
    file = tmp_path / "raw.json"
    file.write_text(json.dumps({"inferences": {"case": {"text": "{}", "prompt_sha256": prompt_digest("original")}}}))
    replay = ReplayModelRuntime(file)
    replay.set_scenario_key("missing")
    with pytest.raises(ValueError): replay.infer("original")
    replay.set_scenario_key("case")
    with pytest.raises(ValueError): replay.infer("changed")
    assert replay.infer("original").text == "{}"
    with pytest.raises(RuntimeError): replay.infer("original")

def test_duplicate_response_fields_fail_closed():
    assert not parse_response('{"action":"suggest_command","command":"ls","command":"pwd"}').success
