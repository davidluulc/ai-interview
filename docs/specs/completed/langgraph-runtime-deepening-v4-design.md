# LangGraph Runtime Deepening V4 设计文档

更新时间：2026-06-14

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段开发：在已经完成 classic Agent、Agent Policy、LangGraph V1/V2 旁路、LangGraph Runtime Governance V3、AI Debug Console V1 的基础上，把 LangGraph 从“可运行、可暂停、可恢复的实验 runtime”继续升级为“可评估、可灰度、可迁移的候选主链路”。

本阶段不是重新接入 LangGraph，也不是为了展示框架而重写 Agent。

本阶段真正要解决的是：

```text
LangGraph 和 classic Agent 的效果差异能不能被系统记录？
LangGraph shadow 运行结果能不能被评估？
checkpoint 摘要能不能从内存态走向更稳定的项目侧持久化？
什么时候可以把某些用户、某些模式、某些场景切到 LangGraph？
如果 LangGraph 输出异常，能不能自动回退 classic Agent？
这些过程能不能在管理员后台看清楚？
```

## 2. 当前项目状态

当前已落地能力：

```text
classic Interview Orchestrator Agent
Agent State / Tool Calls / Agent Decision
Agent Policy 公共策略层
coach / interview 双模式
三类 RAG：岗位知识库、题库、候选人画像
LangGraph V1 POC
LangGraph V2 真实 RAG / Agent decision 旁路
LangGraph Runtime Governance V3
runtime/run 与 runtime/resume 实验接口
checkpoint summary store
human review policy
agentRuntime = classic | langgraph | shadow 的后端抽象
AI Debug Console V1
Vue3 管理员后台
```

主要代码证据：

```text
backend_python/agent_runtime.py
backend_python/human_review_policy.py
backend_python/ai_debug.py
backend_python/langgraph_agent/
backend_python/routes/langgraph_agent.py
backend_python/routes/admin.py
frontend/src/pages/app/AdminPage.vue
frontend/src/stores/admin.ts
tests/test_agent_runtime_switching.py
tests/test_human_review_policy.py
tests/test_langgraph_runtime_interrupt_resume.py
tests/test_langgraph_runtime_checkpoint_store.py
tests/test_admin_ai_debug.py
```

当前短板：

- shadow 模式能返回 classic 主结果和 LangGraph 旁路摘要，但还没有系统性的质量对比指标。
- checkpoint summary 已经有内存态 store，但仍不是可长期恢复的持久化记录。
- runtime 切换已经有抽象，但缺少“什么时候允许切 langgraph”的门禁规则。
- AI Debug Console 能看 runtime 信息，但还不能很好地回答“LangGraph 比 classic 好在哪里或差在哪里”。
- 主面试接口仍然没有明确的 runtime migration 策略。

## 3. 本阶段定位

阶段名称：

```text
LangGraph Runtime Deepening V4
```

核心定位：

```text
把 LangGraph 从实验 runtime 深化为可评估、可观测、可灰度迁移的候选 Agent 主链路。
```

本阶段继续坚持双轨策略：

```text
classic Agent：稳定主链路，继续服务真实面试
LangGraph Agent：候选 runtime，用于 shadow compare、checkpoint 持久化验证和后续灰度迁移
```

短期不直接替换 `/api/interview/next-question`。

V4 的重点不是“能不能跑 LangGraph”，而是“怎么证明 LangGraph 可以被放心迁移到主链路”。

## 4. 为什么不直接迁移主链路

当前 classic Agent 已经承载：

- 面试问题生成。
- 三类 RAG 检索。
- Agent decision。
- fallback / normalize / guardrail。
- 历史记录。
- 报告生成。
- 训练任务闭环。
- 前端展示。

如果直接把主链路切到 LangGraph，会同时影响面试体验、报告、训练、日志、后台调试和用户数据闭环。

因此 V4 采用：

```text
先 shadow compare
-> 再 runtime quality gate
-> 再小范围灰度
-> 最后再评估主链路迁移
```

这是一种更接近真实生产系统的迁移路线。它表达的不是“不敢用 LangGraph”，而是：

```text
框架能力必须经过业务效果和稳定性验证，不能因为框架先进就直接替换核心链路。
```

## 5. 本阶段目标

### 5.1 Shadow Compare 质量评估

在 `agentRuntime=shadow` 时：

```text
用户仍然看到 classic Agent 的问题
后台同时运行 LangGraph
系统记录两边的 decision、question、difficulty、focus、checkpoint、runtimeTrace
系统生成 comparison summary
```

