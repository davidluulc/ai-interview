# LangGraph Runtime Governance V3 设计文档

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段开发：在已经完成 classic Agent、Agent Policy、LangGraph V1/V2 旁路、AI Debug Console V1 的基础上，把 LangGraph 从“能跑通的旁路工作流”升级为“可治理的 Agent Runtime”。

本阶段重点不是再证明 LangGraph 能不能跑，而是解决更接近企业 AI 应用的问题：

```text
一次 Agent 工作流能不能恢复？
关键决策能不能暂停等待人工判断？
classic Agent 和 LangGraph Agent 能不能灰度切换？
LangGraph 运行状态能不能进入 AI Debug Console？
如果结果异常，能不能回放状态并定位是哪一步出问题？
```

官方能力边界参考：

- LangGraph Persistence 文档说明，checkpointer 用于把 thread 的 graph state 保存为 checkpoint，适合 conversation continuity、human-in-the-loop、time travel 和 fault tolerance。
- LangGraph Checkpointers 文档说明，`thread_id` 是 checkpointer 保存和恢复 checkpoint 的主键。
- LangGraph Interrupts 文档说明，`interrupt()` 可以在图节点中暂停执行，LangGraph 会通过 persistence layer 保存状态，并在后续用 `Command(resume=...)` 恢复。

参考链接：

- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/checkpointers
- https://docs.langchain.com/oss/python/langgraph/interrupts

## 2. 当前项目状态

当前已经落地：

```text
classic Interview Orchestrator Agent
Agent State / Tool Calls / Agent Decision
Agent Policy 公共策略层
coach / interview 双模式
三类 RAG：岗位知识库、题库、候选人画像
LangGraph V1 POC
LangGraph V2 旁路工作流
MemorySaver checkpoint 摘要
LangGraph checkpoint 查询接口
AI Debug Console V1
Vue3 管理员后台
```

当前 LangGraph 相关证据：

- `backend_python/langgraph_agent/state.py`
- `backend_python/langgraph_agent/nodes.py`
- `backend_python/langgraph_agent/graph.py`
- `backend_python/langgraph_agent/service.py`
- `backend_python/langgraph_agent/checkpoint.py`
- `backend_python/routes/langgraph_agent.py`
- `tests/test_langgraph_agent_state.py`
- `tests/test_langgraph_agent_nodes.py`
- `tests/test_langgraph_agent_checkpoint.py`
- `tests/test_langgraph_agent_graph.py`
- `tests/test_langgraph_agent_graph_v2.py`
- `tests/test_langgraph_agent_route.py`

当前短板：

- checkpoint 仍以 MemorySaver 为主，进程重启后不可长期保留。
- LangGraph 仍是旁路实验能力，尚未形成 runtime 灰度切换机制。
- 没有真正的 interrupt / resume 实验闭环。
- AI Debug Console 可以展示 LangGraph 摘要，但还不能清楚展示暂停原因、恢复决策和 runtime 差异。
- classic Agent 与 LangGraph 的运行差异还不能被系统性对比。

## 3. 本阶段定位

阶段名称：

```text
LangGraph Runtime Governance V3
```

核心目标：

```text
让 LangGraph 从“旁路实验接口”升级为“可持久化、可暂停、可恢复、可灰度切换、可调试”的 Agent 工作流治理能力。
```

面试表达目标：

```text
我没有直接把主面试流程替换成 LangGraph，而是采用 classic Agent 稳定主流程、LangGraph 旁路演进的双轨架构。
在 V3 阶段，我重点做 runtime governance：checkpoint 持久化抽象、interrupt/resume 实验接口、classic/langgraph 灰度切换和 AI Debug Console 可观测性。
这样既保证已有功能稳定，又能证明我理解 Agent 工作流的状态管理、人工介入和故障恢复。
```

## 4. 本阶段非目标

本阶段明确不做：

- 不替换 `/api/interview/next-question` 主面试接口。
- 不删除 classic Agent。
- 不把 LangGraph 设为所有用户默认 runtime。
- 不重写 RAG 检索算法。
- 不做生产级 RAG 文件解析、OCR、PDF / Word 入库。
- 不做 Docker、Nginx、VPS、域名、HTTPS 上线。
- 不做全站 UI 重构。
- 不引入复杂多 Agent 平台。
- 不做 LangSmith 云端部署。
- 不做完整商业级 RBAC 审批后台。

