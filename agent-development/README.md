# 三种经典智能体范式：ReAct、Plan-and-Solve 与 Reflection

本目录参考 Datawhale《Hello Agents》第四章，用尽量少的代码实现三种经典智能体范式。它们并不是三种互斥的“智能体产品”，而是组织大语言模型推理过程的三种方法：

| 范式 | 核心循环 | 主要价值 | 适合的任务 |
| --- | --- | --- | --- |
| ReAct | 思考 → 行动 → 观察 → 再思考 | 借助外部工具获得新信息，并根据环境反馈动态纠错 | 搜索、API 调用、数据库查询、开放环境任务 |
| Plan-and-Solve | 规划 → 分步执行 → 汇总 | 先建立全局结构，减少复杂任务中的遗漏和混乱 | 数学题、报告、多步骤且路径较明确的任务 |
| Reflection | 初次执行 → 反思 → 优化 → 再反思 | 审查已有结果，从失败或不足中持续提高质量 | 代码优化、写作润色、对准确性和质量要求高的任务 |

三者关注的是不同层次：Plan-and-Solve 管理全局路线，ReAct 管理当前行动，Reflection 管理结果审计与策略改进。实际系统可以把它们组合起来，而不必只选择一种。

## 1. 项目结构

```text
agent-development/
├── original_agent/
│   ├── __init__.py
│   └── build_first_agent.py       # 公共 LLM 客户端 HelloAgentsLLM
├── react_agent/
│   ├── __init__.py
│   ├── run.py                     # ReAct 的统一运行入口
│   ├── react_agent.py             # ReAct 主循环
│   ├── system_prompt.py           # Thought/Action 提示词协议
│   ├── tool_executor.py           # 工具注册与调度
│   ├── search_tool.py             # Tavily 搜索工具
│   ├── README.md                  # ReAct 的详细说明
│   └── REGEX_GUIDE.md             # Thought/Action 正则解析说明
├── plan_and_solve/
│   ├── plan_and_solve_agent.py    # 组合 Planner 和 Executor
│   ├── plan_llm.py                # 生成并解析计划
│   ├── plan_prompt.py             # 规划提示词
│   ├── executor.py                # 按计划逐步执行
│   └── execution_template.py      # 执行提示词
├── reflection/
│   ├── __init__.py
│   ├── reflection_agent.py        # Reflection 主循环
│   ├── memory.py                  # 保存执行与反思记录
│   ├── init_prompt.py             # 首次生成提示词
│   ├── reflection_prompt.py       # 评审提示词
│   └── refinement_prompt.py       # 根据反馈优化的提示词
└── README.md
```

`original_agent/build_first_agent.py` 中的 `HelloAgentsLLM` 是三种智能体共享的模型客户端。它负责读取模型配置、调用兼容 OpenAI 接口的服务，并把流式响应拼接为完整字符串。智能体本身只依赖它的统一接口：

```python
response_text = llm_client.think(messages)
```

这种拆分让“如何调用模型”和“如何组织智能体循环”彼此独立。

## 2. 环境准备

建议使用 Python 3.10 或更高版本。在已经激活的虚拟环境中安装依赖：

```powershell
pip install openai python-dotenv tavily-python
```

在项目根目录或 `agent-development` 目录可被 `python-dotenv` 找到的位置创建 `.env`：

```dotenv
LLM_MODEL_ID=你的模型名称
LLM_API_KEY=你的模型服务密钥
LLM_BASE_URL=兼容OpenAI接口的服务地址

# 只有运行 ReAct 搜索示例时需要
TAVILY_API_KEY=你的Tavily密钥
```

如果使用项目中支持的 Qwen 配置分支，也可以设置：

```dotenv
LLM_PROVIDER=qwen
QWEN_MODEL_ID=你的模型名称
QWEN_API_KEY=你的密钥
QWEN_BASE_URL=服务地址
```

不要将真实密钥提交到版本库。

## 3. Python 包与运行方式

所有命令都建议在三个包的共同父目录 `agent-development` 中执行：

```powershell
cd D:\pythonProject\gitProject\agent-practice\agent-development
```

项目采用的绝对导入可以按照下面的格式理解：

```python
from 包名.文件名 import 类名或变量名
```

例如：

```python
from plan_and_solve.executor import Executor
from original_agent.build_first_agent import HelloAgentsLLM
```

同一个包内部也可以使用相对导入：

```python
from .executor import Executor
from .plan_llm import Planner
```

如果使用相对导入，应通过 `python -m 包名.模块名` 启动。不要进入某个子包后运行另一个兄弟包，也不要把包含相对导入的文件当作孤立脚本直接执行。

## 4. ReAct：在环境反馈中边想边做

### 4.1 核心思想

ReAct 是 Reasoning and Acting 的缩写。模型不会一次性给出完整答案，而是重复执行：

```text
Question
   ↓
Thought：分析当前信息
   ↓
Action：选择工具及参数
   ↓
Observation：获得工具结果
   ↓
写入历史，返回下一轮 Thought
```

