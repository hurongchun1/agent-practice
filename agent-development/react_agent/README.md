# ReAct Agent：原理与当前实现

本目录用于从零理解并实现 ReAct Agent。ReAct 是 **Reasoning + Acting** 的缩写：它让大语言模型在解决问题时，不只进行推理，也可以调用搜索、计算器或业务 API 等外部工具，并根据工具返回的结果继续调整判断。

项目中用于解析 `Thought` 和 `Action` 的正则表达式说明，参见 [REGEX_GUIDE.md](./REGEX_GUIDE.md)。

> 当前目录已经实现了“工具定义、注册与执行”这一部分，尚未实现完整的 LLM 调用、Action 解析和多轮循环。本文会同时说明完整的 ReAct 原理，以及现有代码在整个流程中的位置。

## 0. 从整体上理解 ReAct

可以把 ReAct Agent 理解成一个**通过工具感知和影响外部环境，并根据环境反馈不断调整下一步行动的智能体**。它的实现主线可以概括为：

1. **确定工具**：先根据智能体要解决的问题，定义搜索、计算、数据库查询或业务 API 等工具。每个工具都要有明确的名称、功能描述、输入参数和执行函数。
2. **注册和调度工具**：当工具较多时，使用统一的工具执行器维护工具清单。它既能把“有哪些工具、每个工具能做什么”整理给模型，也能根据模型生成的 Action 找到并执行对应函数。
3. **编写提示词**：在提示词中定义智能体的角色、目标、可用工具、输出格式和每一轮应遵循的执行规则。
4. **保存上下文**：保留用户原始问题以及此前的 Action、Observation 等执行历史，让模型在下一轮能够基于已有结果重新判断。
5. **循环执行**：模型产生 Thought 和 Action，程序调度工具得到 Observation，再把 Observation 放回上下文；如此循环，直到模型输出 Finish 或达到最大执行步数。

需要特别区分“决策”和“调度”：

- **LLM 是决策者**：根据问题、提示词和历史记录决定是否调用工具、调用哪个工具以及传入什么参数。
- **工具执行器是调度者**：保存工具元数据，并将已经确定的工具名称映射到具体函数。它通常不负责推理，也不会自主决定下一步使用什么工具。

因此，完整结构不是简单地“模型调用工具”，而是以下几个组件共同构成的反馈系统：

```text
工具集合 ──注册──> 工具执行器 ──工具说明──┐
                                        │
用户问题 ────────────────────────────────┤
历史记录 ────────────────────────────────┤
                                        ▼
                                提示词 + LLM（决策）
                                        │
                                      Action
                                        │
                                        ▼
                                工具执行器（调度）
                                        │
                                   Observation
                                        │
                                        └──写入历史，进入下一轮
```

## 1. 为什么需要 ReAct

只依赖大语言模型通常存在两个问题：

- **纯推理无法访问外部世界**：模型可以分析问题，但不知道训练数据之后发生的新闻、价格或产品信息，也不能真正操作数据库和业务系统。
- **直接行动缺少反馈与纠错**：如果模型一次性决定并执行动作，就很难根据执行结果修正搜索词、切换工具或调整后续步骤。

ReAct 将推理和行动放进同一个反馈循环中：推理负责决定下一步做什么，工具负责与环境交互，工具结果再成为下一轮推理的依据。因此，它适合需要实时知识、精确计算或外部 API 的任务。

## 2. 核心循环

一次典型的 ReAct 轨迹由以下几个部分组成：

1. **Question（问题）**：用户希望智能体完成的任务。
2. **Thought（思考）**：模型分析当前已知信息，并决定是否需要使用工具。
3. **Action（行动）**：模型选择一个工具及其输入，例如 `Search[英伟达最新的 GPU 型号]`。
4. **Observation（观察）**：程序执行工具，将结果返回给模型。
5. **Finish（结束）**：模型判断信息已经足够，输出最终答案。

流程可以表示为：

```text
用户问题
   │
   ▼
Thought：分析问题和已有观察
   │
   ▼
Action：选择工具并给出参数 ──────┐
   │                            │
   ▼                            │
执行工具                         │
   │                            │
   ▼                            │
Observation：取得外部结果         │
   │                            │
   ├── 信息不足：写入历史并继续 ───┘
   │
   └── 信息充分：Finish[最终答案]
```

若用形式化方式描述，在第 `t` 轮中，模型会根据用户问题 `q` 和之前的行动、观察历史生成本轮思考与行动：

```text
(thought_t, action_t) = LLM(q, (action_1, observation_1), ..., (action_t-1, observation_t-1))
observation_t = Tool(action_t)
```

关键点是：`Observation` 必须追加到上下文中。否则模型看不到工具执行结果，也就无法形成闭环。

## 3. 一个简单示例

用户提问：`英伟达最新的 GPU 型号是什么？`

```text
Thought: 这是一个具有时效性的问题，需要查询最新网页信息。
Action: Search[英伟达最新的 GPU 型号是什么]

Observation: 搜索工具返回若干搜索摘要……

Thought: 已获得相关信息，但需要确认发布时间和产品定位。
Action: Search[英伟达官网 最新 GPU 发布时间 产品定位]

Observation: 搜索工具返回官网或新闻摘要……

Thought: 信息已经足够，可以整理答案。
Action: Finish[根据搜索结果生成的最终答案]
```

这个例子展示了 ReAct 与“一次搜索后立即回答”的区别：模型可以根据第一次观察决定继续核实，而不是被固定计划束缚。

## 4. 本目录的代码结构

