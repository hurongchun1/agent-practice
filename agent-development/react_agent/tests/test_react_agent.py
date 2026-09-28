import json
import unittest

from ..common_result.tool_execution_error import ToolExecutionError
from ..react_agent import ReActAgent
from ..tool_executor import ToolExecutor
from .helpers import FakeLLM


def response(**fields) -> str:
    return json.dumps(fields, ensure_ascii=False)


class ReActAgentTests(unittest.TestCase):
    def test_corrects_wrong_tool_and_finishes(self):
        llm = FakeLLM([
            response(thought="尝试数学工具", action="tool",
                     tool_name="Math", tool_input="1+1"),
            response(thought="改用 Calculate", action="tool",
                     tool_name="Calculate", tool_input="1+1"),
            response(thought="已获得结果", action="finish", final_answer="2"),
        ])
        executor = ToolExecutor()
        executor.registerTool("Calculate", "计算表达式", lambda _value: "2")
        agent = ReActAgent(llm, executor, max_steps=3)

        self.assertEqual(agent.run("1+1 等于多少？"), "2")
        self.assertIn("TOOL_NOT_FOUND", agent.history[1])

    def test_non_retryable_error_stops_immediately(self):
        def unavailable(_value: str) -> str:
            raise ToolExecutionError(
                "CONFIGURATION_ERROR",
                "工具缺少必要配置",
                False,
            )

        executor = ToolExecutor()
        executor.registerTool("Unavailable", "不可用工具", unavailable)
        llm = FakeLLM([
            response(thought="调用工具", action="tool",
                     tool_name="Unavailable", tool_input="input"),
        ])

        result = ReActAgent(llm, executor).run("调用工具")

        self.assertEqual(result.tool_error.code, "CONFIGURATION_ERROR")
        self.assertFalse(result.tool_error.retryable)

    def test_repeated_failures_trigger_breaker(self):
        invalid = response(
            thought="尝试不存在的工具",
            action="tool",
            tool_name="Math",
            tool_input="1+1",
        )
        agent = ReActAgent(
            FakeLLM([invalid, invalid]),
            ToolExecutor(),
            max_steps=5,
            max_consecutive_failures=2,
        )

        result = agent.run("1+1 等于多少？")

        self.assertEqual(result.tool_error.code, "TOO_MANY_FAILURES")
