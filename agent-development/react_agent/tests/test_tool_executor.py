import unittest

from ..common_result.tool_execution_error import ToolExecutionError
from ..error_observation import build_error_observation
from ..tool_executor import ToolExecutor


class ToolExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = ToolExecutor()
        self.executor.registerTool("Calculate", "计算表达式", self._calculate)

    @staticmethod
    def _calculate(expression: str) -> str:
        if expression != "1+1":
            raise ValueError("只接受示例表达式 1+1")
        return "2"

    def test_unknown_tool_requires_reselection(self):
        result = self.executor.execute("Math", "1+1")
        correction = build_error_observation(result)["correction"]

        self.assertTrue(result.tool_error.retryable)
        self.assertEqual(result.tool_error.code, "TOOL_NOT_FOUND")
        self.assertEqual(correction["action"], "SELECT_ANOTHER_TOOL")

    def test_invalid_argument_requires_new_arguments(self):
        result = self.executor.execute("Calculate", "1+1=?")
        correction = build_error_observation(result)["correction"]

        self.assertTrue(result.tool_error.retryable)
        self.assertEqual(result.tool_error.code, "INVALID_ARGUMENT")
        self.assertEqual(correction["action"], "RETRY_WITH_NEW_ARGUMENTS")

    def test_non_retryable_error_stops(self):
        def unavailable(_value: str) -> str:
            raise ToolExecutionError(
                "CONFIGURATION_ERROR",
                "工具缺少必要配置",
                False,
            )

        self.executor.registerTool("Unavailable", "不可用工具", unavailable)
        result = self.executor.execute("Unavailable", "input")
        correction = build_error_observation(result)["correction"]

        self.assertFalse(result.tool_error.retryable)
        self.assertEqual(correction["action"], "STOP")
