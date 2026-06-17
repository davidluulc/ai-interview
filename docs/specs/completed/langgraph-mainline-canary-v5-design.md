# LangGraph 主链路灰度迁移 V5 设计文档

更新时间：2026-06-14

## 1. 文档目的

本文档规划 AI 模拟面试系统下一阶段 LangGraph 深化工作。

上一阶段 `LangGraph Runtime Deepening V4` 已经完成：

- classic Agent 继续作为稳定主链路。
- LangGraph 可以作为候选 runtime 运行。
- shadow compare 可以对比 classic 和 LangGraph。
- runtime quality gate 可以拦截空问题、重复问题、非法决策和需要人工复核的结果。
- checkpoint summary 已经做了项目侧持久化摘要。
- AI Debug 后台可以看到 Runtime 对比、Quality Gate 和 Fallback 信息。

V5 的目标不是重复 V4，也不是立刻把全部用户切到 LangGraph。

V5 要解决的问题是：

```text
LangGraph 已经能被评估，那么它怎样开始小范围进入真实可见链路？
```

换句话说，本阶段要把 LangGraph 从“候选 runtime”推进到“可灰度的候选主链路”。

## 2. 当前项目状态

当前已落地能力：

- FastAPI 后端模块化。
- 三类 RAG：岗位知识库、题库、候选人画像。
- classic Interview Orchestrator Agent。
- Agent Policy 公共策略层。
- coach / interview 双模式。
- Agent 决策日志。
- LangGraph V1/V2/V3/V4 旁路与治理能力。
- checkpoint summary 持久化。
- Vue3 用户工作台。
- Vue3 管理员后台。
- AI Debug Console。

主要代码证据：

```text
backend_python/agent_runtime.py
backend_python/runtime_quality_gate.py
backend_python/runtime_compare.py
backend_python/human_review_policy.py
backend_python/langgraph_agent/
backend_python/routes/langgraph_agent.py
backend_python/routes/interview.py
backend_python/routes/admin.py
frontend/src/pages/app/AdminPage.vue
frontend/src/pages/app/InterviewPage.vue
tests/test_agent_runtime_switching.py
tests/test_runtime_quality_gate.py
tests/test_runtime_compare.py
tests/test_langgraph_runtime_checkpoint_persistence.py
tests/test_admin_ai_debug.py
```

当前边界：

- `/api/interview/next-question` 仍以 classic Agent 为默认稳定链路。
- LangGraph 主要通过实验接口、shadow 模式和后台调试体现。
- 后台能看单次 runtime 质量，但还缺少“是否允许本轮可见使用 LangGraph”的统一灰度策略。
- 用户侧还没有明确的“本轮由 LangGraph 接管，但失败自动回退 classic”的产品化链路。

## 3. 阶段定位

阶段名称：

```text
LangGraph Mainline Canary V5
```

中文定位：

```text
LangGraph 主链路灰度迁移 V5
```

核心目标：

```text
在不破坏现有面试主流程的前提下，允许管理员或实验配置把少量面试请求切到 LangGraph 可见链路，并确保所有 LangGraph 可见输出都经过 quality gate、fallback 和日志审计。
```

这不是全量替换，而是灰度迁移。

## 4. 为什么要做灰度迁移

classic Agent 已经串起了：

- 简历档案。
- 岗位 JD。
- 三类 RAG 检索。
- Agent State。
- Agent Decision。
- 问题生成。
- 历史记录。
- 报告复盘。
- 训练任务。
- 后台日志。

如果直接全部切到 LangGraph，风险是：

- 某一轮 LangGraph 输出异常会影响真实用户面试。
- 报告和训练任务可能拿到质量不稳定的问题数据。
- 用户体验问题不容易定位。
- 面试时也不好解释为什么要冒险替换稳定链路。

所以 V5 采用：

```text
默认 classic
-> 管理员或测试账号可选 langgraph_canary
-> LangGraph 通过 quality gate 才能可见
-> 不通过自动 fallback classic
-> 后台记录为什么切换、为什么回退、质量如何
```

