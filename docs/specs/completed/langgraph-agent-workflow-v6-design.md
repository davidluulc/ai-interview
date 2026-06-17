# LangGraph / Agent 工作流深化 V6 设计文档

更新时间：2026-06-17

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段开发：在已经完成 classic Agent、三类 RAG、Agent Policy、LangGraph POC、checkpoint summary、human review policy、runtime quality gate、shadow compare、langgraph canary 和 Vue3 管理员后台的基础上，把 LangGraph 从“可灰度的候选链路”继续推进为“可回放、可复核、可解释、可迁移”的 Agent 工作流能力。

本阶段不再重复解决“LangGraph 能不能跑”的问题，而是解决：

```text
一次 LangGraph / Agent 执行之后，开发者能不能回放它每一步怎么走？
当 Agent 需要人工介入时，管理员能不能看到待复核队列并做出恢复决策？
classic Agent 和 LangGraph canary 的差异能不能形成更清楚的运行报告？
每个 LangGraph 节点的输入输出边界能不能稳定下来，方便后续迁移主链路？
面试时能不能讲清：为什么我的项目不是简单调用 LLM，而是具备工作流治理能力？
```

## 2. 当前项目状态

已经落地的 LangGraph / Agent 能力：

- classic Interview Orchestrator Agent 仍是默认稳定主链路。
- LangGraph 已作为旁路、实验 runtime、shadow runtime 和 canary runtime 接入。
- `agentRuntime` 已支持 `classic`、`shadow`、`langgraph`、`langgraph_canary`。
- runtime quality gate 已能拦截空问题、非法决策、重复问题、缺失 checkpoint、human review 等风险。
- runtime audit 已能记录请求链路、允许链路、可见链路、fallback 状态和原因。
- checkpoint summary 已有内存态 store 和数据库持久化摘要。
- human review policy 已能基于连续弱回答或 policy 标记触发人工复核建议。
- Vue3 管理员后台已能展示 AI Debug、Runtime 审计、checkpoint 和 Agent 决策摘要。

主要代码证据：

```text
backend_python/agent_runtime.py
backend_python/runtime_policy.py
backend_python/runtime_quality_gate.py
backend_python/runtime_compare.py
backend_python/runtime_audit.py
backend_python/human_review_policy.py
backend_python/langgraph_agent/
backend_python/routes/langgraph_agent.py
backend_python/routes/interview.py
backend_python/routes/admin.py
frontend/src/pages/app/AdminPage.vue
tests/test_agent_runtime_switching.py
tests/test_runtime_quality_gate.py
tests/test_runtime_compare.py
tests/test_runtime_audit.py
tests/test_human_review_policy.py
tests/test_langgraph_runtime_checkpoint_persistence.py
tests/test_langgraph_runtime_interrupt_resume.py
tests/test_admin_ai_debug.py
```

当前短板：

- checkpoint summary 虽然已持久化，但还缺少面向调试的“执行时间线回放”。
- interrupt / resume 已有实验接口，但管理员后台还没有形成清晰的“待人工复核队列”。
- runtime comparison 主要是单次对比，还缺少按 threadId 聚合的运行报告。
- LangGraph 节点输入输出契约还散落在 state、nodes、graph 和 route 中，不利于后续主链路迁移。
- 当前后台能看工程字段，但还需要进一步翻译成“为什么这么走、哪里被拦截、如何恢复”的中文诊断视角。

## 3. 阶段定位

阶段名称：

```text
LangGraph / Agent 工作流深化 V6
```

核心定位：

```text
让 LangGraph canary 从“可灰度运行”升级为“可回放调试、可人工复核、可形成迁移证据”的候选 Agent 工作流。
```

本阶段仍坚持双轨架构：

```text
classic Agent：默认稳定主链路，继续保障真实面试体验。
LangGraph Agent：候选工作流链路，用于状态图治理、checkpoint、回放、人工复核和后续迁移验证。
```

## 4. 本阶段目标

### 4.1 LangGraph 执行时间线回放

新增一个项目侧 replay service，把一次 LangGraph / Agent 运行整理成开发者能读懂的时间线。

输入来源：