本阶段可以增加实验接口、配置开关、调试页面和学习文档，但必须保持现有用户面试流程稳定。

## 5. 关键概念说明

### 5.1 thread_id

`thread_id` 是一场 LangGraph 工作流的会话编号。

在本项目中可以对应：

```text
一次实验面试
一次候选人训练会话
一次管理员调试运行
```

同一个 `thread_id` 下，多轮 graph run 可以共享和恢复状态。

### 5.2 checkpoint

checkpoint 是 graph state 在某个执行边界上的快照。

它不是普通日志。日志主要用于事后观察，checkpoint 还承担恢复执行、状态回放和 human-in-the-loop 的基础能力。

### 5.3 interrupt / resume

interrupt 表示图执行到某个节点时主动暂停，等待外部输入。

在本项目中，适合暂停的情况包括：

```text
Agent 准备连续深挖同一个薄弱点
Agent 准备提前结束面试
Agent 判断候选人连续不会，建议切到学习辅导
Agent 准备切换 runtime
Agent Policy 标记 requiresHumanReview=true
```

resume 表示人类或系统给出选择后，从保存的 checkpoint 继续执行。

### 5.4 agentRuntime

`agentRuntime` 表示本轮面试问题生成使用哪条 Agent 执行链路：

```text
classic：继续使用当前稳定的自研 Agent 主流程
langgraph：使用 LangGraph 工作流实验链路
shadow：主流程仍用 classic，但后台同时跑 LangGraph 旁路用于对比
```

第一版默认仍然使用 classic。LangGraph 只允许通过实验接口、管理员配置或 shadow 模式进入。

## 6. 总体架构

本阶段采用三层设计：

```text
前端 / 管理员后台
-> Runtime Control API
-> Agent Runtime Service
-> classic Agent 或 LangGraph Graph
-> AI Debug Console
```

### 6.1 Runtime Control API

新增或增强实验接口：

```text
POST /api/langgraph-agent/runtime/run
POST /api/langgraph-agent/runtime/resume
GET  /api/langgraph-agent/runtime/checkpoint/{thread_id}
GET  /api/langgraph-agent/runtime/runs/{thread_id}
```

接口职责：

- 运行 LangGraph runtime。
- 读取 checkpoint 摘要。
- 恢复 interrupt。
- 返回 runtime trace。

第一版可以只做管理员或测试用途，不直接开放给普通用户主流程。

### 6.2 Agent Runtime Service

建议新增：

```text
backend_python/agent_runtime.py
```

职责：

- 解析 `agentRuntime`。
- 决定本轮使用 classic、langgraph 还是 shadow。
- 统一返回 runtime summary。
- 避免接口层直接写复杂 if/else。

建议核心输出：

```json
{
  "runtime": "classic",
  "threadId": "interview-123",
  "status": "completed",
  "decision": {},
  "question": {},
  "checkpointSummary": {},
  "interrupt": null,
  "runtimeTrace": []
}
```

### 6.3 Checkpoint Store 抽象

当前 MemorySaver 适合 POC，但不适合长期恢复。第一版不一定要立即接 PostgreSQL 或 Redis，但要抽象出可替换边界。

建议新增：

```text
backend_python/langgraph_agent/checkpoint_store.py
```

职责：

- 封装当前 MemorySaver。
- 暴露统一方法：
  - `save_summary`
  - `get_summary`
  - `list_thread_runs`
  - `mark_interrupted`
  - `mark_resumed`
- 后续可以替换为 SQLite / PostgreSQL / Redis backed checkpoint。

注意：LangGraph 自身 checkpointer 和项目业务摘要表不是同一个东西。第一版可以继续使用 LangGraph MemorySaver 保存运行状态，同时把可读摘要写入项目自己的记录结构，方便后台展示和测试。

### 6.4 Human Review Policy

建议新增：

```text
backend_python/human_review_policy.py
```

职责：

- 判断哪些 LangGraph 状态需要 interrupt。
- 输入 Agent Policy 输出、answerAnalysis、history、retrievalQuality。
- 输出是否暂停、暂停原因和可选动作。

示例输出：

```json
{
  "shouldInterrupt": true,
  "reason": "候选人连续 3 次回答不会，建议人工选择继续面试还是切到学习辅导。",
  "options": ["continue_interview", "switch_to_coach", "end_interview"]
}
```

