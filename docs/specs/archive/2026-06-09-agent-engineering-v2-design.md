# Agent 工程化增强 V2 设计

## 1. 文档目的

本文档用于约束 AI 模拟面试系统阶段二：Agent 工程化增强。

阶段一已经完成面试体验增强，系统具备学习辅导模式、真实面试模式、重复问题保护、Agent 决策日志、训练计划和面试工作台 UI。下一阶段的重点不是继续堆前端效果，而是把当前 Agent 从“能做决策”升级成“可拆分、可追踪、可迁移的工作流系统”。

本阶段目标是让项目在面试中能讲清楚：

- Agent 的状态从哪里来。
- Agent 如何分析用户回答。
- RAG 检索在 Agent 中扮演什么工具角色。
- Agent 如何选择下一步动作。
- Agent 如何生成问题。
- Agent 如何记录节点轨迹、工具调用和 fallback。
- 当前自研 Agent 如何迁移到 LangGraph。

## 2. 当前基础

当前项目已经具备 Agent V1.5 能力：

- `build_agent_state`：构造 Agent State。
- `decide_next_action`：调用模型生成 Agent Decision。
- `build_fallback_decision`：规则兜底决策。
- `normalize_agent_decision`：校验模型输出。
- `triggerRules`：记录触发规则。
- `nodeTrace`：记录简化节点轨迹。
- `AgentDecisionLog`：持久化 Agent 决策日志。
- `/api/interview/next-question`：串联三类 RAG、Agent 决策、问题生成和日志写入。

当前 Agent 已经具备可解释雏形，但仍存在工程化不足：

- 节点概念还停留在文档和函数名层面，代码边界不够清晰。
- RAG 检索、回答分析、问题生成还没有统一抽象成 Agent Tool。
- Trace 只记录节点名称，没有记录每个节点的输入摘要、输出摘要、耗时和错误。
- Agent 状态还没有独立的状态对象或状态机事件。
- `routes/interview.py` 仍承担较多编排职责。
- LangGraph 迁移只有预留设计，还没有形成清晰映射表和迁移顺序。

## 3. 阶段二目标

阶段二目标：

```text
把 Interview Orchestrator Agent 从“路由里串起来的一组函数”
升级为“节点清晰、工具清晰、日志清晰、可迁移到 LangGraph 的轻量 Agent 工作流”。
```

阶段二完成后，应能回答：

- 一个 Agent 节点的输入和输出是什么？
- 哪些能力算工具？
- 每一轮 Agent 决策经过了哪些节点？
- 如果模型输出不合法，系统如何 fallback？
- 如果用户连续答不上来，状态如何影响下一步动作？
- 为什么当前不直接上 LangGraph？
- 未来如何迁移到 LangGraph StateGraph？

## 4. Agent V2 架构设计

### 4.1 总体结构

Agent V2 推荐按以下工作流理解：

```text
observe_state
-> retrieve_context
-> analyze_answer
-> select_action
-> generate_question
-> update_memory
-> write_trace
```

节点说明：

| 节点 | 职责 | 当前来源 | V2 目标 |
| --- | --- | --- | --- |
| `observe_state` | 收集用户档案、历史问答、当前轮次、模式 | `build_agent_state` | 独立成可测试节点 |
| `retrieve_context` | 调用岗位知识库、题库、候选人画像 RAG | `routes/interview.py` | 抽象为 Agent Tool |
| `analyze_answer` | 判断回答状态、连续弱回答、重复问题 | `interview_agent.py` | 输出结构化 answerAnalysis |
| `select_action` | 决定深挖、降难度、切换话题、结束 | `decide_next_action` | 输出结构化 AgentDecision |
| `generate_question` | 根据 state、decision、RAG 生成下一题 | `routes/interview.py` | 独立问题生成节点 |
| `update_memory` | 更新候选人画像或训练记忆 | 当前间接完成 | 设计显式记忆更新节点 |
| `write_trace` | 记录节点轨迹、工具调用、fallback | `AgentDecisionLog` | 扩展 trace 信息 |

### 4.2 推荐文件边界

阶段二可以逐步拆分，不要求一次性大重构。

推荐新增或演进的文件：

