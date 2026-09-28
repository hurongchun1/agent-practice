"""定义并解析 ReAct 模型每一轮返回的动作。"""

import json
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AgentAction:
    """通过校验后的模型动作。"""

    thought: str
    action: Literal["tool", "finish"]
    tool_name: str | None = None
    tool_input: str | None = None
    final_answer: str | None = None

    @property
    def is_finished(self) -> bool:
        return self.action == "finish"


def parse_model_output(text: str) -> AgentAction:
    """将模型 JSON 文本校验并转换为 AgentAction。"""
    if not text or not text.strip():
        raise ValueError("LLM 没有返回任何内容")

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("必须返回一个 JSON 对象")

    action = data.get("action")
    thought = data.get("thought")

    if action not in {"tool", "finish"}:
        raise ValueError("action 必须是 tool 或 finish")

    if not isinstance(thought, str) or not thought.strip():
        raise ValueError("thought 必须是非空字符串")

    if action == "tool":
        tool_name = data.get("tool_name")
        tool_input = data.get("tool_input")

        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name 必须是非空字符串")

        if not isinstance(tool_input, str) or not tool_input.strip():
            raise ValueError("tool_input 必须是非空字符串")

        return AgentAction(
            thought=thought.strip(),
            action="tool",
            tool_name=tool_name.strip(),
            tool_input=tool_input.strip(),
        )

    final_answer = data.get("final_answer")
    if not isinstance(final_answer, str) or not final_answer.strip():
        raise ValueError("final_answer 必须是具体的非空答案")

    return AgentAction(
        thought=thought.strip(),
        action="finish",
        final_answer=final_answer.strip(),
    )