当信息充分时，模型输出：

```text
Thought: 已获得足够信息。
Action: Finish[最终答案]
```

### 4.2 当前实现

`system_prompt.py` 定义模型必须遵循的 `Thought/Action` 输出协议，并注入：

- 用户问题 `question`；
- 可用工具说明 `tools`；
- 之前的行动和观察 `history`。

`ToolExecutor` 保存工具名称、描述和 Python 函数。LLM 是决策者，负责选择工具；`ToolExecutor` 是调度者，只负责找到并调用已经选定的函数。

`ReActAgent.run()` 完成主循环：

1. 生成包含问题、工具和历史的提示词；
2. 调用 LLM；
3. 用正则表达式解析 `Thought` 和 `Action`；
4. 遇到 `Finish[...]` 时返回最终答案；
5. 否则调用相应工具，得到 `Observation`；
6. 将行动与观察写入历史，再进入下一轮；
7. 超过 `max_steps` 时终止，防止无限循环。

当前注册的 `Search` 工具通过 Tavily 查询网页信息，因此 ReAct 特别适合回答具有时效性、模型自身知识无法覆盖的问题。

### 4.3 运行

```powershell
python -m react_agent.run
```

也可以直接运行包含示例入口的主循环模块：

```powershell
python -m react_agent.react_agent
```

### 4.4 优势与局限

优势：

- 能访问搜索、计算器、数据库或业务 API 等外部能力；
- 每一轮都能根据新观察调整下一步，环境适应性强；
- 行动和观察轨迹清晰，便于定位工具选择或参数问题。

局限：

- 可能反复调用相同工具，因此需要最大步数和预算限制；
- 自由文本格式可能不稳定，正则解析可能失败；
- 工具结果不一定可靠，关键事实仍需验证；
- 多轮模型与工具调用会增加延迟和成本。

## 5. Plan-and-Solve：先规划，再逐步解决

### 5.1 核心思想

Plan-and-Solve 把复杂任务拆成两个阶段：

```text
用户问题
   ↓
Planner：生成完整计划
   ↓
[步骤1, 步骤2, 步骤3, ...]
   ↓
Executor：按顺序执行，每一步读取此前结果
   ↓
最后一步结果
```

它强调先确定全局路线，再处理局部步骤。与 ReAct 的“走一步看一步”相比，这种方式对逻辑路径明确、多步骤依赖明显的任务更稳定。

### 5.2 Planner 如何生成计划

`plan_prompt.py` 要求模型把计划输出成 Python 列表代码块：

````text
```python
["步骤1", "步骤2", "步骤3"]
```
````

`Planner.plan()` 先截取代码块内容：

```python
plan_str = response_text.split("```python")[1].split("```")[0].strip()
```

这两次切分分别表示：

1. 以开始标记 `` ```python `` 切分，取 `[1]`，即开始标记之后；
2. 再以结束标记 `` ``` `` 切分，取 `[0]`，即结束标记之前；
3. 使用 `strip()` 删除首尾空白。

随后使用：

```python
plan = ast.literal_eval(plan_str)
```

`ast.literal_eval()` 不会像 `eval()` 那样执行任意 Python 代码。它只接受字符串、数字、列表、字典、元组、布尔值和 `None` 等字面量，然后将文本形式的列表转换为真正的 `list`。代码还通过 `isinstance(plan, list)` 确认结果类型。

这种解析方式适合教学，但依赖模型严格输出代码块。工程项目中可以优先要求模型返回 JSON，再用 `json.loads()` 解析，或者使用结构化输出。

### 5.3 Executor 如何执行计划

`Executor.execute()` 遍历计划。每一步都把以下信息放入提示词：

- 原始问题：防止偏离最终目标；
- 完整计划：说明当前步骤在全局中的位置；
- 历史步骤及结果：把前一步结果传递给后一步；
- 当前步骤：限制模型只解决眼前的子任务。

每一步的结果都会追加到 `history`。循环完成后，当前实现把最后一步的模型响应作为最终答案。

### 5.4 运行

```powershell
python -m plan_and_solve.plan_and_solve_agent
```

### 5.5 优势与局限

优势：

- 复杂任务结构清晰，不容易遗漏关键步骤；
- 后续步骤可以读取历史结果，适合有依赖关系的推理；
- 计划与执行职责分离，方便分别改进和测试。

局限：

- 初始计划如果错误，执行器可能严格执行一条错误路线；
- 当前实现不会在执行中自动重新规划；
- 计划代码块格式不符合约定时会解析失败；
- 把最后一步直接视为最终答案，要求规划器必须把“汇总答案”安排在最后。

## 6. Reflection：执行、审计与迭代优化

### 6.1 核心思想

Reflection 为智能体增加内部质量改进回路：

```text
初次执行
   ↓
记录结果
   ↓
反思：找出不足并给出改进建议
   ↓
优化：根据反馈生成新结果
   ↓
再次反思 ── 无需改进 → 返回最终结果
   │
   └──────── 仍需改进 → 继续优化
```

