"""工具调用的统一成功/失败结果。"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FailedCall:
    tool_name: str
    tool_input: Any


@dataclass(frozen=True)
class ToolError:
    stage: str
    code: str
    message: str
    retryable: bool


@dataclass(frozen=True)
class ToolResult:
    """成功包含 data；失败包含 tool_error，可选 failed_call。"""

    ok: bool
    data: Any = None
    tool_error: ToolError | None = None
    failed_call: FailedCall | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.tool_error is not None or self.failed_call is not None):
            raise ValueError("成功结果不能包含错误信息")
        if not self.ok and self.tool_error is None:
            raise ValueError("失败结果必须包含 tool_error")
        if not self.ok and self.data is not None:
            raise ValueError("失败结果不能包含 data")

    @classmethod
    def success(cls, data: Any = None) -> "ToolResult":
        return cls(ok=True, data=data)

    @classmethod
    def failure(
        cls,
        *,
        stage: str,
        code: str,
        message: str,
        retryable: bool,
        failed_call: FailedCall | None = None,
    ) -> "ToolResult":
        return cls(
            ok=False,
            tool_error=ToolError(stage, code, message, retryable),
            failed_call=failed_call,
        )
