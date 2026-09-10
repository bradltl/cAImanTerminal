import unittest
from terminal_ai_bench.output_parser import ActionType, AssistantResponse, ParseResult, RiskLevel
from terminal_ai_bench.scenario import Difficulty, Domain, InteractionMode, Scenario, ScenarioInput, HistoryTurn
from terminal_ai_bench.system.pipeline import SystemEvaluationPipeline
from terminal_ai_bench.system.runtime_intent_resolver import RuntimeIntentResolver
from terminal_ai_bench.system.types import (
    IntentSource,
    RuntimeIntentConfidence,
    RuntimeIntentInput,
    RuntimeIntentStatus,
)


class MockRuntime:
    def __init__(self, repair_output: str = "{}"):
        self.repair_output = repair_output
        self.call_count = 0

    def infer(self, prompt: str):
        self.call_count += 1
        class MockInfer:
            text = self.repair_output
            ttft_ms = 10.0
            total_latency_ms = 20.0
            tokens_per_second = 50.0
            prompt_tokens = 10
            completion_tokens = 10
        return MockInfer()


class TestRuntimeIntentResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = RuntimeIntentResolver()

    def test_approve_pr_88(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="Approve PR 88"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertEqual(res.confidence, RuntimeIntentConfidence.HIGH)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "gh")
        self.assertIn(res.contract.operation, ("pr_review_approve", "review_pr"))
        self.assertEqual(res.contract.parameters.get("pr_number"), "88")
        self.assertEqual(res.contract.parameters.get("action"), "approve")

    def test_approve_the_pr_no_context_ambiguous(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="Approve the PR"))
        self.assertEqual(res.status, RuntimeIntentStatus.AMBIGUOUS)
        self.assertIn("pr_number", res.missing_slots)
        self.assertIn(res.confidence, (RuntimeIntentConfidence.MEDIUM, RuntimeIntentConfidence.LOW))

    def test_approve_it_after_gh_pr_view(self):
        res = self.resolver.resolve(RuntimeIntentInput(
            user_text="approve it",
            previous_command="gh pr view 88",
        ))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertEqual(res.confidence, RuntimeIntentConfidence.HIGH)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "gh")
        self.assertIn(res.contract.operation, ("pr_review_approve", "review_pr"))
        self.assertEqual(res.contract.parameters.get("pr_number"), "88")
        self.assertTrue(any(ev.get("source") == "previous_command" for ev in res.evidence))

    def test_restart_nginx(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="restart nginx"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertEqual(res.confidence, RuntimeIntentConfidence.HIGH)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "systemctl")
        self.assertEqual(res.contract.operation, "restart_service")
        self.assertEqual(res.contract.parameters.get("service"), "nginx")

    def test_restart_it_after_systemctl_status(self):
        res = self.resolver.resolve(RuntimeIntentInput(
            user_text="restart it",
            previous_command="systemctl status nginx",
        ))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertEqual(res.confidence, RuntimeIntentConfidence.HIGH)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "systemctl")
        self.assertEqual(res.contract.operation, "restart_service")
        self.assertEqual(res.contract.parameters.get("service"), "nginx")

    def test_restart_it_ambiguous_context(self):
        res = self.resolver.resolve(RuntimeIntentInput(
            user_text="restart it",
            previous_command="ls -la /var/log",
        ))
        self.assertEqual(res.status, RuntimeIntentStatus.AMBIGUOUS)
        self.assertIn("service", res.missing_slots)

    def test_clean_pacman_cache(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="clean pacman cache"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "pacman")
        self.assertEqual(res.contract.operation, "clean_cache")

    def test_clean_pacman_cache_keep_2_versions(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="clean pacman cache, keep latest 2 cached versions"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "pacman")
        self.assertEqual(res.contract.operation, "clean_cache")
        self.assertEqual(res.contract.parameters.get("retain_versions"), 2)

    def test_show_kernel_errors(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="show kernel errors"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "journalctl")
        self.assertEqual(res.contract.operation, "kernel_logs")
        self.assertEqual(res.contract.parameters.get("priority"), "err")

    def test_follow_logs(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="follow logs"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "journalctl")
        self.assertEqual(res.contract.operation, "follow")

    def test_count_lines_in_readme(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="count lines in README.md"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.operation, "count_lines")
        self.assertEqual(res.contract.parameters.get("path"), "README.md")

    def test_compare_files(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="compare nginx.conf and nginx.conf.bak"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertIn(res.contract.operation, ("compare_files", "diff_files"))
        self.assertEqual(res.contract.parameters.get("file1"), "nginx.conf")
        self.assertEqual(res.contract.parameters.get("file2"), "nginx.conf.bak")

    def test_list_machine_types_in_zone(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="list machine types in us-central1-a"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "gcloud")
        self.assertEqual(res.contract.operation, "list_machine_types")
        self.assertEqual(res.contract.parameters.get("zone"), "us-central1-a")

    def test_stop_dev_server_in_zone(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="stop dev-server in us-east1-b"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "gcloud")
        self.assertEqual(res.contract.operation, "stop_instance")
        self.assertEqual(res.contract.parameters.get("instance"), "dev-server")
        self.assertEqual(res.contract.parameters.get("zone"), "us-east1-b")

    def test_fork_and_clone_repo(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="fork kubernetes/kubernetes and clone it"))
        self.assertEqual(res.status, RuntimeIntentStatus.RESOLVED)
        self.assertIsNotNone(res.contract)
        self.assertEqual(res.contract.domain, "gh")
        self.assertIn(res.contract.operation, ("repo_fork", "fork_repo"))
        self.assertEqual(res.contract.parameters.get("repo"), "kubernetes/kubernetes")
        self.assertTrue(res.contract.parameters.get("clone"))


