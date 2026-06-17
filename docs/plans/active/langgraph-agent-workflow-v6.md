# LangGraph / Agent 工作流深化 V6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 LangGraph canary 从“可灰度运行”升级为“可回放、可人工复核、可形成运行报告”的 Agent 工作流治理能力。

**Architecture:** 保留 classic Agent 默认主链路，围绕已有 checkpoint summary、runtimeAudit、qualityGate 和 comparisonSummary 新增只读/轻写服务：节点契约、执行回放、人工复核队列和 runtime report。后端先用测试锁定服务层，再扩展 API，最后让 Vue3 管理员后台展示中文摘要。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Vue3、TypeScript、Pinia、Vitest。

---

## 1. 文件结构

新增文件：

- `backend_python/langgraph_agent/contracts.py`：LangGraph 节点契约、节点名称常量和 nodeTrace 校验。
- `backend_python/langgraph_agent/replay.py`：把 checkpoint summary 转换成中文执行时间线。
- `backend_python/langgraph_agent/review_queue.py`：筛选待人工复核 checkpoint，并校验恢复决策。
- `backend_python/langgraph_agent/runtime_report.py`：按 threadId 聚合运行报告。
- `tests/test_langgraph_agent_contracts.py`：节点契约测试。
- `tests/test_langgraph_runtime_replay.py`：执行回放测试。
- `tests/test_langgraph_human_review_queue.py`：人工复核队列测试。
- `tests/test_langgraph_runtime_report.py`：运行报告测试。

修改文件：

- `backend_python/routes/langgraph_agent.py`：新增 replay、reviews、resolve、report 接口。
- `backend_python/routes/admin.py`：按需要聚合 replay / report 到 AI Debug。
- `backend_python/ai_debug.py`：补充 replaySummary / runtimeReport 规范化输出。
- `frontend/src/api/admin.ts`：补充管理员后台展示所需类型。
- `frontend/src/stores/admin.ts`：加载并保存新的调试摘要。
- `frontend/src/pages/app/AdminPage.vue`：展示运行时间线、人工复核队列、runtime report。
- `frontend/src/pages/app/admin-page.test.ts`：覆盖新展示区域。
- `frontend/src/stores/admin.test.ts`：覆盖 store 空态和正常态。
- `docs/roadmap/current-state.md`：阶段完成后更新。
- `docs/specs/README.md`：阶段完成后更新。
- `docs/plans/README.md`：阶段完成后更新。

## 2. 开发任务

### Task 1: LangGraph 节点契约

**Files:**
- Create: `backend_python/langgraph_agent/contracts.py`
- Test: `tests/test_langgraph_agent_contracts.py`

- [ ] **Step 1: 写失败测试**

测试要求：

```python
from backend_python.langgraph_agent.contracts import get_node_contracts, validate_node_trace


def test_node_contracts_include_core_workflow_nodes() -> None:
    contracts = get_node_contracts()
    names = {item["name"] for item in contracts}

    assert "observe_state" in names
    assert "retrieve_context" in names
    assert "analyze_answer" in names
    assert "apply_policy" in names
    assert "decide_action" in names
    assert "human_review" in names
    assert "generate_question" in names
    assert "update_memory" in names


def test_validate_node_trace_marks_unknown_nodes() -> None:
    result = validate_node_trace([{"node": "observe_state"}, {"node": "unknown_node"}])

    assert result["valid"] is False
    assert result["unknownNodes"] == ["unknown_node"]
    assert result["knownNodes"] == ["observe_state"]
```

- [ ] **Step 2: 运行失败测试**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_contracts.py -q
```

Expected: 因为 `contracts.py` 不存在而失败。

- [ ] **Step 3: 实现节点契约模块**

实现要求：

```python
from __future__ import annotations

from typing import Any


