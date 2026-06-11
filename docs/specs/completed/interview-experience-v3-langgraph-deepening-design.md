# 面试体验增强 V3 + LangGraph 深化设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统的下一阶段开发：把“面试体验增强”和“LangGraph 深化”合并为一个阶段，但按两条轨道分阶段落地。

当前项目已经完成：

```text
自研 Interview Orchestrator Agent
三类 RAG：岗位知识库 / 题库 / 候选人画像
Agent State / Tool Calls / Agent Decision / nodeTrace
coach / interview 双模式
训练任务和 weakTag 训练闭环
LangGraph V1 POC
LangGraph V2 旁路工作流：真实/fake RAG adapter、真实/fake Agent decision adapter、threadId、MemorySaver checkpoint、checkpoint summary
```

下一阶段不应重复做 V1/V2，也不应立刻替换主流程。目标是让系统从“能跑通 Agent 工作流”继续升级到：

```text
面试体验更自然，训练价值更强；
Agent 策略更可复用，LangGraph 深化方向更清晰；
主流程稳定，旁路能力逐步增强。
```

## 2. 本阶段总目标

本阶段采用合并 spec、分轨开发：

```text
A 轨：面试体验增强 V3
B 轨：LangGraph 深化 V3
C 轨：Agent Policy 抽象，把 A / B 连接起来
```

最终效果：

- 候选人连续答不上来时，系统不再机械追问同一个点。
- coach 模式更像学习陪练，会先解释、拆题、再追问。
- interview 模式保留真实面试压力，但避免无意义重复。
- Agent 的“追问 / 降难度 / 切话题 / 进入讲解 / 等待用户选择”变成可测试的 policy。
- classic 自研 Agent 和 LangGraph 旁路工作流能复用同一套 policy。
- LangGraph 后续可继续升级 checkpoint 持久化、human-in-the-loop 和 runtime 灰度切换。

## 3. 为什么 A 和 B 可以合并

面试体验问题本质上不是单纯的前端问题，也不是单纯的 prompt 问题，而是 Agent 决策问题。

例如：

```text
用户连续回答“不知道”
-> Agent 要判断是继续深挖、降低难度，还是切换话题
-> coach 模式可能先解释基础概念
-> interview 模式可能保留压力但换一个相邻考察点
-> LangGraph 深化时，这些判断应变成可观察、可暂停、可恢复的节点状态
```

所以 A 轨和 B 轨的连接点是：

```text
Agent Policy
```

也就是把“面试体验规则”抽成一层稳定策略，让 classic Agent 和 LangGraph Agent 都能调用。

## 4. 官方能力边界参考

LangGraph 官方 persistence 文档强调，checkpointer 依赖 `thread_id` 存储和恢复 checkpoint；thread 可以理解为一组连续 graph runs 的状态容器，checkpoint 是某个时刻的 graph state 快照。

官方 interrupt 文档说明，`interrupt()` 可以暂停图执行，并在恢复时继续使用同一个 `thread_id` 对应的 checkpoint。

因此，本项目下一阶段可以合理设计：

- 用 `threadId` 表示同一场 LangGraph 实验面试。
- 用 checkpoint 保存 graph state。
- 后续在关键节点引入 human-in-the-loop。
- 但当前不急着直接替换主流程。

参考：

- LangGraph Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts

## 5. 本阶段要做

### 5.1 A 轨：面试体验增强 V3

目标：让面试更像真实训练，而不是机械问答。

要做：

- 增强连续弱回答处理：
  - 连续 1 次不会：降低难度。
  - 连续 2 次不会：给提示或拆小问题。
  - 连续 3 次不会：切换到基础解释或相邻话题。
- 增强重复问题检测：
  - 不只比较完全相同 prompt。
  - 还要识别同一 focus 下连续重复追问。
- 增强 coach 模式：
  - 允许生成“解释 + 小问题”的下一轮。
  - 支持“先看参考思路再回答”。
  - 训练语气更像学习陪练。
