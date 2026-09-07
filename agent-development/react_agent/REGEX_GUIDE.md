# ReAct Agent 中的 Python 正则表达式

本文记录本项目解析大语言模型输出时使用的 Python 正则表达式，重点说明捕获组、`group()`、贪婪与非贪婪匹配、先行断言，以及它们在解析 `Thought` 和 `Action` 时的作用。

## 1. 正则表达式的作用

ReAct Agent 会要求大语言模型按照约定格式输出：

```text
Thought: 我需要查询最新的天气信息。
Action: Search[北京天气]
```

模型返回的是普通字符串。程序需要从字符串中提取：

```text
思考内容：我需要查询最新的天气信息。
行动名称：Search
行动参数：北京天气
```

正则表达式的作用，就是按照指定规则匹配并提取这些文本。

## 2. 常用正则符号

| 符号 | 含义 | 示例 |
|---|---|---|
| `.` | 任意一个字符，默认不包括换行 | `a.c` |
| `*` | 前面的规则出现零次或多次 | `a*` |
| `+` | 前面的规则出现一次或多次 | `a+` |
| `?` | 前面的规则出现零次或一次；放在量词后还可表示非贪婪 | `a?`、`.*?` |
| `\d` | 一个数字 | `\d+` |
| `\w` | 一个字母、数字或下划线等单词字符 | `\w+` |
| `\s` | 一个空白字符，包括空格、制表符和换行 | `\s*` |
| `[...]` | 匹配集合中的一个字符 | `[abc]` |
| `^` | 字符串开头；开启多行模式后也可表示行开头 | `^Action` |
| `$` | 字符串结尾；开启多行模式后也可表示行结尾 | `答案$` |
| `(...)` | 分组并捕获匹配内容 | `(\w+)` |
| `(?:...)` | 分组但不捕获 | `(?:Search|Finish)` |
| `|` | 或 | `Search|Finish` |
| `(?=...)` | 正向先行断言，只检查后方内容但不消耗字符 | `(?=\nAction:|$)` |

建议把正则从左到右拆开理解，不要一次记忆完整表达式。

## 3. Python 原始字符串

Python 中通常使用 `r"..."` 保存正则：

```python
pattern = r"Action:\s*(\w+)\[(.*?)\]"
```

字符串前面的 `r` 表示原始字符串，使反斜杠尽量按原样交给正则引擎。

如果不使用 `r`，通常需要写更多反斜杠：

```python
pattern = "Action:\\s*(\\w+)\\[(.*?)\\]"
```

这也是 Python 正则看起来与 Java 不太一样的主要原因。Java 字符串同样需要处理转义，通常写成：

```java
"Action:\\s*(\\w+)\\[(.*?)\\]"
```

普通捕获组 `(...)`、量词和字符规则在 Python 与 Java 中基本一致。

## 4. 捕获组与 `group()`

普通小括号表示捕获组：

```regex
(...)
```

例如：

```python
import re

text = "Action: Search[北京天气]"
pattern = r"Action:\s*(\w+)\[(.*?)\]"
match = re.search(pattern, text)

if match:
    print(match.group(0))
    print(match.group(1))
    print(match.group(2))
    print(match.groups())
```

输出：

```text
Action: Search[北京天气]
Search
北京天气
('Search', '北京天气')
```

对应关系是：

```text
Action:\s*  (\w+)  \[  (.*?)  \]
              组1         组2
```

- `group(0)`：整个正则表达式匹配到的完整内容。
- `group(1)`：第一个捕获组 `(...)` 捕获的内容。
- `group(2)`：第二个捕获组 `(...)` 捕获的内容。
- `groups()`：由所有捕获组组成的元组，不包含 `group(0)`。

因此，`group(1)` 更准确的含义是“第一个捕获组的内容”，而不是笼统的“第一次匹配结果”。

## 5. 解析 Action

使用的表达式是：

```regex
Action:\s*(\w+)\[(.*?)\]
```

目标文本：

```text
Action: Search[北京天气]
```

逐段匹配：

| 正则部分 | 含义 | 匹配内容 |
|---|---|---|
| `Action:` | 固定文本 | `Action:` |
| `\s*` | 零个或多个空白字符 | `Action:` 后的空格 |
| `(\w+)` | 捕获一个或多个单词字符 | `Search` |
| `\[` | 匹配普通左方括号 | `[` |
| `(.*?)` | 非贪婪捕获任意数量的字符 | `北京天气` |
| `\]` | 匹配普通右方括号 | `]` |

其中，匹配 `[北京天气]` 的规则是：

```regex
\[(.*?)\]
```

可以对齐理解：

```text
正则：\[  (.*?)  \]
文本： [  北京天气  ]
```

