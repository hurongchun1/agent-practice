from tavily import TavilyClient
import os

def search(query: str) -> str:
    """
    一个基于 Tavily 的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回综合答案（include_answer）。
    """
    print(f"🔍 正在执行 [Tavily] 网页搜索: {query}")
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "错误:TAVILY_API_KEY 未在 .env 文件中配置。"

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

    except Exception as e:
        return f"搜索时发生错误: {e}"
