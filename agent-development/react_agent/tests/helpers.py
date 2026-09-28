class FakeLLM:
    """按顺序返回预设响应。"""

    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    def think(self, messages: list[dict[str, str]]) -> str:
        return next(self._responses)
