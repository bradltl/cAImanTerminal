import unittest
from terminal_ai_bench.output_parser import parse_response, ActionType, RiskLevel


class TestOutputParser(unittest.TestCase):
    def test_clean_json(self):
        raw = '{"action": "suggest_command", "command": "pacman -Syu", "risk": "elevated"}'
        res = parse_response(raw)
        self.assertTrue(res.success)
        self.assertEqual(res.response.action, ActionType.SUGGEST_COMMAND)
        self.assertEqual(res.response.command, "pacman -Syu")
        self.assertEqual(res.response.risk, RiskLevel.ELEVATED)
        self.assertEqual(res.format_compliance, 1.0)

    def test_markdown_codeblock_json(self):
        raw = """Here is the suggestion:
```json
{
  "action": "no_action"
}
```
Hope that helps!"""
        res = parse_response(raw)
        self.assertTrue(res.success)
        self.assertEqual(res.response.action, ActionType.NO_ACTION)
        self.assertEqual(res.format_compliance, 1.0)

    def test_invalid_json(self):
        raw = "Sorry, I can't help with that"
        res = parse_response(raw)
        self.assertFalse(res.success)
        self.assertIsNone(res.response)
        self.assertEqual(res.format_compliance, 0.0)


if __name__ == "__main__":
    unittest.main()
