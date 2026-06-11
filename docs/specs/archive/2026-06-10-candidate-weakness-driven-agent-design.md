# 候选人画像弱点驱动 Agent 决策 V1 设计

## 1. 文档目的

本文档用于设计 AI 模拟面试系统下一阶段的训练闭环增强：

```text
让候选人画像中的高频薄弱标签 frequentWeakTags
真正进入 Agent State，
并影响下一轮 Agent Decision 和问题生成策略。
```

当前项目已经完成：

- 面试报告中的 `questionReviews[*].weakTags`。
- 训练计划中的 `trainingPlan.weakTopics[*].weakTags`。
- 候选人画像聚合中的 `candidateProfile.frequentWeakTags`。
- 前端“一键重练薄弱点”入口。

但当前链路仍有一个关键缺口：

```text
系统已经能记住用户薄弱点，
但下一题生成时还没有明确把这些薄弱点转成 Agent 决策策略。
```

本阶段目标就是补齐这个缺口，让项目从“能记录薄弱点”升级为“能用薄弱点驱动下一轮训练”。

## 2. 当前上下文

### 2.1 已有训练闭环

当前训练闭环大致是：

```text
用户完成面试
-> /api/interview/report 生成报告
-> questionReviews 提取逐题薄弱点
-> trainingPlan 汇总下一轮训练计划
-> weakTags 标准化
-> 历史记录保存
-> 候选人画像聚合 frequentWeakTags
-> 前端一键重练
```

这个闭环已经能支撑用户看到自己的长期薄弱方向。

### 2.2 已有候选人画像能力

候选人画像当前会从历史报告中提取：

- 历史风险点。
- 历史训练建议。
- `questionReviews[*].weakTags`。
- `trainingPlan.weakTopics[*].weakTags`。

然后聚合出：

```text
candidateProfile.frequentWeakTags
```

例如：

```json
{
  "frequentWeakTags": ["rag_quality", "agent_state", "backend_fastapi"]
}
```

### 2.3 已有 Agent 能力

当前 Interview Orchestrator Agent 已经具备：

- `observe_state`
- `analyze_answer`
- `retrieve_context`
- `select_action`
- `generate_question`
- `update_memory`
- `nodeTrace`
- `toolCalls`
- `coach / interview` 双模式
- fallback / normalize / guardrail

因此本阶段不需要重新发明 Agent，而是增强 Agent State 和策略规则。

## 3. 总目标

本阶段采用“策略增强版”方案。

核心目标：

```text
frequentWeakTags 不只停留在候选人画像里，
还要进入 Agent State，
并让 Agent 在 coach / interview 两种模式下产生不同策略。
```

更具体地说：

- Agent State 能显式看到 `candidateProfile.frequentWeakTags`。
- Agent Decision 能根据弱点标签产生策略提示。
- coach 模式下优先补弱点、降难度、解释和训练。
- interview 模式下可以围绕弱点追问，但不能连续死磕。
- Agent 日志能记录本轮是否触发弱点策略、触发了哪些 weakTags、为什么这样问。
- 不破坏现有 `/api/interview/next-question` 前端调用。

## 4. 非目标

本阶段明确不做：

- 不新增数据库表。
- 不新增训练任务系统。
- 不做完整训练路径引擎。
- 不做 weakTags 到固定题库模板的大规模映射。
- 不引入 LangGraph。
- 不安装 LangChain。
- 不重构前端为 React / Vue / Next.js。
- 不开发管理员后台。
- 不做 Docker / Nginx / 云服务器上线。
- 不改变已有 `questionReviews` 和 `trainingPlan` 的响应结构。

如果后续要做“训练路径版”，应另写 spec，而不是塞进本阶段。

## 5. 关键概念

### 5.1 weakTags

`weakTags` 是单次报告或单道题里的薄弱标签。

例如：

```text
rag_quality
rag_retrieval
agent_state
backend_fastapi
database_modeling
deployment_readiness
project_storytelling
communication_expression
```

它回答的问题是：

```text
这一次回答暴露了哪些薄弱点？
```

### 5.2 frequentWeakTags

`frequentWeakTags` 是候选人画像聚合后的高频薄弱标签。

它回答的问题是：

```text
这个用户长期反复薄弱在哪里？
```

