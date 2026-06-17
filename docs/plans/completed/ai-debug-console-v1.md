# AI Debug Console V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an admin-only AI Debug Console that links RAG retrieval, Agent decisions, fallback/guardrail status, and LangGraph checkpoint/nodeTrace summaries into one readable debugging surface.

**Architecture:** Reuse existing admin auth and existing log tables instead of adding new tables. Add a small backend aggregation service and admin-only read endpoints, then extend the Vue3 admin store/page to show a Chinese, product-readable debugging panel. Keep the classic Agent and current interview API unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic-style dict responses, pytest, Vue3, Pinia, TypeScript, Vitest, Vite.

---

## File Structure

Backend:

- Create `backend_python/ai_debug.py`
  - Pure aggregation and formatting helpers.
  - Converts `AgentDecisionLog`, nearby `RagRetrievalLog`, and LangGraph checkpoint summaries into a stable AI Debug payload.
  - Generates rule-based diagnostics without calling the LLM.
- Modify `backend_python/routes/admin.py`
  - Add `GET /api/admin/ai-debug/recent`.
  - Add `GET /api/admin/ai-debug/{trace_id}`.
  - Keep existing admin endpoints compatible.
- Create `tests/test_admin_ai_debug.py`
  - Covers admin auth, recent list, detail shape, fallback diagnostics, empty RAG diagnostics, and missing checkpoint behavior.

Frontend:

- Modify `frontend/src/api/admin.ts`
  - Add AI Debug response interfaces.
  - Add `fetchAdminAiDebugRecent()` and `fetchAdminAiDebugDetail(traceId)`.
- Modify `frontend/src/stores/admin.ts`
  - Add AI Debug state, selected trace id, loading/error state, and loader actions.
  - Keep existing `loadDashboard()` behavior intact.
- Modify `frontend/src/pages/app/AdminPage.vue`
  - Add AI Debug Console section inside admin page.
  - Render recent traces, RAG trace, Agent decision trace, LangGraph trace, diagnostics, and clear empty states.
- Modify `frontend/src/stores/admin.test.ts`
  - Cover store loading and detail selection.
- Modify `frontend/src/pages/app/admin-page.test.ts`
  - Cover panel rendering, Chinese enum labels, fallback state, no-checkpoint state, and no `undefined`.

Docs:

- Create `docs/learning/18-AI调试控制台如何串起RAG-Agent-LangGraph.md`
  - Explain observability, RAG debugging, Agent debugging, and interview expression.
- Update `docs/roadmap/current-state.md`
  - Mark AI Debug Console V1 as active or completed depending on final implementation state.

---

## Task 1: Backend AI Debug Aggregation Tests

**Files:**

- Create: `tests/test_admin_ai_debug.py`
- Read before editing: `tests/test_admin_routes.py`, `tests/test_admin_auth.py`, `backend_python/routes/admin.py`, `backend_python/db_models.py`

- [ ] **Step 1: Write failing backend tests**

Create `tests/test_admin_ai_debug.py` with tests covering:

```python
def test_admin_ai_debug_requires_admin(client, auth_headers):
    # normal user should get 403 for /api/admin/ai-debug/recent
    ...

def test_admin_ai_debug_recent_returns_agent_trace_summary(client, admin_headers, db_session):
    # create AgentDecisionLog with fallbackUsed and state_json retrievalQuality
    # create nearby RagRetrievalLog
    # assert recent response contains id, nextAction, fallbackUsed, totalRagHits, diagnostics
    ...

def test_admin_ai_debug_detail_contains_rag_agent_langgraph_and_diagnostics(client, admin_headers, db_session):
    # create AgentDecisionLog and RagRetrievalLog with empty recall
    # assert detail has summary, rag, agent, langgraph, diagnostics
    ...

def test_admin_ai_debug_detail_handles_missing_checkpoint(client, admin_headers, db_session):
    # no LangGraph checkpoint should not fail
    # assert langgraph.exists is False and explanation is readable
    ...
```

Use the existing test helper style in this repo. If fixtures are named differently, follow the actual fixtures in `tests/conftest.py`.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected result:

```text
FAIL because /api/admin/ai-debug/recent and /api/admin/ai-debug/{trace_id} do not exist yet
```

---

## Task 2: Backend AI Debug Aggregation Service

**Files:**