NODE_CONTRACTS: list[dict[str, Any]] = [
    {
        "name": "observe_state",
        "title": "观察当前状态",
        "inputs": ["profile", "history", "agentMode", "runtime"],
        "outputs": ["agentState", "nodeTrace"],
        "risks": [],
    },
    {
        "name": "retrieve_context",
        "title": "检索三类 RAG 上下文",
        "inputs": ["profile", "history", "nextStage"],
        "outputs": ["roleHits", "questionHits", "memoryHits", "retrievalQuality", "toolCalls"],
        "risks": ["empty_retrieval", "weak_retrieval"],
    },
    {
        "name": "analyze_answer",
        "title": "分析上一轮回答",
        "inputs": ["history", "answer"],
        "outputs": ["answerAnalysis", "answerStatus"],
        "risks": ["weak_answer_streak"],
    },
    {
        "name": "apply_policy",
        "title": "应用 Agent 策略",
        "inputs": ["answerAnalysis", "retrievalQuality", "agentMode"],
        "outputs": ["policy", "triggerRules"],
        "risks": ["topic_lock", "requires_human_review"],
    },
    {
        "name": "decide_action",
        "title": "生成下一步决策",
        "inputs": ["agentState", "policy"],
        "outputs": ["decision"],
        "risks": ["invalid_decision"],
    },
    {
        "name": "human_review",
        "title": "人工复核",
        "inputs": ["policy", "decision", "answerAnalysis"],
        "outputs": ["interrupt", "resumeDecision"],
        "risks": ["requires_human_review"],
    },
    {
        "name": "generate_question",
        "title": "生成下一题",
        "inputs": ["decision", "retrievalContext", "history"],
        "outputs": ["nextQuestion"],
        "risks": ["empty_question", "repeated_question"],
    },
    {
        "name": "update_memory",
        "title": "更新候选人记忆",
        "inputs": ["history", "answerAnalysis", "decision"],
        "outputs": ["memoryUpdate"],
        "risks": [],
    },
]


def get_node_contracts() -> list[dict[str, Any]]:
    return [dict(item) for item in NODE_CONTRACTS]


def validate_node_trace(node_trace: list[dict[str, Any]] | None) -> dict[str, Any]:
    known = {item["name"] for item in NODE_CONTRACTS}
    known_nodes: list[str] = []
    unknown_nodes: list[str] = []

    for item in node_trace or []:
        node = str(item.get("node") or "").strip()
        if not node:
            continue
        if node in known:
            known_nodes.append(node)
        else:
            unknown_nodes.append(node)

    return {
        "valid": not unknown_nodes,
        "knownNodes": known_nodes,
        "unknownNodes": unknown_nodes,
    }
```

- [ ] **Step 4: 运行测试通过**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_contracts.py -q
```

Expected: 2 passed.

### Task 2: Replay Service

**Files:**
- Create: `backend_python/langgraph_agent/replay.py`
- Test: `tests/test_langgraph_runtime_replay.py`

- [ ] **Step 1: 写失败测试**

覆盖 interrupted、fallback、缺字段三种情况。

- [ ] **Step 2: 实现 replay service**

函数要求：

```text
build_runtime_replay(summary: dict) -> dict
```

输出必须包含：

```text
threadId
exists
status
summary
timeline
risks
nextActions
nodeValidation
```

规则：

- `exists=false` 时返回空时间线和“未找到运行记录”。
- `status=interrupted` 时 summary 说明暂停原因。
- `runtimeAudit.fallbackUsed=true` 时 risks 包含 `fallback_used`。
- `qualityGate.reasons` 必须进入 risks 或 timeline。
- `nodeTrace` 通过 Task 1 的 `validate_node_trace()` 校验。

- [ ] **Step 3: 运行 focused 测试**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_replay.py -q
```

Expected: passed.

### Task 3: Human Review Queue

**Files:**
- Create: `backend_python/langgraph_agent/review_queue.py`
- Test: `tests/test_langgraph_human_review_queue.py`

- [ ] **Step 1: 写失败测试**

测试要求：

- `status=interrupted` 的 checkpoint 会进入队列。
- `requiresHumanReview=true` 的 checkpoint 会进入队列。
- `completed` 且不需要人审的 checkpoint 不进入队列。
- `validate_review_decision()` 只允许 `continue_interview`、`switch_to_coach`、`fallback_classic`、`end_interview`。

- [ ] **Step 2: 实现 review queue service**

函数要求：

```text
build_review_queue(items: list[dict]) -> list[dict]
validate_review_decision(decision: str) -> str
```

队列 item 至少包含：

```text
threadId
status
currentNode
reason
options
lastQuestion
createdAt
```

- [ ] **Step 3: 运行 focused 测试**

Run:

```powershell
python -m pytest tests/test_langgraph_human_review_queue.py -q
```

Expected: passed.

### Task 4: Runtime Report Service

**Files:**
- Create: `backend_python/langgraph_agent/runtime_report.py`
- Test: `tests/test_langgraph_runtime_report.py`

- [ ] **Step 1: 写失败测试**

测试要求：

- 能统计 `totalRuns`。
- 能统计 `statusCounts`。
- 能统计 `fallbackCount`。
- 能统计 `humanReviewCount`。
- 能聚合 `qualityGate.reasons`。
- 空列表返回安全空报告。

- [ ] **Step 2: 实现 report service**

函数要求：

```text
build_runtime_report(thread_id: str, items: list[dict]) -> dict
```

输出至少包含：

```text
threadId
totalRuns
statusCounts
fallbackCount
humanReviewCount
topQualityGateReasons
summary
```

- [ ] **Step 3: 运行 focused 测试**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_report.py -q
```

