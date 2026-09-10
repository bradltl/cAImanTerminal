import unittest
from pathlib import Path
from terminal_ai_bench.scenario import load_all_scenarios, Domain, InteractionMode


class TestScenarioValidation(unittest.TestCase):
    def setUp(self):
        self.scenarios = load_all_scenarios("scenarios")

    def test_scenarios_count_and_uniqueness(self):
        self.assertGreaterEqual(len(self.scenarios), 15)
        ids = [s.id for s in self.scenarios]
        self.assertEqual(len(ids), len(set(ids)), "Scenario IDs must be globally unique")

    def test_domain_distribution(self):
        domain_counts = {}
        for s in self.scenarios:
            domain_counts[s.domain] = domain_counts.get(s.domain, 0) + 1
        
        self.assertGreaterEqual(domain_counts.get(Domain.BASH, 0), 3)
        self.assertGreaterEqual(domain_counts.get(Domain.ARCH, 0), 3)
        self.assertGreaterEqual(domain_counts.get(Domain.TROUBLESHOOTING, 0), 2)
        self.assertGreaterEqual(domain_counts.get(Domain.GCLOUD, 0), 2)
        self.assertGreaterEqual(domain_counts.get(Domain.GH, 0), 2)
        self.assertGreaterEqual(domain_counts.get(Domain.INTERACTION, 0), 1)
        self.assertGreaterEqual(domain_counts.get(Domain.SAFETY, 0), 2)

    def test_forbidden_execute_command(self):
        for s in self.scenarios:
            self.assertIn(
                "execute_command",
                s.forbidden.behaviors,
                f"Scenario {s.id} must forbid autonomous execute_command behavior",
            )


if __name__ == "__main__":
    unittest.main()
