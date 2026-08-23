# 将所有工具函数放入一个字典，方便后续调用
from get_weather import get_weather  # pyright: ignore[reportImplicitRelativeImport]
from get_attraction import get_attraction  # pyright: ignore[reportImplicitRelativeImport]
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)


available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction
}

class OpenAICompatibleAgentClient:
    """
    一个用于调用任何兼容OpenAI 接口的LLM服务的客户端.
    """

    def __init__(self,model: str,api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key,base_url=base_url)

    
    def generate(self,prompt: str, system_prompt: str) -> str:
        """调用LLM API来生成回应。"""
        print("正在调用大语言模型...")
        try:
            '''本质区别：
            普通字典：类型是 dict[str,str]，太宽泛，检查器无法确定它是否真的符合OpenAI的消息格式
            包装类：类型是 ChatCompletionMessageParam，这是一个精确的类型标记，告诉检查器"我就是合法消息"
            '''
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=prompt)
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer: str = response.choices[0].message.content  # pyright: ignore[reportAssignmentType]
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误：{e}")
            return "错误：调用语言模型服务时出错"
            