单次 `weakTags` 是局部结果，`frequentWeakTags` 是长期画像。

### 5.3 weakness strategy

本阶段新增一个概念：弱点驱动策略。

它不直接等于最终问题，而是影响 Agent Decision。

例如：

```json
{
  "enabled": true,
  "matchedWeakTags": ["rag_quality"],
  "modePolicy": "coach_remediation",
  "reason": "候选人历史上多次在 RAG 质量评估表达不完整，本轮优先用基础问题复练。"
}
```

## 6. 数据流设计

目标数据流：

```text
历史报告
-> extract_weak_tags()
-> retrieve_candidate_memory()
-> build_candidate_profile()
-> candidateProfile.frequentWeakTags
-> build_agent_state()
-> weaknessStrategy
-> decide_next_action()
-> generate_question prompt
-> agent decision log
```

本阶段要保证 `frequentWeakTags` 同时进入三处：

1. **Agent State**
   - 让 Agent 决策时能看到长期弱点。

2. **Agent Decision**
   - 让本轮决策能说明是否触发弱点策略。

3. **Agent 日志**
   - 让开发者和面试讲解时能追溯为什么围绕某个薄弱点追问。

## 7. Agent State 设计

Agent State 中应增加或明确包含：

```json
{
  "candidateProfile": {
    "hasHistory": true,
    "frequentWeakTags": ["rag_quality", "agent_state"]
  },
  "weaknessStrategy": {
    "enabled": true,
    "matchedWeakTags": ["rag_quality"],
    "primaryWeakTag": "rag_quality",
    "modePolicy": "coach_remediation",
    "reason": "候选人历史高频薄弱点包含 rag_quality，当前为学习辅导模式，优先补 RAG 质量评估。"
  }
}
```

字段含义：

- `candidateProfile.frequentWeakTags`
  - 候选人长期高频薄弱标签。

- `weaknessStrategy.enabled`
  - 本轮是否启用弱点驱动策略。

- `weaknessStrategy.matchedWeakTags`
  - 本轮与当前岗位、阶段或上下文匹配的薄弱标签。

- `weaknessStrategy.primaryWeakTag`
  - 本轮优先处理的薄弱标签。

- `weaknessStrategy.modePolicy`
  - 根据 Agent 模式得到的策略类型。

- `weaknessStrategy.reason`
  - 可写入日志和 prompt 的中文原因。

## 8. 策略规则设计

### 8.1 通用规则

如果 `candidateProfile.frequentWeakTags` 为空：

```text
不启用弱点策略，保持现有 Agent 行为。
```

如果存在高频薄弱标签：

```text
优先选择与当前岗位、当前问题阶段、当前 RAG 命中内容相关的 weakTag。
```

如果无法判断相关性：

```text
只选择第一个高频 weakTag 作为轻量提示，不强行改变问题方向。
```

### 8.2 coach 模式规则

`agentMode = coach` 时，弱点策略偏训练辅导。

规则：

- 优先围绕 `primaryWeakTag` 出题。
- 难度建议为 `basic` 或 `medium`。
- `nextAction` 可倾向：
  - `lower_difficulty`
  - `explain_concept`
  - `practice_weakness`
  - `deep_dive`
- 问题表达应允许拆解、解释和引导。
- 如果用户连续答不上来，应优先降难度或换成概念解释。

示例：

```text
候选人长期薄弱点是 rag_quality。
coach 模式下，下一题可以问：
“我们先不写完整 JSON，你先说说 Hit@K、MRR、关键词覆盖率分别解决什么问题。”
```

### 8.3 interview 模式规则

`agentMode = interview` 时，弱点策略偏真实追问。

规则：

- 可以围绕 `primaryWeakTag` 追问，但不能连续死磕。
- 如果最近 2 轮都围绕同一个 weakTag 且回答很弱，应触发 topic shift。
- 难度可以保持 `medium`，但避免直接给答案。
- `nextAction` 可倾向：
  - `deep_dive`
  - `switch_topic`
  - `keep_pressure`
  - `end_interview`
- 问题表达应像真实面试官，不明显“教学”。

示例：

```text
候选人长期薄弱点是 agent_state。
interview 模式下，下一题可以问：
“你说 Agent 会根据状态决策，那你项目里的 Agent State 具体包含哪些字段？这些字段分别来自哪里？”
```

