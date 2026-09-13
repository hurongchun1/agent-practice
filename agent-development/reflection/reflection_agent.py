from .memory import Memory
from ..original_agent.build_first_agent import HelloAgentsLLM
from .init_prompt import INIT_PROMPT_TEMPLATE
from .refinement_prompt import REFINE_PROMPT_TEMPLATE

class ReflectionAgent:
    
    def __init__(self,llm_client : HelloAgentsLLM,max_iterations=3) -> None:
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations
        
    
    def run(self,task: str):
        print("\n ---- 开始处理任务 ----\n任务：{task}")

        # --- 1.初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = INIT_PROMPT_TEMPLATE.format(task=task)
        reflection_prompt
        # 还有这里没写
        pass



    def _get_llm_response(self,prompt :str) -> str:
        """一个辅助方法，用于调用LLM"""
        messages = [{"role":"user","content":prompt}]
        response_text = self.llm_client.think(messages = messages) or ""
        return response_text


