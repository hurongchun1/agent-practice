"""ReAct Agent 的运行入口。

请在 agent-development 目录下执行：
    python -m react_agent.run
"""

from original_agent.build_first_agent import HelloAgentsLLM

from .react_agent import ReActAgent
from .search_tool import search
from .tool_executor import ToolExecutor
from .calculate_tool import calculate


def main():
    """初始化模型和搜索工具，然后运行 ReAct Agent。"""
    llm = HelloAgentsLLM()

    tool_executor = ToolExecutor()
    search_description = (
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中"
        "找不到的信息时，应使用此工具。"
    )

    calculate_description = (
        "一个可以用于计算的工具"
    )

    tool_executor.registerTool("Search", search_description, search)

    tool_executor.registerTool("Calculate", "一个计算工具。", calculate)

    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "计算 (123 + 456) × 789 / 12，并告诉我结果。"

    print(f"\n{'=' * 50}")
    print(f"问题: {question}")
    print(f"{'=' * 50}\n")

    result = agent.run(question)

    print(f"\n{'=' * 50}")
    print(f"最终结果: {result}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