这比“直接上 LangGraph”更接近真实生产系统。

## 5. 术语定义

### 5.1 classic runtime

现有稳定 Agent 主链路。它是默认可见链路。

### 5.2 shadow runtime

用户看到 classic，后台同时运行 LangGraph 做对比。shadow 不影响用户输出。

### 5.3 langgraph runtime

用户可见输出由 LangGraph 生成，但必须通过 quality gate。不通过则 fallback classic。

### 5.4 langgraph_canary

灰度模式。它不是无条件使用 LangGraph，而是：

```text
先运行 LangGraph
-> 经过 quality gate
-> 通过则展示 LangGraph
-> 不通过则展示 classic
-> 全程写入 runtime audit
```

### 5.5 runtime audit

运行时审计摘要，用来记录：

- 本轮请求想使用哪个 runtime。
- 实际可见 runtime 是什么。
- 是否触发 quality gate。
- 是否 fallback。
- fallback 原因。
- 是否需要人工复核。
- checkpoint 是否存在。

## 6. 本阶段目标

### 6.1 新增 Runtime 灰度策略层

新增独立策略模块，用来决定本轮请求是否允许 LangGraph 可见。

策略输入：

- 请求里的 runtime 偏好。
- 当前用户角色。
- 当前 agent mode：coach / interview。
- 最近回答状态。
- LangGraph 历史 fallback 情况。
- 管理员配置。

策略输出：

```json
{
  "requestedRuntime": "langgraph_canary",
  "allowedRuntime": "langgraph",
  "visibleRuntimeOnFailure": "classic",
  "reasons": ["管理员开启 LangGraph 灰度", "当前用户允许实验 runtime"],
  "requiresAudit": true
}
```

### 6.2 让主面试接口具备兼容式 runtime 选择能力

保持 `/api/interview/next-question` 向后兼容。

可选增强：

```text
QuestionRequest.agentRuntime?: classic | shadow | langgraph_canary
```

如果前端不传，默认仍是 classic。

如果普通用户未被允许使用 LangGraph，则后端自动降级 classic，并在日志中记录原因。

### 6.3 LangGraph Canary 可见链路

当请求进入 `langgraph_canary`：

```text
构造 Agent State
-> 运行 LangGraph runtime
-> 运行 Runtime Quality Gate
-> gate 通过：返回 LangGraph 问题
-> gate 不通过：运行或复用 classic 结果
-> 写入 runtime audit / agent log / checkpoint summary
```

### 6.4 Runtime Audit 后台可观测

管理员后台需要能看懂：

- 本轮请求是 classic、shadow 还是 canary。
- 用户请求的是哪个 runtime。
- 后端最终允许的是哪个 runtime。
- 最终展示给用户的是哪个 runtime。
- LangGraph 是否通过 quality gate。
- 为什么 fallback classic。
- 哪些规则触发了灰度或拦截。

### 6.5 前端体验保持克制

用户侧不应该暴露过多工程调试字段。

建议：

- 普通用户只看到“学习辅导 / 真实面试”模式。
- 管理员或开发演示账号才看到“实验 runtime”选择。
- 面试页可以展示简短说明：`本轮由 LangGraph 实验链路生成，异常会自动回退稳定链路。`
- 详细 runtime 信息放到管理员后台和 AI Debug。

## 7. 非目标

本阶段不做：

- 不删除 classic Agent。
- 不全量替换 `/api/interview/next-question`。
- 不重写三类 RAG。
- 不做多 Agent 平台。
- 不做 LangGraph Cloud。
- 不做真实 VPS / 域名 / HTTPS 上线。
- 不重构全站 UI。
- 不引入复杂 AB 实验平台。
- 不做完整 graph state 生产级恢复承诺。

## 8. 推荐架构

```text
Vue3 Interview Page
-> POST /api/interview/next-question
-> Runtime Policy
-> Agent Runtime Service
   -> classic runner
   -> langgraph runner
   -> shadow compare
   -> quality gate
   -> fallback classic
-> Runtime Audit Summary
-> Agent Log / Checkpoint Summary / AI Debug
-> Vue3 Admin Console
```

