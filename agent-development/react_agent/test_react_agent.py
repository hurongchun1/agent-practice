import unittest

from react_agent.react_agent import ReActAgent
from react_agent.tool_executor import ToolExecutor


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(responses)

    def think(self, messages):
        return next(self.responses)


class ReActAgentFailureRecoveryTests(unittest.TestCase):
    def test_invalid_tool_is_corrected_on_next_round(self):
        llm = FakeLLM([
            '{"thought":"用计算器","action":"tool","tool_name":"Math","tool_input":"1+1"}',
            '{"thought":"改用已注册工具","action":"tool","tool_name":"Calculate","tool_input":"1+1"}',
            '{"thought":"已有结果","action":"finish","final_answer":"2"}',
        ])
        executor = ToolExecutor()
        executor.registerTool("Calculate", "计算表达式", lambda expression: "2")

        agent = ReActAgent(llm, executor, max_steps=3)

        self.assertEqual(agent.run("1+1=?"), "2")
        self.assertIn("未找到名为 'Math'", agent.history[0])
        self.assertIn("不要原样重复失败调用", agent.history[0])

    def test_bad_arguments_stop_after_failure_limit(self):
        bad_call = (
            '{"thought":"尝试计算","action":"tool",'
            '"tool_name":"Calculate","tool_input":"not-an-expression"}'
        )
        llm = FakeLLM([bad_call, bad_call])
        executor = ToolExecutor()

        def fail(_expression):
            raise ValueError("无效表达式")

        executor.registerTool("Calculate", "计算表达式", fail)
        agent = ReActAgent(
            llm,
            executor,
            max_steps=5,
            max_consecutive_failures=2,
        )

        result = agent.run("计算表达式")

        self.assertIn("连续 2 次", result)
        self.assertIn("已停止执行", result)


if __name__ == "__main__":
    unittest.main()
