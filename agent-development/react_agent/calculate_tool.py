



def calculate(expression: str) -> str:
    '''
    将公式转换为逆波兰表达式，用数字栈计算并返回结果字符串。
    支持非负整数输入、括号和二元四则运算，中间结果可以是负数或小数。
    '''
    print(f"✍ 正在执行计算工具，公式：{expression}")
    
    postfix = calculate_expression(expression)

    # 这里计算,按照逆波兰表达式计算,如果遇到数字则进栈,如果遇到操作符,先将数字出栈计算后再入栈
    stack = []
    for element in postfix:
        if element.isdigit():
            stack.append(int(element))
            continue

        if element not in ("+", "-", "*", "/"):
            raise ValueError(f"未知运算符：{element}")

        if len(stack) < 2:
            raise ValueError("公式错误：缺少操作数")

        # 先弹出右操作数，再弹出左操作数。
        right = stack.pop()
        left = stack.pop()

        if element == "+":
            value = left + right
        elif element == "-":
            value = left - right
        elif element == "*":
            value = left * right
        else:
            if right == 0:
                raise ValueError("除数不能为零")
            value = left / right

        stack.append(value)
    if len(stack) != 1:
        raise ValueError("公式错误：最终应只剩一个结果")

    return str(stack.pop())

def calculate_expression(expression: str):

    """
    将公式字符串分词后转换为逆波兰表达式列表。

    遇到数字时：
    直接添加到输出列表 output。

    遇到 +、-、*、/ 时：
        将当前运算符与栈顶运算符比较：
            - 如果栈为空，或者栈顶是左括号 (，停止比较。
            - 如果当前运算符优先级高于栈顶，停止比较。
            - 如果当前运算符优先级低于或等于栈顶，
            将栈顶运算符弹出到 output，继续比较新的栈顶。
        比较结束后，将当前运算符入栈。

    遇到左括号 ( 时：
        直接入栈，作为优先级比较的边界。
        括号内部的运算符仍按上述规则处理，不能越过左括号比较。

    遇到右括号 ) 时：
        将栈顶运算符逐个弹出到 output，直到栈顶是左括号 (。
        弹出并丢弃左括号，右括号也不入栈、不输出。
        如果找不到左括号，说明括号不匹配，报错。

    所有 token 遍历结束后：
        将栈中剩余的运算符逐个弹出到 output。
        如果仍有左括号，说明括号不匹配，报错。
    """
    tokens: list = tokenization_general(expression)
    # 输出列表
    output =[]
    # 操作符栈
    operators = []

    # 优先级表
    precedence = {
        "+":1,
        "-":1,
        "*":2,
        "/":2
    }

    for  token in tokens:
        # 如果是数字，那么直接进去输出列表中
        if token.isdigit():
            output.append(token)
        
        elif token == "(":
            operators.append(token)

        elif token == ")":
            while operators and operators[-1]!= "(":
                output.append(operators.pop())

            if not  operators:
                raise ValueError("括号不匹配")
            # 弹出并丢弃左括号，不添加到 output。
            operators.pop()
        # 如果操作符在 precedence 中    
        elif token in precedence:
            while operators and operators[-1] != "(" and precedence[operators[-1]] >= precedence[token]:
                output.append(operators.pop())
            
            operators.append(token)

        else:
            raise ValueError("无效的字符")
    
    while operators:
        token  = operators.pop()

        if token == "(":
            raise ValueError("括号不匹配：缺少右括号")
        output.append(token)
    
    return output

def tokenization_general(expression: str):
    """
    将表达式字符串拆分为数字、运算符和括号组成的 token 列表。
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



                



                
        
    

