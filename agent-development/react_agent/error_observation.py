"""将工具的结构化失败结果转换为模型可以使用的 Observation。"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from react_agent.common_result.tool_result import ToolError, ToolResult


class CorrectionAction(str, Enum):
    """模型在失败后可以采取的有限动作。"""
    # 修改模型输出
    FIX_MODEL_OUTPUT = "FIX_MODEL_OUTPUT"
    # 选择其他工具
    SELECT_ANOTHER_TOOL = "SELECT_ANOTHER_TOOL"
    # 修改参数后重试
    RETRY_WITH_NEW_ARGUMENTS = "RETRY_WITH_NEW_ARGUMENTS"
    # 稍后重试
    RETRY_LATER = "RETRY_LATER"
    # 询问用户
    ASK_USER = "ASK_USER"
    # 停止调用
    STOP = "STOP"


@dataclass(frozen=True)
class Correction:
    """告诉模型下一步应采取的动作和限制。"""

    action: CorrectionAction
    instruction: str
    constraints: tuple[str, ...] = ()


def build_correction(error: ToolError) -> Correction:
    """根据稳定的错误码构造纠错策略。"""
    if not error.retryable:
        return Correction(
            action=CorrectionAction.STOP,
            instruction="当前错误不允许重试，请停止调用并向用户说明限制。",
            constraints=("不要重复失败调用",),
        )

    strategies = {
        "INVALID_MODEL_OUTPUT": Correction(
            action=CorrectionAction.FIX_MODEL_OUTPUT,
            instruction="请按照系统约定重新输出合法的 JSON 对象。",
            constraints=("JSON 之外不要输出其他文字",),
        ),
        "TOOL_NOT_FOUND": Correction(
            action=CorrectionAction.SELECT_ANOTHER_TOOL,
            instruction="请从当前可用工具中重新选择。",
            constraints=("不要再次选择不存在的工具",),
        ),
        "TOOL_NOT_APPLICABLE": Correction(
            action=CorrectionAction.SELECT_ANOTHER_TOOL,
            instruction="当前工具不适合用户目标，请重新选择更匹配的工具。",
            constraints=("选择前重新检查用户目标和工具用途",),
        ),
        "INVALID_ARGUMENT": Correction(
            action=CorrectionAction.RETRY_WITH_NEW_ARGUMENTS,
            instruction="请根据错误信息和工具参数说明修改参数后重试。",
            constraints=("不要原样重复失败参数",),
        ),
        "EXECUTION_FAILED": Correction(
            action=CorrectionAction.RETRY_LATER,
            instruction="请检查错误原因；若属于临时性故障，可在重试限制内再试一次。",
            constraints=("不要无限重试",),
        ),
    }

    return strategies.get(
        error.code,
        Correction(
            action=CorrectionAction.STOP,
            instruction="无法确定安全的纠错方式，请停止当前调用并说明失败原因。",
            constraints=("不要原样重复失败调用",),
        ),
    )


def build_error_observation(result: ToolResult) -> dict[str, Any]:
    """将失败 ToolResult 组装为必定包含 correction 的 Observation。"""
    if result.ok:
        raise ValueError("成功的 ToolResult 不能转换为错误 Observation")

    if result.tool_error is None:
        raise ValueError("失败的 ToolResult 必须包含 tool_error")

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

    if result.failed_call is not None:
        observation["failed_call"] = asdict(result.failed_call)

    return observation