- 增强 interview 模式：
  - 保持压力。
  - 不直接喂答案。
  - 连续答不上来时换话题，避免无效卡死。
- 增强训练闭环：
  - 把 weakTag、训练任务、上一轮回答质量纳入下一轮策略。
  - 让“面试报告 -> weakTag -> 训练任务 -> 下一轮 Agent 策略”更明显。

### 5.2 B 轨：LangGraph 深化 V3

目标：让 LangGraph 从旁路 V2 继续走向“可治理工作流”。

要做：

- checkpoint summary 增强：
  - 记录当前节点。
  - 记录最近 action。
  - 记录最近 weakAnswerStreak。
  - 记录是否需要人工介入。
- human-in-the-loop 设计预留：
  - 先不做完整产品化 interrupt。
  - 先定义哪些情况需要暂停：
    - Agent 准备连续深挖同一薄弱点。
    - Agent 准备结束面试。
    - Agent 准备切换到学习辅导。
    - Agent 判断候选人持续不会，需要用户选择“继续面试 / 先学一下”。
- runtime 灰度切换预留：
  - 设计 `agentRuntime = classic | langgraph`。
  - 默认仍然 classic。
  - LangGraph 只作为实验或管理员调试开关。
- 后台可观测预留：
  - 让管理员能看到 classic Agent 和 LangGraph Agent 的策略结果差异。

### 5.3 C 轨：Agent Policy 抽象

目标：不要让 classic Agent 和 LangGraph Agent 写两套体验规则。

建议新增模块：

```text
backend_python/agent_policy.py
```

职责：

- 输入：
  - `agentMode`
  - `answerAnalysis`
  - `retrievalQuality`
  - `weaknessStrategy`
  - `candidateTrainingTasks`
  - `history`
- 输出：
  - `recommendedAction`
  - `difficulty`
  - `shouldExplainBeforeAsk`
  - `shouldSwitchTopic`
  - `shouldAskUserChoice`
  - `policyReasons`
  - `triggerRules`

classic Agent 和 LangGraph V3 都调用它：

```text
classic next-question
-> build Agent State
-> apply_agent_policy
-> decide_next_action
-> generate question

LangGraph V3
-> observe_state
-> analyze_answer
-> retrieve_context
-> apply_policy
-> select_action
-> generate_question
```

## 6. 本阶段不做

- 不替换 `/api/interview/next-question` 主流程。
- 不删除自研 Agent。
- 不把 LangGraph 设为默认 runtime。
- 不做完整 Vue3 重构。
- 不做 Docker / Nginx / 云服务器上线。
- 不做复杂多 Agent 平台。
- 不做生产级 checkpoint 持久化的最终方案。
- 不直接把 human-in-the-loop 做成完整产品闭环。
- 不重构 RAG 底层检索算法。

## 7. 推荐开发阶段

### 阶段 1：Agent Policy 设计与测试

新增 `agent_policy.py`，先把体验规则抽出来。

验收：

- 连续弱回答能得到不同 policy。
- coach / interview 同样状态下策略不同。
- repeated focus 能触发 switch topic。
- policy 输出有 `policyReasons` 和 `triggerRules`。

### 阶段 2：classic Agent 接入 Policy

在现有自研 Agent 主流程中接入 policy，但保持接口兼容。

验收：

- `/api/interview/next-question` 响应字段不破坏前端。
- AgentDecisionLog 能看到 policy 触发原因。
- 连续不会时不再机械重复。

### 阶段 3：LangGraph V3 接入 Policy

在 LangGraph 旁路中新增或强化 `apply_policy` 节点。

验收：

- `/api/langgraph-agent/next-question-v2` 或新的 V3 实验接口能返回 `policy`。
- checkpoint summary 能看到 policy 结果摘要。
- fake 路径稳定，真实路径可选。

### 阶段 4：轻量 human-in-the-loop 预留

先不做真正 interrupt 产品化，只做“是否建议暂停”的策略字段。

验收：

