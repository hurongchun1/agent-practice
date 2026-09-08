"""
ReAct Agent 统一运行入口
使用方式：在 agent-development 目录下运行
  python run.py
"""

import sys
import os

# 解决 Windows 控制台 GBK 编码无法打印 emoji 等字符的问题
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 确保当前目录在 Python 路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from original_agent.build_first_agent import HelloAgentsLLM
from react_agent.tool_executor import ToolExecutor
from react_agent.search_tool import search
from react_agent.react_agent import ReActAgent


def main():
    """主函数：运行 ReAct Agent"""
    
    # 1. 初始化 LLM 客户端
    llm = HelloAgentsLLM()
    
    # 2. 初始化工具执行器并注册搜索工具
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    
    # 3. 创建 ReAct Agent
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    
    # 4. 运行问题
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    print(f"\n{'='*50}")
    print(f"问题: {question}")
    print(f"{'='*50}\n")
    
    result = agent.run(question)
    
    print(f"\n{'='*50}")
    print(f"最终结果: {result}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()

# ==================================================
# 问题: 华为最新的手机是哪一款？它的主要卖点是什么？
# ==================================================

# 当前运行第1步
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# Thought:用户想了解华为最新手机型号及其主要卖点。这个问题需要获取最新的产品信息，我需要搜索当前最新的华为手机型号和其主打特点。      

# Action: Search[华为 2024年 最新手机型号 主要卖点]
# 思考：用户想了解华为最新手机型号及其主要卖点。这个问题需要获取最新的产品信息，我需要搜索当前最新的华为手机型号和其主打特点。        
# 行动：Search [华为 2024年 最新手机型号 主要卖点]
# 🔍 正在执行 [Tavily] 网页搜索: 华为 2024年 最新手机型号 主要卖点
# 观察：Huawei's 2024 flagship model is the Mate 60 Pro+, featuring a self-developed 5G chip, satellite communication, and upgraded cameras and memory. It's a high-end model with strong performance and innovative technology.
# 当前运行第2步
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# Thought: 我需要先确定当前的时间，以确保“最新”信息是基于最新发布的。根据用户的搜索历史，之前的搜索是关于2024年的华为最新手机，结果提 到了Mate 60 Pro+。但为了确保准确性，我应该再次搜索，以确认是否有更新的型号发布，或者Mate 60 Pro+仍然是当前最新的旗舰机型。然后，我需要从搜索结果中提取其主要卖点，以便全面回答用户的问题。

# Action: Search[华为最新手机型号 2024 2025 主要特点]
# 思考：我需要先确定当前的时间，以确保“最新”信息是基于最新发布的。根据用户的搜索历史，之前的搜索是关于2024年的华为最新手机，结果提到了Mate 60 Pro+。但为了确保准确性，我应该再次搜索，以确认是否有更新的型号发布，或者Mate 60 Pro+仍然是当前最新的旗舰机型。然后，我需要从搜索结果中提取其主要卖点，以便全面回答用户的问题。
# 行动：Search [华为最新手机型号 2024 2025 主要特点]
# 🔍 正在执行 [Tavily] 网页搜索: 华为最新手机型号 2024 2025 主要特点
# 观察：Huawei's latest models in 2024 are the Pura 70 series, and in 2025, the Pura X is expected. Both feature advanced Kirin chips and HarmonyOS.
# 当前运行第3步
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# Thought: 用户想知道华为最新的手机是哪一款及其主要卖点。根据历史记录，已经进行了两次搜索，但结果有些冲突：一次提到2024年旗舰是Mate 60 Pro+，另一次提到2024年最新系列是Pura 70，且2025年预计有Pura X。这需要进一步澄清。考虑到当前时间（2025年），最新的应该是Pura 70系列 （2024年发布）或可能更新的机型。我需要再搜索一次，明确华为在2024-2025年最新型号及其关键特点，以便给出准确、最新的信息。

# Action: Search[华为 Pura 70 系列 主要卖点 2024]
# 思考：用户想知道华为最新的手机是哪一款及其主要卖点。根据历史记录，已经进行了两次搜索，但结果有些冲突：一次提到2024年旗舰是Mate 60 Pro+，另一次提到2024年最新系列是Pura 70，且2025年预计有Pura X。这需要进一步澄清。考虑到当前时间（2025年），最新的应该是Pura 70系列（2024年发布）或可能更新的机型。我需要再搜索一次，明确华为在2024-2025年最新型号及其关键特点，以便给出准确、最新的信息。
# 行动：Search [华为 Pura 70 系列 主要卖点 2024]
# 🔍 正在执行 [Tavily] 网页搜索: 华为 Pura 70 系列 主要卖点 2024
# 观察：The main selling points of Huawei Pura 70 series are advanced AI-driven photography, innovative satellite communication, and sleek, minimalist design.
# 当前运行第4步
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# Thought: 用户询问华为最新的手机及其主要卖点。回顾历史记录，有三次搜索结果：第一次提到华为2024年的旗舰型号是Mate 60 Pro+，第二次指出 华为2024年的最新型号是Pura 70系列，第三次具体描述了Pura 70系列的卖点。考虑到Pura 70系列被明确标识为2024年最新型号，且历史记录中未提 及其他更新型号，我可以推断Pura 70系列是华为目前最新的手机系列。其主要卖点从搜索结果中得出，包括先进的AI驱动摄影、创新的卫星通信和时 尚简约的设计。因此，我无需进一步搜索，可以直接基于历史信息提供最终答案。

# Action: Finish[华为最新的手机是Pura 70系列。其主要卖点包括先进的AI驱动摄影、创新的卫星通信和时尚简约的设计。]
# 思考：用户询问华为最新的手机及其主要卖点。回顾历史记录，有三次搜索结果：第一次提到华为2024年的旗舰型号是Mate 60 Pro+，第二次指出华为2024年的最新型号是Pura 70系列，第三次具体描述了Pura 70系列的卖点。考虑到Pura 70系列被明确标识为2024年最新型号，且历史记录中未提及其 他更新型号，我可以推断Pura 70系列是华为目前最新的手机系列。其主要卖点从搜索结果中得出，包括先进的AI驱动摄影、创新的卫星通信和时尚简 约的设计。因此，我无需进一步搜索，可以直接基于历史信息提供最终答案。
# 最终答案：华为最新的手机是Pura 70系列。其主要卖点包括先进的AI驱动摄影、创新的卫星通信和时尚简约的设计。

# ==================================================
# 最终结果: 华为最新的手机是Pura 70系列。其主要卖点包括先进的AI驱动摄影、创新的卫星通信和时尚简约的设计。
# ==================================================