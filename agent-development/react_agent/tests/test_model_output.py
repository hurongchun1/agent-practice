import json
import unittest

from ..model_output import parse_model_output


class ModelOutputTests(unittest.TestCase):
    def test_parse_tool_action(self):
        action = parse_model_output(json.dumps({
            "thought": "需要精确计算",
            "action": "tool",
            "tool_name": "Calculate",
            "tool_input": "1+1",
        }, ensure_ascii=False))

        self.assertFalse(action.is_finished)
        self.assertEqual(action.tool_name, "Calculate")
        self.assertEqual(action.tool_input, "1+1")

    def test_reject_missing_tool_input(self):
        with self.assertRaisesRegex(ValueError, "tool_input"):
            parse_model_output(json.dumps({
                "thought": "需要精确计算",
                "action": "tool",
                "tool_name": "Calculate",
            }, ensure_ascii=False))