- Create: `backend_python/ai_debug.py`
- Modify only if needed: `backend_python/agent_logging.py`
- Test: `tests/test_admin_ai_debug.py`

- [ ] **Step 1: Implement safe JSON and label helpers**

Create helpers with these responsibilities:

```python
def safe_json_loads(value: str, fallback: Any) -> Any:
    ...

def normalize_rag_name(value: str) -> str:
    ...

def action_label(value: str) -> str:
    ...

def quality_level_from_hit_count(hit_count: int) -> str:
    ...
```

Expected Chinese labels:

```text
role_knowledge -> 岗位知识库
question_bank -> 题库
candidate_memory -> 候选人画像
deepen -> 继续深挖
lower_difficulty -> 降低难度
shift_topic / switch_topic -> 切换话题
finish_interview / end_interview -> 结束面试
```

- [ ] **Step 2: Implement diagnostics builder**

Add:

```python
def build_ai_debug_diagnostics(*, agent: dict[str, Any], rag_items: list[dict[str, Any]], langgraph: dict[str, Any]) -> list[dict[str, str]]:
    ...
```

Required diagnostics:

- `fallback_used`: decision used fallback.
- `empty_recall`: a retriever has `hitCount == 0`.
- `weak_recall`: a retriever quality level is weak.
- `missing_checkpoint`: LangGraph checkpoint does not exist.
- `human_review`: policy says `requiresHumanReview == true`.

Each diagnostic returns:

```python
{
    "type": "fallback_used",
    "level": "warning",
    "title": "兜底规则已启用",
    "message": "模型决策输出不稳定，系统已使用 fallback 规则保证流程继续。"
}
```

- [ ] **Step 3: Implement serializers**

Add:

```python
def build_ai_debug_recent_item(log: AgentDecisionLog, rag_logs: list[RagRetrievalLog], checkpoint: dict[str, Any]) -> dict[str, Any]:
    ...

def build_ai_debug_detail(log: AgentDecisionLog, rag_logs: list[RagRetrievalLog], checkpoint: dict[str, Any]) -> dict[str, Any]:
    ...
```

Detail payload shape:

```json
{
  "summary": {},
  "rag": {"items": [], "totalHitCount": 0},
  "agent": {},
  "langgraph": {},
  "diagnostics": []
}
```

- [ ] **Step 4: Run backend unit tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected result after routes are still missing:

```text
Some helper-level assertions may pass, route-level assertions still fail.
```

---

## Task 3: Admin AI Debug API Routes

**Files:**

- Modify: `backend_python/routes/admin.py`
- Test: `tests/test_admin_ai_debug.py`

- [ ] **Step 1: Add imports**

Add:

```python
from ..ai_debug import build_ai_debug_detail, build_ai_debug_recent_item
from ..langgraph_agent.checkpoint import summarize_checkpoint
```

- [ ] **Step 2: Add local query helper**

Inside `backend_python/routes/admin.py`, add a helper near other admin helpers:

```python
def list_rag_logs_for_agent_log(db: Session, log: AgentDecisionLog) -> list[RagRetrievalLog]:
    statement = select(RagRetrievalLog).where(RagRetrievalLog.user_id == log.user_id)
    if log.application_profile_id is not None:
        statement = statement.where(RagRetrievalLog.application_profile_id == log.application_profile_id)
    return list(
        db.scalars(
            statement.order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc()).limit(12)
        ).all()
    )
```

This is an intentional first-version approximation because old logs may not have a unified `traceId`.

- [ ] **Step 3: Add recent endpoint**

Add:

```python
@router.get("/ai-debug/recent")
async def admin_ai_debug_recent(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    ...
```

Expected behavior:

- Query recent `AgentDecisionLog`.
- For each log, load nearby RAG logs.
- Derive `threadId` from decision/state if present, otherwise `agent-log-{id}`.
- Use `summarize_checkpoint(thread_id)`.
- Return `{"items": [...]}`.

- [ ] **Step 4: Add detail endpoint**

Add:

```python
@router.get("/ai-debug/{trace_id}")
async def admin_ai_debug_detail(
    trace_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    ...
```

Expected behavior:

- `404` if log does not exist.
- Return stable detail payload.
- Do not fail if checkpoint does not exist.