## 7. 数据结构设计

### 7.1 Runtime Run Request

```json
{
  "threadId": "interview-demo-001",
  "agentRuntime": "langgraph",
  "agentMode": "coach",
  "applicationProfileId": 1,
  "profile": {},
  "history": [],
  "answer": "我不太会",
  "nextStage": "技术追问",
  "enableInterrupt": true
}
```

字段说明：

- `threadId`：LangGraph checkpoint 维度。
- `agentRuntime`：`classic | langgraph | shadow`。
- `agentMode`：`coach | interview`。
- `applicationProfileId`：候选人档案。
- `history`：历史问答。
- `enableInterrupt`：是否允许中途暂停。

### 7.2 Runtime Run Response

```json
{
  "threadId": "interview-demo-001",
  "runtime": "langgraph",
  "status": "interrupted",
  "question": null,
  "decision": {},
  "interrupt": {
    "reason": "连续弱回答，需要人工选择下一步。",
    "options": ["continue_interview", "switch_to_coach", "end_interview"]
  },
  "checkpointSummary": {
    "exists": true,
    "threadId": "interview-demo-001",
    "currentNode": "human_review",
    "nodeTraceCount": 5,
    "lastAction": "lower_difficulty",
    "requiresHumanReview": true
  },
  "runtimeTrace": []
}
```

### 7.3 Resume Request

```json
{
  "threadId": "interview-demo-001",
  "decision": "switch_to_coach",
  "comment": "候选人连续不会，先进入学习辅导。"
}
```

### 7.4 Resume Response

```json
{
  "threadId": "interview-demo-001",
  "runtime": "langgraph",
  "status": "completed",
  "question": {
    "content": "我们先把 checkpoint 的概念拆开讲..."
  },
  "resumeDecision": "switch_to_coach",
  "checkpointSummary": {},
  "runtimeTrace": []
}
```

## 8. 后端阶段拆分

### 阶段 1：Checkpoint Store 摘要抽象

目标：

- 保留现有 MemorySaver。
- 增加项目侧 checkpoint summary 抽象。
- 让测试可以不依赖真实外部存储。

验收：

- 同一个 `threadId` 能查询最近 checkpoint 摘要。
- checkpoint summary 包含 currentNode、lastAction、requiresHumanReview、nodeTraceCount。
- 旧 `/api/langgraph-agent/checkpoint/{thread_id}` 保持兼容。

### 阶段 2：Human Review Policy

目标：

- 抽出是否需要人工介入的规则。
- 与 Agent Policy 输出解耦。

验收：

- `requiresHumanReview=true` 能触发 interrupt 建议。
- 连续弱回答能触发人工选择建议。
- 正常问答不触发 interrupt。
- policy 输出包含 reason 和 options。

### 阶段 3：LangGraph Interrupt / Resume 实验接口

目标：

- 增加 runtime run / resume 接口。
- 允许图在 human_review 节点暂停。
- resume 后继续生成下一题。

验收：

- `enableInterrupt=true` 且命中人工复核条件时返回 `status=interrupted`。
- response 包含 interrupt payload。
- resume 接口能根据 `threadId` 和 decision 恢复流程。
- 错误的 `threadId` 返回清晰错误。

### 阶段 4：Agent Runtime 灰度切换

目标：

- 引入 `agentRuntime = classic | langgraph | shadow`。
- 默认 classic。
- shadow 模式只用于对比，不影响真实用户问题。

验收：

- classic 模式保持现有行为。
- langgraph 模式走 LangGraph 实验链路。
- shadow 模式返回 classic 结果，同时记录 LangGraph shadow summary。
- 不破坏 `/api/interview/next-question` 兼容性。

### 阶段 5：AI Debug Console 增强

目标：

- 在管理员后台展示 runtime、interrupt、resume、checkpoint 摘要。
- 能区分 classic / langgraph / shadow。

验收：

- AI Debug Console 能看到 runtime 类型。
- 能看到是否发生 interrupt。
- 能看到 resume decision。
- 能看到 checkpoint currentNode 和 requiresHumanReview。
- 页面不出现 `undefined`、`Not Found` 和横向溢出。

## 9. 前端阶段拆分

本阶段不做全站 UI 重构，只增强 Vue3 管理员后台。