- checkpoint summary。
- runtimeTrace。
- nodeTrace。
- qualityGate。
- comparisonSummary。
- runtimeAudit。
- interrupt / resumeDecision。

输出示例：

```json
{
  "threadId": "interview-123",
  "status": "interrupted",
  "summary": "本轮 LangGraph 在 human_review 节点暂停，原因是候选人连续弱回答。",
  "timeline": [
    {
      "step": 1,
      "node": "observe_state",
      "title": "观察当前面试状态",
      "detail": "读取历史问答、候选人档案、RAG 命中摘要和当前模式。"
    },
    {
      "step": 2,
      "node": "human_review",
      "title": "触发人工复核",
      "detail": "连续弱回答触发 human review，系统建议切换到学习辅导。"
    }
  ],
  "risks": ["requiresHumanReview"],
  "nextActions": ["resume", "fallback_classic"]
}
```

目标是让后台能回答：

- 本轮执行到了哪个节点。
- 为什么暂停或回退。
- 是否进入质量门禁。
- LangGraph 与 classic 差异在哪里。
- 下一步应该恢复、切换辅导，还是回退 classic。

### 4.2 Human Review 待复核队列

把已有 interrupt / resume 实验能力产品化为管理员可理解的队列。

第一版只做后台调试用途，不给普通用户开放。

管理员需要看到：

- 哪些 thread 当前处于 interrupted。
- 暂停原因。
- 建议动作。
- 最近问题。
- 当前节点。
- 是否已经恢复。
- 恢复决策是什么。

第一版支持的恢复动作：

```text
continue_interview：继续真实面试
switch_to_coach：切换到学习辅导
fallback_classic：回退到 classic Agent
end_interview：结束本轮面试
```

### 4.3 节点契约稳定化

新增 LangGraph 节点契约模块，明确每个节点读什么、写什么。

建议节点：

```text
observe_state
retrieve_context
analyze_answer
apply_policy
decide_action
human_review
generate_question
update_memory
```

每个节点需要稳定描述：

- 输入字段。
- 输出字段。
- 可触发的风险。
- 可写入的 trace 字段。
- 失败时的 fallback 行为。

这不是为了写复杂框架，而是为了让后续主链路迁移时能逐个节点替换和测试。

### 4.4 Runtime 对比报告

在单次 comparison summary 基础上，增加按 threadId 聚合的 runtime report。

报告至少包含：

- 总运行次数。
- completed / interrupted / failed 分布。
- visibleRuntime 分布。
- fallback 次数和原因。
- quality gate 失败原因 TopN。
- human review 触发次数。
- action / difficulty 差异摘要。

目标是让管理员后台能从“一条日志”升级为“一个运行证据报告”。

### 4.5 管理员后台可读性增强

后台不应该只显示 JSON。

本阶段后台重点展示四块：

```text
运行时间线：这轮 Agent 怎么走。
人工复核：为什么暂停，能选什么动作。
质量门禁：为什么通过或回退。
对比报告：classic 和 LangGraph 差异如何。
```

原始 JSON 可以保留折叠展示，但默认视图必须是中文摘要。

## 5. 非目标

本阶段不做：

- 不把 LangGraph 直接设为所有用户默认主链路。
- 不删除 classic Agent。
- 不重写三类 RAG。
- 不做生产级 RAG V3、OCR、Word / Excel / 网页解析。
- 不替换 SQLiteVectorStore 为 Qdrant / pgvector。
- 不做 Redis / Celery 新队列开发。
- 不做 Docker / Nginx / VPS / HTTPS 上线。
- 不做 Vue3 全站大重构。
- 不引入复杂多 Agent 平台。
- 不接 LangGraph Cloud。

## 6. 推荐架构

```text
Vue3 Admin Page
-> Admin API / LangGraph Runtime API
-> Replay Service
-> Human Review Queue Service
-> Runtime Report Service
-> Checkpoint Persistence
-> LangGraph Runtime / classic Agent Runtime
```

建议新增或增强模块：

```text
backend_python/langgraph_agent/contracts.py
backend_python/langgraph_agent/replay.py
backend_python/langgraph_agent/review_queue.py
backend_python/langgraph_agent/runtime_report.py
backend_python/routes/langgraph_agent.py
backend_python/routes/admin.py
frontend/src/api/admin.ts
frontend/src/stores/admin.ts
frontend/src/pages/app/AdminPage.vue
```