- [ ] **Step 5: Run backend tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py tests/test_admin_routes.py tests/test_admin_auth.py -q
```

Expected:

```text
All selected backend admin tests pass.
```

---

## Task 4: Frontend API and Store Tests

**Files:**

- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`

- [ ] **Step 1: Write failing store/API tests**

In `frontend/src/stores/admin.test.ts`, add coverage for:

```typescript
it("loads admin AI debug recent traces with dashboard data", async () => {
  // mock /api/admin/ai-debug/recent
  // assert store.aiDebugRecent is populated
});

it("loads selected AI debug detail", async () => {
  // call store.loadAiDebugDetail(1)
  // assert selected detail has summary/rag/agent/langgraph/diagnostics
});
```

- [ ] **Step 2: Run failing frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected:

```text
FAIL because AI Debug API/store fields do not exist yet
```

---

## Task 5: Frontend API and Store Implementation

**Files:**

- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Test: `frontend/src/stores/admin.test.ts`

- [ ] **Step 1: Add TypeScript interfaces**

Add interfaces:

```typescript
export interface AdminAiDebugDiagnostic {
  type: string;
  level: "info" | "warning" | "error" | string;
  title: string;
  message: string;
}

export interface AdminAiDebugRecentItem {
  traceId: number;
  createdAt: string | null;
  userId: number;
  applicationProfileId: number | null;
  agentMode: string;
  nextAction: string;
  nextActionLabel: string;
  difficulty: string;
  fallbackUsed: boolean;
  totalRagHits: number;
  threadId: string;
  diagnostics: AdminAiDebugDiagnostic[];
}

export interface AdminAiDebugDetail {
  summary: Record<string, unknown>;
  rag: Record<string, unknown>;
  agent: Record<string, unknown>;
  langgraph: Record<string, unknown>;
  diagnostics: AdminAiDebugDiagnostic[];
}
```

- [ ] **Step 2: Add API functions**

Add:

```typescript
export function fetchAdminAiDebugRecent(): Promise<AdminListResponse<AdminAiDebugRecentItem>> {
  return apiRequest<AdminListResponse<AdminAiDebugRecentItem>>("/api/admin/ai-debug/recent");
}

export function fetchAdminAiDebugDetail(traceId: number): Promise<AdminAiDebugDetail> {
  return apiRequest<AdminAiDebugDetail>(`/api/admin/ai-debug/${traceId}`);
}
```

- [ ] **Step 3: Add store state and actions**

In `useAdminStore`, add:

```typescript
const aiDebugRecent = ref<adminApi.AdminAiDebugRecentItem[]>([]);
const selectedAiDebugTraceId = ref<number | null>(null);
const selectedAiDebugDetail = ref<adminApi.AdminAiDebugDetail | null>(null);
const aiDebugLoading = ref(false);
const aiDebugError = ref("");
```

Add `adminApi.fetchAdminAiDebugRecent()` into `loadDashboard()`.

Add:

```typescript
async function loadAiDebugDetail(traceId: number): Promise<void> {
  ...
}
```

- [ ] **Step 4: Run frontend store tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected:

```text
PASS
```

---

## Task 6: Admin Page AI Debug Panel Tests

**Files:**

- Modify: `frontend/src/pages/app/admin-page.test.ts`
- Modify later: `frontend/src/pages/app/AdminPage.vue`

- [ ] **Step 1: Extend admin page mocked store**

Add mocked fields:

```typescript
aiDebugRecent: [
  {
    traceId: 1,
    createdAt: "2026-06-13T18:00:00",
    userId: 101,
    applicationProfileId: 201,
    agentMode: "coach",
    nextAction: "lower_difficulty",
    nextActionLabel: "降低难度",
    difficulty: "basic",
    fallbackUsed: true,
    totalRagHits: 0,
    threadId: "agent-log-1",
    diagnostics: [{ type: "fallback_used", level: "warning", title: "兜底规则已启用", message: "模型决策输出不稳定。" }]
  }
],
selectedAiDebugTraceId: 1,
selectedAiDebugDetail: {
  summary: { traceId: 1, agentMode: "coach", stage: "技术追问" },
  rag: { totalHitCount: 0, items: [{ retrieverLabel: "岗位知识库", hitCount: 0, qualityLevel: "miss" }] },
  agent: { nextActionLabel: "降低难度", fallbackUsed: true, reason: "连续弱回答" },
  langgraph: { exists: false, explanation: "本次请求未启用 LangGraph 旁路。" },
  diagnostics: [...]
}
```

