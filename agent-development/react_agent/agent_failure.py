"""创建 Agent 循环自身产生的失败结果。"""

from .common_result.tool_result import FailedCall, ToolResult

# 模型过程中出现json解析错误，值异常
def invalid_model_output(error: Exception) -> ToolResult:
    return ToolResult.failure(
        stage="model_output",
        code="INVALID_MODEL_OUTPUT",
        message=str(error),
        retryable=True,
    )

# 连接失败次数太多失败
def too_many_failures(
    limit: int,
    failed_call: FailedCall | None,
) -> ToolResult:
    return ToolResult.failure(
        stage="agent_loop",
        code="TOO_MANY_FAILURES",
        message=f"连续失败已达 {limit} 次，停止执行",
        retryable=False,
        failed_call=failed_call,
    )

# 达到最大步数，仍未获得最终答案
def max_steps_exceeded(failed_call: FailedCall | None) -> ToolResult:
    return ToolResult.failure(
        stage="agent_loop",
        code="MAX_STEPS_EXCEEDED",
        message="达到最大步数，仍未获得最终答案",
        retryable=False,
        failed_call=failed_call,
    )