```text
react-agent/
├── README.md          # 原理、代码结构与后续实现说明
├── search_tool.py     # 基于 SerpApi 的网页搜索工具
├── tool-executor.py   # 工具注册、描述和查找
├── realize-agent.md   # 预留的实现记录文件
└── .env               # 本地环境变量，不应提交密钥
```

### `search_tool.py`

`search(query)` 是智能体目前可使用的外部工具。它负责：

- 从环境变量读取 `SERPAPI_API_KEY`；
- 通过 SerpApi 请求 Google 搜索结果；
- 优先返回直接答案、知识图谱描述；
- 没有直接答案时，返回前三条自然搜索结果的标题与摘要；
- 将缺少密钥、无结果或调用异常转换成文本结果。

在 ReAct 流程中，该函数产生的返回值就是 `Observation`。

### `tool-executor.py`

`ToolExecutor` 是工具注册表，负责将工具名称、用途说明和 Python 函数关联起来：

- `registerTool(...)`：注册工具；
- `getTool(...)`：根据 Action 中的工具名获取函数；
- `getAvailableTools()`：生成工具说明，供提示词告知模型“有哪些工具可用”。

当前示例注册了 `Search` 工具，并演示了从 Action 到 Observation 的执行过程。这个模块相当于 ReAct 中模型与外部环境之间的适配层。

## 5. 完整 ReAct Agent 还需要什么

要从当前工具层扩展为完整智能体，还需要补齐以下组件：

### 5.1 提示词协议

提示词应包含工具列表、用户问题、历史轨迹和严格的输出格式。例如：

```text
可用工具：
{tools}

请按以下格式输出：
Thought: 对当前问题的分析
Action: ToolName[tool input]

当信息足够时输出：
Thought: 已经可以回答问题
Action: Finish[final answer]

Question: {question}
History: {history}
```

工具描述非常重要：模型主要依靠名称和描述判断何时调用哪个工具。

### 5.2 Action 解析器

程序需要把模型输出解析为结构化数据，例如：

```text
Search[查询内容]  -> tool_name = "Search", tool_input = "查询内容"
Finish[最终答案]  -> 结束循环并返回答案
```

教学实现可以使用正则表达式；生产环境更适合使用模型的结构化输出或 Function Calling，并对工具名、参数类型和必填字段进行校验。

### 5.3 Agent 主循环

主循环需要依次完成：

1. 将问题、工具说明和历史记录填入提示词；
2. 调用 LLM；
3. 解析 `Action`；
4. 若为工具调用，通过 `ToolExecutor` 执行；
5. 将 `Action` 和 `Observation` 写入历史；
6. 若为 `Finish`，返回最终答案；
7. 达到最大步数仍未完成时，安全终止。

伪代码如下：

```python
history = []

for _ in range(max_steps):
    response = llm(build_prompt(question, tools, history))
    action = parse_action(response)

    if action.name == "Finish":
        return action.input

    tool = tool_executor.getTool(action.name)
    observation = tool(action.input)
    history.extend([
        f"Action: {action.raw}",
        f"Observation: {observation}",
    ])

return "达到最大执行步数，任务未完成。"
```

## 6. 优势与局限

### 优势

- **能够使用外部知识和能力**：弥补模型知识过期、计算不精确和无法操作系统等不足。
- **动态规划**：每一步都能依据最新 Observation 调整下一步，而不是机械执行预先生成的完整计划。
- **便于调试**：可以从 Action、Observation 和状态历史中定位选错工具、参数错误或结果不足等问题。
- **易于扩展**：向工具注册表增加计算器、数据库或业务 API 后，主循环通常无需大幅修改。

### 局限

- **可能陷入循环**：模型会反复使用相同或相似的搜索词，因此必须设置 `max_steps`。
- **格式不稳定**：自由文本输出可能不符合 `Thought/Action` 协议，需要校验、重试或结构化输出。
- **工具结果并不天然可信**：网页摘要可能过时或错误，关键事实应使用可靠来源交叉验证。
- **成本和延迟较高**：每轮推理和工具调用都会增加耗时与费用。
- **存在安全风险**：工具调用可能带来提示注入、敏感信息泄露或破坏性操作，不能直接执行未经验证的参数。

## 7. 工程化注意事项

- 为循环设置最大步数、超时、重试次数和整体预算。
- 对工具名及输入参数做白名单和类型校验；高风险操作增加人工确认。
- 限制 Observation 的长度，并区分可信数据与网页中的非可信指令。
- 日志优先记录步骤编号、Action、Observation 摘要、耗时和错误。不要在面向最终用户的界面暴露模型的私密推理文本。
- 对搜索类答案保留来源链接，并对时效性或高风险信息进行交叉验证。
- API 密钥只通过环境变量读取，不写进代码、日志或版本库。
- 对同一问题多次运行可能得到不同轨迹，测试时应覆盖成功、无结果、工具异常、非法 Action 和超过最大步数等情况。

## 8. 运行当前工具示例

安装依赖后，在 `.env` 中配置 SerpApi 密钥：

```dotenv
SERPAPI_API_KEY=your_api_key
```

然后在本目录执行：

```bash
python tool-executor.py
```

该命令只验证工具注册和一次搜索调用，并不会启动完整的 ReAct 循环。

## 9. 参考资料

- [Datawhale Hello-Agents：第四章 智能体经典范式构建（ReAct）](https://hello-agents.datawhale.cc/#/./chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA?id=_421-react-%E7%9A%84%E5%B7%A5%E4%BD%9C%E6%B5%81%E7%A8%8B)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
