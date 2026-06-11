# Agent Policy 如何连接面试体验和 LangGraph

## 1. Agent Policy 是什么

Agent Policy 是本项目新增的一层“面试策略规则层”。

它不负责生成最终问题，也不直接调用大模型。它只根据当前面试状态判断下一步更适合采取什么策略，例如：

- 继续追问。
- 降低难度。
- 切换话题。
- coach 模式下先解释再追问。
- 提醒前端让用户选择“继续面试 / 先学一下”。
- 标记是否建议人工介入。

对应代码是：

```text
backend_python/agent_policy.py
```

它的核心函数是：

```text
apply_agent_policy(state) -> policy
```

输入是当前 Agent State 的一部分，输出是结构化 policy。

## 2. 为什么不只靠 prompt

如果只靠 prompt，大模型也能说“不要重复追问”，但这个规则不稳定：

- 模型可能忘记。
- 模型可能继续深挖同一个点。
- 模型输出不容易测试。
- classic Agent 和 LangGraph Agent 容易写出两套不同逻辑。

Agent Policy 把这些体验规则变成普通 Python 代码，所以可以单元测试。

例如连续两轮答不上来时：

```text
coach 模式：先解释、拆小问题、建议用户选择。
interview 模式：保持压力，但切换相邻话题，避免卡死。
```

这就是代码层面的策略差异，不再只依赖模型自由发挥。

## 3. Agent Policy 的输入

当前主要输入包括：

```text
agentMode：coach 或 interview
answerAnalysis：回答质量分析，比如 weakAnswerStreak、repeatedQuestionCount、topicLock
retrievalQuality：三类 RAG 的召回质量摘要
weaknessStrategy：候选人历史薄弱点策略
candidateTrainingTasks：训练任务
history：历史问答
```

其中最关键的是 `answerAnalysis`：

```json
{
  "answerStatus": "不会",
  "weakAnswerStreak": 2,
  "repeatedQuestionCount": 1,
  "topicLock": {
    "locked": false,
    "topic": "",
    "count": 0
  }
}
```

这段状态告诉 Agent：候选人是不是连续答不上来、是不是被同一类问题卡住、是否需要换一种问法。

## 4. Agent Policy 的输出

Policy 输出是一个可记录、可展示、可测试的 JSON 结构：

```json
{
  "recommendedAction": "lower_difficulty",
  "difficulty": "basic",
  "shouldExplainBeforeAsk": true,
  "shouldSwitchTopic": false,
  "shouldAskUserChoice": true,
  "requiresHumanReview": false,
  "policyReasons": [
    "候选人连续两轮答不上来，coach 模式先解释或拆小问题，再继续追问。"
  ],
  "triggerRules": [
    "weak_answer_streak",
    "coach_explain_before_ask"
  ]
}
```

这些字段的意义是：

- `recommendedAction`：建议下一步动作。
- `difficulty`：建议难度。
- `shouldExplainBeforeAsk`：是否先解释再追问。
- `shouldSwitchTopic`：是否应该换话题。
- `shouldAskUserChoice`：是否建议让用户选择继续面试还是先学习。
- `requiresHumanReview`：是否建议人工介入，这是 human-in-the-loop 的预留字段。
- `policyReasons`：为什么这么判断。
- `triggerRules`：触发了哪些规则，方便日志排查。

## 5. 它和 classic Agent 的关系

classic Agent 仍然是当前主面试流程。

主流程大致是：

```text
前端提交回答
-> 后端查三类 RAG
-> 构造 Agent State
-> apply_agent_policy
-> decide_next_action
-> normalize / guardrail
-> 生成下一题
-> 写 AgentDecisionLog
```

这次升级没有替换 `/api/interview/next-question`，只是让现有决策里多了 `policy`。

好处是：

- 前端调用不被破坏。
- 老的 fallback / normalize 还能继续兜底。
- 决策日志里能看到策略原因。
- 面试体验规则能被测试覆盖。

## 6. 它和 LangGraph 的关系

LangGraph 旁路工作流本来已经有这些节点：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
```

这次新增了：

```text
apply_policy
```

现在 LangGraph V2/V3 旁路更接近：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> apply_policy
-> select_action
-> generate_question
-> update_memory
```

这说明 LangGraph 不是重新写一套 Agent，而是把自研 Agent 的能力拆成可观察节点。`apply_policy` 就是其中一个独立节点。

## 7. checkpoint summary 为什么记录 policy

LangGraph 的 checkpoint 可以保存 graph state。当前项目里用的是内存版 `MemorySaver`，还不是生产级持久化。

这次 checkpoint summary 增加了 policy 摘要：

```text
policyRecommendedAction
shouldAskUserChoice
requiresHumanReview
policyReasons
policyTriggerRules
```

这样做的意义是：以后如果引入真正的 human-in-the-loop，就能知道 Agent 在哪个状态下建议暂停、为什么暂停、恢复时应该继续哪条策略。

当前阶段只做字段和日志预留，不直接做完整 interrupt 产品化，这是为了避免过度开发。

## 8. 面试时怎么讲

可以这样说：

```text
我在项目里把面试体验规则抽成了 Agent Policy 层。它会根据回答质量、连续弱回答次数、重复追问、话题锁、RAG 质量和候选人训练任务，判断下一轮是继续追问、降难度、切换话题，还是在 coach 模式下先解释再追问。

这样做的好处是：策略不完全依赖大模型 prompt，而是变成可测试的 Python 逻辑。classic 自研 Agent 和 LangGraph 旁路工作流都复用同一套 policy，避免两套规则分叉。LangGraph 里我把它映射成 apply_policy 节点，并把 policy 摘要写入 checkpoint summary，为后续 human-in-the-loop 和 runtime 灰度切换做准备。
```

如果面试官问为什么不直接全量切 LangGraph：

```text
因为当前主流程已经承载真实面试、三类 RAG、历史记录和训练任务。直接替换风险较高，所以我先用 LangGraph 做旁路验证，把稳定的策略层抽出来让两边复用。等旁路稳定后，再考虑 agentRuntime 灰度切换。
```
