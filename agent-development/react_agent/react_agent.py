import json
from typing import Optional

from original_agent.build_first_agent import HelloAgentsLLM
from react_agent.system_prompt import REACT_PROMPT_TEMPLATE
from react_agent.tool_executor import ToolExecutor

class ReActAgent():

    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
        max_consecutive_failures: int = 3,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.max_consecutive_failures = max_consecutive_failures
        self.history=[]
    
    # 这里是运行智能体的主入口
    def run(self,question:str):
        # 每次运行时，历史记录都会被清空
        self.history = []
        # 当前步数
        current_step = 0
        consecutive_failures = 0

        while current_step < self.max_steps:
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
            try:
                json_data = self._parse_output(response_text)
            except (json.JSONDecodeError, ValueError) as error:
                consecutive_failures += 1
                feedback = self._build_correction_feedback(
                    reason=f"输出格式错误：{error}",
                    failure_count=consecutive_failures,
                )
                print(f"观察：{feedback}")
                self.history.append(f"Observation: {feedback}")
                if consecutive_failures >= self.max_consecutive_failures:
                    return self._stop_after_failures(feedback)
                continue

            thought = json_data.get("thought")
            action = json_data.get("action")

            if thought:
                print(f"思考：{thought}")
            

            # 4.执行Action
            if action == "finish":
                # 如果是Finish指令，提取最终答案并结束
                final_answer = json_data.get("final_answer")
                print(f"最终答案：{final_answer}")
                return final_answer

            
            tool_name = json_data.get("tool_name")
            tool_input = json_data.get("tool_input")

            print(f"行动：{tool_name} [{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)

            if not tool_function:
                observation = f"错误：未找到名为 '{tool_name}' 的工具。"

            else:
                try:
                    observation = str(tool_function(tool_input))
                except Exception as error:
                    observation = f"错误：工具参数或执行失败：{error}"

            if self._is_failed_observation(observation):
                consecutive_failures += 1
                observation = self._build_correction_feedback(
                    reason=observation,
                    failure_count=consecutive_failures,
                    failed_tool=tool_name,
                    failed_input=tool_input,
                )
            else:
                consecutive_failures = 0
            
            print(f"观察：{observation}")

            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

            if consecutive_failures >= self.max_consecutive_failures:
                return self._stop_after_failures(observation)

        # while 循环结束后执行：达到最大步数仍未得到最终答案
        print("已达到最大步数，流程终止。")
        return None

    def _build_correction_feedback(
        self,
        reason: str,
        failure_count: int,
        failed_tool: Optional[str] = None,
        failed_input: Optional[str] = None,
    ) -> str:
        """把失败转换成模型下一轮可执行的纠错提示。"""
        failed_call = ""
        if failed_tool:
            failed_call = f"\n失败调用：{failed_tool}[{failed_input}]"

        return (
            f"工具调用失败（连续第 {failure_count} 次）：{reason}{failed_call}\n"
            "请先重新检查用户目标，再从下面的工具中选择最匹配的一项，并严格按其输入说明重写参数；"
            "不要原样重复失败调用。若无需工具或已有足够信息，请使用 finish。\n"
            f"可用工具：\n{self.tool_executor.getAvailableTools()}"
        )

    @staticmethod
    def _is_failed_observation(observation: str) -> bool:
        normalized = observation.strip().lower()
        return normalized.startswith(("错误", "error")) or "发生错误" in normalized

    def _stop_after_failures(self, last_feedback: str):
        """失败达到阈值后安全停止，避免无限重试和无效工具消耗。"""
        message = (
            f"连续 {self.max_consecutive_failures} 次未能生成有效的工具调用，已停止执行。"
            f"最后一次反馈：{last_feedback}"
        )
        print(message)
        return message
    
    def _parse_output(self,text:str):
        """解析LLM的输出，提取Thought和Action"""
        
        data = json.loads(text)
        if not isinstance(data,dict):
            raise ValueError("必须返回一个 JSON 对象")
        
        action = data.get("action")
        thought = data.get("thought")

        if action not in {"tool","finish"}:
            raise ValueError("action 必须是 tool 或 finish")
        
        if not isinstance(thought,str) or not thought.strip():
            raise ValueError("thought 必须是非空字符串")
        
        if action == "tool":
            tool_name = data.get("tool_name")
            tool_input = data.get("tool_input")

            if not isinstance(tool_name,str) or not tool_name.strip():
                raise ValueError("tool_name 必须是非空字符串")

            if not isinstance(tool_input,str) or not tool_input.strip():
                raise ValueError("tool_input 必须是非空字符串")
            
            if self.tool_executor.getTool(tool_name) is None:
                raise ValueError(f"未找到名为 '{tool_name}' 的工具。")
        else :
            # finish
            final_answer = data.get("final_answer")

            if not isinstance(final_answer,str) or not final_answer.strip():
                raise ValueError("final_answer 必须是具体的非空答案")
        
        return data 


if __name__ == '__main__':
    from react_agent.search_tool import search

    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