- `\[` 匹配字符 `[`；
- `(.*?)` 捕获中间的“北京天气”；
- `\]` 匹配字符 `]`。

`[` 和 `]` 在正则中具有特殊含义，所以匹配普通方括号时需要写成 `\[` 和 `\]`。

## 6. 贪婪与非贪婪匹配

`.*` 是贪婪匹配，表示在满足后续规则的前提下尽可能多地匹配。

`.*?` 是非贪婪匹配，表示在满足后续规则的前提下尽可能少地匹配。

例如：

```text
[北京天气][上海天气]
```

使用：

```regex
\[(.*)\]
```

捕获结果可能是：

```text
北京天气][上海天气
```

因为 `.*` 会尽量延伸到最后一个 `]`。

使用：

```regex
\[(.*?)\]
```

第一次匹配捕获的是：

```text
北京天气
```

因为 `.*?` 遇到第一个能够满足后续 `\]` 的位置就会停止。

## 7. 解析 Thought

使用的表达式是：

```regex
Thought:\s*(.*?)(?=\r?\nAction:|$)
```

目标文本：

```text
Thought: 我需要查询最新信息。
Action: Search[北京天气]
```

逐段匹配：

| 正则部分 | 含义 |
|---|---|
| `Thought:` | 匹配固定文本 `Thought:` |
| `\s*` | 跳过后面的零个或多个空白字符 |
| `(.*?)` | 非贪婪捕获 Thought 内容 |
| `(?=...)` | 检查结束位置，但不把结束标记包含进结果 |
| `\r?\nAction:` | 后面是 Windows 或 Linux 换行以及 `Action:` |
| `|` | 或者 |
| `$` | 已到达整个字符串结尾 |

### `$` 的作用

`$` 表示字符串结束位置，它不匹配某个具体字符。

加入 `$` 后，下面这种没有 `Action:` 的内容也可以被解析：

```text
Thought: 当前信息不足，无法继续处理
```

此时 `(.*?)` 捕获到字符串结尾：

```text
当前信息不足，无法继续处理
```

如果没有 `$`，正则必须在后面找到 `Action:` 才能成功。

### `(?=...)` 的作用

`(?=...)` 是正向先行断言。它只检查当前位置后面是否符合规则，但不消耗这些字符。

```regex
(?=\r?\nAction:|$)
```

表示 Thought 必须结束在以下位置之一：

1. 下一行 `Action:` 之前；
2. 整个字符串结尾。

因为先行断言不消耗字符，所以 `Action:` 不会进入 Thought 的捕获结果，后续仍可单独解析 Action。

## 8. `re.DOTALL` 和 `re.MULTILINE`

默认情况下，`.` 不匹配换行符。如果 Thought 可能包含多行，需要启用 `re.DOTALL`：

```python
thought_match = re.search(
    r"Thought:\s*(.*?)(?=\r?\nAction:|$)",
    response,
    re.DOTALL,
)
```

`re.DOTALL` 使 `.` 也能匹配换行。

`re.MULTILINE` 会改变 `^` 和 `$` 的含义，使它们也能匹配每一行的开头和结尾。本项目的表达式通常只需要 `re.DOTALL`，不要随意加入 `re.MULTILINE`，否则 `$` 可能在某一行末尾提前成立。

## 9. 推荐的解析函数

使用命名捕获组比 `group(1)`、`group(2)` 更容易阅读：

```python
import re
from typing import Optional


ACTION_PATTERN = re.compile(
    r"Action:\s*"
    r"(?P<action_name>\w+)"
    r"\["
    r"(?P<action_input>.*?)"
    r"\]",
    re.DOTALL,
)


def parse_action(response: str) -> Optional[tuple[str, str]]:
    match = ACTION_PATTERN.search(response)

    if match is None:
        return None

    action_name = match.group("action_name").strip()
    action_input = match.group("action_input").strip()

    return action_name, action_input
```

命名捕获组的格式是：

```regex
(?P<名称>...)
```

因此可以通过名称读取内容：

```python
match.group("action_name")
match.group("action_input")
```

## 10. 快速记忆

```text
(...)            分组并捕获
(?:...)          分组但不捕获
(?P<name>...)    Python 命名捕获组
group(0)         整个匹配结果
group(n)         第 n 个捕获组
.*               贪婪匹配任意内容
.*?              非贪婪匹配任意内容
(?=...)          检查后面的内容，但不消耗它
$                字符串结束位置
```

对于当前 ReAct Agent，优先记住下面两个表达式即可：

```python
action_pattern = r"Action:\s*(\w+)\[(.*?)\]"
thought_pattern = r"Thought:\s*(.*?)(?=\r?\nAction:|$)"
```

