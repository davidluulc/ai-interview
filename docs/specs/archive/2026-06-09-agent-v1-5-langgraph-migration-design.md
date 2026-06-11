# Agent V1.5 与 LangGraph 预留设计

## 1. 目标

本阶段目标是把当前 AI 模拟面试系统的 Interview Orchestrator Agent 从 V1 决策层升级为 V1.5：

- 支持“学习辅导模式”和“真实面试模式”。
- 能识别连续答不上来、连续重复问题等异常状态。
- 能在必要时降低难度或切换话题，避免一直卡在同一个知识点。
- 在 Agent 日志中记录状态、动作、原因、触发规则和兜底情况。
- 保持自研实现，不直接引入 LangGraph，但把节点边界设计成后续可迁移到 LangGraph 的形态。

## 2. 当前 Agent V1.5 节点

当前代码仍由 FastAPI 路由触发，Agent 逻辑集中在 `backend_python/interview_agent.py`。

V1.5 按以下节点理解：

| 节点 | 当前实现 | 职责 |
| --- | --- | --- |
| `observe_state` | `build_agent_state` | 收集简历、JD、历史问答、当前阶段、RAG 命中质量 |
| `analyze_answer` | `classify_answer_status`、`analyze_answer_history` | 判断上一轮回答质量、连续弱回答次数、重复问题信号 |
| `retrieve_context` | FastAPI route 中的三类 RAG 检索 | 召回岗位知识库、题库、候选人画像 |
| `select_action` | `build_fallback_decision`、`decide_next_action` | 决定降难度、深挖、换话题或结束 |
| `generate_question` | `/api/interview/next-question` 中的问题生成模型 | 根据 RAG 上下文和 Agent 决策生成下一题 |
| `update_memory` | 当前通过历史记录与候选人画像间接完成 | 后续可升级为显式记忆写入节点 |

## 3. Agent State 预留字段

V1.5 的 Agent State 应包含以下可迁移字段：

```json
{
  "profile": {},
  "history": [],
  "agentMode": "coach",
  "nextStage": "技术追问",
  "lastAnswer": {},
  "askedQuestions": [],
  "roundCount": 3,
  "remainingRounds": 5,
  "answerStatus": "不会",
  "answerAnalysis": {
    "weakAnswerStreak": 3,
    "repeatedQuestionCount": 0,
    "triggerSignals": ["weak_answer_streak"]
  },
  "retrievalQuality": {},
  "agentNodes": [
    "observe_state",
    "analyze_answer",
    "retrieve_context",
    "select_action",
    "generate_question",
    "update_memory"
  ]
}
```

这些字段后续可以直接作为 LangGraph 的 graph state。

## 4. Agent Decision 预留字段

V1.5 的 Agent Decision 应包含：

```json
{
  "nextAction": "switch_topic",
  "stage": "技术追问",
  "difficulty": "basic",
  "focus": "技术追问",
  "reason": "候选人连续答不上来，Agent 切换到更基础或相邻话题。",
  "tools": ["retrieve_context", "analyze_answer", "generate_question"],
  "triggerRules": ["weak_answer_streak", "topic_shift"],
  "agentMode": "coach",
  "nodeTrace": ["observe_state", "analyze_answer", "select_action"],
  "shouldUpdateMemory": true,
  "fallbackUsed": false,
  "decisionSummary": "学习辅导模式：switch_topic。候选人连续答不上来，Agent 切换到更基础或相邻话题。"
}
```

其中：

- `triggerRules` 用于解释触发了哪些规则。
- `nodeTrace` 用于记录这次决策经过了哪些节点。
- `fallbackUsed` 用于区分模型决策和规则兜底。
- `decisionSummary` 用于前端展示“为什么这么问”。

## 5. LangGraph 迁移方向

后续如果引入 LangGraph，可以把当前 V1.5 迁移成状态图：

```text
START
-> observe_state
-> retrieve_context
-> analyze_answer
-> select_action
-> generate_question
-> update_memory
-> END
```

条件边建议：

- `remainingRounds <= 0` -> `finish_interview`
- `weakAnswerStreak >= 3` -> `switch_topic`
- `answerStatus == "不会"` -> `lower_difficulty`
- `answerStatus == "完整"` -> `deep_follow_up` 或 `raise_difficulty`
- 模型输出非法 -> `fallback_decision`

## 6. Checkpoint 与 Human-in-the-loop

LangGraph 的 checkpoint 可以用于保存 graph state。迁移后可支持：

- 面试中断后恢复到上一轮。
- 查看某一轮 Agent 决策前后的状态差异。
- 在关键节点加入人工确认，例如正式面试报告生成前先让用户确认。
- Agent 出错后从最近 checkpoint 继续，而不是整场面试重来。

Human-in-the-loop 可用于：

- 用户确认是否继续深挖某个薄弱点。
- 用户选择“继续真实面试压力”或“切换学习辅导”。
- 管理员审查系统生成的题库或训练建议。

## 7. 本阶段非目标

- 不安装 LangGraph。
- 不引入 LangChain 依赖。
- 不做多 Agent 协作。
- 不做复杂 checkpoint 持久化。
- 不把所有后端流程重写成 graph。

当前阶段重点是先把 Agent 的状态、决策、日志、兜底和可解释性做扎实。

## 8. 面试表达

可以这样讲：

> 我没有一开始就直接上 LangGraph，而是先做了一个自研 Interview Orchestrator Agent V1.5。它会维护面试状态，包括历史问答、上一轮回答质量、连续弱回答次数、RAG 命中质量和剩余轮次。Agent 会输出结构化决策 JSON，决定下一步是深挖、降难度、换话题还是结束，并把触发规则、原因、工具和 fallback 情况写入日志。这样先保证我能讲清楚 Agent 的核心机制，后续再把这些节点迁移成 LangGraph 的 state graph 和 checkpoint。
