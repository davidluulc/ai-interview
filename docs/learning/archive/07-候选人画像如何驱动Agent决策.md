# 07 候选人画像如何驱动 Agent 决策

## 1. 本阶段解决什么问题

上一阶段系统已经能从面试报告里提取薄弱点标签，也就是 `weakTags`。

例如某次面试报告里，用户在 RAG 质量评估相关问题上回答不好，报告中可能出现：

```json
{
  "weakTags": ["rag_quality"]
}
```

如果很多次历史记录里都出现类似标签，候选人画像会聚合出长期高频薄弱点：

```json
{
  "frequentWeakTags": ["rag_quality", "agent_state"]
}
```

本阶段继续往前走一步：不只是记录这些薄弱点，还要让它们进入 Agent State，并影响下一轮 Agent Decision。

也就是说，系统不再只是“面试完生成报告”，而是形成训练闭环：

```text
历史回答表现
-> 报告弱点标签 weakTags
-> 候选人画像 frequentWeakTags
-> Agent State
-> weaknessStrategy
-> Agent Decision
-> 下一轮问题生成
-> 新的回答和报告
```

这一步的工程价值是：让 AI 模拟面试系统从一次性问答工具，升级成能根据用户长期薄弱点调整训练策略的 Agent 应用。

## 2. weakTags 和 frequentWeakTags 的区别

`weakTags` 表示单次报告、单道题或单轮训练里暴露出来的局部薄弱点。

它回答的问题是：

```text
这一次回答暴露了哪些问题？
```

例如：

```text
rag_quality
agent_state
backend_fastapi
database_modeling
deployment_readiness
project_storytelling
communication_expression
```

`frequentWeakTags` 表示多轮历史中反复出现的高频薄弱点。

它回答的问题是：

```text
这个候选人长期反复薄弱在哪里？
```

所以两者关系可以这样理解：

```text
weakTags 是单次诊断结果
frequentWeakTags 是长期训练画像
```

在代码中，报告里的 `questionReviews[*].weakTags` 和 `trainingPlan.weakTopics[*].weakTags` 会被历史记录保存下来。后续候选人画像检索时，`build_candidate_profile()` 会把这些标签聚合成 `candidateProfile.frequentWeakTags`。

## 3. 候选人画像怎样进入 Agent State

当前下一题接口 `/api/interview/next-question` 会先运行 Interview Orchestrator Agent。

Agent 会做几件事：

```text
读取用户 profile
读取当前 history
调用岗位知识库 RAG
调用题库 RAG
调用候选人画像 RAG
分析上一轮回答状态
构造 Agent State
生成 Agent Decision
```

本阶段新增的关键点是：构造 Agent State 时，不只放入本轮回答状态和 RAG 命中质量，还会根据候选人画像 RAG 的结果构造：

```json
{
  "candidateProfile": {
    "hasHistory": true,
    "frequentWeakTags": ["rag_quality"]
  }
}
```

这样 Agent 决策时就能看到：

```text
这个用户历史上经常在 RAG 质量评估这里薄弱
```

而不是只看到：

```text
用户上一轮回答了“不知道”
```

这两者差别很大。前者是长期画像，后者只是当前状态。

## 4. weaknessStrategy 是什么

`weaknessStrategy` 可以理解成“弱点驱动策略”。

它不是最终面试问题，而是 Agent Decision 之前的一层策略判断。

例如：

```json
{
  "enabled": true,
  "matchedWeakTags": ["rag_quality"],
  "primaryWeakTag": "rag_quality",
  "primaryWeakLabel": "RAG 质量评估",
  "modePolicy": "coach_remediation",
  "recommendedAction": "practice_weakness",
  "recommendedDifficulty": "basic",
  "reason": "候选人画像显示 RAG 质量评估是高频薄弱点，当前为学习辅导模式，本轮优先拆小问题并补基础。",
  "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
  "guardrailApplied": false
}
```

字段可以这样理解：

- `enabled`：本轮是否启用弱点策略。
- `matchedWeakTags`：本轮命中的历史薄弱标签。
- `primaryWeakTag`：本轮优先处理哪个薄弱标签。
- `primaryWeakLabel`：给人看的中文标签。
- `modePolicy`：不同 Agent 模式下采取什么策略。
- `recommendedAction`：建议 Agent 下一步做什么。
- `recommendedDifficulty`：建议问题难度。
- `reason`：为什么这样决策，写入日志和决策摘要。
- `triggerRules`：触发了哪些规则，方便排查。
- `guardrailApplied`：是否触发保护规则。

## 5. coach 和 interview 模式有什么区别

同样是历史薄弱点，系统在不同模式下的处理方式不同。

### 5.1 coach 模式

coach 是学习辅导模式。

如果 `frequentWeakTags` 里有 `rag_quality`，系统会倾向于：

```text
降低难度
拆小问题
解释基础概念
围绕薄弱点做训练
```

例如问题可以变成：

```text
我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？
```

这种模式适合你现在学习项目、查漏补缺、准备项目讲解。

### 5.2 interview 模式

interview 是真实面试模式。

如果 `frequentWeakTags` 里有 `agent_state`，系统会倾向于：

