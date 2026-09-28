class ToolExecutionError(Exception):
    """工具主动报告的、可以被执行器识别的结构化异常。"""

    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
