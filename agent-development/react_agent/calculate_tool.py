"""不使用 eval 的四则运算工具。"""

OPERATORS = {"+": 1, "-": 1, "*": 2, "/": 2}


def calculate(expression: str) -> str:
    """把表达式转换为后缀形式后求值。"""
    print(f"正在执行计算工具，公式：{expression}")
    stack: list[int | float] = []

    for token in calculate_expression(expression):
        if token.isdigit():
            stack.append(int(token))
            continue

        if len(stack) < 2:
            raise ValueError("公式错误：缺少操作数")

        right = stack.pop()
        left = stack.pop()
        stack.append(_apply_operator(left, right, token))

    if len(stack) != 1:
        raise ValueError("公式错误：最终应只剩一个结果")
    return str(stack[0])


def _apply_operator(left: int | float, right: int | float, operator: str):
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        if right == 0:
            raise ValueError("除数不能为零")
        return left / right
    raise ValueError(f"未知运算符：{operator}")


def calculate_expression(expression: str) -> list[str]:
    """使用调度场算法，将中缀表达式转换成后缀表达式。"""
    output: list[str] = []
    operators: list[str] = []

    for token in tokenization_general(expression):
        if token.isdigit():
            output.append(token)
        elif token == "(":
            operators.append(token)
        elif token == ")":
            _close_parenthesis(operators, output)
        else:
            while (
                operators
                and operators[-1] != "("
                and OPERATORS[operators[-1]] >= OPERATORS[token]
            ):
                output.append(operators.pop())
            operators.append(token)

    while operators:
        operator = operators.pop()
        if operator == "(":
            raise ValueError("括号不匹配：缺少右括号")
        output.append(operator)
    return output


def _close_parenthesis(operators: list[str], output: list[str]) -> None:
    while operators and operators[-1] != "(":
        output.append(operators.pop())
    if not operators:
        raise ValueError("括号不匹配：缺少左括号")
    operators.pop()


def tokenization_general(expression: str) -> list[str]:
    """拆分数字、运算符和括号，并拒绝其他字符。"""
    expression = expression.replace("×", "*").replace("÷", "/")
    tokens: list[str] = []
    index = 0

    while index < len(expression):
        character = expression[index]

        if character.isspace():
            index += 1
            continue

        if character.isdigit():
            start = index
            while index < len(expression) and expression[index].isdigit():
                index += 1
            tokens.append(expression[start:index])
            continue

        if character in "()+-*/":
            tokens.append(character)
            index += 1
            continue

        raise ValueError(f"无效字符：{character}")

    return tokens