```text
backend_python/agent_orchestrator.py
backend_python/agent_state.py
backend_python/agent_tools.py
backend_python/agent_trace.py
backend_python/interview_agent.py
backend_python/routes/interview.py
```

职责建议：

- `agent_state.py`
  - 定义 Agent State 构造和状态字段规范。
  - 定义轻量 session state 和事件名称。

- `agent_tools.py`
  - 包装 RAG 检索、回答分析、候选人记忆读取等工具。
  - 每个工具输出统一格式：`name`、`inputSummary`、`outputSummary`、`success`、`error`。

- `agent_trace.py`
  - 构造节点 Trace。
  - 记录工具调用摘要。
  - 生成前端和日志都能理解的 trace JSON。

- `agent_orchestrator.py`
  - 串联 Agent 节点。
  - 暴露一个高层函数，例如 `run_next_question_agent(...)`。
  - 让 `routes/interview.py` 从“复杂编排者”退回“HTTP 接口层”。

- `interview_agent.py`
  - 保留纯决策逻辑。
  - 继续承载 fallback、normalize 和模型决策。

## 5. Agent State 设计

Agent State 是 Agent 的“工作记忆”，不是数据库表。

V2 State 建议包含：

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
    "targetRole": "AI 应用开发实习生",
    "resume": "...",
    "jd": "...",
    "company": "..."
  },
  "history": [],
  "lastAnswer": {
    "question": "",
    "answer": "",
    "focus": ""
  },
  "answerAnalysis": {
    "answerStatus": "不会",
    "weakAnswerStreak": 2,
    "repeatedQuestionCount": 1,
    "triggerSignals": ["weak_answer_streak"]
  },
  "retrievalQuality": {
    "roleKnowledge": {},
    "questionBank": {},
    "candidateMemory": {}
  },
  "nodeTrace": [],
  "toolCalls": []
}
```

设计原则：

- State 应该是可序列化 JSON。
- State 不应该直接保存数据库 Session、模型客户端等运行时对象。
- State 字段要能被日志记录和未来 LangGraph checkpoint 保存。
- State 只记录摘要，不保存过大的原始文档全文。

## 6. Agent Tool 设计

### 6.1 什么算 Tool

在本项目里，Tool 不是必须等同于 OpenAI / LangChain 的 tool calling 协议。

阶段二先采用“自研轻量 Tool 抽象”：

```text
一个被 Agent 调用、输入输出结构化、可记录日志的能力，就可以先视为 Tool。
```

当前可抽象为 Tool 的能力：

- `retrieve_role_knowledge`
  - 调用岗位知识库 RAG。

- `retrieve_question_bank`
  - 调用题库 RAG。

- `retrieve_candidate_memory`
  - 调用候选人画像 RAG。

- `analyze_answer`
  - 分析上一轮回答状态。

- `select_action`
  - 生成下一步动作。

- `generate_question`
  - 生成下一道问题。

- `update_candidate_memory`
  - 后续显式更新候选人训练记忆。

### 6.2 Tool 调用记录格式

建议每次工具调用记录：

```json
{
  "toolName": "retrieve_question_bank",
  "inputSummary": {
    "query": "AI 应用开发实习生 技术追问 RAG",
    "limit": 4
  },
  "outputSummary": {
    "hitCount": 3,
    "topScores": [0.92, 0.87, 0.76]
  },
  "success": true,
  "error": "",
  "elapsedMs": 38
}
```

注意：

- 不在日志里保存过长原文。
- 不记录用户敏感信息全文。
- 对简历和回答只记录摘要。
- 工具失败时记录 error 和 fallback。

## 7. Agent Trace 设计

Agent Trace 用来解释“这一轮 Agent 是怎么走到当前问题的”。

### 7.1 节点 Trace 格式

建议格式：

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
    "focus": "RAG 召回链路"
  },
  "fallbackUsed": false,
  "elapsedMs": 120,
  "error": ""
}
```

### 7.2 Trace 存储位置

当前优先不新增数据库表。

推荐先复用 `AgentDecisionLog`：

- `state_json`：保存 Agent State 摘要。
- `decision_json`：保存 Agent Decision、`nodeTrace`、`toolCalls`。

后续如果日志膨胀，再新增：

