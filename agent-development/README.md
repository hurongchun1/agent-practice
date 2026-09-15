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

## 10. 第四章习题与答案

### 习题 1：三种范式如何组织“思考”与“行动”？

**题目：**本章介绍了三种经典的智能体范式：`ReAct`、`Plan-and-Solve` 和 `Reflection`。这三种范式在“思考”与“行动”的组织方式上有什么本质区别？

**答案：**三者的区别主要在于思考和行动的先后关系，以及何时利用反馈调整后续行为，而不是是否使用某一种工具。

1. **ReAct：思考与行动交替进行。**智能体根据当前问题和已有观察，只决定下一步行动；执行行动、获得外部反馈后，再思考下一步。其循环是 `Thought → Action → Observation → Thought → …`。因此，它的路线会随环境反馈动态变化，不要求预先制定完整计划。
2. **Plan-and-Solve：先整体规划，再逐步执行。**智能体先把问题拆解为有顺序的子任务，然后按计划逐步完成，并将前面步骤的结果传给后续步骤。其流程是 `Plan → Step 1 → Step 2 → … → Final Answer`。它强调全局结构，但如果初始计划有误且没有重新规划机制，执行也可能沿着错误路线继续。
3. **Reflection：先执行，再审查和改进已有结果。**智能体先产生初始结果，再分析其中的问题或可优化之处，根据反馈生成新版本，必要时重复这一过程。其循环是 `Execution → Reflection → Refinement → Reflection → …`。反思对象可以是代码、文章、答案或行动策略，不限于代码。

概括来说，**ReAct 是边想边做，根据每一步的观察调整行动；Plan-and-Solve 是先想好整体路线，再按步骤行动；Reflection 是做出结果后回顾并修正。**三者可以组合：先规划，在执行步骤时与环境交互，再对阶段性或最终结果进行反思。

### 习题 2：智能家居控制助手应选择哪种基础范式？

**题目：**如果要设计一个“智能家居控制助手”（需要控制灯光、空调、窗帘等多个设备，并根据用户习惯自动调节），你会选择哪种范式作为基础架构？为什么？

**答案：**选择 **ReAct 作为基础架构**，辅以用户习惯记录和 Reflection。智能家居环境会变化：助手要读取时间、室温、光照、设备状态和用户偏好，决定当前要调用哪个设备控制工具；工具执行后再观察设备状态与环境变化，据此决定是否继续调整。这符合 `Thought → Action → Observation` 的动态循环。

例如，用户说“我要睡觉了”，助手可以读取睡眠偏好和当前设备状态，依次调暗灯光、设置空调、关闭窗帘，并检查每个动作是否成功。Reflection 更适合在任务结束后结合**实际状态和用户反馈**复盘本次调节，改进之后的策略；它不能仅凭模型自评替代真实反馈，也不应让模型无约束地反复控制设备。Plan-and-Solve 可以用于“睡前模式”这类较固定的多设备流程，但环境适应与实时纠错仍应由 ReAct 承担。

**实现层面的补充：**模型不直接操作硬件。上层程序把 `get_device_status`、`turn_off_light`、`close_curtain` 等能力封装为工具；设备或网关接收控制指令后，由内部控制电路切换灯光或插座状态、驱动窗帘电机。传感器的数据先被设备或网关读取，再提供给上层程序。这里要区分“命令发送成功”和“设备实际完成动作”，后者需要读取设备状态或其他真实反馈。


### 习题 3：能否组合三种范式？如何设计混合架构？

**题目：**是否可以将这三种范式进行组合使用？若可以，请尝试设计一个混合范式的智能体架构，并说明其适用场景。

**答案：**可以。三种范式关注不同层次：Plan-and-Solve 负责全局规划，ReAct 负责执行时与环境动态交互，Reflection 负责审查阶段性或最终结果并改进策略。以代码开发智能体为例：

1. **Plan-and-Solve 制定可修订的计划。**理解用户需求和现有代码，拆解为检查模块、设计接口、实现功能、编写测试和验证结果等有依赖关系的步骤。
2. **ReAct 执行当前步骤。**读取文件、修改代码、运行检查，并根据新的工具结果决定下一步。测试失败时，先观察报错和相关代码，再决定如何修复，而不是机械执行原计划。
3. **Reflection 审查与优化。**在关键阶段完成或反复失败时，回顾实现、测试结果和原始目标，分析是否存在需求遗漏、错误假设或不合理设计；必要时修订计划，再实现并验证。

```text
用户需求
  → Plan-and-Solve：制定任务计划
  → ReAct：执行步骤、调用工具、观察结果
  → 外部验证：测试和检查实际结果
  → Reflection：复盘不足及失败原因
  → 修订计划或实现，必要时进入下一轮
  → 验证通过后交付
```

