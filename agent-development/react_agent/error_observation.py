"""把 ToolError 转换为模型可执行的纠错 Observation。"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .common_result.tool_result import ToolError, ToolResult


class CorrectionAction(str, Enum):
    FIX_MODEL_OUTPUT = "FIX_MODEL_OUTPUT"
    SELECT_ANOTHER_TOOL = "SELECT_ANOTHER_TOOL"
    RETRY_WITH_NEW_ARGUMENTS = "RETRY_WITH_NEW_ARGUMENTS"
    RETRY_LATER = "RETRY_LATER"
    STOP = "STOP"


@dataclass(frozen=True)
class Correction:
    action: CorrectionAction
    instruction: str
    constraints: tuple[str, ...] = ()


STRATEGIES = {
    "INVALID_MODEL_OUTPUT": Correction(
        CorrectionAction.FIX_MODEL_OUTPUT,
        "请按照系统约定重新输出合法的 JSON 对象。",
        ("JSON 之外不要输出其他文字",),
    ),
    "TOOL_NOT_FOUND": Correction(
        CorrectionAction.SELECT_ANOTHER_TOOL,
        "请从当前可用工具中重新选择。",
        ("不要再次选择不存在的工具",),
    ),
    "INVALID_ARGUMENT": Correction(
        CorrectionAction.RETRY_WITH_NEW_ARGUMENTS,
        "请根据错误信息和工具说明修改参数。",
        ("不要原样重复失败参数",),
    ),
    "EXECUTION_FAILED": Correction(
        CorrectionAction.RETRY_LATER,
        "如果是临时故障，可以在限制内再试一次。",
        ("不要无限重试",),
    ),
}

STOP = Correction(
    CorrectionAction.STOP,
    "当前错误不允许安全重试，请停止调用并说明限制。",
    ("不要重复失败调用",),
)


def build_correction(error: ToolError) -> Correction:
    if not error.retryable:
        return STOP
    return STRATEGIES.get(error.code, STOP)


def build_error_observation(result: ToolResult) -> dict[str, Any]:
    if result.ok or result.tool_error is None:
        raise ValueError("这里只能处理包含 tool_error 的失败结果")

    correction = build_correction(result.tool_error)
    observation: dict[str, Any] = {
        "ok": False,
        "error": asdict(result.tool_error),
        "correction": {
            "action": correction.action.value,
            "instruction": correction.instruction,
            "constraints": list(correction.constraints),
        },
    }
    if result.failed_call:
        observation["failed_call"] = asdict(result.failed_call)
    return observation