class TestNegativeCollisions(unittest.TestCase):
    def setUp(self):
        self.resolver = RuntimeIntentResolver()

    def test_sort_k_does_not_trigger_kernel_logs(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="sort data.csv by second column sort -k 2"))
        self.assertNotEqual(res.contract.operation if res.contract else None, "kernel_logs")
        self.assertNotEqual(res.contract.domain if res.contract else None, "journalctl")

    def test_zone_us_east1_b_does_not_trigger_current_boot(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="list instances in zone us-east1-b"))
        self.assertNotEqual(res.contract.operation if res.contract else None, "current_boot")
        self.assertEqual(res.contract.domain if res.contract else None, "gcloud")

    def test_log_failed_does_not_trigger_follow(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="find all errors and log failed runs"))
        self.assertNotEqual(res.contract.operation if res.contract else None, "follow")

    def test_feature_auth_flow_does_not_trigger_follow(self):
        res = self.resolver.resolve(RuntimeIntentInput(user_text="create git branch feature/auth-flow"))
        self.assertNotEqual(res.contract.operation if res.contract else None, "follow")
        self.assertEqual(res.contract.domain if res.contract else None, "git")


class TestProductionRuntimePipelineIsolation(unittest.TestCase):
    def test_runtime_intent_isolation(self):
        """Verify pipeline in runtime mode operates strictly without contracts_by_id."""
        pipeline = SystemEvaluationPipeline(
            fixtures_dir="fixtures",
            intent_source=IntentSource.RUNTIME,
            contracts_by_id=None,
        )
        self.assertEqual(pipeline.intent_source, IntentSource.RUNTIME)
        self.assertIsNone(pipeline.contracts_by_id)

        scenario = Scenario(
            id="arbitrary-unregistered-id-9999",
            name="Unregistered Scenario",
            domain=Domain.GH,
            difficulty=Difficulty.BASIC,
            mode=InteractionMode.EXPLICIT,
            input=ScenarioInput(text="Approve PR 88"),
        )
        initial_resp = AssistantResponse(
            action=ActionType.SUGGEST_COMMAND,
            command="gh pr approve 88",
            risk=RiskLevel.NORMAL,
        )
        parse_res = ParseResult(success=True, response=initial_resp, raw_text="{}")
        runtime = MockRuntime(repair_output="{}")

        final_parse, sys_eval = pipeline.evaluate(scenario, parse_res, runtime)
        # Even with completely unknown scenario_id and contracts_by_id=None,
        # the runtime resolver resolves user_text="Approve PR 88" to gh review_pr and applies deterministic correction!
        self.assertEqual(sys_eval.intent_source, "runtime")
        self.assertIsNotNone(sys_eval.runtime_intent_resolution)
        self.assertEqual(sys_eval.runtime_intent_resolution.status, RuntimeIntentStatus.RESOLVED)
        self.assertEqual(sys_eval.final_command, "gh pr review 88 --approve")
        self.assertTrue(sys_eval.staging_eligible)

    def test_ambiguous_intent_leads_to_clarify(self):
        pipeline = SystemEvaluationPipeline(
            fixtures_dir="fixtures",
            intent_source=IntentSource.RUNTIME,
            contracts_by_id=None,
        )
        scenario = Scenario(
            id="ambiguous-pr-id",
            name="Ambiguous PR",
            domain=Domain.GH,
            difficulty=Difficulty.BASIC,
            mode=InteractionMode.EXPLICIT,
            input=ScenarioInput(text="Approve the PR"),
        )
        initial_resp = AssistantResponse(
            action=ActionType.SUGGEST_COMMAND,
            command="gh pr review --approve",
            risk=RiskLevel.NORMAL,
        )
        parse_res = ParseResult(success=True, response=initial_resp, raw_text="{}")
        runtime = MockRuntime(repair_output="{}")

        final_parse, sys_eval = pipeline.evaluate(scenario, parse_res, runtime)
        # Ambiguous resolution must trigger clarify and prevent staging
        self.assertEqual(sys_eval.final_action, "clarify")
        self.assertFalse(sys_eval.staging_eligible)
        self.assertIn("clarify", final_parse.response.action.value)


if __name__ == "__main__":
    unittest.main()
