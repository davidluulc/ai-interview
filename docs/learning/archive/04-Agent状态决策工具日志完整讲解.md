# 04 Agent 状态、决策、工具和日志完整讲解

## 1. Agent 和普通 LLM 调用有什么区别

普通 LLM 调用通常是：

```text
用户输入
-> 拼 prompt
-> 调模型
-> 返回结果
```

这种方式能聊天，但很难控制复杂流程。

Agent 更像一个“带状态和工具的流程调度器”：

```text
观察当前状态
-> 调用工具
-> 分析工具结果
-> 做下一步决策
-> 执行动作
-> 记录过程
-> 更新状态
```

在本项目里，Agent 的目标不是“自由聊天”，而是围绕模拟面试这个任务做流程控制：

- 用户答得好：继续深挖。
- 用户答不上来：降难度或切换到学习辅导。
- 题目重复：触发重复问题保护。
- RAG 命中差：减少对检索内容的依赖。
- 轮次结束：进入报告生成。

所以你可以把本项目的 Agent 理解为：

> 一个面试流程 Orchestrator，它会结合用户状态、历史回答、三类 RAG 结果和面试轮次，决定下一轮该怎么问。

## 2. 项目里的 Agent 主线

当前 Agent 主线大致是：

```text
前端提交回答
-> /api/interview/next-question
-> Agent Orchestrator 调用三类 RAG tool
-> 构造 Agent State
-> 调用 Agent 决策逻辑
-> normalize / fallback / guardrail
-> 生成下一道问题
-> 写入 Agent 决策日志
-> 返回前端
```

这里面最关键的几个文件：

- `backend_python/agent_state.py`
  - 管 Agent State。
  - 分析回答状态、弱回答连续次数、重复问题和 topic lock。

- `backend_python/agent_tools.py`
  - 管 Tool 调用。
  - 三个 RAG 都被包装成工具。

- `backend_python/agent_trace.py`
  - 管日志结构。
  - 负责生成 `nodeTrace` 和 `toolCalls`。

- `backend_python/agent_orchestrator.py`
  - 管流程编排。
  - 把 state、tools、decision 串起来。

- `backend_python/interview_agent.py`
  - 管决策。
  - 包括 LLM decision、fallback decision、normalize 和 guardrail。

## 3. Agent State 是什么

Agent State 是 Agent 做决策前看到的“当前局面”。

它不是数据库表，也不是前端页面状态，而是一份可以被序列化成 JSON 的工作记忆。

你可以把它理解成：

```text
Agent 的输入资料包
```

里面通常包含：

- 当前用户档案 profile。
- 历史问答 history。
- 上一轮回答 lastAnswer。
- 当前轮次 roundCount。
- 剩余轮次 remainingRounds。
- 当前模式 agentMode。
- 下一阶段 nextStage。
- 回答分析 answerAnalysis。
- 三类 RAG 质量 retrievalQuality。
- 工具调用 toolCalls。
- 节点轨迹 nodeTrace。

面试表达：

> Agent State 是我给 Agent 的结构化上下文。它不是简单 prompt 字符串，而是把候选人档案、历史问答、上一轮回答状态、RAG 检索质量、剩余轮次和 Agent 模式都结构化放进去，方便后续决策和日志记录。

## 4. answerAnalysis 是什么

`answerAnalysis` 用来描述用户上一轮回答的状态。

它解决的问题是：

```text
用户刚才到底答得怎么样？
```

当前项目会关注：

- `answerStatus`
  - `不会`、`模糊`、`完整`。

- `weakAnswerStreak`
  - 连续几轮答不上来。

- `repeatedQuestionCount`
  - 是否连续出现重复问题。

- `topicLock`
  - 是否一直卡在同一个话题上。

- `triggerSignals`
  - 触发了哪些规则，例如 `weak_answer_streak`。

面试表达：