模块职责：

- `runtime_policy.py`：判断本轮是否允许 LangGraph 可见。
- `agent_runtime.py`：执行 classic / shadow / langgraph / canary。
- `runtime_quality_gate.py`：判断 LangGraph 输出是否可靠。
- `runtime_compare.py`：比较 classic 与 LangGraph。
- `runtime_audit.py`：生成可观测审计摘要。
- `routes/interview.py`：保持接口兼容，接入 runtime 偏好。
- `routes/admin.py`：向后台暴露 runtime audit。

## 9. 数据结构设计

### 9.1 Runtime Policy Decision

```json
{
  "requestedRuntime": "langgraph_canary",
  "allowedRuntime": "langgraph",
  "fallbackRuntime": "classic",
  "visibleRuntimeOnSuccess": "langgraph",
  "visibleRuntimeOnFailure": "classic",
  "canUseLangGraph": true,
  "requiresAudit": true,
  "reasons": ["管理员账号允许使用实验 runtime"]
}
```

### 9.2 Runtime Audit Summary

```json
{
  "traceId": "interview-123-round-4",
  "requestedRuntime": "langgraph_canary",
  "allowedRuntime": "langgraph",
  "visibleRuntime": "classic",
  "fallbackRuntime": "classic",
  "fallbackUsed": true,
  "qualityGatePassed": false,
  "qualityGateReasons": ["LangGraph 问题与最近问题重复度过高"],
  "policyReasons": ["管理员账号允许使用实验 runtime"],
  "checkpointExists": true,
  "requiresHumanReview": false
}
```

### 9.3 QuestionResponse 兼容扩展

保持现有字段不破坏。

可新增可选字段：

```json
{
  "runtimeAudit": {
    "requestedRuntime": "langgraph_canary",
    "visibleRuntime": "classic",
    "fallbackUsed": true
  }
}
```

前端可以不使用该字段，旧调用不受影响。

## 10. 后端开发范围

### 10.1 Runtime Policy

新增：

```text
backend_python/runtime_policy.py
tests/test_runtime_policy.py
```

职责：

- 普通用户默认 classic。
- 管理员可请求 shadow 或 langgraph_canary。
- 非法 runtime 自动降级 classic。
- interview 模式比 coach 模式更保守。
- 策略输出必须有中文 reasons。

### 10.2 Runtime Audit

新增：

```text
backend_python/runtime_audit.py
tests/test_runtime_audit.py
```

职责：

- 汇总 policy、qualityGate、comparisonSummary、checkpointSummary。
- 输出适合前端和后台展示的稳定结构。
- 不直接访问数据库。

### 10.3 Agent Runtime Service 增强

修改：

```text
backend_python/agent_runtime.py
tests/test_agent_runtime_switching.py
```

职责：

- 支持 `langgraph_canary`。
- canary 通过 quality gate 时可见 runtime 是 LangGraph。
- canary 不通过时可见 runtime 是 classic。
- shadow 仍然保持 classic 可见。
- response 带上 runtimeAudit。

### 10.4 Interview 主接口兼容扩展

修改：

```text
backend_python/schemas.py
backend_python/routes/interview.py
tests/test_interview_agent_route.py
```

职责：

- `QuestionRequest` 增加可选 `agentRuntime`。
- 不传时默认 classic。
- 非管理员用户请求实验 runtime 时自动降级，不报错。
- 管理员用户可以走 shadow / canary。

### 10.5 AI Debug 与管理员后台增强

修改：

```text
backend_python/ai_debug.py
backend_python/routes/admin.py
frontend/src/api/admin.ts
frontend/src/pages/app/AdminPage.vue
frontend/src/pages/app/admin-page.test.ts
```

职责：

- AI Debug detail 展示 runtimeAudit。
- 管理员后台显示“请求链路 / 允许链路 / 可见链路 / 回退原因”。
- 不展示 `undefined`。

## 11. 前端开发范围