需要注意，**运行测试本身是外部验证，不等于 Reflection**；Reflection 是利用测试等证据进一步思考“为什么失败、原方案是否需要改变”。混合架构适合软件开发、复杂资料研究等既需要多步骤规划，又依赖外部反馈和质量审查的任务。智能家居也可组合三者，但实际设备控制必须另外设置权限与安全限制。

### 习题 4：ReAct 的正则解析为何脆弱？如何改用 JSON？

**题目：**在 4.2 节的 ReAct 实现中，我们使用正则表达式解析大语言模型输出的 `Thought` 和 `Action`。当前解析方法有哪些潜在脆弱性、在什么情况下会失败？除了正则还有哪些更鲁棒的方案？尝试使用一种更可靠的输出格式修改代码，并比较两种方案的优缺点。

**答案：**旧实现要求模型输出类似 `Thought: ...` 和 `Action: Search[查询词]` 的文本，再用正则提取字段。这在字段名、括号和排版都稳定时很简单；但模型可能改变字段大小写、添加说明、输出多个 Action，或把 `Search[参数]` 写成别的形式。更重要的是，工具名和参数被放在同一段文本中，参数一旦变复杂，就要增加切分、转义和类型校验规则。正则可以写得更能容忍空白，所以问题不只是“对换行或空格敏感”，而是**自由文本协议的结构容易变化**。

本目录已经尝试改为每轮输出一个 JSON 对象。`action` 只允许 `tool` 或 `finish`，`thought` 为共同必填字段；`tool` 要求 `tool_name`、`tool_input`，`finish` 要求具体的 `final_answer`。`react_agent.py` 用 `json.loads()` 将响应解析成字典，并根据 `action` 校验不同字段和执行对应分支。这取代了从 `Search[参数]` 中提取工具名的 `_parse_action()`。一次正常的 `tool → finish` 流程已验证能调用工具并返回答案；**无效 JSON 的有限重试或安全终止仍需完善**，因此不能把正常路径通过等同于整体健壮性已完成。

其他可选方案包括模型服务支持的结构化输出或工具调用机制。它们能更严格地约束输出形状，但取决于所用服务的能力。仅在提示词中要求 JSON，仍可能得到语法错误、漏字段或附加代码块的响应；`json.loads()` 后还必须检查类型、必填字段、`action` 的合法值和工具白名单。

| 方案 | 优点 | 局限 |
| --- | --- | --- |
| 正则解析文本协议 | 实现少、容易观察和调试；一工具一字符串参数时很合适 | 文本结构变化时易失败；多参数和可选字段需要自定义分隔、转义与校验 |
| 提示词要求 JSON + 解析和校验 | 字段相互独立，条件校验清晰；多参数、可选参数和嵌套数据更容易扩展 | 不能保证模型每次都输出合法 JSON；需要异常处理和字段校验 |
| 服务级结构化输出或工具调用 | 能在输出阶段更严格地约束结构 | 依赖模型服务支持情况，接入方式更复杂 |

**为什么说 JSON 在复杂场景下更灵活？**不是因为新增字段时不用改提示词和代码——两种方案都要同步修改。当前 `Search[华为最新手机]` 与 `{"action":"tool","tool_name":"Search","tool_input":"华为最新手机"}` 差别并不大。但如果搜索工具增加语言和返回条数，文本协议可能写成 `Search[华为最新手机|zh|3]`，程序还要按位置拆分、转换整数，并处理查询词中恰好含有 `|` 的情况。JSON 则可以表示为：

```json
{
  "action": "tool",
  "tool_name": "Search",
  "arguments": {
    "query": "华为最新手机",
    "language": "zh",
    "limit": 3
  }
}
```

此时字段按名称读取，顺序不重要，也不需要自行约定 `|` 的转义方式。**这只是说明可扩展性的设计示例，并非当前代码已支持 `arguments`。**总体上，简单、固定的文本任务中正则与 JSON 差距很小；随着参数和动作结构变复杂，JSON 的结构和校验优势才更明显。两者都必须处理模型违反输出约定的情况。

## 11. 参考资料

- [Datawhale《Hello Agents》第四章：智能体经典范式构建](https://hello-agents.datawhale.cc/#/./chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA)
- [Datawhale Hello Agents GitHub 仓库](https://github.com/datawhalechina/hello-agents)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)

本 README 是对教程思想与本目录代码的结合性总结。教程提供范式背景，本项目代码用于展示这些循环如何落实为提示词、状态、解析器、工具调度和终止条件。