### 8.4 防死磕规则

无论 coach 还是 interview，都必须避免连续卡死。

建议规则：

```text
如果最近 2 轮问题都围绕同一个 primaryWeakTag，
且 answerStatus 连续为 不会 / 模糊，
则下一轮不要继续同一个 weakTag。
```

处理方式：

- coach 模式：
  - 切换到更基础解释。
  - 或换到相邻基础主题。

- interview 模式：
  - 切换到新话题。
  - 或进入项目经历、后端基础、行为面试等稳定环节。

## 9. Agent Decision 设计

Agent Decision 中建议扩展：

```json
{
  "nextAction": "practice_weakness",
  "difficulty": "basic",
  "focus": "RAG 质量评估",
  "reason": "候选人画像显示 rag_quality 是高频薄弱点，当前为 coach 模式，本轮优先用基础问题复练。",
  "weaknessStrategy": {
    "enabled": true,
    "primaryWeakTag": "rag_quality",
    "matchedWeakTags": ["rag_quality"],
    "modePolicy": "coach_remediation"
  }
}
```

为了兼容现有前端，本阶段可以把 `weaknessStrategy` 放入已有 `agentDecision` 或 `debugSignals` 中。

不强制新增 `QuestionResponse` 顶层字段。

## 10. Prompt 设计

生成下一题时，prompt 应包含弱点策略摘要。

建议加入类似文本：

```text
候选人长期高频薄弱标签：rag_quality、agent_state。
本轮弱点策略：coach_remediation。
本轮优先弱点：rag_quality。
策略原因：候选人历史上多次在 RAG 质量评估表达不完整，本轮先用基础问题复练。
```

要求：

- coach 模式可以显式训练。
- interview 模式不要直接告诉候选人“我正在根据你的 weakTag 提问”。
- 不要让 weakTags 覆盖岗位 JD、简历和当前历史回答。
- weakTags 只是策略输入，不是唯一输入。

## 11. 日志与可观测性

Agent 日志应能看到：

- `candidateProfile.frequentWeakTags`
- `weaknessStrategy.enabled`
- `weaknessStrategy.primaryWeakTag`
- `weaknessStrategy.modePolicy`
- `weaknessStrategy.reason`
- 是否触发防死磕规则

