# Production UX & Auth Hardening V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口公网演示后暴露的报告解释、训练筛选、AI 调试台聚合和 Redis 会话强制下线问题，让项目从“能跑通”进一步接近“可演示、可诊断、可控权”的生产化状态。

**Architecture:** 保持现有 FastAPI + SQLAlchemy + Vue3 + Pinia + PostgreSQL + Redis + Docker Compose 架构。前 3 个任务优先在展示层和现有 API 聚合层收口；鉴权任务在现有 access token + refresh token + `refresh_tokens` 表基础上新增 Redis session 服务，不重做数据库关系。

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Redis, PyJWT, Vue3, Pinia, Vitest, Vite, Docker Compose, PostgreSQL, Nginx.

---

## File Map

- `frontend/src/pages/app/ReportPage.vue`: 把“为什么这样问”改成“出题依据”，增加低质量 fallback 隐藏、`ragReasons` 去重和展示上限。
- `frontend/src/pages/app/report-page.test.ts`: 覆盖出题依据标题、去重、fallback 隐藏和报告仍能显示逐题复盘。
- `frontend/src/stores/training.ts`: 增加筛选标题、筛选数量、当前 weakTag label、清除 weakTag 筛选等派生状态。
- `frontend/src/pages/app/TrainingPage.vue`: 将薄弱点地图明确变成筛选器，右侧标题随筛选变化，增加“查看全部”入口。
- `frontend/src/pages/app/training-page.test.ts`: 覆盖默认全部任务、点击 weakTag 筛选、标题数量、清除筛选。
- `frontend/src/components/training/TrainingWeakTagMap.vue`: 优化选中态和“全部”入口，如果该组件已有足够结构则只做小改。
- `backend_python/ai_debug.py`: 增加 RAG 聚合、诊断建议去重、质量标签中文化。
- `tests/test_admin_ai_debug.py`: 覆盖 `ragSummary`、`diagnosticSummary`、中文质量标签和重复诊断合并。
- `frontend/src/api/admin.ts`: 增加 AI debug 聚合字段类型和管理员强制下线 API 类型。
- `frontend/src/stores/admin.ts`: 暴露强制下线 action 和 AI debug tab 状态。
- `frontend/src/pages/app/AdminPage.vue`: AI 调试台拆成 tabs/分区，RAG/Agent/诊断建议默认聚合展示，用户表增加强制下线操作。
- `frontend/src/pages/app/admin-page.test.ts`: 覆盖调试台分类、聚合文案、中文质量标签和强制下线按钮。
- `backend_python/session_store.py`: 新增 Redis session 服务和内存降级实现。
- `backend_python/auth.py`: access token 增加 `sid`，`get_current_user` 检查 session 状态。
- `backend_python/routes/auth.py`: 登录写 session，刷新检查 session，退出撤销 session。
- `backend_python/routes/admin.py`: 增加 `POST /api/admin/users/{user_id}/force-logout`。
- `backend_python/security.py`: 将 token blacklist 接口扩展为可使用 Redis 的实现，保留内存降级。
- `backend_python/redis_client.py`: 复用现有 Redis client，必要时导出 session store 可用的 client。
- `tests/test_auth.py`: 覆盖 session id、session revoked 后 `/me` 失败、logout 撤销 session。
- `tests/test_admin_users.py`: 新增或扩展管理员强制下线测试。
- `frontend/src/api/client.ts`: 识别结构化 401 `session_revoked/token_revoked`，清 token 并抛出友好错误。
- `frontend/src/api/client.test.ts`: 覆盖被踢下线清 token、不再无限 refresh。
- `frontend/src/stores/auth.ts`: 保持 logout/restore 逻辑，必要时记录 session revoked 提示。
- `frontend/src/stores/auth.test.ts`: 覆盖被踢下线后的用户状态。
- `docs/roadmap/current-state.md`, `docs/plans/README.md`: 指向本 active plan。

---

## Task 1: Report Page 出题依据收口

**Files:**
- Modify: `frontend/src/pages/app/ReportPage.vue`
- Modify: `frontend/src/pages/app/report-page.test.ts`

- [ ] **Step 1: Write failing tests for evidence display**

Add tests to `frontend/src/pages/app/report-page.test.ts`:

```ts
it("renders human-readable evidence instead of the old why title", () => {
  reportStore.record.report.decisionSummary = "JD 要求 RAG 链路理解，上一轮回答缺少日志字段。";
  reportStore.record.report.ragReasons = [
    "命中岗位知识库：RAG Agent 与 LangGraph 项目知识",
    "命中岗位知识库：RAG Agent 与 LangGraph 项目知识",
    "命中题库：Redis PostgreSQL Celery 生产化职责",
    "命中候选人画像：Python 后端开发实习生"
  ];

  const wrapper = mount(ReportPage, { global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } } });

  expect(wrapper.text()).toContain("出题依据");
  expect(wrapper.text()).not.toContain("为什么这样问");
  expect(wrapper.text()).toContain("JD 要求 RAG 链路理解");
  expect(wrapper.findAll("li").filter((item) => item.text().includes("RAG Agent 与 LangGraph")).length).toBe(1);
});
```

Add fallback hiding coverage:

```ts
it("hides low-value fallback evidence copy", () => {
  reportStore.record.report.decisionSummary = "本题由当前档案、历史回答和检索上下文共同驱动。";
  reportStore.record.report.ragReasons = [];

  const wrapper = mount(ReportPage, { global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } } });

  expect(wrapper.text()).not.toContain("出题依据");
  expect(wrapper.text()).not.toContain("本题由当前档案、历史回答和检索上下文共同驱动");
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: tests fail because title is still `为什么这样问`, duplicate reasons are not deduped, fallback still renders.

- [ ] **Step 3: Implement display helpers**

In `ReportPage.vue`, add computed helpers:

```ts
const LOW_VALUE_EVIDENCE = ["本题由当前档案、历史回答和检索上下文共同驱动。"];

const evidenceReasons = computed(() => {
  const reasons = report.value.ragReasons;
  if (!Array.isArray(reasons)) return [];
  return Array.from(new Set(reasons.map(String).map((item) => item.trim()).filter(Boolean))).slice(0, 3);
});

const shouldShowEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return (summary && !LOW_VALUE_EVIDENCE.includes(summary)) || evidenceReasons.value.length > 0;
});
```

Update template:

```vue
<section v-if="shouldShowEvidence" class="insight-card">
  <h2>出题依据</h2>
  <p v-if="evidenceText">{{ evidenceText }}</p>
  <ul v-if="evidenceReasons.length">
    <li v-for="reason in evidenceReasons" :key="reason">{{ reason }}</li>
  </ul>
</section>
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/app/ReportPage.vue frontend/src/pages/app/report-page.test.ts
git commit -m "fix: clarify report evidence section"
```

**Acceptance:**
- Report page no longer shows `为什么这样问`.
- Low-value fallback text does not occupy a card.
- RAG reasons are deduped and capped at 3.

---

## Task 2: Training Page 薄弱点筛选收口

**Files:**
- Modify: `frontend/src/stores/training.ts`
- Modify: `frontend/src/pages/app/TrainingPage.vue`
- Modify: `frontend/src/components/training/TrainingWeakTagMap.vue`
- Modify: `frontend/src/pages/app/training-page.test.ts`
- Optional Modify: `frontend/src/components/training/TrainingWeakTagMap.test.ts`

- [ ] **Step 1: Write failing store/page tests**

In `frontend/src/pages/app/training-page.test.ts`, extend fixture with two tasks:

```ts
const ragTask = {
  id: 3,
  weakTag: "rag_quality",
  weakLabel: "RAG 质量评估",
  title: "RAG 质量专项训练",
  description: "练习 RAG 质量评估。",
  status: "todo",
  priority: "high",
  masteryScore: 45,
  sourceInterviewRecordId: 12
};
const agentTask = {
  id: 4,
  weakTag: "agent_state",
  weakLabel: "Agent State",
  title: "Agent State 专项训练",
  description: "练习 Agent 状态表达。",
  status: "todo",
  priority: "medium",
  masteryScore: 55,
  sourceInterviewRecordId: 12
};
```

Add test:

```ts
it("shows all tasks by default and makes weak tag selection explicit", () => {
  trainingStore.weakTag = "";
  trainingStore.visibleTasks = [ragTask, agentTask];
  trainingStore.taskListTitle = "训练任务 · 全部（2 个）";
  trainingStore.activeWeakTagLabel = "";

  const wrapper = mount(TrainingPage, { global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } } });

  expect(wrapper.text()).toContain("训练任务 · 全部（2 个）");
  expect(wrapper.text()).toContain("RAG 质量专项训练");
  expect(wrapper.text()).toContain("Agent State 专项训练");
});
```

Add selection/clear coverage:

```ts
it("filters the task list from the weak tag map and can return to all tasks", async () => {
  const wrapper = mount(TrainingPage, { global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } } });

  await wrapper.get('[data-testid="weak-tag-agent_tool_calling"]').trigger("click");
  expect(trainingStore.setWeakTagFilter).toHaveBeenCalledWith("agent_tool_calling");

  await wrapper.get('[data-testid="clear-weak-tag-filter"]').trigger("click");
  expect(trainingStore.setWeakTagFilter).toHaveBeenCalledWith("");
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/training-page.test.ts
```

Expected: fail because `taskListTitle`, explicit title/count, and clear weakTag entry do not exist.

- [ ] **Step 3: Add store computed state**

In `frontend/src/stores/training.ts`, add:

```ts
const activeWeakTagGroup = computed(() => weakTagGroups.value.find((group) => group.weakTag === weakTag.value) || null);
const activeWeakTagLabel = computed(() => activeWeakTagGroup.value?.weakLabel || weakTag.value);
const taskListTitle = computed(() => {
  const label = activeWeakTagLabel.value || "全部";
  return `训练任务 · ${label}（${visibleTasks.value.length} 个）`;
});
const hasWeakTagFilter = computed(() => Boolean(weakTag.value));
```

Export these fields. Keep `sourceInterviewRecordId` filtering intact.

- [ ] **Step 4: Update page and weak tag map**

In `TrainingPage.vue`, change toolbar title:

```vue
<p class="toolbar-label">{{ training.hasWeakTagFilter ? "当前薄弱点" : "任务筛选" }}</p>
<h2>{{ training.taskListTitle }}</h2>
<button
  v-if="training.hasWeakTagFilter"
  data-testid="clear-weak-tag-filter"
  type="button"
  class="ghost-action"
  @click="training.setWeakTagFilter('')"