Expected: passed.

### Task 5: LangGraph Runtime API 扩展

**Files:**
- Modify: `backend_python/routes/langgraph_agent.py`
- Test: `tests/test_langgraph_agent_route.py`

- [ ] **Step 1: 写路由测试**

新增测试覆盖：

- `GET /api/langgraph-agent/runtime/replay/{thread_id}`
- `GET /api/langgraph-agent/runtime/report/{thread_id}`
- `GET /api/langgraph-agent/runtime/reviews`
- `POST /api/langgraph-agent/runtime/reviews/{thread_id}/resolve`

- [ ] **Step 2: 实现路由**

实现要求：

- replay 从 `get_latest_checkpoint_summary(db, thread_id)` 读取 summary，再调用 replay service。
- report 从 `list_checkpoint_summaries(db, thread_id)` 读取列表，再调用 report service。
- reviews 第一版读取最近若干 checkpoint summaries，再调用 review queue service。
- resolve 校验 decision 后复用 checkpoint store 的 resume 逻辑，并持久化 checkpoint。

- [ ] **Step 3: 运行 focused 测试**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_route.py -q
```

Expected: passed.

### Task 6: Admin AI Debug 聚合

**Files:**
- Modify: `backend_python/ai_debug.py`
- Modify: `backend_python/routes/admin.py`
- Test: `tests/test_admin_ai_debug.py`

- [ ] **Step 1: 写失败测试**

要求 AI Debug detail 中可以看到：

```text
langgraph.replaySummary
langgraph.runtimeReport
```

缺少 checkpoint 时也不能报错。

- [ ] **Step 2: 实现聚合**

实现要求：

- 在已有 checkpoint normalize 基础上追加 replay summary。
- 如果能拿到同 threadId runs，则追加 runtime report。
- 保持旧字段兼容。

- [ ] **Step 3: 运行 focused 测试**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected: passed.

### Task 7: Vue3 管理员后台展示

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Test: `frontend/src/pages/app/admin-page.test.ts`
- Test: `frontend/src/stores/admin.test.ts`

- [ ] **Step 1: 写前端失败测试**

测试要求：

- AI Debug detail 能渲染“运行时间线”。
- 能渲染“人工复核”空态或队列。
- 能渲染“Runtime 报告”。
- 缺字段不出现 `undefined`。

- [ ] **Step 2: 实现类型和 store**

要求：

- 给 replaySummary / runtimeReport 补 TypeScript 类型。
- store 默认值使用空数组和空字符串。
- 不让模板直接读不确定深层字段。

- [ ] **Step 3: 实现 AdminPage 展示**

展示四块：

```text
运行时间线
人工复核
质量门禁
Runtime 报告
```

原始 JSON 保留折叠区域。

- [ ] **Step 4: 运行前端 focused 测试**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts src/stores/admin.test.ts
```

Expected: passed.

### Task 8: 全量验证与归档

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move after completion:
  - `docs/specs/active/langgraph-agent-workflow-v6-design.md` -> `docs/specs/completed/langgraph-agent-workflow-v6-design.md`
  - `docs/plans/active/langgraph-agent-workflow-v6.md` -> `docs/plans/completed/langgraph-agent-workflow-v6.md`

- [ ] **Step 1: 后端全量测试**

Run:

```powershell
python -m pytest -q
```

Expected: all passed.

- [ ] **Step 2: 前端全量测试**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected: all passed.

- [ ] **Step 3: 前端构建**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build passed.

- [ ] **Step 4: 浏览器验证**

验证：

```text
http://127.0.0.1:5173/vue/app/admin
```

检查：

- 桌面端管理员后台无 `undefined`。
- 移动端无横向溢出。
- AI Debug 区域能看到运行时间线、人工复核、质量门禁、Runtime 报告。

- [ ] **Step 5: 文档归档与提交**

完成后移动 active spec / plan 到 completed，更新 README 和 current-state，提交：

```powershell
git add backend_python tests frontend docs
git commit -m "feat: deepen langgraph agent workflow observability"
```

## 3. 执行约束

- 每轮开发前先用中文解释本轮要学的 Agent 工程化知识点。
- 优先测试驱动：先写或更新测试，再实现。
- 不改普通用户默认 classic 主链路。
- 不做生产 RAG V3。
- 不做 Docker / Nginx / VPS / HTTPS 上线。
- 不直接接 LangGraph Cloud。
- 不删除旧原生前端。
- 完成后必须运行后端测试、前端测试、前端 build 和浏览器验证。
