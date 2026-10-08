from autogen_ext.models.openai import OpenAIChatCompletionClient
import os

def create_openai_model_client():
    """创建并配置 OpenAI 模型客户端"""
    return OpenAIChatCompletionClient(
        model = os.getenv("LLM_MODEL_ID","gpt-4o")
        api_key= os.os.getenv("LLM_API_KEY")
        base_url=os.os.getenv("LLM_BASE_URL","https://api.openai.com/v1")
    )