- [ ] **Step 2: Add page assertions**

Assert page contains:

```text
AI 调试控制台
最近 AI 请求
RAG 召回链路
Agent 决策链路
LangGraph 执行链路
诊断建议
兜底规则已启用
本次请求未启用 LangGraph 旁路
```

Assert page does not contain:

```text
undefined
```

- [ ] **Step 3: Run failing page test**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected:

```text
FAIL because AdminPage.vue does not render AI Debug panel yet.
```

---

## Task 7: Admin Page AI Debug Panel Implementation

**Files:**

- Modify: `frontend/src/pages/app/AdminPage.vue`
- Test: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Add AI Debug section after platform overview**

Add a new section title:

```html
<h2>AI 调试控制台</h2>
```

Render recent traces as buttons/cards:

```html
<button
  v-for="trace in admin.aiDebugRecent"
  :key="trace.traceId"
  type="button"
  @click="admin.loadAiDebugDetail(trace.traceId)"
>
  {{ trace.nextActionLabel }}
</button>
```

- [ ] **Step 2: Add readable detail panels**

Render four sub-panels:

```text
RAG 召回链路
Agent 决策链路
LangGraph 执行链路
诊断建议
```

Use helper functions to avoid `undefined`:

```typescript
function displayValue(value: unknown, fallback = "暂无"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}
```

- [ ] **Step 3: Keep raw JSON folded**

If raw JSON is shown, use:

```html
<details>
  <summary>查看原始调试 JSON</summary>
  <pre>{{ JSON.stringify(admin.selectedAiDebugDetail, null, 2) }}</pre>
</details>
```

- [ ] **Step 4: Run page tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected:

```text
PASS
```

---

## Task 8: Learning Doc and Roadmap Update

**Files:**

- Create: `docs/learning/18-AI调试控制台如何串起RAG-Agent-LangGraph.md`
- Modify: `docs/roadmap/current-state.md`
- Modify after final completion: move active spec/plan to completed

- [ ] **Step 1: Write learning document**

Include these sections:

```markdown
# AI 调试控制台如何串起 RAG、Agent 和 LangGraph

## 1. 为什么 AI 应用需要可观测性
## 2. 一次面试问题生成链路
## 3. RAG 调试看什么
## 4. Agent 调试看什么
## 5. LangGraph checkpoint 看什么
## 6. 面试时怎么讲
```

- [ ] **Step 2: Update roadmap**

Add a short record that AI Debug Console V1 is the current active phase during implementation.

- [ ] **Step 3: After implementation is verified, archive active docs**

Move:

```text
docs/specs/active/ai-debug-console-v1-design.md
docs/plans/active/ai-debug-console-v1.md
```

To:

```text
docs/specs/completed/ai-debug-console-v1-design.md
docs/plans/completed/ai-debug-console-v1.md
```

Only do this after all verification passes.

---

## Task 9: Full Verification

**Files:** no code files unless failures require fixes.

- [ ] **Step 1: Run backend full test suite**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All backend tests pass.
```

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected:

```text
All frontend tests pass.
```

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected:

```text
Build succeeds.
```

- [ ] **Step 4: Browser verification**

Open:

```text
http://127.0.0.1:5173/vue/app/admin
```

Verify desktop:

- Admin page loads.
- AI 调试控制台 is visible.
- Recent trace list is readable.
- RAG / Agent / LangGraph / diagnostics panels are visible.
- No `undefined` text.

Verify mobile:

- No horizontal overflow.
- AI Debug cards stack vertically.
- Text remains readable.

---

## Self-Review

Spec coverage:

- Admin-only AI Debug recent/detail endpoints are covered by Tasks 1-3.
- RAG, Agent, fallback, LangGraph checkpoint aggregation is covered by Tasks 2-3.
- Vue3 admin panel is covered by Tasks 4-7.
- Tests-first workflow is covered in every implementation task.
- Learning doc and interview expression are covered by Task 8.
- Full verification and browser validation are covered by Task 9.

Scope guard:

- This plan does not rewrite RAG algorithms.
- This plan does not replace `/api/interview/next-question`.
- This plan does not delete classic Agent.
- This plan does not do deployment work.
- This plan only extends the Vue3 admin page, not the entire frontend.