设计原则：

- replay、review queue、runtime report 都只读或轻写摘要，不直接调用模型。
- LangGraph 节点契约是纯结构描述，优先可测试。
- 主面试接口保持兼容。
- 管理员后台只展示可读摘要，不把普通用户界面变成调试台。

## 7. 接口规划

### 7.1 Runtime Replay

新增或增强：

```text
GET /api/langgraph-agent/runtime/replay/{thread_id}
```

返回：

```json
{
  "threadId": "interview-123",
  "exists": true,
  "status": "interrupted",
  "summary": "本轮在 human_review 节点暂停。",
  "timeline": [],
  "risks": [],
  "nextActions": []
}
```

### 7.2 Human Review Queue

新增或增强：

```text
GET /api/langgraph-agent/runtime/reviews
POST /api/langgraph-agent/runtime/reviews/{thread_id}/resolve
```

`resolve` 请求：

```json
{
  "decision": "switch_to_coach",
  "comment": "候选人连续不会，先切到学习辅导。"
}
```

第一版可以复用已有 `/runtime/resume` 的底层逻辑，但要让接口语义更贴近“人工复核”。

### 7.3 Runtime Report

新增或增强：

```text
GET /api/langgraph-agent/runtime/report/{thread_id}
```

返回：

```json
{
  "threadId": "interview-123",
  "totalRuns": 5,
  "statusCounts": {"completed": 3, "interrupted": 1, "failed": 1},
  "fallbackCount": 2,
  "humanReviewCount": 1,
  "topQualityGateReasons": ["问题为空", "与最近问题重复"],
  "summary": "该线程 LangGraph 可运行，但有 2 次 fallback，需要继续观察。"
}
```

## 8. 后端开发范围

### 8.1 节点契约模块

新增：

```text
backend_python/langgraph_agent/contracts.py
tests/test_langgraph_agent_contracts.py
```

职责：

- 定义节点名称常量。
- 定义每个节点的输入输出字段。
- 提供 `get_node_contracts()`。
- 提供 `validate_node_trace()`，用于检查 nodeTrace 里的节点是否可识别。

### 8.2 Replay Service

新增：

```text
backend_python/langgraph_agent/replay.py
tests/test_langgraph_runtime_replay.py
```

职责：

- 从 checkpoint summary 生成中文 timeline。
- 把 runtimeAudit、qualityGate、comparisonSummary 翻译成风险和下一步动作。
- 缺字段时返回安全空状态，不抛出无意义异常。

### 8.3 Human Review Queue Service

新增：

```text
backend_python/langgraph_agent/review_queue.py
tests/test_langgraph_human_review_queue.py
```

职责：

- 从 checkpoint summaries 中筛选 `status=interrupted` 或 `requiresHumanReview=true` 的记录。
- 生成队列 item。
- 校验恢复动作是否合法。
- 复用已有 resume 持久化逻辑。

### 8.4 Runtime Report Service

新增：

```text
backend_python/langgraph_agent/runtime_report.py
tests/test_langgraph_runtime_report.py
```

职责：

- 聚合同一 threadId 的 checkpoint summaries。
- 统计 status、fallback、quality gate、human review。
- 输出中文 summary。

### 8.5 Route 扩展

修改：

```text
backend_python/routes/langgraph_agent.py
tests/test_langgraph_agent_route.py
```

职责：

- 暴露 replay、reviews、resolve、report 接口。
- 保持现有 `/runtime/run`、`/runtime/resume`、`/runtime/runs/{thread_id}` 兼容。
- 非法 threadId 返回清晰错误。

### 8.6 Admin 聚合

修改：

```text
backend_python/routes/admin.py
backend_python/ai_debug.py
tests/test_admin_ai_debug.py
```

职责：

- AI Debug detail 增加 replaySummary / runtimeReport。
- 管理员后台不需要直接理解底层 checkpoint JSON。

## 9. 前端开发范围

修改：

