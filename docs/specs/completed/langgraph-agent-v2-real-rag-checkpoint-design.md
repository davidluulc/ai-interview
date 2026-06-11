# LangGraph Agent V2：真实 RAG 与 Checkpoint 设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统 LangGraph 路线的第二阶段开发。

第一版 LangGraph POC 已经完成：

```text
StateGraph 可以 compile / invoke
observe_state -> analyze_answer -> retrieve_context -> select_action -> generate_question -> update_memory 能跑通
有独立实验接口 /api/langgraph-agent/next-question-poc
不影响现有 /api/interview/next-question 主流程
```

但 V1 仍然是概念验证：

```text
retrieve_context 使用 POC 样例数据
generate_question 使用 stub 文案
select_action 使用简化规则
没有 checkpoint
没有 thread state
没有写入 Agent 日志
```

V2 的目标是把 LangGraph 从“能跑通的示例图”推进到“接入真实项目能力的旁路 Agent 工作流”。

## 2. 本阶段总目标

V2 目标：

```text
保留现有自研 Agent 主流程稳定运行，
继续使用旁路 LangGraph 实验接口，
但让 LangGraph POC 接入真实三类 RAG、真实 Agent 决策逻辑，
并引入 checkpoint / thread_id 概念，让多轮 graph state 可保存、可查询、可解释。
```

完成后，项目应能证明：

```text
自研 Agent 的状态、工具、决策、日志，不只是能被写成文档，
而是可以真正迁移到 LangGraph 的 StateGraph + checkpoint 工作流里。
```

## 3. 为什么不一次性替换主流程

当前 `/api/interview/next-question` 已经承担真实面试体验：

- 读取投递档案。
- 调用三类 RAG。
- 构造 Agent State。
- 调用模型决策。
- 生成下一题。
- 写 Agent 日志。
- 返回前端可展示字段。

如果直接把主流程全部替换为 LangGraph，会同时影响：

```text
真实面试功能
RAG 命中
Agent 决策
问题生成
前端展示
历史记录
训练任务
测试基线
```

风险太大，也不利于学习。V2 继续采用“双轨”策略：

```text
主流程：继续使用现有自研 Agent
旁路流程：LangGraph V2，逐步接入真实能力
```

等 V2 稳定后，再评估是否增加：

```text
agentRuntime = classic | langgraph
```

但这不是本阶段目标。

## 4. V2 能力边界

### 本阶段要做

- 真实 RAG 接入：
  - 岗位知识库 RAG。
  - 题库 RAG。
  - 候选人画像 RAG。
- 真实 Agent 决策接入：
  - 复用 `decide_next_action`。
  - 复用 fallback / normalize / guardrail 逻辑。
  - 保留 `decisionSummary`。
- Graph thread state：
  - 请求支持 `threadId`。
  - LangGraph invoke 使用 `configurable.thread_id`。
  - 响应返回 `threadId`。
- Checkpoint：
  - 第一版使用 LangGraph `MemorySaver`。
  - 支持同一 thread 多轮状态保留。
  - 提供查询最近 checkpoint 摘要的实验接口。
- 可观测性：
  - 返回 `nodeTrace`。
  - 返回 `toolCalls`。
  - 返回 `checkpointSummary`。
  - 可选写入现有 `AgentDecisionLog`。
- 文档：
  - 新增学习文档解释 checkpoint、thread state、普通数据库记录的区别。

### 本阶段不做

- 不替换 `/api/interview/next-question`。
- 不把前端主流程改成 LangGraph。
- 不做完整 human-in-the-loop 产品功能。
- 不做复杂多 Agent。
- 不做 LangGraph 云部署。
- 不做 Docker / Nginx / 云服务器上线。
- 不做 Vue3 前端重构。
- 不重构 RAG 底层检索算法。
- 不新增复杂数据库迁移。

## 5. V2 目标工作流

V2 的 LangGraph 工作流：

```text
START
-> observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
-> write_trace
-> END
```

其中 V2 相比 V1 的变化：

| 节点 | V1 | V2 |
| --- | --- | --- |
| observe_state | 读取输入 state | 增加 threadId、applicationProfileId、roundCount |
| analyze_answer | 复用回答分析 | 保持，并补充 topicLock / repeatedQuestion 摘要 |
| retrieve_context | POC 样例 hits | 接真实三类 RAG |
| select_action | 简化规则 | 接 `decide_next_action` 和 fallback |
| generate_question | stub 文案 | 优先复用现有问题生成能力或隔离式 LLM 调用 |
| update_memory | deferred 摘要 | 继续 deferred，但记录 weakSignals 和 selectedTrainingTask |
| write_trace | 无独立节点 | 形成 graph 执行摘要和可选日志写入 |