Reflection 不一定只出现在最终阶段。它既可以作为交付前的终局审计，也可以在失败、停滞或高风险节点触发。它是一种可以嵌入 ReAct 和 Plan-and-Solve 的横切能力。

### 6.2 当前实现

当前示例任务是生成并优化“查找 1 到 n 之间所有素数”的 Python 函数。

`ReflectionAgent.run()` 包含三个角色明确的提示词：

1. `INIT_PROMPT_TEMPLATE`：根据任务生成初始代码；
2. `REFLECTION_PROMPT_TEMPLATE`：扮演严格的代码评审员，重点分析算法效率并提出改进建议；
3. `REFINE_PROMPT_TEMPLATE`：根据上一版代码和评审反馈生成优化版本。

`Memory` 使用记录列表保存两类数据：

```python
{"type": "execution", "content": "本轮生成结果"}
{"type": "reflection", "content": "本轮评审反馈"}
```

`get_last_execution()` 从后向前查找最近一次执行结果，让下一轮反思始终审查最新版本。

循环遇到反馈包含“无需改进”时提前停止；否则最多执行 `max_iterations` 轮，防止过度反思或无限迭代。

### 6.3 运行

```powershell
python -m reflection.reflection_agent
```

### 6.4 优势与局限

优势：

- 能从已有结果中发现算法、结构或表达层面的不足；
- 将生成与评审角色分离，使改进目标更加明确；
- 记忆模块保留执行和反馈轨迹，便于连续优化；
- 可以嵌入其他智能体，形成阶段性或最终质量门。

局限：

- 模型对自己的批评也可能出错，内部反思不能替代测试和事实验证；
- 当前终止条件依赖“无需改进”这段自然语言，可能误判；
- 反复反思会增加成本，并可能把已经正确的结果改坏；
- 当前示例只生成代码文本，没有自动运行测试或测量性能。

## 7. 三种范式如何选择

| 任务特征 | 优先选择 | 原因 |
| --- | --- | --- |
| 需要最新信息或外部系统能力 | ReAct | 可以调用工具并依据观察动态调整 |
| 步骤较多，但路线相对明确 | Plan-and-Solve | 先拆解任务，再维护步骤间的状态传递 |
| 已有初稿，需要提高质量 | Reflection | 通过评审与优化循环改进结果 |
| 任务复杂、风险高且需要工具 | 组合使用 | 规划负责全局、ReAct 负责行动、Reflection 负责审计 |

一种组合式智能体可以这样工作：

```text
用户目标
   ↓
Plan：制定全局计划
   ↓
ReAct：执行当前步骤并获取外部反馈
   ↓
Reflection：在失败、高风险节点或交付前审计
   ↓
必要时修订计划或重新行动
   ↓
验证并交付
```

## 8. 从教学实现走向工程实现

本项目刻意保留了许多容易看懂的实现方式，例如字符串协议、正则表达式和内存列表。生产环境还应考虑：

- 使用 JSON Schema、Function Calling 或其他结构化输出代替脆弱的文本解析；
- 对工具名和参数进行白名单、类型及权限检查；
- 为模型调用和工具调用设置超时、重试、步数及费用预算；
- 使用测试、静态检查或真实执行结果约束 Reflection，而不是只相信模型自评；
- 为 Plan-and-Solve 增加执行失败后的重新规划能力；
- 限制工具返回内容长度，并防范网页内容中的提示注入；
- 记录必要的行动、观察、耗时和错误，但不要泄露密钥或敏感推理信息。

## 9. 常见问题

### `No module named 'plan_and_solve'`

通常是因为当前目录位于 `original_agent`、`plan_and_solve` 等子目录。请回到共同父目录：

```powershell
cd D:\pythonProject\gitProject\agent-practice\agent-development
python -m plan_and_solve.plan_and_solve_agent
```

### `No module named 'executor'`

通过 `-m` 运行包模块时，包内导入应写成相对导入：

```python
from .executor import Executor
```

或写成完整绝对导入：

```python
from plan_and_solve.executor import Executor
```

### `name 'ast' is not defined`

`ast` 是 Python 标准库，使用前需要：

```python
import ast
```

### 模型初始化时提示配置缺失

确认 `.env` 已配置 `LLM_MODEL_ID`、`LLM_API_KEY` 和 `LLM_BASE_URL`，并且运行位置能让 `load_dotenv()` 找到该文件。

## 10. 参考资料

- [Datawhale《Hello Agents》第四章：智能体经典范式构建](https://hello-agents.datawhale.cc/#/./chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA)
- [Datawhale Hello Agents GitHub 仓库](https://github.com/datawhalechina/hello-agents)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)

本 README 是对教程思想与本目录代码的结合性总结。教程提供范式背景，本项目代码用于展示这些循环如何落实为提示词、状态、解析器、工具调度和终止条件。