### 9.1 管理员后台 Runtime 状态展示

在 AI Debug Console 增加：

```text
Runtime：classic / langgraph / shadow
执行状态：completed / interrupted / failed
当前节点：currentNode
是否需要人工介入：requiresHumanReview
恢复决策：resumeDecision
```

### 9.2 Human Review 调试面板

第一版只做管理员调试用途，不进入普通用户面试页面。

可以展示：

```text
暂停原因
可选动作
恢复记录
原始 interrupt payload
```

是否做“点击恢复”按钮，取决于后端阶段 3 的实现进度。第一版可以先只展示状态，避免误操作。

## 10. 测试策略

### 10.1 后端测试

新增或更新：

```text
tests/test_langgraph_runtime_checkpoint_store.py
tests/test_human_review_policy.py
tests/test_langgraph_runtime_interrupt_resume.py
tests/test_agent_runtime_switching.py
tests/test_admin_ai_debug.py
```

覆盖：

- checkpoint summary 存取。
- human review policy 判断。
- interrupt payload shape。
- resume 决策恢复。
- agentRuntime 默认 classic。
- shadow 模式不影响主结果。
- AI Debug 聚合 runtime 字段。

### 10.2 前端测试

新增或更新：

```text
frontend/src/stores/admin.test.ts
frontend/src/pages/app/admin-page.test.ts
```

覆盖：

- runtime 字段展示。
- interrupt 状态展示。
- checkpoint currentNode 展示。
- resumeDecision 展示。
- 空状态不出现 `undefined`。

### 10.3 验证命令

阶段结束必须运行：

```powershell
python -m pytest -q
npm.cmd run test
npm.cmd run build
```

并用浏览器验证：

```text
http://127.0.0.1:5173/vue/app/admin
```

## 11. 风险与约束

### 11.1 interrupt 依赖 checkpoint

LangGraph interrupt 需要 checkpointer 和 `thread_id`。如果没有稳定 checkpoint，resume 可能无法可靠恢复。因此阶段 1 必须先做 checkpoint summary 和状态边界，再做 interrupt / resume。

### 11.2 不直接替换主流程

当前 classic Agent 已经承载真实面试体验。LangGraph V3 应先作为实验 runtime 或 shadow runtime，不应直接替换主接口。

### 11.3 避免过早产品化人工审批

human-in-the-loop 第一版重点是理解机制和调试链路，不是做复杂审批后台。先让后端闭环和 AI Debug 可见，再考虑普通用户产品化。

### 11.4 checkpoint 与业务数据库边界

checkpoint 是 graph state 快照，业务数据库记录的是用户、档案、面试历史、RAG 文档和日志。两者不要混在一个概念里。

## 12. 学习文档要求

本阶段完成后新增学习文档：

```text
docs/learning/19-LangGraph工作流治理如何理解checkpoint-interrupt-runtime.md
```

文档需要讲清：

- `thread_id` 是什么。
- checkpoint 和普通日志有什么区别。
- interrupt / resume 为什么需要 checkpoint。
- classic Agent 和 LangGraph Agent 的区别。
- shadow runtime 为什么适合灰度。
- 面试时如何讲“没有直接替换主流程”的工程判断。

## 13. 面试表达

阶段完成后，建议表达：

```text
我在项目里没有直接把稳定的自研 Agent 主流程替换成 LangGraph，而是采用 runtime governance 的方式渐进接入。
classic Agent 继续承载线上稳定流程，LangGraph 先作为实验 runtime 和 shadow runtime。
我实现了 checkpoint summary、interrupt/resume 实验链路、human review policy 和 AI Debug Console 展示。
这样一方面能保证主流程稳定，另一方面能证明 Agent 工作流具备状态恢复、人工介入、灰度切换和可观测能力。
```

## 14. 本阶段完成定义

本阶段完成必须同时满足：

- active plan 已编写。
- 后端 checkpoint summary 抽象可测试。
- human review policy 可测试。
- LangGraph interrupt / resume 实验接口可测试。
- agentRuntime 灰度切换至少完成后端实验链路。
- AI Debug Console 能展示 runtime、interrupt、resume、checkpoint 摘要。
- 学习文档已补充。
- 全量后端测试通过。
- 全量前端测试通过。
- 前端构建通过。
- 浏览器验证管理员后台通过。

