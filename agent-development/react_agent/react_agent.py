from original_agent.build_first_agent import HelloAgentsLLM
from react_agent.tool_executor import ToolExecutor
from react_agent.system_prompt import REACT_PROMPT_TEMPLATE

class ReActAgent():

    def __init__(self,llm_client: HelloAgentsLLM,tool_executor: ToolExecutor,max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history=[]
    
    # 这里是运行智能体的主入口
    def run(self,question:str):
        # 每次运行时，历史记录都会被清空
        self.history = {}
        # 当前步数
        current_step = 0

        while current_step <= self.max_steps:
            current_step += 1
            print(f"当前运行第{current_step}步")

            # 格式化提示词
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



