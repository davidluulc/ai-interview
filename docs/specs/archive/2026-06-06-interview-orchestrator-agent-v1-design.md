# Interview Orchestrator Agent V1 设计说明

## 背景

当前项目的 `/api/interview/next-question` 已经具备完整的 LLM + RAG 工作流：

```text
读取候选人 profile/history
-> 检索岗位知识库 RAG
-> 检索题库 RAG
-> 检索候选人记忆
-> 记录 RAG 日志
-> 拼接 prompt
-> 调用大模型生成下一题
```

这条链路能工作，但它本质上还是固定流程。它没有明确的 Agent State，也没有显式的 Agent Action，更没有把“为什么下一步要深挖、换题、降难度或结束”结构化记录下来。

为了让项目更符合 AI 应用开发岗的要求，本阶段新增一个轻量但真实的 Agent：

```text
Interview Orchestrator Agent
面试流程调度 Agent
```

它不替代 FastAPI 后端，也不替代 RAG；它负责在面试过程中做决策：

```text
根据当前面试状态、历史问答、回答质量、RAG 命中质量和剩余轮次，决定下一步动作。
```

## 目标

Agent V1 实现以下能力：

- 定义 Agent State，描述当前面试上下文。
- 定义 Agent Action，描述下一步动作。
- 定义 Agent Tool，复用现有后端能力：
  - RAG 检索
  - 回答质量分析
  - 候选人记忆读取
  - 问题生成
- 新增 `interview_agent.py`，封装 Agent 决策逻辑。
- 新增 Agent 决策 JSON。
- 新增 Agent 决策日志，记录 Agent 为什么这么做。
- 在 `/api/interview/next-question` 中接入 Agent V1。
- Agent 失败时降级为当前固定工作流。

## 非目标

本阶段不实现以下内容：

- 不引入 LangChain、AutoGen、CrewAI 等 Agent 框架。
- 不做多 Agent 协作。
- 不做无限循环 Agent。
- 不做前端 Agent 可视化。
- 不做 MCP。
- 不做管理员系统。
- 不重写报告生成接口。
- 不把所有后端逻辑都改成 Agent。

V1 的重点是：把现有面试流程升级为“可解释的 Agent 决策层”，而不是堆复杂框架。

## Agent 和传统后端的关系

传统 Python 后端继续负责：

```text
鉴权
数据库
接口
事务
日志
异常处理
权限隔离
RAG 检索执行
```

Agent 负责：

```text
观察当前状态
判断下一步动作
选择需要的工具
输出结构化决策
解释决策原因
```

整体结构：

```text
Frontend
-> FastAPI Router
-> InterviewAgentService
-> Agent State / Tools / Decision
-> RAG / DB / LLM
```

也就是说：

```text
FastAPI = 稳定执行层
Agent = 决策层
Tools = 后端函数能力
```

## Agent State

Agent State 是 Agent 做决策时看到的状态。

```json
{
  "profile": {},
  "history": [],
  "nextStage": "技术追问",
  "lastAnswer": {},
  "askedQuestions": [],
  "roundCount": 3,
  "remainingRounds": 5,
  "answerStatus": "不会",
  "retrievalQuality": {
    "roleKnowledge": {},
    "questionBank": {},
    "candidateMemory": {}
  }
}
```

核心字段：

- `profile`：候选人简历、岗位、JD、公司需求。
- `history`：历史问答。
- `nextStage`：前端期望的下一阶段。
- `lastAnswer`：上一轮回答。
- `askedQuestions`：已问问题，避免重复。
- `roundCount`：已进行轮次。
- `remainingRounds`：剩余轮次。
- `answerStatus`：完整、模糊、不会、跑题。
- `retrievalQuality`：RAG 命中质量摘要。

## Agent Action

允许的 Agent 动作：

```text
deep_follow_up
switch_topic
lower_difficulty
raise_difficulty
summarize_feedback
finish_interview
```

含义：

- `deep_follow_up`：继续深挖上一轮回答。
- `switch_topic`：切换到新话题，避免卡死。
- `lower_difficulty`：候选人明显不会，降低问题难度。
- `raise_difficulty`：候选人回答较完整，提高追问深度。
- `summarize_feedback`：阶段性反馈。
- `finish_interview`：达到轮次上限或信息足够，结束面试。

