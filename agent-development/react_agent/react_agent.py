import re
import sys
import os

# 确保 agent-development 目录在 Python 路径中（支持绝对导入，无需 __init__.py）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from original_agent.build_first_agent import HelloAgentsLLM
from react_agent.tool_executor import ToolExecutor
from react_agent.system_prompt import REACT_PROMPT_TEMPLATE
from react_agent.search_tool import search

class ReActAgent():

    def __init__(self,llm_client: HelloAgentsLLM,tool_executor: ToolExecutor,max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history=[]
    
    # 这里是运行智能体的主入口
    def run(self,question:str):
        # 每次运行时，历史记录都会被清空
        self.history = []
        # 当前步数
        current_step = 0

        while current_step <= self.max_steps:
            current_step += 1
            print(f"当前运行第{current_step}步")

            # 1.格式化提示词
            tool_des = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt=REACT_PROMPT_TEMPLATE.format(
                tools = tool_des,
                history = history_str,
                question = question
            )

            # 2.调用LLM进行思考
            messages = [{"role":"user","content":prompt}]
            response_text = self.llm_client.think(messages)

            if not response_text:
                print("LLM没有返回任何内容")
                break

            # 3.解析LLM的输出
            thought,action = self._parse_output(response_text)

            if thought:
                print(f"思考：{thought}")
            

            if not action:
                print("未能及析出有效的Action，流程终止")
                break

            # 4.执行Action
            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_match = re.search(r"Finish\[(.*)\]", action, re.DOTALL)
                if final_match:
                    final_answer = final_match.group(1).strip()
                    print(f"最终答案：{final_answer}")
                    return final_answer
                print("Finish 指令格式无法解析，流程终止")
                return None
            
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # .. 处理无效Action格式 ...
                continue

            print(f"行动：{tool_name} [{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)

            if not tool_function:
                observation = f"错误：未找到名为 '{tool_name} 的工具。'"

            else :
                observation = tool_function(tool_input) # 调用真实工具
            
            print(f"观察：{observation}")

            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # while 循环结束后执行：达到最大步数仍未得到最终答案
        print("已达到最大步数，流程终止。")
        return None
    
    def _parse_output(self,text:str):
        """解析LLM的输出，提取Thought和Action"""
        # Thought：匹配到 Action：或文本末尾
        thought_match = re.search(fr"Thought:\s*(.*?)(?=\nAction:|$)",text,re.DOTALL)

        # Action：匹配到文本末尾
        action_match = re.search("Action:\s*(.*?)$",text,re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None

        return thought,action
    
    def _parse_action(self,action_text:str):
        """解析Action字符串，提取工具名称和输入"""

        match = re.match(r"(\w+)\[(.*)\]",action_text,re.DOTALL)
        if match:
            return match.group(1), match.group(2)

        return None,None

if __name__ == '__main__':
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)