### 11.1 面试页实验开关

只对管理员或演示账号展示。

选项：

```text
稳定链路 classic
旁路对比 shadow
LangGraph 灰度 langgraph_canary
```

普通用户不显示该开关。

### 11.2 面试页提示

当使用实验 runtime 时，显示轻量提示：

```text
当前启用实验链路，系统会自动进行质量门禁和稳定链路回退。
```

### 11.3 管理员后台

AI Debug 增加：

- Runtime 策略。
- Runtime 审计。
- Fallback 原因。
- Quality Gate 原因。

## 12. 测试策略

### 12.1 后端测试

必须覆盖：

- 普通用户请求 `langgraph_canary` 被降级 classic。
- 管理员请求 `langgraph_canary` 被允许。
- 非法 runtime 被降级 classic。
- canary 下 LangGraph gate 通过时 visibleRuntime=langgraph。
- canary 下 LangGraph gate 失败时 visibleRuntime=classic。
- runtimeAudit 字段稳定。
- `/api/interview/next-question` 不传 `agentRuntime` 时行为不变。

### 12.2 前端测试

必须覆盖：

- 管理员可以看到 runtime 开关。
- 普通用户看不到 runtime 开关。
- 选择 canary 后请求 payload 包含 `agentRuntime`。
- 管理员后台能展示 runtimeAudit。
- 页面不出现 `undefined`。

### 12.3 验证命令

阶段完成后运行：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

```text
http://127.0.0.1:5173/vue/app/training
http://127.0.0.1:5173/vue/app/interview
http://127.0.0.1:5173/vue/app/admin
```

## 13. 风险与控制

### 13.1 LangGraph 输出仍可能不稳定

控制：

```text
canary 必须通过 quality gate，不通过直接 fallback classic。
```

### 13.2 前端暴露太多工程概念

控制：

```text
普通用户不展示 runtime 开关，详细信息只放管理员后台。
```

### 13.3 主接口被破坏

控制：

```text
agentRuntime 是可选字段，不传时默认 classic。
```

### 13.4 管理员误以为 LangGraph 已经全量接管

控制：

```text
后台明确展示 requestedRuntime、allowedRuntime、visibleRuntime 和 fallbackUsed。
```

## 14. 完成标准

V5 完成时必须满足：

- active plan 已编写。
- runtime policy 有测试。
- runtime audit 有测试。
- `agent_runtime.py` 支持 `langgraph_canary`。
- `/api/interview/next-question` 兼容可选 `agentRuntime`。
- 普通用户不会误用实验 runtime。
- 管理员可以选择实验 runtime。
- canary 失败时 fallback classic。
- AI Debug 后台能展示 runtime audit。
- Vue3 页面不出现 `undefined`。
- 后端全量测试通过。
- 前端全量测试通过。
- 前端 build 通过。
- 浏览器桌面端和移动端验证通过。

## 15. 面试表达

完成后可以这样讲：

```text
我的项目不是简单把 LangGraph 接进来就完事，而是做了 classic Agent 到 LangGraph 的灰度迁移。

classic Agent 继续作为默认稳定链路，LangGraph 先通过 shadow compare 和 quality gate 证明质量。到了 V5，我让管理员或实验账号可以请求 langgraph_canary。系统会先运行 LangGraph，如果输出通过质量门禁，就让 LangGraph 成为本轮可见链路；如果输出为空、重复、非法或者需要人工复核，就自动 fallback 到 classic。

同时我会记录 runtime audit，包括请求链路、允许链路、最终可见链路、回退原因和 quality gate 结果。这样既能体现 LangGraph 的工作流能力，又不会牺牲线上系统稳定性。
```

如果面试官问“为什么不直接全量切 LangGraph”，可以回答：

```text
LangGraph 是工作流框架，不是质量保证本身。真实业务里核心链路迁移需要灰度、门禁、回退和可观测。我的设计是先让 LangGraph 小范围可见，并用数据证明它稳定后再扩大流量，这比一次性替换更接近生产实践。
```