- policy 能输出 `shouldAskUserChoice`。
- LangGraph checkpoint summary 能看到 `requiresHumanReview`。
- 文档说明未来如何升级为 `interrupt()`。

### 阶段 5：体验文案和前端小入口

只做轻量前端，不做 Vue3。

验收：

- coach 模式下能看到“先解释 / 继续面试”的提示。
- Agent 决策解释里能看到 policy 原因。
- 不新增大型页面重构。

## 8. 数据结构草案

### 8.1 Policy 输入

```json
{
  "agentMode": "coach",
  "answerAnalysis": {
    "answerStatus": "不会",
    "weakAnswerStreak": 2,
    "repeatedQuestionCount": 1,
    "topicLock": {
      "locked": true,
      "topic": "RAG 命中日志",
      "count": 2
    }
  },
  "retrievalQuality": {
    "roleKnowledge": {"level": "good", "hitCount": 3},
    "questionBank": {"level": "weak", "hitCount": 1},
    "candidateMemory": {"level": "good", "hitCount": 2}
  },
  "weaknessStrategy": {},
  "candidateTrainingTasks": [],
  "history": []
}
```

### 8.2 Policy 输出

```json
{
  "recommendedAction": "lower_difficulty",
  "difficulty": "basic",
  "shouldExplainBeforeAsk": true,
  "shouldSwitchTopic": false,
  "shouldAskUserChoice": true,
  "requiresHumanReview": false,
  "policyReasons": [
    "候选人连续两轮答不上来，coach 模式下先解释再追问。"
  ],
  "triggerRules": [
    "weak_answer_streak",
    "coach_explain_before_ask"
  ]
}
```

## 9. 测试策略

必须继续 TDD。

重点测试：

- `tests/test_agent_policy.py`
  - weak answer streak。
  - coach / interview 策略差异。
  - repeated focus / topic lock。
  - shouldExplainBeforeAsk。
  - shouldAskUserChoice。
- `tests/test_interview_agent.py`
  - classic Agent 接入 policy 后 fallback / normalize 不破坏。
- `tests/test_interview_agent_route.py`
  - `/api/interview/next-question` 兼容。
- `tests/test_langgraph_agent_graph_v2.py` 或新增 V3 测试
  - LangGraph 能返回 policy。
  - checkpoint summary 能包含 policy 摘要。
- 前端 `.mjs` 测试
  - Agent 决策解释能展示 policy 原因。

全量验收：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 10. 面试表达目标

完成后可以这样讲：

```text
我把面试体验规则从 Agent 决策里抽成了 Agent Policy 层。Policy 会根据回答质量、连续弱回答、重复追问、RAG 质量、候选人弱点和训练任务，决定下一轮是深挖、降难度、切话题，还是先解释再问。这样 classic 自研 Agent 和 LangGraph 旁路工作流都能复用同一套策略，避免两套逻辑分叉。
```

如果面试官问为什么不直接全量切 LangGraph：

```text
因为主流程已经承载真实面试、RAG、历史记录和训练任务。我先把策略层抽出来，再让 LangGraph 旁路复用这层策略，并继续用 checkpoint 记录状态。等旁路稳定后，再评估 agentRuntime 灰度切换，而不是直接替换主流程。
```

如果面试官问 human-in-the-loop 做到什么程度：

```text
当前阶段先做策略预留：当 Agent 判断可能需要人工介入时，会输出 shouldAskUserChoice 或 requiresHumanReview。LangGraph 官方 interrupt 能支持暂停和恢复，但我没有急着产品化，而是先把暂停点、状态字段和 checkpoint 摘要设计出来，避免过度开发。
```

## 11. 下一步

下一步应写 implementation plan：

```text
docs/plans/active/interview-experience-v3-langgraph-deepening.md
```

建议按以下顺序执行：

```text
Agent Policy 测试
-> Agent Policy 实现
-> classic Agent 接入
-> LangGraph 旁路接入
-> checkpoint summary 增强
-> 前端轻量展示
-> 学习文档
-> 全量验证
```