```text
frontend/src/api/admin.ts
frontend/src/stores/admin.ts
frontend/src/pages/app/AdminPage.vue
frontend/src/pages/app/admin-page.test.ts
frontend/src/stores/admin.test.ts
```

前端目标：

- 在管理员后台展示“运行时间线”。
- 展示“人工复核队列”。
- 展示“质量门禁和回退原因”。
- 展示“Runtime 对比报告”。
- 原始 JSON 折叠保留。
- 页面不出现 `undefined`。
- 桌面端和移动端不横向溢出。

## 10. 测试策略

### 10.1 后端测试

必须覆盖：

- 节点契约列表包含核心节点。
- nodeTrace 里未知节点会被标记，而不是让服务崩溃。
- replay 能把 checkpoint summary 转换为中文 timeline。
- interrupted checkpoint 会出现在 review queue。
- resolve 只允许合法决策。
- runtime report 能统计 fallback、人审、质量门禁原因。
- 新增接口 shape 稳定。
- 旧接口不被破坏。

### 10.2 前端测试

必须覆盖：

- 管理员后台能展示 replay timeline。
- 管理员后台能展示 human review 队列空态和有数据态。
- 管理员后台能展示 runtime report。
- 缺字段时不出现 `undefined`。
- 普通用户仍不能看到管理员后台。

### 10.3 验证命令

阶段完成后运行：

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

至少验证：

- 桌面端管理员后台可读。
- 移动端无横向溢出。
- AI Debug / LangGraph 区域没有 `undefined`。
- 人工复核和时间线区域在空数据时也有清晰提示。

## 11. 风险与控制

### 11.1 范围过大

控制：

```text
本阶段只做 LangGraph / Agent 工作流治理，不做 RAG 生产化和上线部署。
```

### 11.2 后台变成 JSON 堆砌

控制：

```text
默认展示中文摘要、时间线、风险和下一步动作；原始 JSON 折叠。
```

### 11.3 人工复核误影响真实用户

控制：

```text
第一版只用于管理员调试和实验 thread，不改变普通用户默认 classic 主链路。
```

### 11.4 节点契约与真实节点漂移

控制：

```text
用测试锁定核心节点列表和 nodeTrace 校验，后续新增节点必须更新契约。
```

## 12. 完成标准

V6 完成时必须满足：

- active plan 已编写。
- 节点契约模块和测试完成。
- replay service 和接口完成。
- human review 队列和 resolve 接口完成。
- runtime report service 和接口完成。
- 管理员后台能展示时间线、复核队列、质量门禁和运行报告。
- 后端全量测试通过。
- 前端全量测试通过。
- 前端 build 通过。
- 浏览器桌面端和移动端验证通过。
- spec / plan 归档到 completed。
- `docs/roadmap/current-state.md`、`docs/specs/README.md`、`docs/plans/README.md` 更新。

## 13. 面试表达

完成后可以这样讲：

```text
我的项目里 LangGraph 不是简单“接了一个框架”。我先保留 classic Agent 作为稳定主链路，再把 LangGraph 作为候选工作流逐步接入。

前几个阶段已经实现了 checkpoint、human review、runtime quality gate、shadow compare 和 canary。到了 V6，我进一步做了工作流治理：把每次 Agent 执行整理成可回放时间线，把需要人工介入的状态放入复核队列，并按 threadId 生成 runtime 对比报告。

这样我可以回答一次 AI 面试问题到底为什么这么生成：RAG 命中了什么，Agent 决策是什么，LangGraph 走到哪个节点，是否触发质量门禁，为什么 fallback，以及人工复核应该怎么恢复。这个设计的重点是减少 AI 黑箱，提高 Agent 系统的可观测性、可维护性和迁移安全性。
```

如果面试官问“为什么还不直接全量切 LangGraph”，可以回答：

```text
LangGraph 提供状态图、checkpoint 和 interrupt 能力，但它不天然保证业务输出质量。我的做法是先用 classic Agent 保障主流程稳定，再通过 shadow、canary、quality gate、replay 和 report 收集迁移证据。等 fallback 率、重复问题率、人审率等指标稳定后，再扩大 LangGraph 的可见流量。这更接近真实生产系统的灰度迁移方式。
```
