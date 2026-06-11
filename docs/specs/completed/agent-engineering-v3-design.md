# Agent 工程化 V3 设计

## 1. 目标

本阶段目标是把 AI 模拟面试系统里的 Interview Orchestrator Agent 继续升级为更清晰的工程化工作流，但仍然不直接引入 LangGraph / LangChain。

V3 的重点不是“让 Agent 更玄”，而是让它更可解释、更可测试、更可迁移：

- 状态清晰：Agent 每一轮到底看到了什么。
- 工具清晰：三类 RAG 如何作为工具被调用。
- 决策清晰：为什么深挖、降难度、换话题或结束。
- 轨迹清晰：每个节点输入什么、输出什么、是否 fallback。
- 边界清晰：HTTP 路由只负责接口，Agent Orchestrator 负责流程编排。
- 迁移清晰：未来如何映射到 LangGraph StateGraph、checkpoint 和 human-in-the-loop。

## 2. 当前基础

当前项目已经具备 Agent V2 雏形：

- `backend_python/agent_state.py`
  - 定义 `AGENT_SESSION_STATES`、`AGENT_EVENTS`、`AGENT_NODES`。
  - 提供 `build_interview_agent_state()`。
  - 能分析弱回答、重复问题、topic lock。

- `backend_python/agent_tools.py`
  - 提供 `run_agent_tool()`。
  - 包装岗位知识库、题库 RAG、候选人画像 RAG。
  - 每次工具调用返回 `toolCall` 摘要。

- `backend_python/agent_trace.py`
  - 提供 `build_node_trace()` 和 `build_tool_call_summary()`。
  - 统一记录节点和工具调用字段。

- `backend_python/agent_orchestrator.py`
  - 提供 `run_next_question_agent()`。
  - 串联三类 RAG tool、Agent State、Agent Decision 和 nodeTrace。

- `backend_python/interview_agent.py`
  - 负责 fallback decision、LLM decision、normalize、guardrail 和 decision summary。

当前已经比“一次 LLM 调用”更进一步，但还可以继续增强：

- `analyze_answer` 还没有成为独立 trace 节点。
- `generate_question` 还主要留在面试路由和生成逻辑里。
- `update_memory` 还没有显式节点。
- trace 中的 `elapsedMs` 还没有覆盖每个节点。
- toolCalls 和 nodeTrace 的前端展示还可以继续增强。
- Agent State 还没有形成稳定的文档化 schema 和验收用例。

## 3. Agent V3 工作流

