"""维护 ReAct 的 Action/Observation 历史。"""

import json

from .common_result.tool_result import ToolResult
from .error_observation import build_error_observation
from .model_output import AgentAction


class AgentTrace:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def clear(self) -> None:
        self.entries.clear()

    def as_prompt_text(self) -> str:
        return "\n".join(self.entries)

    def record_action(self, action: AgentAction) -> None:
        content = json.dumps(
            {"tool_name": action.tool_name, "tool_input": action.tool_input},
            ensure_ascii=False,
        )
        self.entries.append(f"Action: {content}")

    def record_success(self, result: ToolResult) -> None:
        observation = str(result.data)
        print(f"观察：{observation}")
        self.entries.append(f"Observation: {observation}")

    def record_failure(self, result: ToolResult) -> None:
        observation = json.dumps(
            build_error_observation(result),
            ensure_ascii=False,
        )
        print(f"观察：{observation}")
        self.entries.append(f"Observation: {observation}")