```text
agent_node_traces
agent_tool_call_logs
```

### 7.3 前端展示

前端不需要一开始展示完整 trace。

阶段二建议：

- 普通用户：展示“为什么这么问”。
- 学习/开发者视角：展示节点链路。
- Debug 面板：展示完整 trace JSON。

## 8. 轻量状态机预留

阶段二仍不直接引入完整状态机框架，但需要把状态和事件定义清楚。

### 8.1 Session 状态

建议状态：

```text
idle
collecting_profile
ready
asking
waiting_answer
analyzing_answer
retrieving_context
deciding_next_action
generating_question
updating_memory
generating_report
completed
failed
```

### 8.2 事件

建议事件：

```text
START_INTERVIEW
PROFILE_READY
QUESTION_GENERATED
ANSWER_SUBMITTED
ANSWER_ANALYZED
CONTEXT_RETRIEVED
DECISION_SELECTED
MEMORY_UPDATED
REPORT_REQUESTED
REPORT_GENERATED
ERROR_OCCURRED
RESET_SESSION
```

### 8.3 转移示例

```text
ready + START_INTERVIEW -> retrieving_context
retrieving_context + CONTEXT_RETRIEVED -> analyzing_answer
analyzing_answer + ANSWER_ANALYZED -> deciding_next_action
deciding_next_action + DECISION_SELECTED -> generating_question
generating_question + QUESTION_GENERATED -> waiting_answer
waiting_answer + ANSWER_SUBMITTED -> retrieving_context
waiting_answer + REPORT_REQUESTED -> generating_report
generating_report + REPORT_GENERATED -> completed
任意状态 + ERROR_OCCURRED -> failed
```

本阶段可以先写成常量和文档，不强制改造成状态机类。

## 9. LangGraph 迁移设计

本阶段仍然不直接引入 LangGraph。

但 Agent V2 的设计要保证未来可迁移：

| 自研 Agent V2 | LangGraph 概念 |
| --- | --- |
| Agent State JSON | Graph State |
| `observe_state` | node |
| `retrieve_context` | node / tool node |
| `analyze_answer` | node |
| `select_action` | node |
| `generate_question` | node |
| `update_memory` | node |
| `nodeTrace` | graph execution trace |
| `AgentDecisionLog` | checkpoint / trace persistence |
| fallback decision | conditional edge fallback |

未来迁移顺序：

1. 先把当前节点函数拆清楚。
2. 再把 Agent State 变成统一 TypedDict 或 Pydantic schema。
3. 再用 LangGraph StateGraph 映射节点。
4. 再引入 checkpoint 保存多轮状态。
5. 最后考虑 human-in-the-loop。

## 10. 阶段二开发顺序建议

建议分四轮开发：

### 10.1 Agent State 与 Trace 结构

目标：

- 明确 state schema。
- 明确 node trace 和 tool call 格式。
- 测试覆盖 state、trace 构造。

### 10.2 Tool 抽象

目标：

- 把三类 RAG 检索包装成 Agent Tool。
- 每个 Tool 返回统一调用摘要。
- 失败时记录 error 和 fallback 信息。

### 10.3 Orchestrator 拆分

目标：

- 新增 `run_next_question_agent`。
- 把 `routes/interview.py` 中的编排逻辑下沉到 Agent Orchestrator。
- 路由层只负责 HTTP 入参、鉴权、数据库依赖和返回响应。

### 10.4 前端 Debug 展示增强

目标：

- Agent 决策日志中展示节点链路。
- Debug 面板能看到 toolCalls 和 nodeTrace。
- 普通用户仍只看简洁解释，不被日志淹没。

## 11. 测试策略

阶段二必须继续 TDD。

后端测试建议：

- `test_agent_state.py`
  - 验证 Agent State 字段完整。
  - 验证弱回答、重复问题、剩余轮次进入 state。

- `test_agent_trace.py`
  - 验证 node trace 格式。
  - 验证 tool call summary 格式。
  - 验证错误时记录 fallback。

- `test_agent_tools.py`
  - 验证 RAG tool 返回统一结构。
  - 验证空召回、异常召回都能记录。

