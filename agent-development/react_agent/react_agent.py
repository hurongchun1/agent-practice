"""ReAct 主循环，只负责编排各模块。"""

import json
from typing import Protocol

from .agent_failure import (
    invalid_model_output,
    max_steps_exceeded,
    too_many_failures,
)
from .agent_trace import AgentTrace
from .common_result.tool_result import FailedCall, ToolResult
from .model_output import AgentAction, parse_model_output
from .system_prompt import REACT_PROMPT_TEMPLATE
from .tool_executor import ToolExecutor


class LLMClient(Protocol):
    def think(self, messages: list[dict[str, str]]) -> str: ...


class ReActAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
        max_consecutive_failures: int = 3,
    ) -> None:
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.max_consecutive_failures = max_consecutive_failures
        self.trace = AgentTrace()

    @property
    def history(self) -> list[str]:
        return self.trace.entries

    def run(self, question: str):
        self.trace.clear()
        failures = 0
        last_failed_call: FailedCall | None = None

        for step in range(1, self.max_steps + 1):
            print(f"当前运行第{step}步")

            try:
                action = self._request_action(question)
            except (json.JSONDecodeError, ValueError) as error:
                failures += 1
                stopped = self._handle_failure(
                    invalid_model_output(error), failures, last_failed_call,
                )
                if stopped:
                    return stopped
                continue

            print(f"思考：{action.thought}")
            if action.is_finished:
                print(f"最终答案：{action.final_answer}")
                return action.final_answer

            result = self._execute(action)
            if result.ok:
                failures = 0
                self.trace.record_success(result)
                continue

            failures += 1
            last_failed_call = result.failed_call
            stopped = self._handle_failure(result, failures, last_failed_call)
            if stopped:
                return stopped

        print("已达到最大步数，流程终止。")
        return max_steps_exceeded(last_failed_call)

    def _request_action(self, question: str) -> AgentAction:
        prompt = REACT_PROMPT_TEMPLATE.format(
            tools=self.tool_executor.getAvailableTools(),
            history=self.trace.as_prompt_text(),
            question=question,
        )
        response = self.llm_client.think([{"role": "user", "content": prompt}])
        return parse_model_output(response)

    def _execute(self, action: AgentAction) -> ToolResult:
        if action.tool_name is None or action.tool_input is None:
            raise ValueError("工具动作缺少 tool_name 或 tool_input")

        print(f"行动：{action.tool_name} [{action.tool_input}]")
        self.trace.record_action(action)
        return self.tool_executor.execute(action.tool_name, action.tool_input)

    def _handle_failure(
        self,
        result: ToolResult,
        failures: int,
        last_failed_call: FailedCall | None,
    ) -> ToolResult | None:
        self.trace.record_failure(result)
        error = result.tool_error

        if error is None:
            raise ValueError("失败结果必须包含 tool_error")
        if not error.retryable:
            return result
        if failures >= self.max_consecutive_failures:
            return too_many_failures(
                self.max_consecutive_failures,
                last_failed_call,
            )
        return None