目标是能回答：

- 两边下一步动作是否一致。
- 两边难度是否一致。
- LangGraph 是否触发了 human review。
- LangGraph 是否生成了更安全的问题。
- LangGraph 是否出现空问题、重复问题或异常。
- 哪条链路更适合当前场景。

### 5.2 Runtime Quality Gate

新增一层 runtime 质量门禁，用来判断 LangGraph 输出是否可以进入可见链路。

示例规则：

```text
问题不能为空。
问题不能和最近 N 轮高度重复。
decision.nextAction 必须合法。
difficulty 必须合法。
checkpointSummary 必须存在。
如果 requiresHumanReview=true，则不能直接进入真实用户可见链路。
如果 LangGraph 报错，则自动 fallback classic。
```

### 5.3 Checkpoint Summary 持久化边界

当前 `checkpoint_summary_store` 是内存态。V4 不要求立刻替换为完整 LangGraph 持久化数据库 checkpointer，但要做项目侧 checkpoint summary 的持久化设计。

推荐第一阶段：

```text
新增数据库表或复用现有日志表扩展字段，保存 checkpoint summary / runtime comparison summary。
```

目标不是保存完整 graph state，而是保存可观测摘要：

```text
threadId
runtime
status
currentNode
lastAction
lastQuestion
requiresHumanReview
interrupt
resumeDecision
comparisonSummary
createdAt
```

### 5.4 Admin 可观测增强

管理员后台需要能看懂：

```text
这次请求使用了哪个 runtime
classic 输出是什么
LangGraph shadow 输出是什么
两边差异是什么
是否触发 quality gate
是否 fallback classic
checkpoint 是否可恢复
```

目标不是做复杂运营后台，而是让 Agent 工作流“不黑箱”。

### 5.5 迁移条件文档化

V4 必须明确主链路迁移条件。

只有当满足以下条件，才考虑把某些场景切到 LangGraph：

- shadow compare 连续多轮质量稳定。
- LangGraph 输出空问题率低于阈值。
- 重复问题率低于阈值。
- fallback 率低于阈值。
- checkpoint summary 能稳定记录。
- interrupt / resume 错误率可控。
- 前端接口兼容。
- 出错可回退 classic。

## 6. 非目标

本阶段不做：

- 不直接把所有面试用户切到 LangGraph。
- 不删除 classic Agent。
- 不重写三类 RAG。
- 不重写 `/api/interview/next-question` 返回结构。
- 不做 LangGraph 云端平台。
- 不引入复杂多 Agent 编排平台。
- 不做真实 VPS / Nginx / 域名 / HTTPS 上线。
- 不做全站 UI 重构。
- 不做大规模商业审批后台。

## 7. 建议总体架构

V4 推荐架构：

```text
Interview API / Runtime Experiment API
-> Agent Runtime Service
-> classic runner
-> langgraph runner
-> Shadow Compare Evaluator
-> Runtime Quality Gate
-> Checkpoint Summary Persistence
-> AI Debug Console
```

其中：

- `Agent Runtime Service` 负责选择 classic / langgraph / shadow。
- `Shadow Compare Evaluator` 负责比较两条链路。
- `Runtime Quality Gate` 负责判断 LangGraph 输出是否可见。
- `Checkpoint Summary Persistence` 负责保存项目侧可观测摘要。
- `AI Debug Console` 负责展示 runtime 差异。

## 8. 数据结构设计

### 8.1 Runtime Comparison Summary

建议结构：

```json
{
  "threadId": "interview-001",
  "runtimeMode": "shadow",
  "visibleRuntime": "classic",
  "classic": {
    "status": "completed",
    "nextAction": "deep_follow_up",
    "difficulty": "medium",
    "questionText": "请结合你的项目说明 Agent State 的作用。"
  },
  "langgraph": {
    "status": "completed",
    "nextAction": "lower_difficulty",
    "difficulty": "basic",
    "questionText": "我们先拆开 Agent State，它主要保存哪些信息？",
    "checkpointExists": true,
    "requiresHumanReview": false
  },
  "comparison": {
    "actionMatched": false,
    "difficultyMatched": false,
    "questionSimilarity": 0.42,
    "qualityGatePassed": true,
    "fallbackToClassic": false,
    "reasons": [
      "LangGraph 选择降低难度，更适合连续弱回答场景。"
    ]
  }
}
```

### 8.2 Runtime Quality Gate Result

建议结构：