```text
保持面试压力
围绕薄弱点追问
要求说清楚项目里的具体字段和流程
但不能连续卡死在同一个点
```

例如问题可以变成：

```text
你说 Agent 会根据状态决策，那你项目里的 Agent State 具体包含哪些字段？这些字段分别来自哪里？
```

这种模式更像真实面试官，会追问真实性和细节。

## 6. 为什么要做防死磕规则

如果系统只知道“用户 rag_quality 薄弱”，就可能一直问：

```text
Hit@K 是什么？
MRR 是什么？
quality 怎么算？
写一条 JSON 日志。
再写一条 JSON 日志。
```

这会变成机械化追问，用户体验很差，也不像真实面试。

所以本阶段加入了防死磕规则：

```text
如果最近几轮都围绕同一个 weakTag，
并且用户连续回答不会、写不出来、不清楚，
下一轮就不要继续死磕同一个点。
```

触发后，`weaknessStrategy` 会变成：

```json
{
  "modePolicy": "avoid_weakness_deadlock",
  "recommendedAction": "switch_topic",
  "recommendedDifficulty": "basic",
  "guardrailApplied": true,
  "triggerRules": ["weakness_strategy", "weakness_deadlock_guardrail"]
}
```

这就是 Agent 工程化里的 guardrail，意思是给模型和规则加一层保护，避免系统进入不合理状态。

## 7. 日志和 nodeTrace 为什么重要

AI 应用最怕黑箱。

如果用户问：

```text
为什么系统下一题又问 RAG 质量评估？
```

我们不能只说：

```text
因为大模型觉得应该这么问。
```

本阶段会把关键状态写入 Agent 日志和 `nodeTrace`。

日志里可以看到：

```text
candidateProfile.frequentWeakTags
weaknessStrategy.primaryWeakTag
weaknessStrategy.modePolicy
weaknessStrategy.reason
triggerRules
guardrailApplied
```

`nodeTrace` 里会出现：

```text
observe_state
analyze_answer
retrieve_context
select_weakness_strategy
select_action
generate_question
update_memory
```

这样你就能解释：

```text
系统先观察状态，再分析回答，再检索上下文，然后单独选择弱点策略，最后才决定下一步动作并生成问题。
```

这就是 AI 应用工程化里的可观测性。

## 8. 代码层面怎么串起来

核心代码链路可以按这几个文件理解。

`backend_python/candidate_memory.py`

负责从历史记录中提取候选人画像，包括：

```text
memories[*].weakTags
candidateProfile.frequentWeakTags
```

`backend_python/weakness_strategy.py`

负责根据 `frequentWeakTags`、当前模式、历史回答和 RAG 上下文选择弱点策略。

`backend_python/interview_agent.py`

负责构造 Agent State，并让 fallback / normalize 之后的 Agent Decision 保留 `weaknessStrategy`。

`backend_python/agent_orchestrator.py`

负责把 Agent 的节点执行过程组织起来，并在 `nodeTrace` 中增加 `select_weakness_strategy`。

`backend_python/routes/interview.py`

负责 `/api/interview/next-question` 接口，把 Agent Decision、questionStrategy、RAG 上下文一起传给最终问题生成模型，并把状态和决策写入 Agent 日志。

## 9. 面试时怎么讲

可以这样讲：

> 我的项目里不只是生成一次面试报告，还把报告中的 weakTags 沉淀到候选人画像里。多轮训练后，系统会聚合出 frequentWeakTags，比如 rag_quality、agent_state、backend_fastapi。下一轮生成问题时，这些高频薄弱标签会进入 Agent State，然后由 weaknessStrategy 根据当前模式选择不同策略。coach 模式下会优先降难度、拆概念、补薄弱点；interview 模式下会保持真实追问，但如果连续卡在同一个 weakTag 上，会触发防死磕规则切换话题。同时我把 weaknessStrategy 写入 Agent 日志和 nodeTrace，所以系统能解释为什么这一轮这样问，而不是黑箱生成问题。

如果面试官问“这和普通 RAG 有什么区别”，可以回答：

> 普通 RAG 主要是根据当前 query 召回资料，解决的是当前问题上下文不足的问题。我的候选人画像 RAG 会沉淀用户长期训练表现，再把 frequentWeakTags 转成 Agent State 和 Agent Decision 的策略输入。也就是说，系统不是每轮从零开始问，而是能根据历史薄弱点调整下一轮训练策略。

如果面试官问“为什么不用纯大模型自己判断”，可以回答：

> 因为纯大模型判断不可控，也不容易排查。我的做法是把高频薄弱点、触发规则、推荐动作和防死磕保护都结构化成 weaknessStrategy，再写入日志和 nodeTrace。这样既保留大模型生成问题的自然性，又让关键决策有规则、有状态、有日志可查。

## 10. 本阶段边界

本阶段没有做：

- 新增数据库表。
- 大规模数据库迁移。
- 引入 LangGraph 或 LangChain。
- 改造成 React / Vue / Next.js。
- 做 Docker、Nginx、云服务器上线。

原因是当前重点是把 Agent 决策闭环讲清楚。等这个链路稳定后，后续可以继续做训练路径系统、weakTag 固定题库模板、LangGraph 状态图迁移和上线部署。