## 6. 数据结构设计

### 6.1 LangGraph 请求

新增或扩展实验接口：

```text
POST /api/langgraph-agent/next-question-v2
```

请求体：

```json
{
  "threadId": "interview-demo-001",
  "applicationProfileId": 1,
  "profile": {},
  "history": [],
  "nextStage": "技术追问",
  "agentMode": "coach",
  "useRealRag": true,
  "useRealDecision": true
}
```

字段说明：

- `threadId`：LangGraph checkpoint 维度，同一个 thread 表示同一场实验面试。
- `applicationProfileId`：可选，用于读取真实投递档案和候选人画像。
- `profile`：候选人资料。
- `history`：历史问答。
- `nextStage`：下一阶段。
- `agentMode`：`coach` 或 `interview`。
- `useRealRag`：是否接真实 RAG，测试中可关闭。
- `useRealDecision`：是否接真实 Agent 决策，测试中可关闭。

### 6.2 LangGraph 响应

响应体：

```json
{
  "threadId": "interview-demo-001",
  "graphState": {},
  "nodeTrace": [],
  "toolCalls": [],
  "decision": {},
  "nextQuestion": {},
  "memoryUpdate": {},
  "checkpointSummary": {
    "enabled": true,
    "threadId": "interview-demo-001",
    "stateKeys": ["profile", "history", "decision", "nextQuestion"],
    "nodeCount": 7
  }
}
```

### 6.3 Checkpoint 查询接口

新增实验接口：

```text
GET /api/langgraph-agent/checkpoint/{thread_id}
```

第一版返回摘要，不返回超长完整 state：

```json
{
  "threadId": "interview-demo-001",
  "exists": true,
  "roundCount": 2,
  "lastAction": "lower_difficulty",
  "lastQuestion": "你能解释 RAG 为什么需要重排吗？",
  "nodeTraceCount": 7
}
```

## 7. 模块规划

现有 V1 模块：

```text
backend_python/langgraph_agent/state.py
backend_python/langgraph_agent/nodes.py
backend_python/langgraph_agent/graph.py
backend_python/routes/langgraph_agent.py
```

V2 建议新增：

```text
backend_python/langgraph_agent/adapters.py
backend_python/langgraph_agent/checkpoint.py
backend_python/langgraph_agent/service.py
```

### 7.1 adapters.py

职责：

- 把现有 RAG / Agent 能力包装给 LangGraph 节点使用。

建议函数：

```text
retrieve_real_context_for_graph()
decide_real_action_for_graph()
generate_real_question_for_graph()
```

要求：

- 不复制 RAG 算法。
- 不复制 Agent 决策算法。
- 只做适配层。

### 7.2 checkpoint.py

职责：

- 管理 LangGraph checkpointer。
- 第一版使用 `MemorySaver`。
- 提供 `build_graph_config(thread_id)`。
- 提供 `summarize_checkpoint(thread_id)`。

边界：

- 暂不做数据库持久化 checkpoint。
- 暂不做跨进程恢复。

### 7.3 service.py

职责：

- 面向路由提供稳定函数：

```text
run_langgraph_agent_v2()
get_langgraph_checkpoint_summary()
```

好处：

- 路由层不直接理解 LangGraph 内部细节。
- 后续替换 checkpoint 实现时，不影响接口层。

## 8. 真实 RAG 接入设计

V2 不重写 RAG，而是复用已有检索服务。

可复用模块：

```text
backend_python/retrieval_service.py
backend_python/rag.py
backend_python/question_rag.py
backend_python/candidate_memory.py
backend_python/rag_quality.py
backend_python/agent_tools.py
```

建议优先复用 `agent_tools.py` 里已有工具封装，因为它已经能输出 toolCall 摘要。

LangGraph 的 `retrieve_context` 节点应该返回：

```text
roleHits
questionHits
memoryHits
toolCalls
retrievalQuality
```

测试中允许注入 fake retriever，避免每次测试依赖真实数据库和模型。

## 9. 真实 Agent Decision 接入设计

V2 的 `select_action` 节点应复用：

```text
backend_python/interview_agent.py
```

优先目标：

- 复用 `decide_next_action`。
- 保留 fallback。
- 保留 normalize / guardrail。
- 保留 `decisionSummary`。

测试中允许使用 fake `call_model_fn`，返回稳定 JSON。

如果模型不可用，必须能 fallback，不让 graph 崩掉。

## 10. 问题生成设计

V2 有两种方案：

### 方案 A：继续 stub 生成

优点：

- 稳定。
- 测试简单。

缺点：

- “真实 LangGraph Agent”说服力不足。

### 方案 B：复用现有问题生成 prompt 和 LLM 调用

优点：

- 更接近真实面试链路。
- 面试表达更强。