```json
{
  "passed": true,
  "fallbackToClassic": false,
  "riskLevel": "low",
  "reasons": [],
  "checks": {
    "nonEmptyQuestion": true,
    "validDecision": true,
    "validDifficulty": true,
    "notRepeated": true,
    "checkpointAvailable": true,
    "humanReviewBlocked": false
  }
}
```

### 8.3 Persisted Checkpoint Summary

建议结构：

```json
{
  "threadId": "interview-001",
  "runtime": "langgraph",
  "status": "completed",
  "currentNode": "generate_question",
  "roundCount": 4,
  "lastAction": "lower_difficulty",
  "lastQuestion": "我们先拆开 Agent State...",
  "requiresHumanReview": false,
  "interruptJson": null,
  "resumeDecision": "",
  "runtimeTraceJson": [],
  "comparisonJson": {},
  "createdAt": "2026-06-14T10:00:00"
}
```

## 9. 后端模块规划

### 9.1 `backend_python/runtime_quality_gate.py`

职责：

- 校验 LangGraph 输出是否适合进入可见链路。
- 输出 `RuntimeQualityGateResult`。
- 不直接调用模型，不直接查数据库。

核心函数：

```text
evaluate_runtime_quality(result, recent_questions) -> dict
```

### 9.2 `backend_python/runtime_compare.py`

职责：

- 对比 classic 与 LangGraph 输出。
- 生成 comparison summary。
- 计算 action / difficulty / question 差异。

核心函数：

```text
compare_runtime_outputs(classic_result, langgraph_result, quality_gate) -> dict
```

### 9.3 `backend_python/langgraph_agent/checkpoint_persistence.py`

职责：

- 保存项目侧 checkpoint summary。
- 不直接替代 LangGraph 内部 checkpointer。
- 第一版可以使用 SQLAlchemy 表，也可以先用独立 service 封装，为数据库持久化留边界。

核心能力：

```text
save_checkpoint_summary()
get_latest_checkpoint_summary()
list_checkpoint_summaries()
```

### 9.4 `backend_python/agent_runtime.py` 增强

当前已经支持：

```text
classic
langgraph
shadow
```

V4 增强：

- shadow 模式调用 compare evaluator。
- langgraph 模式必须经过 quality gate。
- quality gate 不通过时 fallback classic。
- response 增加 `comparisonSummary` 和 `qualityGate`。

## 10. 接口规划

### 10.1 保持兼容

必须保持：

```text
POST /api/interview/next-question
```

现有前端调用不应被破坏。

### 10.2 实验接口增强

可增强：

```text
POST /api/langgraph-agent/runtime/run
POST /api/langgraph-agent/runtime/resume
GET  /api/langgraph-agent/checkpoint/{thread_id}
```

建议新增或扩展：

```text
GET /api/langgraph-agent/runtime/compare/{thread_id}
GET /api/langgraph-agent/runtime/runs/{thread_id}
```

第一版可以只给管理员和测试使用。

## 11. 管理员后台规划

AI Debug Console 增强展示：

```text
Runtime Mode：classic / langgraph / shadow
Visible Runtime：classic / langgraph
LangGraph Status：completed / interrupted / failed
Quality Gate：passed / failed
Fallback：是否回退 classic
Comparison：action 是否一致、difficulty 是否一致、问题差异摘要
Checkpoint：currentNode、requiresHumanReview、resumeDecision
```

页面设计原则：

- 不把后台做成复杂运营系统。
- 只展示调试所需的关键字段。
- 保持中文解释，避免只展示 JSON。
- 原始 JSON 可以折叠展示，作为调试材料。

## 12. 测试策略

### 12.1 后端测试

新增或更新：

```text
tests/test_runtime_quality_gate.py
tests/test_runtime_compare.py
tests/test_agent_runtime_switching.py
tests/test_langgraph_runtime_checkpoint_persistence.py
tests/test_admin_ai_debug.py
```

覆盖：

- LangGraph 空问题被 quality gate 拦截。
- 非法 decision 被 quality gate 拦截。
- requiresHumanReview=true 时不能直接进入可见链路。
- shadow 模式返回 classic 可见结果和 LangGraph comparison summary。
- quality gate 失败时 fallback classic。
- checkpoint summary 可持久化查询。
- AI Debug 能展示 comparisonSummary。

### 12.2 前端测试

更新：

```text
frontend/src/stores/admin.test.ts
frontend/src/pages/app/admin-page.test.ts
```

覆盖：