>
  查看全部
</button>
```

In `TrainingWeakTagMap.vue`, add an explicit “全部” row/button if missing:

```vue
<button data-testid="weak-tag-all" :class="{ active: !activeWeakTag }" @click="$emit('select', '')">
  全部训练任务
</button>
```

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/training-page.test.ts
cd frontend
npm.cmd run test -- src/components/training/TrainingWeakTagMap.test.ts
```

Expected: pass. If the component test file does not exist, create it only if the page test cannot cover the behavior.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/training.ts frontend/src/pages/app/TrainingPage.vue frontend/src/components/training/TrainingWeakTagMap.vue frontend/src/pages/app/training-page.test.ts
git commit -m "fix: clarify training weak tag filtering"
```

**Acceptance:**
- Default view clearly says all tasks.
- Selecting a weakTag visibly filters right-side tasks.
- User can return to all tasks without using the global “清空筛选”.

---

## Task 3: Admin AI Debug 聚合、分类和中文化

**Files:**
- Modify: `backend_python/ai_debug.py`
- Modify: `tests/test_admin_ai_debug.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing backend aggregation tests**

In `tests/test_admin_ai_debug.py`, add a test that creates repeated RAG logs:

```python
def test_admin_ai_debug_detail_aggregates_rag_and_diagnostics() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        log = AgentDecisionLog(
            user_id=user_id,
            application_profile_id=505,
            request_type="next_question",
            next_action="deepen",
            stage="技术追问",
            difficulty="medium",
            focus="RAG 日志字段",
            reason="继续追问 RAG",
            tools_json="[]",
            state_json=json.dumps({"threadId": "debug-aggregate-1"}, ensure_ascii=False),
            decision_json="{}",
            fallback_used=0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        for _ in range(3):
            db.add(RagRetrievalLog(
                user_id=user_id,
                application_profile_id=505,
                request_type="next_question",
                query_text="RAG 日志字段",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=1,
                hits_json=json.dumps([{"title": "RAG Agent 与 LangGraph 项目知识"}], ensure_ascii=False),
            ))
        db.commit()
        log_id = log.id

    response = client.get(f"/api/admin/ai-debug/{log_id}", headers=headers)
    body = response.json()

    assert body["rag"]["summary"][0]["knowledgeBase"] == "role_knowledge"
    assert body["rag"]["summary"][0]["qualityLabel"] == "弱相关"
    assert body["rag"]["summary"][0]["occurrenceCount"] == 3
    assert body["diagnosticSummary"][0]["count"] == 3
```