缺点：

- 需要处理模型超时、API Key、测试稳定性。

### V2 推荐

第一轮实现：

```text
测试环境使用 stub。
运行环境允许注入 real question generator。
```

这样既保证测试稳定，又给真实链路留接口。

## 11. Checkpoint 设计

第一版 checkpoint 使用：

```text
langgraph.checkpoint.memory.MemorySaver
```

原因：

- 不需要数据库迁移。
- 适合 POC。
- 可以证明 thread_id / checkpoint 的核心概念。

使用方式：

```text
graph.compile(checkpointer=memory_saver)
graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
```

需要记录：

- `threadId`。
- 最新 decision。
- 最新 nextQuestion。
- nodeTrace 数量。
- roundCount。

重要边界：

```text
MemorySaver 是进程内存级别，服务重启后会丢失。
它证明 checkpoint 概念，不代表生产级持久化。
```

后续可升级：

```text
SQLite checkpoint
PostgreSQL checkpoint
与 AgentDecisionLog 联动
```

## 12. Human-in-the-loop 预留

V2 不做完整 human-in-the-loop，但要把设计写清楚。

后续可在以下节点暂停：

```text
select_action 后
generate_question 前
generate_report 前
```

适合人工介入的情况：

- Agent 决定连续深挖同一薄弱点。
- Agent 决定结束面试。
- Agent 生成的追问可能过难。
- 用户主动要求切换到学习辅导。

后续接口设想：

```text
POST /api/langgraph-agent/human-approval
```

本阶段只做文档预留，不实现 interrupt。

## 13. 测试策略

必须继续 TDD。

### 13.1 Adapter 测试

验证：

- fake retriever 能注入。
- 真实 RAG adapter 返回三类 hits。
- toolCalls 字段稳定。
- RAG 失败时 graph 可以 fallback。

### 13.2 Decision 测试

验证：

- fake model decision 能被 graph 使用。
- 非法模型输出会 fallback。
- `decisionSummary` 存在。

### 13.3 Checkpoint 测试

验证：

- 同一个 threadId 连续 invoke 后可查询摘要。
- 不同 threadId 状态隔离。
- checkpointSummary 包含 threadId、nodeTraceCount、lastAction。

### 13.4 Route 测试

验证：

- `POST /api/langgraph-agent/next-question-v2` 可调用。
- `GET /api/langgraph-agent/checkpoint/{thread_id}` 可调用。
- 现有 `/api/interview/next-question` 不被替换。

### 13.5 全量回归

必须运行：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 14. 分阶段开发建议

### 阶段 1：Checkpoint 基础

目标：

- 增加 `threadId`。
- 引入 `MemorySaver`。
- graph 支持 config。
- 新增 checkpoint summary。

### 阶段 2：真实 RAG Adapter

目标：

- `retrieve_context` 支持真实三类 RAG。
- 测试中仍可注入 fake retriever。
- toolCalls 和 retrievalQuality 保持稳定。

### 阶段 3：真实 Agent Decision Adapter

目标：

- `select_action` 复用现有 `decide_next_action`。
- 非法输出 fallback。
- decisionSummary 保留。

### 阶段 4：V2 实验接口

目标：

- 新增 `next-question-v2`。
- 新增 checkpoint 查询接口。
- 不影响 V1 POC 和主流程。

### 阶段 5：学习文档和验收

目标：

- 新增学习文档。
- 更新进度。
- 运行全量测试。

## 15. 面试表达目标

完成 V2 后，可以这样讲：

```text
第一版 LangGraph POC 只是跑通了 StateGraph 节点链路。第二版我把它接入了项目的真实三类 RAG 和现有 Agent 决策逻辑，并引入 thread_id 和 MemorySaver checkpoint。这样同一场面试实验可以保留 graph state，方便做多轮状态追踪和调试回放。主流程仍然保留自研 Agent，LangGraph 作为旁路工作流验证，这样风险可控，也能证明项目具备迁移到标准 Agent 框架的能力。
```

如果面试官问为什么不用 LangGraph 直接替换主流程：

```text
我没有直接替换，是因为主流程已经承载真实面试、RAG、训练任务和历史记录。直接替换会把风险集中到一个大改动里。所以我先做旁路 LangGraph V2，接真实能力、跑 checkpoint、保持测试覆盖。等旁路稳定后，再考虑用 agentRuntime 参数做灰度切换。
```

## 16. 下一步

下一步应写 implementation plan：

```text
docs/plans/active/langgraph-agent-v2-real-rag-checkpoint.md
```

然后按 TDD 执行：

```text
Checkpoint 测试
-> Adapter 测试
-> Decision 测试
-> Route 测试
-> 学习文档
-> 全量验证
```
