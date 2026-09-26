# 当智能体需要使用多种工具时（例如，除了搜索，还可能需要计算、查询数据库等），我们需要一个统一的管理器来注册和调度这些工具。

from collections.abc import Callable
from typing import Any, TypedDict

from react_agent.common_result.tool_result import (
    FailedCall,
    ToolError,
    ToolResult,
)


class ToolInfo(TypedDict):
    """工具注册表中单个工具的结构。"""

    description: str
    func: Callable[[str], Any]

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: dict[str, ToolInfo] = {}

    def registerTool(
        self,
        name: str,
        description: str,
        func: Callable[[str], Any],
    ) -> None:
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> Callable[[str], Any] | None:
        """
        根据名称获取一个工具的执行函数。
        """
        tool_info = self.tools.get(name)
        if tool_info is None:
            return None

        return tool_info["func"]

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])

    def execute(self, tool_name: str, tool_input: str) -> ToolResult:
        """
        这里是统一的工具执行的入口
        """
        # 说明模型输入参数为空，需要加上校验规则
        if not isinstance(tool_input, str) or not tool_input.strip():
            return ToolResult(
                ok = False,
                tool_error= ToolError(
                    stage = "validation",
                    code = "INVALID_ARGUMENT",
                    message = "模型输入参数不合法",
                    retryable = True
                ),
                failed_call = FailedCall(
                    tool_name = tool_name,
                    tool_input = tool_input
                )
            )


        tool_callable = self.getTool(tool_name)
        # 判断1：能否找到工具
        if tool_callable is None:
            return ToolResult(
                ok = False,
                tool_error= ToolError(
                    stage = "tool_selection",
                    code = "TOOL_NOT_FOUND",
                    message = "调用的工具不存在",
                    retryable = True
                ),
                failed_call = FailedCall(
                    tool_name = tool_name,
                    tool_input = tool_input
                )
            )
        
        try:
            # 执行工具
            tool_data = tool_callable(tool_input)
            # 返回成功的 ToolResult
            return ToolResult(
                ok = True,
                data = tool_data
            )
        except Exception as error:
            # 返回 EXECUTION_FAILED
            return ToolResult(
                ok = False,
                tool_error= ToolError(
                    stage = "tool_execution",
                    code = "EXECUTION_FAILED",
                    message = f"工具执行失败：{error}",
                    retryable = True
                ),
                failed_call = FailedCall(
                    tool_name = tool_name,
                    tool_input = tool_input
                )
            )


# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    from .search_tool import search

    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    
    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")
