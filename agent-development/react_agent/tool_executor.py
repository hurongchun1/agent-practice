"""工具注册与执行。"""

from collections.abc import Callable
from typing import Any, TypedDict

from .common_result.tool_execution_error import ToolExecutionError
from .common_result.tool_result import FailedCall, ToolResult


class ToolInfo(TypedDict):
    description: str
    func: Callable[[str], Any]


class ToolExecutor:
    """维护工具注册表，并把执行结果统一转换为 ToolResult。"""

    def __init__(self) -> None:
        self.tools: dict[str, ToolInfo] = {}

    def registerTool(
        self,
        name: str,
        description: str,
        func: Callable[[str], Any],
    ) -> None:
        if name in self.tools:
            print(f"警告：工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> Callable[[str], Any] | None:
        tool = self.tools.get(name)
        return tool["func"] if tool else None

    def getAvailableTools(self) -> str:
        return "\n".join(
            f"- {name}: {tool['description']}"
            for name, tool in self.tools.items()
        )

    def execute(self, tool_name: str, tool_input: str) -> ToolResult:
        if not isinstance(tool_input, str) or not tool_input.strip():
            return self._failure(
                tool_name, tool_input, "validation", "INVALID_ARGUMENT",
                "模型输入参数不合法", True,
            )

        tool = self.getTool(tool_name)
        if tool is None:
            return self._failure(
                tool_name, tool_input, "tool_selection", "TOOL_NOT_FOUND",
                "调用的工具不存在", True,
            )

        try:
            return ToolResult.success(tool(tool_input))
        except ValueError as error:
            return self._failure(
                tool_name, tool_input, "validation", "INVALID_ARGUMENT",
                f"工具参数不合法：{error}", True,
            )
        except ToolExecutionError as error:
            return self._failure(
                tool_name, tool_input, "tool_execution", error.code,
                error.message, error.retryable,
            )
        except Exception as error:
            return self._failure(
                tool_name, tool_input, "tool_execution", "EXECUTION_FAILED",
                f"工具执行失败：{error}", False,
            )

    @staticmethod
    def _failure(
        tool_name: str,
        tool_input: Any,
        stage: str,
        code: str,
        message: str,
        retryable: bool,
    ) -> ToolResult:
        return ToolResult.failure(
            stage=stage,
            code=code,
            message=message,
            retryable=retryable,
            failed_call=FailedCall(tool_name, tool_input),
        )
