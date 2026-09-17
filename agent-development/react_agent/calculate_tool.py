import ast
from readline import write_history_file

def calculate(formula:str):
    '''
    这是一个计算工具，通过传入公式字符串，转译成计算机使用的表达式，最后返回计算结果。
    '''
    print(f"✍ 正在执行计算工具，公式：{formula}")
    pass

def tokenization_general(expression: str):
    """
    这是一个将字符串提取成计算公式列表
    """
    expression = expression.replace("×","*").replace("÷","/")
    tokens = []
    i = 0

    while i < len(expression):
        
        ch = expression[i]

        # 如果是空格，则跳过
        if  ch.isspace():
            i += 1
        
        # 如果是数字，则继续向后取
        elif ch >= '0' and ch <= '9':
            start = i
            # 继续向后取，直到遇到不是数字的字符
            while  i < len(expression) and expression[i] >= '0' and expression[i] <= '9':
                i += 1
            
            tokens.append(expression[start:i])

        # 如果是操作符，就添加到列表中
        elif ch in "()+-*/":
            tokens.append(ch)
            i += 1
        
        else :
            raise ValueError("无效的字符")
    return tokens


def calculate_expression(tokens: list):
    """
    将列表转成逆波兰表达式
    """
    

