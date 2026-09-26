
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class FailedCall:
    tool_name : str
    tool_input : Any

@dataclass(frozen=True)
class ToolError:
    stage : str
    code : str
    message : str
    retryable : bool

# (frozen=True) 这个为了防止第一次创建为OK的时候，没有tool_error和failed_call校验通过后
# 假如修改了OK值后，不再校验的情况
@dataclass(frozen=True)
class ToolResult:
    '''
    工具调用的统一返回结果。
    使用约束：
    1.成功结果：
     - ok 必须为 True
     - data 可以是任意数据或 None
     - tool_error 必须为 None
     - failed_call 必须为 None
    
    2.失败结果：
     - ok 必须为 False
     - data 必须为 None
     - tool_error 必须存在
     - failed_call 在能够解析出工具调用的存在，在模型输出无法解析时可以为 None
    '''
    ok: bool
    tool_error : Optional[ToolError] = None
    failed_call : Optional[FailedCall] = None
    data : Any  = None


    def __post_init__(self):
        # 说明返回成功
        if self.ok :
            if self.tool_error is not None:
                raise ValueError("成功结果里不能包含 tool_error ")
            
            if self.failed_call is not None:
                raise ValueError("成功结果里不能包含 failed_call ")
        
        # 说明返回失败
        else :
            if self.tool_error is None :
                raise ValueError("失败结果里必须包含 tool_error")

            if self.data is not None:
                raise ValueError("失败结果里不能包含 data")