V3 目标工作流：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
-> write_trace
```

说明：

- `observe_state`：收集 profile、history、轮次、模式、下一阶段。
- `analyze_answer`：分析上一轮回答质量、弱回答连续次数、重复问题、topic lock。
- `retrieve_context`：调用岗位知识库 RAG、题库 RAG、候选人画像 RAG。
- `select_action`：决定下一步动作和难度。
- `generate_question`：结合 state、decision、RAG 上下文生成下一题。
- `update_memory`：把关键弱点、风险、训练建议写入候选人画像或后续记忆。
- `write_trace`：把节点轨迹、工具调用、fallback、错误写入日志。

## 4. Agent State Schema

V3 的 Agent State 应保持 JSON 可序列化，不保存数据库 Session、模型 client 或其它运行时对象。

推荐 schema：

```json
{
  "session": {
    "applicationProfileId": 1,
    "agentMode": "coach",
    "nextStage": "技术追问",
    "roundCount": 3,
    "remainingRounds": 5
  },
  "profile": {
    "candidateName": "David",
    "targetRole": "AI 应用开发实习生",
    "positionTag": "ai_app_intern",
    "resume": "摘要，不保存超长全文",
    "jd": "摘要，不保存超长全文",
    "company": "岗位要求摘要"
  },
  "history": [],
  "lastAnswer": {
    "question": "上一轮问题",
    "answer": "上一轮回答",
    "stage": "RAG 追问",
    "focus": "RAG 质量评估"
  },
  "answerAnalysis": {
    "answerStatus": "不会",
    "weakAnswerStreak": 2,
    "repeatedQuestionCount": 0,
    "topicLock": {
      "locked": true,
      "topic": "RAG 质量评估",
      "count": 2
    },
    "triggerSignals": ["weak_answer_streak", "topic_lock_guardrail"]
  },
  "retrievalQuality": {
    "roleKnowledge": {},
    "questionBank": {},
    "candidateMemory": {}
  },
  "toolCalls": [],
  "nodeTrace": []
}
```

## 5. Tool 设计

本项目当前采用自研轻量 Tool 抽象。

判断一个能力是不是 Tool，可以问：

```text
它是不是被 Agent 调用？
它是不是有明确输入？
它是不是有结构化输出？
它是不是需要记录成功、失败、耗时和摘要？
```

当前 Tool：

- `retrieve_role_knowledge`
  - 输入：profile、stage、limit。
  - 输出：岗位知识库 hits。

- `retrieve_question_bank`
  - 输入：profile、stage、limit。
  - 输出：题库 hits。

- `retrieve_candidate_memory`
  - 输入：profile、limit。
  - 输出：候选人历史画像 hits。

V3 可继续补充：

- `analyze_answer`
  - 输入：history、lastAnswer。
  - 输出：answerStatus、weakAnswerStreak、topicLock。

- `generate_question`
  - 输入：agentState、agentDecision、RAG context。
  - 输出：nextQuestion、stage、focus。

- `update_candidate_memory`
  - 输入：本轮问答、报告摘要、风险点。
  - 输出：memoryUpdate summary。

## 6. Node Trace 设计

每个节点 trace 推荐格式：

```json
{
  "nodeName": "select_action",
  "inputSummary": {
    "answerStatus": "不会",
    "weakAnswerStreak": 2,
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

要求：

- `nodeName` 使用固定常量，避免日志里同一个节点出现多个名字。
- `inputSummary` 不保存超长简历原文。
- `outputSummary` 只保存决策摘要，不保存完整 prompt。
- 失败时必须写 `error`。
- 兜底时必须写 `fallbackUsed`。

## 7. 路由层与 Orchestrator 边界

V3 期望边界：

```text
routes/interview.py
  负责：HTTP 入参、鉴权、数据库 Session、响应封装。

agent_orchestrator.py
  负责：串联 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory。

interview_agent.py
  负责：LLM decision、fallback、normalize、guardrail。

agent_tools.py
  负责：工具调用包装、异常捕获、toolCall 摘要。

agent_trace.py
  负责：nodeTrace 和 toolCall 数据结构。
```

这样拆分后，面试时可以说：

> 我把 HTTP 接口层和 Agent 编排层拆开了。接口层不直接处理复杂业务，而是把 profile、history、数据库依赖和模型调用函数传给 Orchestrator。Orchestrator 负责调用工具、构造状态、选择动作和返回结构化结果。

## 8. 状态机是否需要引入

当前阶段不强制引入完整状态机库。

原因：

- 当前产品还在快速迭代，强行引入状态机类可能增加理解成本。
- 项目已经通过 `AGENT_SESSION_STATES` 和 `AGENT_EVENTS` 预留了状态机语言。
- 先把节点、事件、状态和日志设计清楚，后续再决定是否封装状态机。

推荐做法：

```text
先常量化状态和事件
-> 在 trace 里记录节点流转
-> 在测试里验证关键状态
-> 等流程稳定后再抽状态机
```

## 9. LangGraph 预留

本阶段不直接安装 LangGraph。

未来映射关系：

| 当前自研 Agent | LangGraph 概念 |
| --- | --- |
| Agent State dict | Graph State |
| `observe_state` | node |
| `analyze_answer` | node |
| `retrieve_context` | tool node / node |
| `select_action` | node |
| `generate_question` | node |
| `update_memory` | node |
| `nodeTrace` | graph execution trace |
| `AgentDecisionLog` | checkpoint / persistence 的简化替代 |
| fallback decision | conditional edge / fallback edge |

未来迁移顺序：

1. 先稳定自研节点函数。
2. 把 Agent State 改造成 TypedDict 或 Pydantic schema。
3. 用 StateGraph 注册节点。
4. 把 `nextAction` 映射成 conditional edge。
5. 引入 checkpoint 保存多轮面试状态。
6. 再考虑 human-in-the-loop，例如人工审查某轮追问是否合理。

## 10. V3 开发顺序

### 10.1 第一轮：补齐 answerAnalysis 节点 trace

目标：

- `analyze_answer` 成为显式节点。
- `nodeTrace` 中能看到弱回答、重复问题、topic lock。
- 测试覆盖连续答不上来时的 trace。

### 10.2 第二轮：补齐 generate_question 节点 trace

目标：

- 问题生成不再是黑盒。
- trace 记录生成依据：stage、focus、difficulty、使用了哪些 RAG context。
- 不记录完整 prompt，避免日志过长。

### 10.3 第三轮：补齐 update_memory 设计或轻量实现

目标：

- 当用户完成一轮问答或生成报告后，明确哪些信息会进入候选人画像。
- 先记录 `memoryUpdate` 摘要，不急着新增复杂数据库表。

### 10.4 第四轮：前端 Agent Debug 增强

目标：

- Agent 日志面板展示 nodeTrace。
- Agent 日志面板展示 toolCalls。
- 普通用户看到“为什么这么问”，开发者可以展开看 trace。

## 11. 测试计划

后端测试优先：

- `tests/test_agent_state.py`
  - 验证 Agent State 字段完整。
  - 验证弱回答和 topic lock。

- `tests/test_agent_trace.py`
  - 验证 node trace 和 tool call 格式。

- `tests/test_agent_orchestrator.py`
  - 验证 orchestrator 返回 roleHits、questionHits、memoryHits、toolCalls、nodeTrace、agentState、agentDecision。
  - 验证 tool 失败时不会打断流程。
  - 验证 answerAnalysis trace 存在。

- `tests/test_interview_next_question.py`
  - 验证 `/api/interview/next-question` 兼容旧前端调用。

前端测试：

- `tests/frontend_agent_logs.test.mjs`
  - 验证 Agent 日志可以展示 trace 和 toolCalls。

## 12. 非目标

本阶段明确不做：

- 不安装 LangGraph。
- 不安装 LangChain。
- 不做多 Agent 协作。
- 不做 Docker / Nginx / 云服务器部署。
- 不做管理员后台。
- 不切换 React / Vue / Next.js。
- 不把现有 Agent 推倒重写。
- 不把所有 trace 都塞进前端主流程。

## 13. 验收标准

V3 阶段完成后，应满足：

- Agent 节点链路能在日志里看见。
- `answerAnalysis`、`toolCalls`、`nodeTrace` 能串起来解释一次追问。
- `routes/interview.py` 复杂度下降，更多编排逻辑进入 Orchestrator。
- `/api/interview/next-question` 响应兼容。
- 后端测试通过。
- 前端测试通过。
- 能讲清为什么当前是自研 Agent，未来如何迁移 LangGraph。

## 14. 面试表达

可以这样讲：

> 我的 Agent 不是单纯把用户回答拼进 prompt，而是一个轻量 Orchestrator。每轮会先观察状态，分析上一轮回答，再调用岗位知识库、题库和候选人画像三个 RAG 工具，然后根据回答质量、检索质量、剩余轮次和模式选择下一步动作。每个节点和工具调用都会记录 trace，所以可以解释为什么这一轮要深挖、降难度或切换话题。

如果面试官问 LangGraph：

> 当前我先做自研轻量 Agent，是为了把状态、节点、工具、日志这些底层概念掌握清楚。后续可以把 `observe_state`、`analyze_answer`、`retrieve_context`、`select_action`、`generate_question`、`update_memory` 映射成 LangGraph StateGraph 的 nodes，用 checkpoint 保存多轮面试状态。
