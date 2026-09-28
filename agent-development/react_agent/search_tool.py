import os

from .common_result.tool_execution_error import ToolExecutionError

def search(query: str) -> str:
    """
    一个基于 Tavily 的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回综合答案（include_answer）。
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("搜索内容不能为空")

    print(f"正在执行 [Tavily] 网页搜索: {query}")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ToolExecutionError(
            code="CONFIGURATION_ERROR",
            message="搜索工具未配置 TAVILY_API_KEY",
            retryable=False,
        )

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="advanced", include_answer=True)

        # 1. 优先返回 Tavily 生成的综合回答
        if response.get("answer"):
            return response["answer"]

        # 2. 没有综合回答时，格式化原始搜索结果
        results = response.get("results", [])
        if results:
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('content', '')}"
                for i, res in enumerate(results[:3])
            ]
            return "\n\n".join(snippets)

        return f"对不起，没有找到关于 '{query}' 的信息。"

    except ModuleNotFoundError as error:
        raise ToolExecutionError(
            code="CONFIGURATION_ERROR",
            message="搜索工具缺少 tavily-python 依赖",
            retryable=False,
        ) from error
    except TimeoutError as error:
        raise ToolExecutionError(
            code="EXECUTION_FAILED",
            message=f"搜索服务暂时超时：{error}",
            retryable=True,
        ) from error
    except Exception as error:
        raise ToolExecutionError(
            code="EXECUTION_FAILED",
            message=f"搜索工具发生未知异常：{error}",
            retryable=False,
        ) from error