> 我没有完全依赖大模型主观判断用户回答，而是先做一层规则化 answerAnalysis，比如识别连续答不上来、重复问题和 topic lock。这样 Agent 在做下一步决策时，不会一直机械地围绕同一个点追问。

## 5. ToolCalls 是什么

ToolCalls 是 Agent 调用工具的记录。

在本项目里，三个 RAG 都可以看作工具：

- 岗位知识库 RAG。
- 题库 RAG。
- 候选人画像 RAG。

每个工具调用会记录：

- `toolName`：工具名。
- `inputSummary`：输入摘要。
- `outputSummary`：输出摘要。
- `success`：是否成功。
- `error`：错误信息。
- `elapsedMs`：耗时。

示例：

```json
{
  "toolName": "retrieve_question_bank",
  "inputSummary": {
    "query": "AI 应用开发实习生 RAG 技术追问",
    "limit": 3
  },
  "outputSummary": {
    "hitCount": 3,
    "topScores": [0.92, 0.87, 0.76]
  },
  "success": true,
  "error": "",
  "elapsedMs": 18
}
```

面试表达：

> 我把 RAG 检索包装成了 Agent Tool。这样 Agent 每次检索都不是散落的函数调用，而是有统一输入摘要、输出摘要、成功状态和耗时记录。后续如果接 LangGraph 或真正 tool calling，也比较容易迁移。

## 6. Agent Decision 是什么

Agent Decision 是 Agent 对下一步动作的选择。

它回答的问题是：

```text
下一轮该怎么问？
```

常见字段：

- `nextAction`
  - 深挖、降难度、切换话题、结束面试。

- `difficulty`
  - basic、medium、hard。

- `stage`
  - 下一轮面试阶段。

- `focus`
  - 下一题关注点。

- `reason`
  - 为什么这样决策。

- `tools`
  - 这次决策参考了哪些工具。

- `fallbackUsed`
  - 是否用了规则兜底。

- `guardrailApplied`
  - 是否触发保护规则。

面试表达：

> Agent Decision 是模型或规则综合 state 后给出的下一步动作。它不会直接等于最终问题，而是先决定动作、难度、阶段和关注点，然后问题生成逻辑再结合 RAG context 和历史问答生成下一题。

## 7. fallback、normalize、guardrail 分别是什么

这三个词很容易混。

### 7.1 fallback

fallback 是兜底方案。

当模型不可用、输出不合法，或者需要规则优先时，系统会用预设规则生成一个能工作的决策。

例子：

```text
如果剩余轮次 <= 0，则 end_interview。
如果连续答不上来，则 lower_difficulty 或 switch_topic。
```

### 7.2 normalize

normalize 是格式校验和修正。

大模型可能输出奇怪字段，比如：

```json
{
  "nextAction": "continue_hard_forever"
}
```

normalize 会把不合法字段替换成合法值，保证后续代码不会崩。

### 7.3 guardrail

guardrail 是安全护栏。

它解决的是行为风险，比如：

- 不要重复问同一个问题。
- 用户连续答不上来时不要一直追杀同一个点。
- 学习辅导模式下要更偏解释和引导。

面试表达：

> fallback 保证系统坏不了，normalize 保证模型输出格式合法，guardrail 保证 Agent 行为不要跑偏。三者合起来，让 Agent 决策更稳定、更可控。

## 8. NodeTrace 是什么

NodeTrace 是 Agent 每一步执行过程的轨迹。

它解决的问题是：

```text
这一轮问题到底是怎么被生成出来的？
```

每个节点 trace 记录：

- 节点名称。
- 输入摘要。
- 输出摘要。
- 是否 fallback。
- 耗时。
- 错误。

示例：

```json
{
  "nodeName": "select_action",
  "inputSummary": {
    "answerStatus": "不会",
    "remainingRounds": 5
  },
  "outputSummary": {
    "nextAction": "lower_difficulty",
    "difficulty": "basic",
    "focus": "RAG 基础概念"
  },
  "fallbackUsed": false,
  "elapsedMs": 42,
  "error": ""
}
```

