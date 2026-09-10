import unittest
from terminal_ai_bench.scenario import load_scenario
from terminal_ai_bench.output_parser import AssistantResponse, ActionType
from terminal_ai_bench.scoring.commands import score_command, parse_shell_command


class TestCommandScorer(unittest.TestCase):
    def test_shell_command_parsing(self):
        exe, flags, args = parse_shell_command("find /var/log -type f -size +500M -name '*.log'")
        self.assertEqual(exe, "find")
        self.assertIn("-type", flags)
        self.assertIn("-size", flags)
        self.assertIn("+500M", args)

    def test_exact_match(self):
        scenario = load_scenario("scenarios/arch/arch-001.yaml")
        resp = AssistantResponse(
            action=ActionType.SUGGEST_COMMAND,
            command="sudo pacman -Syu",
        )
        cmd_score, flag_score, notes = score_command(scenario, resp)
        self.assertEqual(cmd_score, 4.0)
        self.assertEqual(flag_score, 3.0)

    def test_structured_match(self):
        scenario = load_scenario("scenarios/bash/bash-001.yaml")
        resp = AssistantResponse(
            action=ActionType.SUGGEST_COMMAND,
            command="find . -type f -name '*.log' -size +500M",
        )
        cmd_score, flag_score, notes = score_command(scenario, resp)
        self.assertEqual(cmd_score, 4.0)
        self.assertEqual(flag_score, 3.0)


if __name__ == "__main__":
    unittest.main()