nodeTrace 中建议新增或增强：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_weakness_strategy
-> select_action
-> generate_question
-> update_memory
```

如果不想新增节点，也可以先把弱点策略写入 `select_action` 的 `outputSummary`。

推荐本阶段采用：

```text
新增 select_weakness_strategy 节点
```

原因：

- 更清晰。
- 更像企业级 Agent 工作流。
- 后续迁移 LangGraph 时可以映射为独立 node。

## 12. API 兼容性

必须保持：

```text
POST /api/interview/next-question
```

现有请求兼容。

不要求前端传新字段。

不要求新增数据库字段。

响应可以在现有 `agentDecision` / `decisionSummary` 内增强，不破坏旧字段。

## 13. 测试计划

本阶段实现时必须测试驱动。

### 13.1 后端单元测试

建议新增测试：

1. `build_candidate_profile()` 已能输出 `frequentWeakTags`。
2. `build_agent_state()` 能包含 `candidateProfile.frequentWeakTags`。
3. `select_weakness_strategy()` 在 coach 模式下返回 `coach_remediation`。
4. `select_weakness_strategy()` 在 interview 模式下返回 `interview_probe`。
5. 连续相同 weakTag 弱回答时触发防死磕策略。

### 13.2 路由测试

建议新增或更新：

```text
tests/test_interview_agent_route.py
```

覆盖：

- 用户历史报告中有 `rag_quality`。
- 下一次请求 `/api/interview/next-question`。
- 响应中的 `agentDecision.weaknessStrategy.primaryWeakTag` 为 `rag_quality`。
- `decisionSummary` 能说明围绕历史薄弱点调整策略。

### 13.3 日志测试

建议验证：

- `AgentDecisionLog.state_json` 中有 `candidateProfile.frequentWeakTags`。
- `AgentDecisionLog.decision_json` 中有 `weaknessStrategy`。
- `nodeTrace` 中存在 `select_weakness_strategy` 或等价记录。

### 13.4 前端测试

本阶段可以不改前端页面。

如果已有 Agent 调试面板能展示 `agentDecision` 中的字段，则只需要补前端测试确认不会出现 `undefined`。

如果前端不能展示，可以后续另开 UI spec。

## 14. 风险与边界

### 14.1 过拟合历史弱点

风险：

```text
用户曾经在 rag_quality 答不好，系统之后一直问 rag_quality。
```

应对：

- 加防死磕规则。
- weakTags 只作为策略输入之一，不覆盖岗位 JD 和当前回答。

### 14.2 coach 和 interview 混淆

风险：

```text
真实面试模式变成教学模式。
```

应对：

- coach 模式可以解释和拆解。
- interview 模式保持真实追问，只在策略上适度利用弱点。

### 14.3 日志泄露给普通用户

风险：

```text
普通用户看到过多内部 weakTag 和 debug 信息。
```

应对：

- Agent 调试面板可以展示。
- 普通问题区只展示自然语言问题，不展示内部标签。

### 14.4 一次性做太大

风险：

```text
同时做策略、模板、训练路径和前端可视化，导致质量下降。
```

应对：

- 本阶段只做策略增强。
- weakTags 到固定训练题模板留到下一阶段。

## 15. 验收标准

本阶段完成后应满足：

- `frequentWeakTags` 能进入 Agent State。
- Agent 有明确的弱点策略对象或等价字段。
- coach 模式下弱点策略偏训练辅导。
- interview 模式下弱点策略偏真实追问。
- 连续围绕同一个 weakTag 卡死时能触发保护。
- Agent 日志能追踪弱点策略触发原因。
- `/api/interview/next-question` 保持兼容。
- 后端测试通过。
- 如改前端，所有 `.mjs` 测试通过。
- 新增中文学习文档，说明“候选人画像如何驱动 Agent 决策”。

## 16. 建议实现阶段

### 阶段 A：状态与策略函数

- 定义 `select_weakness_strategy()`。
- 让 Agent State 包含 `candidateProfile.frequentWeakTags`。
- 补单元测试。

### 阶段 B：Agent Decision 接入

- 在 `run_next_question_agent()` 中加入弱点策略。
- 在 `decide_next_action()` 或 fallback decision 中使用策略。
- 扩展 `agentDecision.weaknessStrategy`。

### 阶段 C：日志与路由验证

- 把策略写入 Agent 日志。
- 补 `/api/interview/next-question` 路由测试。
- 确认前端不需要变更或仅做兼容展示。

### 阶段 D：学习文档

新增：

```text
docs/learning/07-候选人画像如何驱动Agent决策.md
```

内容包括：

- weakTags 和 frequentWeakTags 区别。
- 候选人画像如何进入 Agent State。
- coach / interview 两种策略差异。
- 防死磕规则。
- 面试时怎么讲。

## 17. 面试表达模板

可以这样讲：

```text
我在训练闭环里不只是生成报告，还把报告里的 weakTags 沉淀到候选人画像中。
多轮训练后，系统会聚合出 frequentWeakTags，比如 rag_quality、agent_state、backend_fastapi。
下一轮生成问题时，这些高频薄弱标签会进入 Agent State。
Agent 会根据当前模式选择不同策略：
如果是 coach 模式，就优先围绕薄弱点降难度、拆解和训练；
如果是 interview 模式，就适度围绕薄弱点追问，但不会连续死磕同一个点。
同时我把弱点策略写入 Agent 日志和 nodeTrace，方便解释为什么系统这一轮这样问。
这让项目形成了从历史表现到下一轮训练策略的闭环。
```

如果面试官问“这和普通 RAG 有什么区别”，可以这样答：

```text
普通 RAG 只是根据当前 query 召回资料。
我这里的候选人画像 RAG 会记录用户长期薄弱点，并把这些弱点变成 Agent 决策状态。
所以系统不是每轮从零开始问，而是能根据历史表现调整下一轮训练策略。
```

## 18. 后续扩展方向

本阶段完成后，后续可以继续做：

- weakTags 到固定训练题模板的映射。
- 训练路径系统。
- 每个 weakTag 的掌握度评分。
- 前端弱点雷达图或训练路线图。
- LangGraph 状态图迁移。
- Redis / 任务队列驱动的长期训练任务。

这些都不属于本阶段范围。