面试表达：

> 我给 Agent 加了 nodeTrace，不只是记录最终结果，还记录每个节点的输入摘要、输出摘要、fallback 和错误。这样调试时能看到 Agent 是在哪一步做了什么决策。

## 9. 为什么当前还不直接引入 LangGraph

你可以这样理解：

LangGraph 是更完整的 Agent 工作流框架，但你现在最需要的是先理解 Agent 的底层工程概念。

如果一上来就引入 LangGraph，可能会变成：

```text
会用框架 API，但讲不清状态、节点、边和 checkpoint 为什么存在。
```

当前自研轻量 Agent 的价值是：

- 代码量可控。
- 每个节点能自己讲明白。
- 测试容易写。
- 面试时能解释底层原理。
- 后续迁移 LangGraph 更自然。

面试表达：

> 我没有一开始就上 LangGraph，而是先做自研轻量 Orchestrator。原因是我想先把 Agent 的状态、工具、决策、trace 和 fallback 这些基础概念落清楚。等这些节点稳定后，可以平滑迁移到 LangGraph StateGraph。

## 10. 未来怎样迁移 LangGraph

迁移思路：

```text
Agent State dict
-> TypedDict / Pydantic state
-> LangGraph StateGraph
-> nodes
-> conditional edges
-> checkpoint
-> human-in-the-loop
```

映射关系：

- `Agent State` -> Graph State。
- `observe_state` -> node。
- `retrieve_context` -> node 或 tool node。
- `select_action` -> node。
- `nextAction` -> conditional edge。
- `AgentDecisionLog` -> checkpoint / trace persistence 的简化替代。
- `nodeTrace` -> graph execution trace。

面试表达：

> 未来如果迁移 LangGraph，我会先把当前的 state 固定成 TypedDict，然后把 observe_state、retrieve_context、analyze_answer、select_action、generate_question、update_memory 注册成 nodes。`nextAction` 可以作为 conditional edge 的路由依据，checkpoint 用来保存多轮面试状态。

## 11. 你需要掌握到什么程度

实习面试阶段，不要求你把 LangGraph 源码讲透。

你需要能讲清楚：

- Agent 和普通 LLM 调用的区别。
- Agent State 里放什么。
- 三个 RAG 为什么算工具。
- ToolCalls 记录什么。
- Agent Decision 决定什么。
- fallback、normalize、guardrail 各自解决什么问题。
- NodeTrace 为什么能提升可观测性。
- 当前自研 Agent 如何迁移 LangGraph。

## 12. 一段完整项目讲法

可以这样讲：

> 我的项目是面向大学生和求职者的 AI 模拟面试系统。用户填写简历和岗位 JD 后，系统会结合岗位知识库 RAG、题库 RAG 和候选人画像 RAG 生成面试问题。核心不是简单聊天，而是一个 Interview Orchestrator Agent。每轮用户回答后，Agent 会构造 Agent State，里面包含用户档案、历史问答、上一轮回答分析、三类 RAG 命中质量和剩余轮次。然后它调用 RAG tools 获取上下文，生成 Agent Decision，决定下一轮是深挖、降难度、切换话题还是结束。整个过程会记录 toolCalls 和 nodeTrace，用于解释为什么这么问，也方便后续调试和迁移到 LangGraph。

## 13. 下一步开发建议

下一轮可以从最小代码增强开始：

1. 给 Agent 日志前端展示 nodeTrace 和 toolCalls。
2. 继续让 `routes/interview.py` 变薄，把编排逻辑下沉到 Orchestrator。
3. 后续可以把 deferred 的 `update_memory` 升级为真实记忆更新链路。

这样既能继续提高项目工程化程度，也不会一下子把项目改到你自己讲不清楚。

## 14. 本轮已完成的代码增强

本轮已经把 `analyze_answer` 增加为显式 `nodeTrace` 节点。