- Runtime Mode 展示。
- Quality Gate 展示。
- Fallback 展示。
- Comparison Summary 展示。
- Checkpoint 信息展示。
- 缺字段时不出现 `undefined`。

### 12.3 验证命令

阶段结束必须运行：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

```text
http://127.0.0.1:5173/vue/app/admin
```

## 13. 开发阶段拆分

### 阶段 1：Runtime Quality Gate

目标：

- 实现 LangGraph 输出质量门禁。
- 不动主接口。
- 只加纯函数和测试。

验收：

- 空问题、非法 action、非法 difficulty、human review 均能被识别。
- 输出中文 reasons，便于后台展示。

### 阶段 2：Shadow Compare Evaluator

目标：

- 对比 classic 与 LangGraph 结果。
- 生成结构化 comparison summary。

验收：

- actionMatched、difficultyMatched、qualityGatePassed 可测试。
- comparison reasons 可读。

### 阶段 3：Agent Runtime 集成

目标：

- 在 `agent_runtime.py` 中接入 quality gate 与 compare evaluator。
- shadow 模式更完整。

验收：

- shadow 模式仍返回 classic 可见结果。
- LangGraph 结果进入 `shadow.comparisonSummary`。
- quality gate 失败时 fallback classic。

### 阶段 4：Checkpoint Summary 持久化

目标：

- 把项目侧 checkpoint summary 从纯内存态推进到可查询的持久化摘要。
- 第一版优先保存摘要，不保存完整 graph state。

验收：

- 同一 threadId 可查询最近 summary。
- 多次运行能看到 run history。
- 服务重启后的持久化能力视具体实现方案验证。

### 阶段 5：AI Debug Console 增强

目标：

- 管理员后台展示 comparison、quality gate、fallback、checkpoint 摘要。

验收：

- 后台页面能看懂 LangGraph 与 classic 差异。
- 页面不出现 `undefined`。

### 阶段 6：学习文档与路线更新

新增学习文档：

```text
docs/learning/23-LangGraph从旁路到候选主链路如何灰度迁移.md
```

内容包括：

- 为什么 LangGraph 不直接替换主链路。
- shadow compare 是什么。
- quality gate 是什么。
- checkpoint summary 和完整 graph state 的区别。
- 什么条件下可以迁移主链路。
- 面试时怎么讲。

## 14. 风险与控制

### 14.1 LangGraph 输出不一定更好

控制：

```text
通过 shadow compare 收集证据，不靠主观判断。
```

### 14.2 checkpoint 持久化范围过大

控制：

```text
V4 只持久化项目侧 checkpoint summary，不直接承诺完整 graph state 生产级恢复。
```

### 14.3 主链路被破坏

控制：

```text
/api/interview/next-question 保持兼容。
默认 runtime 仍为 classic。
LangGraph 只通过实验接口、管理员配置或 shadow 模式进入。
```

### 14.4 后台信息过载

控制：

```text
默认展示摘要和中文解释，原始 JSON 折叠。
```

## 15. 完成标准

V4 完成时应满足：

- active plan 已编写。
- runtime quality gate 有测试覆盖。
- shadow compare evaluator 有测试覆盖。
- `agent_runtime.py` 支持 comparison summary。
- LangGraph 质量不达标时能 fallback classic。
- checkpoint summary 持久化边界落地。
- 管理员后台能展示 runtime comparison。
- 新增中文学习文档。
- 后端全量测试通过。
- 前端全量测试通过。
- 前端 build 通过。
- 浏览器验证管理员后台通过。

## 16. 面试表达

完成后可以这样讲：

```text
我的项目里不是简单“用了 LangGraph”，而是做了 classic Agent 到 LangGraph 的渐进式迁移设计。

classic Agent 继续作为稳定主链路，LangGraph 先作为 shadow runtime 跑同一份 Agent State。系统会对比两边的 action、difficulty、question、checkpoint 和 human review 状态，并通过 quality gate 判断 LangGraph 输出是否可靠。

如果 LangGraph 输出为空、重复、非法或者需要人工复核，系统不会直接把它暴露给用户，而是 fallback classic。这样既能利用 LangGraph 的 checkpoint、interrupt、workflow 可观测能力，又能保证现有面试体验稳定。
```

如果面试官问为什么不直接迁移：

```text
因为 Agent 是核心业务链路，LangGraph 是工程化增强，不是效果魔法棒。我需要先用 shadow compare 证明它在质量、稳定性和可观测性上达到迁移条件，再考虑灰度切换主链路。这是更接近生产系统的迁移方式。
```