## Agent Decision JSON

Agent 决策结果必须是结构化 JSON：

```json
{
  "nextAction": "lower_difficulty",
  "stage": "技术追问",
  "difficulty": "basic",
  "focus": "RAG 日志字段",
  "reason": "候选人上一轮回答中明确表示不知道 JSON 日志结构，需要先降低难度补基础概念。",
  "tools": ["retrieve_context", "generate_question"],
  "shouldUpdateMemory": true
}
```

后端会校验：

- `nextAction` 必须在允许列表中。
- `difficulty` 必须是 `basic`、`medium`、`hard` 之一。
- `tools` 只能使用已注册工具名。
- 缺失或非法字段使用 fallback。

## Agent Tools

V1 中工具不是独立进程，而是 Python 函数封装。

### `retrieve_context`

复用已有 RAG 能力：

- `retrieve_role_context`
- `retrieve_questions`
- `retrieve_candidate_memory`

### `analyze_answer`

复用已有回答分类逻辑：

- `classify_answer_status`

输出：

```json
{
  "answerStatus": "不会"
}
```

### `select_action`

根据规则和模型决策选择下一步动作。

基础规则：

- 上一轮回答为空或包含“不会/不知道” -> 倾向 `lower_difficulty`
- 回答完整且轮次未结束 -> 倾向 `deep_follow_up` 或 `raise_difficulty`
- 已问问题过多且主题重复 -> 倾向 `switch_topic`
- 剩余轮次为 0 -> `finish_interview`

### `generate_question`

复用当前 `call_model` 生成下一题。

## 决策方式

Agent V1 采用“规则兜底 + LLM 结构化决策”的方式。

流程：

```text
构建 Agent State
-> 规则生成 fallback decision
-> 调用 LLM 生成 decision JSON
-> 校验 decision
-> 非法或失败则使用 fallback decision
-> 根据 decision 组织问题生成 prompt
-> 返回下一题
-> 记录 Agent 决策日志
```

这样既有 Agent 决策，又不会因为模型输出异常导致接口不可用。

## Agent 日志

新增表或复用独立日志模块，建议新增表：

```text
agent_decision_logs
```

字段：

- `id`
- `user_id`
- `application_profile_id`
- `request_type`
- `next_action`
- `stage`
- `difficulty`
- `focus`
- `reason`
- `tools_json`
- `state_json`
- `decision_json`
- `fallback_used`
- `created_at`

作用：

- 查看 Agent 每轮为什么这么问。
- 面试复盘时解释追问路线。
- 后续做 Agent 评估和调试。

## 和现有接口集成

V1 只改：

```text
POST /api/interview/next-question
```

不改：

```text
POST /api/interview/report
```

集成方式：

```text
next_question route
-> 收集 RAG hits 和 candidate memory
-> InterviewAgentService.decide(...)
-> InterviewAgentService.generate_question(...)
-> 写 RAG 日志
-> 写 Agent 日志
-> 返回 QuestionResponse
```

为了降低风险，V1 可以保留现有固定流程作为 fallback。

## 测试策略

测试覆盖：

- Agent State 构建。
- 回答状态分析。
- fallback decision 规则。
- LLM decision JSON 归一化。
- 非法 action 降级。
- Agent 日志写入。
- `/api/interview/next-question` 可以通过 Agent 返回下一题。
- Agent 失败时 fallback 到旧流程。

## 验收标准

- 有独立 `interview_agent.py`。
- 有 Agent State 和 Decision 结构。
- 有 Agent 决策日志。
- `next-question` 接入 Agent。
- Agent 失败不影响生成下一题。
- 后端测试通过。
- 现有 RAG、报告、历史记录不被破坏。

## 面试表达建议

可以这样讲：

> 我在模拟面试系统里设计了一个 Interview Orchestrator Agent。它不是简单把用户输入拼到 prompt 里，而是维护面试状态，包括历史问答、上一轮回答质量、RAG 命中质量、已问问题和剩余轮次。Agent 会输出结构化决策 JSON，决定下一轮是继续深挖、降低难度、切换话题还是结束面试。后端根据 Agent 决策调用 RAG 检索、问题生成和记忆更新等工具，并把每次 Agent 决策写入日志，方便调试和复盘。