现在 `run_next_question_agent()` 返回的节点顺序包含：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
```

`analyze_answer` 节点会记录：

- `answerStatus`
- `weakAnswerStreak`
- `repeatedQuestionCount`
- `triggerSignals`
- `topicLocked`

这意味着之后查看 Agent 日志时，可以更清楚地解释：

```text
Agent 是先判断用户回答状态，
再结合 RAG 工具结果，
最后选择下一步动作。
```

本轮验证：

```text
python -m pytest tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
23 passed in 0.06s
```

后端全量：

```text
python -m pytest -q
```

结果：

```text
171 passed in 22.41s
```

前端全量 `.mjs`：通过，无失败输出。

## 17. update_memory 节点已显式记录

本轮继续把 `update_memory` 增加为显式 `nodeTrace` 节点。

需要注意：当前 `update_memory` 节点的状态是 `deferred`，意思是：

```text
本轮 next-question 接口只记录“是否应该更新记忆”的意图，
不在这里直接写入长期候选人画像。
```

为什么要这样设计？

因为下一题生成接口的主要职责是生成问题。如果它同时负责复杂的长期记忆沉淀，接口职责会变重，也更容易引入数据污染。当前更稳妥的做法是先在 trace 中记录：

- 是否应该更新记忆。
- 当前问题阶段。
- 当前关注点。
- 为什么延后更新。

后续可以在报告生成或历史保存链路中，把完整问答、评分、风险点和训练建议沉淀为候选人画像。

`update_memory` 节点输出摘要：

- `shouldUpdateMemory`
- `status: deferred`
- `reason`

面试时可以这样讲：

> 我在 Agent trace 里预留了 update_memory 节点，但当前 next-question 阶段不直接写长期记忆，而是标记为 deferred。这样做是为了避免每轮追问都把不完整信息写入画像，后续在报告或历史保存阶段再沉淀更稳定的候选人记忆。

本轮验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
28 passed in 2.17s
```

后端全量：

```text
python -m pytest -q
```

结果：

```text
171 passed in 21.97s
```

前端全量 `.mjs`：通过，无失败输出。

## 15. Agent 日志前端展示

当前前端 Agent 日志已经能展示：

- 模型决策摘要。
- 调试摘要。
- 节点链路 `nodeTrace`。
- 工具调用 `toolCalls`。
- guardrail 是否介入。
- topic shift 是否发生。

本轮补充了前端测试，确认 `analyze_answer` 节点也能在 Agent 日志面板里被展示。

验证命令：

```text
node tests/frontend_agent_logs.test.mjs
```

结果：通过，无失败输出。

## 16. generate_question 节点已显式记录

本轮继续把 `generate_question` 增加为显式 `nodeTrace` 节点。

现在一次完整的下一题生成链路可以解释为：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
```

`generate_question` 节点是在最终问题生成完成后写入 trace 的。它不保存完整 prompt，而是保存可排查摘要。

输入摘要包括：

- `decisionAction`
- `decisionFocus`
- `decisionDifficulty`
- `roleHitCount`
- `questionHitCount`
- `memoryHitCount`

输出摘要包括：

- `stage`
- `focus`
- `stability`
- `promptLength`

为什么不记录完整 prompt？

因为完整问题已经返回给前端，trace 只需要服务调试和日志排查。如果把完整 prompt、简历全文、RAG 全文都塞进 trace，日志会变得很重，也更容易泄露敏感信息。

面试时可以这样讲：

> 我把最终问题生成也纳入了 Agent trace。这样日志里不只看到 Agent 选择了 lower_difficulty 或 switch_topic，还能看到最终生成问题的阶段、关注点和长度。这样可以排查“Agent 决策合理，但问题生成偏了”的情况。

本轮验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
28 passed in 2.19s
```

后端全量：

```text
python -m pytest -q
```

结果：

```text
171 passed in 22.11s
```

前端全量 `.mjs`：通过，无失败输出。