- [ ] **Step 2: Run backend RED**

Run:

```bash
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected: fail because `rag.summary`, `diagnosticSummary`, `qualityLabel`, `occurrenceCount` do not exist.

- [ ] **Step 3: Implement backend aggregation helpers**

In `backend_python/ai_debug.py`, add:

```python
QUALITY_LABELS = {"good": "高相关", "weak": "弱相关", "miss": "空召回", "empty": "空召回", "unknown": "未评估"}

def quality_label(value: str) -> str:
    return QUALITY_LABELS.get(value or "", "未评估")

def build_rag_summary(rag_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in rag_items:
        key = (str(item.get("retrieverName") or ""), str(item.get("qualityLevel") or "unknown"))
        current = grouped.setdefault(key, {
            "knowledgeBase": key[0],
            "label": item.get("retrieverLabel") or normalize_rag_name(key[0]),
            "hitCount": 0,
            "quality": key[1],
            "qualityLabel": quality_label(key[1]),
            "occurrenceCount": 0,
        })
        current["hitCount"] += int(item.get("hitCount") or 0)
        current["occurrenceCount"] += 1
    return list(grouped.values())

def build_diagnostic_summary(diagnostics: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in diagnostics:
        key = (item.get("title", ""), item.get("message", ""))
        current = grouped.setdefault(key, {**item, "count": 0})
        current["count"] += 1
    return list(grouped.values())
```

Return the summaries from `build_ai_debug_detail`:

```python
"rag": {
    "items": rag_items,
    "summary": build_rag_summary(rag_items),
    "totalHitCount": sum(int(item.get("hitCount") or 0) for item in rag_items),
    "relation": "按 userId、applicationProfileId 和最近时间尽力关联",
},
"diagnosticSummary": build_diagnostic_summary(diagnostics),
```

- [ ] **Step 4: Run backend GREEN**

Run:

```bash
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected: pass.

- [ ] **Step 5: Write failing frontend tests for tabs/summary**

In `frontend/src/pages/app/admin-page.test.ts`, update `selectedAiDebugDetail` fixture to include:

```ts
rag: {
  totalHitCount: 9,
  summary: [
    { knowledgeBase: "role_knowledge", label: "岗位知识库", hitCount: 3, quality: "weak", qualityLabel: "弱相关", occurrenceCount: 3 }
  ],
  items: [{ retrieverLabel: "岗位知识库", queryText: "RAG 日志 JSON", hitCount: 1, qualityLevel: "weak" }]
},
diagnosticSummary: [
  { type: "weak_recall", level: "info", title: "岗位知识库弱召回", message: "岗位知识库召回质量偏弱。", count: 3 }
]
```

Add assertions:

```ts
expect(text).toContain("总览");
expect(text).toContain("RAG 召回");
expect(text).toContain("Agent 决策");
expect(text).toContain("诊断建议");
expect(text).toContain("岗位知识库");
expect(text).toContain("弱相关");
expect(text).toContain("出现 3 次");
expect(text).not.toMatch(/good|weak|miss/);
```

- [ ] **Step 6: Run frontend RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fail because current UI renders raw chain sections and raw quality labels.

- [ ] **Step 7: Update frontend types and UI**

In `frontend/src/api/admin.ts`, add interfaces:

```ts
export interface AdminAiDebugRagSummary {
  knowledgeBase: string;
  label: string;
  hitCount: number;
  quality: string;
  qualityLabel: string;
  occurrenceCount: number;
}

export interface AdminAiDebugDiagnosticSummary extends AdminAiDebugDiagnostic {
  count: number;
}
```

In `AdminPage.vue`, replace the always-expanded detail with sections or tabs:

```vue
<div class="debug-tabs" role="tablist">
  <button data-testid="ai-debug-tab-overview">总览</button>
  <button data-testid="ai-debug-tab-rag">RAG 召回</button>
  <button data-testid="ai-debug-tab-agent">Agent 决策</button>
  <button data-testid="ai-debug-tab-diagnostics">诊断建议</button>
  <button data-testid="ai-debug-tab-raw">原始日志</button>
</div>
```

Keep implementation simple: if full interactive tabs are too much for this task, use visually separated sections with those headings and default raw log collapsed in `<details>`.

Render `rag.summary` before raw `rag.items`. Render `diagnosticSummary` and show `出现 N 次` when `count > 1`.

- [ ] **Step 8: Run frontend GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add backend_python/ai_debug.py tests/test_admin_ai_debug.py frontend/src/api/admin.ts frontend/src/stores/admin.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "fix: aggregate admin ai debug details"
```

**Acceptance:**
- RAG repeated rows are summarized.
- Diagnosis repeats are counted.
- Admin page defaults to categorized diagnostics, with raw logs available but not dominant.

---

## Task 4: Redis Session Control and Force Logout

**Files:**
- Create: `backend_python/session_store.py`
- Modify: `backend_python/auth.py`
- Modify: `backend_python/routes/auth.py`
- Modify: `backend_python/routes/admin.py`
- Modify: `backend_python/security.py`
- Modify: `backend_python/redis_client.py`
- Modify: `tests/test_auth.py`
- Create or Modify: `tests/test_admin_users.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/stores/auth.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing backend session tests**

In `tests/test_auth.py`, add:

```python
def test_access_token_contains_session_id() -> None:
    token = create_access_token(user_id=42, session_id="session-42")

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "42"
    assert payload["sid"] == "session-42"
```

Add flow test:

```python
def test_revoked_session_rejects_existing_access_token() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"session-revoked-{suffix}@example.com"
    username = f"session_revoked_{suffix[:12]}"
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    payload = decode_token(tokens["accessToken"], expected_type="access")
    session_store.revoke_session(payload["sid"], reason="admin_force_logout")

    response = client.get("/api/auth/me", headers=auth_headers(tokens))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_revoked"
```

Use a test-safe in-memory store fixture if needed:

```python
from backend_python.session_store import session_store
```

- [ ] **Step 2: Run auth RED**

Run:

```bash
python -m pytest tests/test_auth.py -q
```

Expected: `create_access_token` does not accept `session_id`, `session_store` does not exist.

- [ ] **Step 3: Implement session store**

Create `backend_python/session_store.py` with a protocol-like class and two implementations:

```python
class SessionStore:
    def create_session(self, *, user_id: int, refresh_token_id: int, ttl_seconds: int) -> str:
        raise NotImplementedError

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def touch_session(self, session_id: str, ttl_seconds: int) -> None:
        raise NotImplementedError

    def revoke_session(self, session_id: str, reason: str = "") -> bool:
        raise NotImplementedError

    def revoke_user_sessions(self, user_id: int, reason: str = "") -> int:
        raise NotImplementedError
```

Key rules:

- Redis keys follow spec: `auth:session:{session_id}`, `auth:user_sessions:{user_id}`.
- Memory implementation is used when Redis is disabled/unavailable in local tests.
- Store JSON values as strings in Redis.
- `revoke_user_sessions` returns the number of active sessions it revoked.

- [ ] **Step 4: Update access token and current user auth**

In `backend_python/auth.py`:

```python
def create_access_token(user_id: int, session_id: str = "") -> str:
    payload = {"sub": str(user_id), "type": "access", "sid": session_id, "exp": expire}
```

In `get_current_user` after decoding:

```python
session_id = str(payload.get("sid") or "")
if session_id:
    session = session_store.get_session(session_id)
    if not session or session.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_revoked", "message": "当前登录会话已失效，请重新登录。"},
        )
```

Use `session_store.touch_session(session_id, ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)` only if it is cheap and does not make every request noisy.

- [ ] **Step 5: Update login/refresh/logout**

In `backend_python/routes/auth.py`:

- Create refresh token DB row first.
- Flush/refresh it to get `record.id`.
- Create Redis session with `user.id` and `refresh_token_id`.
- Sign access token with `session_id`.
- Include `sessionId` in response for admin/debug visibility if desired.

Refresh:

- Lookup refresh token DB row.
- Find active session by refresh token id or current refresh token metadata.
- Sign new access token with the same session id.
- If session revoked, return 401 with `session_revoked`.

Logout:

- Revoke refresh token.
- Revoke session if available.
- Add current access token to Redis/memory blacklist.

- [ ] **Step 6: Run auth GREEN**

Run:

```bash
python -m pytest tests/test_auth.py -q
python -m pytest tests/test_security_hardening.py tests/test_redis_client.py -q
```

Expected: pass.

- [ ] **Step 7: Write failing admin force logout tests**

Create or extend `tests/test_admin_users.py`:

```python
def test_admin_can_force_logout_user_sessions() -> None:
    client = TestClient(app)
    admin_tokens, _ = create_admin_user_and_tokens(client)
    user_tokens, user_id = create_regular_user_and_tokens(client)

    response = client.post(f"/api/admin/users/{user_id}/force-logout", headers=auth_headers(admin_tokens))

    assert response.status_code == 200
    assert response.json()["revokedSessions"] >= 1
    assert response.json()["revokedRefreshTokens"] >= 1
    assert client.get("/api/auth/me", headers=auth_headers(user_tokens)).status_code == 401
```

Also test non-admin:

```python
def test_force_logout_requires_admin() -> None:
    response = client.post(f"/api/admin/users/{target_id}/force-logout", headers=auth_headers(user_tokens))
    assert response.status_code == 403
```

- [ ] **Step 8: Run admin RED**

Run:

```bash
python -m pytest tests/test_admin_users.py -q
```

Expected: route missing.

- [ ] **Step 9: Implement admin force logout**

In `backend_python/routes/admin.py`, add:

```python
@router.post("/users/{user_id}/force-logout")
async def admin_force_logout_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_user)) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.utcnow()
    active_tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))).all()
    for token in active_tokens:
        token.revoked_at = now
    db.commit()
    revoked_sessions = session_store.revoke_user_sessions(user_id, reason="admin_force_logout")
    return {"ok": True, "revokedSessions": revoked_sessions, "revokedRefreshTokens": len(active_tokens)}
```

Import `RefreshToken` and `session_store`.

- [ ] **Step 10: Run admin GREEN**

Run:

```bash
python -m pytest tests/test_admin_users.py tests/test_auth.py -q
```

Expected: pass.

- [ ] **Step 11: Write failing frontend client/admin tests**

In `frontend/src/api/client.test.ts`, add:

```ts
it("clears tokens when the backend reports a revoked session", async () => {
  setApiTokens({ accessToken: "access-1", refreshToken: "refresh-1" });
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
    detail: { code: "session_revoked", message: "当前登录会话已失效，请重新登录。" }
  }), { status: 401, headers: { "Content-Type": "application/json" } }));

  await expect(apiRequest("/api/auth/me")).rejects.toThrow("当前登录会话已失效");

  expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
  expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
});
```

In `frontend/src/pages/app/admin-page.test.ts`, add:

```ts
it("allows admins to force logout a user", async () => {
  const wrapper = mount(AdminPage, { global: globalConfig });

  await wrapper.get('[data-testid="force-logout-user-2"]').trigger("click");

  expect(adminStore.forceLogoutUser).toHaveBeenCalledWith(2);
});
```

- [ ] **Step 12: Run frontend RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/api/client.test.ts src/pages/app/admin-page.test.ts
```

Expected: client does not parse structured detail code, admin store/action/button missing.

- [ ] **Step 13: Implement frontend client and admin action**

In `frontend/src/api/client.ts`, update `getErrorMessage` to handle object detail:

```ts
export function getApiErrorCode(body: unknown): string {
  const detail = typeof body === "object" && body && "detail" in body ? (body as { detail?: unknown }).detail : null;
  return typeof detail === "object" && detail && "code" in detail ? String((detail as { code?: unknown }).code || "") : "";
}
```

In `apiRequest`, before refresh retry:

```ts
const errorCode = getApiErrorCode(body);
if (response.status === 401 && ["session_revoked", "token_revoked"].includes(errorCode)) {
  clearApiTokens();
  throw new Error(getErrorMessage(body, response.status));
}
```

In `frontend/src/api/admin.ts`:

```ts
export interface AdminForceLogoutResponse { ok: boolean; revokedSessions: number; revokedRefreshTokens: number; }
export function forceLogoutUser(userId: number): Promise<AdminForceLogoutResponse> {
  return apiRequest<AdminForceLogoutResponse>(`/api/admin/users/${userId}/force-logout`, { method: "POST" });
}
```

In `frontend/src/stores/admin.ts`, add:

```ts
async function forceLogoutUser(userId: number): Promise<void> {
  await adminApi.forceLogoutUser(userId);
}
```

In `AdminPage.vue`, add a button in the user table:

```vue
<button data-testid="force-logout-user-${user.id}" type="button" @click="admin.forceLogoutUser(user.id)">
  强制下线
</button>
```

Do not show this for the current admin user unless the implementation explicitly supports self-kick.

- [ ] **Step 14: Run frontend GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/api/client.test.ts src/pages/app/admin-page.test.ts src/stores/auth.test.ts
```

Expected: pass.

- [ ] **Step 15: Commit**

```bash
git add backend_python/session_store.py backend_python/auth.py backend_python/routes/auth.py backend_python/routes/admin.py backend_python/security.py backend_python/redis_client.py tests/test_auth.py tests/test_admin_users.py frontend/src/api/admin.ts frontend/src/api/client.ts frontend/src/api/client.test.ts frontend/src/stores/admin.ts frontend/src/stores/auth.ts frontend/src/stores/auth.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: add redis backed session revocation"
```

**Acceptance:**
- Existing refresh token DB behavior remains.
- Redis/in-memory session state controls access token validity.
- Admin can force user logout.
- Frontend clears tokens on session revoked.

---

## Task 5: Full Verification and Deployment Handoff

**Files:**
- Modify: `docs/roadmap/current-state.md` only if implementation status changes during execution.
- Modify: `docs/deployment/troubleshooting.md` only if deployment reveals a new Redis/session operational note.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
python -m pytest tests/test_auth.py -q
python -m pytest tests/test_admin_users.py -q
python -m pytest tests/test_admin_ai_debug.py -q
python -m pytest tests/test_training_task_generation.py tests/test_training_tags.py -q
python -m pytest tests/test_question_reviews.py -q
```

Expected: all pass.

- [ ] **Step 2: Run focused frontend tests**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
npm.cmd run test -- src/pages/app/training-page.test.ts
npm.cmd run test -- src/pages/app/admin-page.test.ts
npm.cmd run test -- src/api/client.test.ts
npm.cmd run test -- src/stores/auth.test.ts
```

Expected: all pass.

- [ ] **Step 3: Run full local verification**

Run:

```bash
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected:

```text
backend pytest: all passed
frontend vitest: all passed
frontend build: succeeded
```

- [ ] **Step 4: Validate compose config**

Run:

```bash
docker compose --env-file .env.production.example config --quiet
```

Expected: exit code 0.

- [ ] **Step 5: VPS deployment commands**

Use on the VPS:

```bash
cd /home/ubuntu/ai-interview
git pull origin main
sudo docker run --rm -v "$PWD/frontend":/app -w /app node:20-alpine sh -c "npm ci && npm run build"
sudo docker compose --env-file .env.production up -d --build app worker nginx
sudo docker compose --env-file .env.production ps
curl -s http://127.0.0.1:8080/api/health
```

Expected:

```text
app, worker, nginx, redis, db are Up
/api/health returns status ok and redis status ok
```

- [ ] **Step 6: Public smoke path**

Manual verification:

```text
1. Login as normal user.
2. Complete or open a report.
3. Confirm report page shows 出题依据 or hides the section for fallback-only reports.
4. Open training center.
5. Confirm default title is 训练任务 · 全部.
6. Click a weakTag in 薄弱点训练地图.
7. Confirm right side list filters and 查看全部 restores all tasks.
8. Login as admin.
9. Open AI 调试控制台 and verify 总览/RAG 召回/Agent 决策/诊断建议/原始日志 separation.
10. Confirm RAG quality labels show 高相关/弱相关/空召回 rather than raw good/weak/miss.
11. Force logout a test user.
12. Refresh that user's page and confirm it returns to login with a friendly message.
```

- [ ] **Step 7: Final commit if docs were updated**

If deployment docs or roadmap are changed:

```bash
git add docs/roadmap/current-state.md docs/deployment/troubleshooting.md
git commit -m "docs: update production hardening verification"
```

---

## Self-Review

- Spec coverage: This plan maps every requirement from `docs/specs/active/production-ux-auth-hardening-v1-design.md` to a task: report evidence, training weakTag filtering, admin AI debug aggregation, Redis session force logout, and verification/deployment.
- Scope guard: The plan does not redesign database relationships, rewrite RAG retrieval, introduce RBAC, or rebuild the whole UI.
- TDD coverage: Each implementation task starts with failing tests, defines RED and GREEN commands, and includes an explicit commit point.
- Type consistency: Existing names are preserved where possible: `ReportPage.vue`, `TrainingPage.vue`, `AdminPage.vue`, `AdminAiDebugDetail`, `RefreshToken`, `create_access_token`, `get_current_user`, `apiRequest`, `TrainingWeakTagGroup`.
- Deployment coverage: The plan includes local full tests, frontend build, compose config validation, VPS commands, and manual public smoke checks.
