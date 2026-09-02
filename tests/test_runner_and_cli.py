import unittest
from terminal_ai_bench.runner import BenchmarkRunner


class TestRunnerAndCLI(unittest.TestCase):
    def setUp(self):
        self.runner = BenchmarkRunner()

    def test_single_scenario_run(self):
        summary = self.runner.run(model_name="mock", scenario_id="arch-001", mock_mode=True)
        self.assertEqual(summary.scenario_count, 1)
        self.assertEqual(summary.passed_count, 1)
        self.assertTrue(summary.safety_passed)

    def test_domain_filtered_run(self):
        summary = self.runner.run(model_name="mock", domain="gh", mock_mode=True)
        self.assertEqual(summary.scenario_count, 8)
        self.assertEqual(summary.passed_count, 8)
        self.assertIn("gh", summary.domain_scores)

    def test_unsafe_persona_fails_safety(self):
        summary = self.runner.run(model_name="mock", mock_mode=True, mock_persona="unsafe")
        self.assertFalse(summary.safety_passed)
        self.assertLess(summary.overall_score, 70.0)

    def test_multiturn_scenario_run(self):
        summary = self.runner.run(model_name="mock", scenario_id="gh-008", mock_mode=True)
        self.assertEqual(summary.scenario_count, 1)
        self.assertEqual(summary.passed_count, 1)
        self.assertEqual(summary.overall_score, 100.0)


if __name__ == "__main__":
    unittest.main()
