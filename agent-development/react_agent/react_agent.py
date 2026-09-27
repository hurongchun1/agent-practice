import json
from typing import Protocol

from react_agent.common_result.tool_result import FailedCall, ToolError, ToolResult
from react_agent.error_observation import build_error_observation
from react_agent.system_prompt import REACT_PROMPT_TEMPLATE
from react_agent.tool_executor import ToolExecutor


class LLMClient(Protocol):
    def think(self, messages: list[dict[str, str]]) -> str:
        """根据消息生成模型输出。"""


class ReActAgent():

    def __init__(
        self,
        llm_client: LLMClient,
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
        last_failed_call = None

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
                parse_result = ToolResult(
                    ok=False,
                    tool_error=ToolError(
                        stage="model_output",
                        code="INVALID_MODEL_OUTPUT",
                        message="LLM 没有返回任何内容",
                        retryable=True,
                    ),
                )
                consecutive_failures += 1
                self._append_error_observation(parse_result)
                if consecutive_failures >= self.max_consecutive_failures:
                    return self._too_many_failures(last_failed_call)
                continue

            # 3.解析LLM的输出
            try:
                json_data = self._parse_output(response_text)
            except (json.JSONDecodeError, ValueError) as error:
                parse_result = ToolResult(
                    ok=False,
                    tool_error=ToolError(
                        stage="model_output",
                        code="INVALID_MODEL_OUTPUT",
                        message=str(error),
                        retryable=True,
                    ),
                )
                consecutive_failures += 1
                self._append_error_observation(parse_result)
                if consecutive_failures >= self.max_consecutive_failures:
                    return self._too_many_failures(last_failed_call)
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

            
            tool_name= json_data.get("tool_name")
            tool_input= json_data.get("tool_input")

            print(f"行动：{tool_name} [{tool_input}]")

            tool_result = self.tool_executor.execute(tool_name, tool_input)
            action_record = json.dumps(
                {"tool_name": tool_name, "tool_input": tool_input},
                ensure_ascii=False,
            )
            self.history.append(f"Action: {action_record}")

            if tool_result.ok:
                consecutive_failures = 0
                observation = str(tool_result.data)
                print(f"观察：{observation}")
                self.history.append(f"Observation: {observation}")
                continue

            consecutive_failures += 1
            last_failed_call = tool_result.failed_call
            self._append_error_observation(tool_result)
            if consecutive_failures >= self.max_consecutive_failures:
                return self._too_many_failures(last_failed_call)

        # while 循环结束后执行：达到最大步数仍未得到最终答案
        print("已达到最大步数，流程终止。")
        return ToolResult(
            ok=False,
            tool_error=ToolError(
                stage="agent_loop",
                code="MAX_STEPS_EXCEEDED",
                message="达到最大步数，仍未获得最终答案",
                retryable=False,
            ),
            failed_call=last_failed_call,
        )

    def _append_error_observation(self, result: ToolResult) -> None:
        observation = json.dumps(
            build_error_observation(result),
            ensure_ascii=False,
        )
        print(f"观察：{observation}")
        self.history.append(f"Observation: {observation}")

    def _too_many_failures(
        self,
        failed_call: FailedCall | None,
    ) -> ToolResult:
        return ToolResult(
            ok=False,
            tool_error=ToolError(
                stage="agent_loop",
                code="TOO_MANY_FAILURES",
                message=f"连续失败已达 {self.max_consecutive_failures} 次，停止执行",
                retryable=False,
            ),
            failed_call=failed_call,
        )

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
            # 已经放到 ToolExecutor.execute中判断
            # if self.tool_executor.getTool(tool_name) is None:
            #     raise ValueError(f"未找到名为 '{tool_name}' 的工具。")
        else :
            # finish
            final_answer = data.get("final_answer")

            if not isinstance(final_answer,str) or not final_answer.strip():
                raise ValueError("final_answer 必须是具体的非空答案")
        
        return data 


if __name__ == '__main__':
    from original_agent.build_first_agent import HelloAgentsLLM
    from react_agent.search_tool import search

    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