- `test_agent_orchestrator.py`
  - 验证 orchestrator 串联节点。
  - 验证生成问题时记录 nodeTrace 和 toolCalls。
  - 验证不破坏 `/api/interview/next-question` 当前响应。

前端测试建议：

- `frontend_agent_logs.test.mjs`
  - 验证 Agent 日志展示 triggerRules。
  - 增加 nodeTrace 和 toolCalls 展示断言。

全量验证：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 12. 非目标

阶段二明确不做：

- 不直接安装 LangGraph。
- 不直接引入 LangChain。
- 不做多 Agent 协作。
- 不做云服务器部署。
- 不做 Docker / Nginx。
- 不重构前端框架。
- 不大改 RAG 检索算法。
- 不新增复杂任务队列。
- 不一次性新增多张 Agent 日志表。
- 不把所有后端逻辑推倒重写。

## 13. 验收标准

阶段二完成后应满足：

- Agent 节点边界清晰。
- Agent State 字段稳定、可序列化、可测试。
- RAG 检索、回答分析、问题生成等能力有 Tool 抽象。
- 每轮 Agent 决策能看到 nodeTrace。
- 每次 Tool 调用能看到输入摘要、输出摘要、成功状态和错误信息。
- fallback 决策能被日志追踪。
- `/api/interview/next-question` 行为保持兼容。
- 前端 Agent 日志面板能展示节点链路或工具摘要。
- 能清楚解释自研 Agent 和 LangGraph 的关系。
- 后端全量测试通过。
- 前端测试脚本通过。

## 14. 面试表达

可以这样介绍阶段二：

> 我在项目里把 Agent 从简单的 prompt 调用升级成了轻量工作流。每轮面试会先观察状态，读取用户档案、历史回答和剩余轮次；然后调用 RAG 工具召回岗位知识、题库和候选人画像；再分析上一轮回答质量，决定下一步是深挖、降难度、切换话题还是结束；最后生成下一题并记录 nodeTrace 和 toolCalls。当前是自研轻量实现，没有直接上 LangGraph，是因为我想先把状态、节点、工具和日志边界讲清楚，后续可以平滑迁移到 LangGraph StateGraph 和 checkpoint。

如果面试官问“这算 Agent 吗”，可以这样回答：

> 我理解 Agent 不只是一次 LLM 调用，而是围绕目标维护状态、调用工具、根据观察结果做动作选择，并记录可追踪的执行过程。我的项目里 Agent 会结合 RAG 结果、用户回答质量和面试轮次做下一步决策，所以它是一个轻量 Orchestrator Agent。

如果面试官问“为什么不用 LangGraph”，可以这样回答：

> 当前项目先采用自研轻量 Agent，是为了降低复杂度并确保我能讲清楚每个节点的输入输出。等流程稳定后，可以把 observe_state、retrieve_context、analyze_answer、select_action、generate_question、update_memory 迁移成 LangGraph nodes，并用 checkpoint 保存多轮面试状态。

## 15. 追求目标模式建议

如果要用 Codex 的追求目标模式执行阶段二，可以输入：

```text
根据 docs/superpowers/specs/2026-06-09-agent-engineering-v2-design.md，
持续推进 AI 模拟面试系统阶段二：Agent 工程化增强。

要求：
1. 每次开发前先用中文解释本轮要学的 Agent 工程化知识点。
2. 开发时优先遵循测试驱动，先写后端测试再实现。
3. 当前阶段优先改 backend_python 下的 Agent 相关模块和测试。
4. 保持 /api/interview/next-question 兼容，不破坏现有前端调用。
5. 不直接引入 LangGraph，不安装 LangChain。
6. 不做 Docker、Nginx、云服务器上线。
7. 每轮开发后总结改了哪些文件、为什么这么改、我面试时应该怎么讲。
8. 完成后运行 python -m pytest -q 和所有前端 .mjs 测试。
```

## 16. 后续衔接

阶段二完成后，再进入阶段三：RAG 工程化增强。

阶段三重点应包括：

- 样例知识库建设。
- metadata filter。
- RAG 质量评估面板。
- 引用来源展示。
- 多路召回质量对比。

Agent 工程化先完成，可以让后续 RAG 能力以 Tool 的方式接入，而不是散落在路由函数中。
