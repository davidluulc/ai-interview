# Admin & Report Productization V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing admin/debug/report capabilities into visible, click-through, demo-ready product experiences.

**Architecture:** Keep the current FastAPI + SQLAlchemy + Redis session + Vue3 + Pinia structure. Make the smallest backend additions needed for session enforcement and dashboard aggregates, then concentrate productization in `AdminPage.vue`, `admin.ts`, `admin.ts` store, and `ReportPage.vue`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Redis-backed session store, Vue3, Pinia, Vitest, Vite, Docker Compose.

---

## File Map

- `backend_python/auth.py`: reject protected requests when access tokens do not contain `sid`.
- `tests/test_auth.py`: cover no-`sid` legacy access token rejection and current session token behavior.
- `backend_python/routes/admin.py`: extend RAG quality/document/agent payloads only where dashboard fields cannot be derived safely in the frontend.
- `tests/test_admin_ai_debug.py`: cover RAG quality/dashboard aggregate payloads.
- `frontend/src/api/admin.ts`: add dashboard summary types and keep `forceLogoutUser` response typed.
- `frontend/src/stores/admin.ts`: add force logout pending state, success/error message, selected debug tab, and derived dashboard state.
- `frontend/src/stores/admin.test.ts`: cover force logout state and derived dashboard state.
- `frontend/src/pages/app/AdminPage.vue`: add force logout confirmation/feedback, real AI debug tabs, RAG/Agent/document dashboards.
- `frontend/src/pages/app/admin-page.test.ts`: cover the visible product behavior.
- `frontend/src/pages/app/ReportPage.vue`: transform report evidence into human-readable explanation + secondary sources.
- `frontend/src/pages/app/report-page.test.ts`: cover humanized evidence, weak evidence fallback, and source list behavior.
- `docs/roadmap/current-state.md`: keep active plan/spec pointers current.
- `docs/plans/README.md`: keep active plan/spec pointers current.

## Task 1: Strong Session Enforcement and Force Logout Product Feedback

**Files:**
- Modify: `backend_python/auth.py`
- Modify: `tests/test_auth.py`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write backend failing test for legacy no-sid access tokens**

Add this test to `tests/test_auth.py`:

```python
def test_access_token_without_session_id_is_rejected_for_current_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"legacy-session-{suffix}@example.com"
    username = f"legacy_session_{suffix[:12]}"
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    payload = decode_token(tokens["accessToken"], expected_type="access")

    legacy_access_token = create_access_token(user_id=int(payload["sub"]))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy_access_token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_revoked"
```

- [ ] **Step 2: Run backend RED**

Run:

```bash
python -m pytest tests/test_auth.py::test_access_token_without_session_id_is_rejected_for_current_user -q
```

Expected: fail because `get_current_user` currently accepts access tokens without `sid`.

- [ ] **Step 3: Implement no-sid rejection**

In `backend_python/auth.py`, update `get_current_user` immediately after decoding:

```python
    session_id = str(payload.get("sid") or "")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_revoked", "message": "当前登录会话已失效，请重新登录。"},
        )
```

Keep the existing session lookup block after that. Do not change `create_access_token` because tests still need to create legacy tokens.

- [ ] **Step 4: Run backend GREEN**

Run:

```bash
python -m pytest tests/test_auth.py tests/test_admin_users.py -q
```

Expected: pass. If any test creates protected API access tokens directly without `sid`, update that test to login through `/api/auth/login` or create a session with `session_store.create_session`.

- [ ] **Step 5: Write frontend failing store test for force logout feedback**

In `frontend/src/stores/admin.test.ts`, replace the current force logout test with:

```ts
it("tracks force logout loading and success message", async () => {
  vi.mocked(adminApi.forceLogoutUser).mockResolvedValue({
    ok: true,
    revokedSessions: 2,
    revokedRefreshTokens: 3
  });

  const store = useAdminStore();
  const promise = store.forceLogoutUser({
    id: 2,
    email: "demo@ai-interview.com",
    username: "demo",
    role: "user",
    createdAt: ""
  });

  expect(store.forceLogoutPendingUserId).toBe(2);
  await promise;

  expect(adminApi.forceLogoutUser).toHaveBeenCalledWith(2);
  expect(store.forceLogoutPendingUserId).toBeNull();
  expect(store.forceLogoutMessage).toBe("已下线 demo@ai-interview.com，撤销 2 个会话、3 个 refresh token。");
  expect(store.forceLogoutError).toBe("");
});
```

Add a failure test:

```ts
it("tracks force logout errors", async () => {
  vi.mocked(adminApi.forceLogoutUser).mockRejectedValue(new Error("Admin privileges required"));

  const store = useAdminStore();
  await store.forceLogoutUser({
    id: 2,
    email: "demo@ai-interview.com",
    username: "demo",
    role: "user",
    createdAt: ""
  });

  expect(store.forceLogoutPendingUserId).toBeNull();
  expect(store.forceLogoutMessage).toBe("");
  expect(store.forceLogoutError).toBe("强制下线失败：Admin privileges required");
});
```

- [ ] **Step 6: Run frontend store RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected: fail because the store action currently accepts only `userId` and does not expose pending/message/error state.

- [ ] **Step 7: Implement store force logout state**

In `frontend/src/stores/admin.ts`, add refs:

```ts
  const forceLogoutPendingUserId = ref<number | null>(null);
  const forceLogoutMessage = ref("");
  const forceLogoutError = ref("");
```

Replace `forceLogoutUser(userId: number)` with:

```ts
  async function forceLogoutUser(user: adminApi.AdminUser): Promise<void> {
    forceLogoutPendingUserId.value = user.id;
    forceLogoutMessage.value = "";
    forceLogoutError.value = "";
    try {
      const result = await adminApi.forceLogoutUser(user.id);
      forceLogoutMessage.value = `已下线 ${user.email}，撤销 ${result.revokedSessions} 个会话、${result.revokedRefreshTokens} 个 refresh token。`;
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      forceLogoutError.value = `强制下线失败：${message}`;
    } finally {
      forceLogoutPendingUserId.value = null;
    }
  }
```

Return the three refs.

- [ ] **Step 8: Write failing page test for confirmation modal**

In `frontend/src/pages/app/admin-page.test.ts`, update the store fixture:

```ts
forceLogoutPendingUserId: null,
forceLogoutMessage: "",
forceLogoutError: "",
```

Replace the force logout page test with:

```ts
it("confirms force logout and shows the result message", async () => {
  adminStore.forceLogoutMessage = "已下线 demo@ai-interview.com，撤销 1 个会话、1 个 refresh token。";
  const wrapper = mount(AdminPage, { global: globalConfig });

  await wrapper.get('[data-testid="force-logout-user-2"]').trigger("click");

  expect(wrapper.text()).toContain("确认强制下线该用户？");
  expect(wrapper.text()).toContain("demo@ai-interview.com");
  expect(adminStore.forceLogoutUser).not.toHaveBeenCalled();

  await wrapper.get('[data-testid="confirm-force-logout"]').trigger("click");

  expect(adminStore.forceLogoutUser).toHaveBeenCalledWith(expect.objectContaining({ id: 2, email: "demo@ai-interview.com" }));
  expect(wrapper.text()).toContain("已下线 demo@ai-interview.com");
});
```

Add loading assertion:

```ts
it("disables the force logout button while the user is being logged out", () => {
  adminStore.forceLogoutPendingUserId = 2;
  const wrapper = mount(AdminPage, { global: globalConfig });

  const button = wrapper.get('[data-testid="force-logout-user-2"]');

  expect(button.attributes("disabled")).toBeDefined();
  expect(button.text()).toContain("下线中");
});
```

- [ ] **Step 9: Run page RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fail because the modal, loading label, and message region do not exist.

- [ ] **Step 10: Implement confirmation modal and feedback**

In `AdminPage.vue` script, add:

```ts
const forceLogoutCandidate = ref<AdminUser | null>(null);

function openForceLogout(user: AdminUser): void {
  forceLogoutCandidate.value = user;
}

function closeForceLogout(): void {
  forceLogoutCandidate.value = null;
}

async function confirmForceLogout(): Promise<void> {
  if (!forceLogoutCandidate.value) return;
  await admin.forceLogoutUser(forceLogoutCandidate.value);
  closeForceLogout();
}
```

Import `AdminUser` type from `@/api/admin`.

Change the table button to:

```vue
<button
  v-if="user.id !== auth.user?.id"
  type="button"
  class="table-action"
  :data-testid="`force-logout-user-${user.id}`"
  :disabled="admin.forceLogoutPendingUserId === user.id"
  @click="openForceLogout(user)"
>
  {{ admin.forceLogoutPendingUserId === user.id ? "下线中..." : "强制下线" }}
</button>
```

Add feedback near account management title:

```vue
<p v-if="admin.forceLogoutMessage" class="success-message">{{ admin.forceLogoutMessage }}</p>
<p v-if="admin.forceLogoutError" class="error">{{ admin.forceLogoutError }}</p>
```

Add modal near the end of the admin page template:

```vue
<div v-if="forceLogoutCandidate" class="modal-backdrop" role="dialog" aria-modal="true">
  <section class="confirm-modal">
    <h2>确认强制下线该用户？</h2>
    <p>用户：{{ forceLogoutCandidate.email }}</p>
    <p>操作后，该用户当前登录态会失效，需要重新登录。</p>
    <div class="modal-actions">
      <button type="button" class="ghost-action" @click="closeForceLogout">取消</button>
      <button data-testid="confirm-force-logout" type="button" @click="confirmForceLogout">确认下线</button>
    </div>
  </section>
</div>
```

Add restrained CSS for `.modal-backdrop`, `.confirm-modal`, `.modal-actions`, `.success-message`.

- [ ] **Step 11: Run Task 1 GREEN**

Run:

```bash
python -m pytest tests/test_auth.py tests/test_admin_users.py -q
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts src/api/client.test.ts src/app.test.ts
```

Expected: all pass.

- [ ] **Step 12: Commit Task 1**

```bash
git add backend_python/auth.py tests/test_auth.py frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: productize admin force logout"
```

**Acceptance:**
- Old no-`sid` tokens fail with `session_revoked`.
- Admin sees confirmation, loading, success and failure states.
- Existing revoked-session client behavior still clears tokens and routes to login.

## Task 2: AI Debug True Tabs

**Files:**
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing store test for selected AI debug tab**

Add to `frontend/src/stores/admin.test.ts`:

```ts
it("tracks the selected AI debug detail tab", () => {
  const store = useAdminStore();

  expect(store.selectedAiDebugTab).toBe("overview");

  store.setAiDebugTab("rag");
  expect(store.selectedAiDebugTab).toBe("rag");

  store.setAiDebugTab("raw");
  expect(store.selectedAiDebugTab).toBe("raw");
});
```

- [ ] **Step 2: Run store RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected: fail because `selectedAiDebugTab` and `setAiDebugTab` do not exist.

- [ ] **Step 3: Implement tab state in admin store**

In `frontend/src/stores/admin.ts`, add:

```ts
export type AdminAiDebugTab = "overview" | "rag" | "agent" | "langgraph" | "diagnostics" | "raw";
const selectedAiDebugTab = ref<AdminAiDebugTab>("overview");

function setAiDebugTab(tab: AdminAiDebugTab): void {
  selectedAiDebugTab.value = tab;
}
```

Return both.

Also set `selectedAiDebugTab.value = "overview"` inside `loadAiDebugDetail` when a new trace id is selected.

- [ ] **Step 4: Write failing page test for real tabs**

In `frontend/src/pages/app/admin-page.test.ts`, add to fixture:

```ts
selectedAiDebugTab: "overview",
setAiDebugTab: vi.fn((tab: string) => {
  adminStore.selectedAiDebugTab = tab;
})
```

Add this test:

```ts
it("renders AI debug details as real tabs instead of one long stack", async () => {
  const wrapper = mount(AdminPage, { global: globalConfig });

  expect(wrapper.get('[data-testid="ai-debug-tab-overview"]').attributes("aria-selected")).toBe("true");
  expect(wrapper.text()).toContain("一句话诊断");
  expect(wrapper.text()).not.toContain("查看原始调试 JSON");

  await wrapper.get('[data-testid="ai-debug-tab-rag"]').trigger("click");
  adminStore.selectedAiDebugTab = "rag";
  await nextTick();

  expect(adminStore.setAiDebugTab).toHaveBeenCalledWith("rag");
  expect(wrapper.text()).toContain("RAG 召回链路");
  expect(wrapper.text()).not.toContain("Agent 决策链路");
  expect(wrapper.text()).not.toContain("查看原始调试 JSON");

  await wrapper.get('[data-testid="ai-debug-tab-raw"]').trigger("click");
  adminStore.selectedAiDebugTab = "raw";
  await nextTick();

  expect(wrapper.text()).toContain("查看原始调试 JSON");
});
```

- [ ] **Step 5: Run page RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fail because current “tabs” are static spans and all panels render at once.

- [ ] **Step 6: Implement true tabs in AdminPage**

Replace the static `<nav class="debug-tabs">` spans with buttons:

```vue
<nav class="debug-tabs" aria-label="AI 调试详情分区">
  <button
    v-for="tab in aiDebugTabs"
    :key="tab.key"
    type="button"
    :data-testid="`ai-debug-tab-${tab.key}`"
    :aria-selected="admin.selectedAiDebugTab === tab.key"
    @click="admin.setAiDebugTab(tab.key)"
  >
    {{ tab.label }}
  </button>
</nav>
```

In script:

```ts
const aiDebugTabs = [
  { key: "overview", label: "总览" },
  { key: "rag", label: "RAG 召回" },
  { key: "agent", label: "Agent 决策" },
  { key: "langgraph", label: "LangGraph" },
  { key: "diagnostics", label: "诊断建议" },
  { key: "raw", label: "原始日志" }
] as const;
```

Replace the always-rendered `.debug-grid` with `v-if` sections:

```vue
<section v-if="admin.selectedAiDebugTab === 'overview'" class="debug-panel">...</section>
<section v-else-if="admin.selectedAiDebugTab === 'rag'" class="debug-panel">...</section>
<section v-else-if="admin.selectedAiDebugTab === 'agent'" class="debug-panel">...</section>
<section v-else-if="admin.selectedAiDebugTab === 'langgraph'" class="debug-panel">...</section>
<section v-else-if="admin.selectedAiDebugTab === 'diagnostics'" class="debug-panel">...</section>
<section v-else-if="admin.selectedAiDebugTab === 'raw'" class="debug-panel raw-debug">...</section>
```

Overview content must show:

```vue
<h3>一句话诊断</h3>
<p>{{ aiDebugOverviewText }}</p>
<div class="quality-grid compact">
  <article><span>请求类型</span><strong>{{ debugText(admin.selectedAiDebugDetail.summary, "requestType", "未知") }}</strong></article>
  <article><span>RAG 总命中</span><strong>{{ debugNumber(admin.selectedAiDebugDetail.rag, "totalHitCount") }}</strong></article>
  <article><span>主要动作</span><strong>{{ debugText(admin.selectedAiDebugDetail.agent, "nextActionLabel", "未知") }}</strong></article>
  <article><span>Fallback</span><strong>{{ debugBoolean(admin.selectedAiDebugDetail.agent, "fallbackUsed") ? "已触发" : "未触发" }}</strong></article>
</div>
```

Add computed:

```ts
const aiDebugOverviewText = computed(() => {
  const action = debugText(admin.selectedAiDebugDetail?.agent, "nextActionLabel", "继续追问");
  const reason = debugText(admin.selectedAiDebugDetail?.agent, "reason", "");
  const ragHits = debugNumber(admin.selectedAiDebugDetail?.rag, "totalHitCount");
  if (reason && reason !== "暂无") return `本轮主要动作是「${action}」，原因是：${reason}`;
  return `本轮主要动作是「${action}」，RAG 总命中 ${ragHits} 条，系统根据当前面试上下文继续推进。`;
});
```

- [ ] **Step 7: Run Task 2 GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: pass.

- [ ] **Step 8: Commit Task 2**

```bash
git add frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: add real admin ai debug tabs"
```

**Acceptance:**
- Only one AI debug tab body is visible at a time.
- Raw JSON is visible only in the raw tab.
- Tests prove tab clicks change visible content.

## Task 3: Admin RAG, Agent, and Document Dashboards

**Files:**
- Modify: `backend_python/routes/admin.py`
- Modify: `tests/test_admin_ai_debug.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing backend test for RAG quality dashboard payload**

In `tests/test_admin_ai_debug.py`, add:

```python
def test_admin_rag_quality_payload_includes_dashboard_summaries() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=7001,
                request_type="next_question",
                query_text="RAG 日志字段",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=7001,
                request_type="next_question",
                query_text="Celery 职责",
                retriever_name="question_bank",
                retrieval_mode="hybrid",
                hit_count=2,
                hits_json=json.dumps([{"score": 9, "source": "database"}, {"score": 8, "source": "database"}], ensure_ascii=False),
                used_in_prompt=1,
            )
        )
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)
    body = response.json()

    assert "knowledgeBaseSummary" in body
    assert "diagnosticSummary" in body
    assert any(item["knowledgeBase"] == "role_knowledge" for item in body["knowledgeBaseSummary"])
    assert any(item["knowledgeBase"] == "question_bank" for item in body["knowledgeBaseSummary"])
    assert body["summary"]["goodCount"] >= 1
```

- [ ] **Step 2: Run backend RED**

Run:

```bash
python -m pytest tests/test_admin_ai_debug.py::test_admin_rag_quality_payload_includes_dashboard_summaries -q
```

Expected: fail because `knowledgeBaseSummary`, `diagnosticSummary`, and `goodCount` are not returned.

- [ ] **Step 3: Implement RAG dashboard aggregation**

In `backend_python/routes/admin.py`, update `build_rag_quality_payload`:

```python
    summary = {
        "totalLogCount": len(logs),
        "goodCount": 0,
        "lowQualityCount": 0,
        "emptyRecallCount": 0,
        "weakRecallCount": 0,
        "unusedInPromptCount": 0,
    }
    kb_summary: dict[str, dict[str, Any]] = {}
    diagnostic_summary: dict[tuple[str, str], dict[str, Any]] = {}
```

For each log after `item = serialize_rag_log(log)`, compute:

```python
        kb_name = str(item.get("retrieverName") or item.get("retriever_name") or "unknown")
        kb_item = kb_summary.setdefault(
            kb_name,
            {
                "knowledgeBase": kb_name,
                "label": normalize_rag_name(kb_name),
                "goodCount": 0,
                "weakCount": 0,
                "emptyCount": 0,
                "unusedInPromptCount": 0,
                "totalCount": 0,
            },
        )
        kb_item["totalCount"] += 1
        quality_level = str((item.get("quality") or {}).get("level") or "unknown")
        if quality_level == "good":
            summary["goodCount"] += 1
            kb_item["goodCount"] += 1
```

When `issue` is present, increment `weakCount` / `emptyCount` / `unusedInPromptCount`, and aggregate diagnostics:

```python
        diagnostic_key = (issue_type, recommendation)
        diagnostic = diagnostic_summary.setdefault(
            diagnostic_key,
            {"type": issue_type, "title": issue_label(issue_type), "message": recommendation, "count": 0},
        )
        diagnostic["count"] += 1
```

Add small helpers in `routes/admin.py`:

```python
def issue_label(issue_type: str) -> str:
    return {
        "empty_recall": "空召回",
        "weak_recall": "弱召回",
        "unused_in_prompt": "未进入 Prompt",
    }.get(issue_type, "低质量召回")
```

Return:

```python
return {
    "summary": summary,
    "items": low_quality_items,
    "knowledgeBaseSummary": list(kb_summary.values()),
    "diagnosticSummary": sorted(diagnostic_summary.values(), key=lambda item: item["count"], reverse=True),
}
```

- [ ] **Step 4: Run backend GREEN**

Run:

```bash
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected: pass.

- [ ] **Step 5: Write failing frontend store tests for dashboard computed values**

In `frontend/src/stores/admin.test.ts`, add:

```ts
it("derives agent action and document coverage dashboards", () => {
  const store = useAdminStore();
  store.agentLogs = [
    { id: 1, nextAction: "deepen", fallbackUsed: false },
    { id: 2, nextAction: "lower_difficulty", fallbackUsed: true },
    { id: 3, nextAction: "deepen", fallbackUsed: false }
  ];
  store.ragDocuments = [
    { id: 1, title: "岗位知识", knowledgeBase: "role_knowledge", status: "enabled", chunkCount: 7 },
    { id: 2, title: "题库", knowledgeBase: "question_bank", status: "enabled", chunkCount: 8 },
    { id: 3, title: "旧文档", knowledgeBase: "role_knowledge", status: "archived", chunkCount: 4 }
  ];

  expect(store.agentActionSummary.find((item) => item.action === "deepen")?.count).toBe(2);
  expect(store.agentDashboardSummary.fallbackCount).toBe(1);
  expect(store.ragDocumentDashboard.readyDocumentCount).toBe(2);
  expect(store.ragDocumentDashboard.readyChunkCount).toBe(15);
  expect(store.ragDocumentDashboard.knowledgeBaseCoverage).toContainEqual(
    expect.objectContaining({ knowledgeBase: "role_knowledge", readyChunkCount: 7 })
  );
});
```

- [ ] **Step 6: Run store RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected: fail because dashboard computed values do not exist.

- [ ] **Step 7: Implement dashboard computed values and API types**

In `frontend/src/api/admin.ts`, extend:

```ts
export interface AdminRagQualityKnowledgeBaseSummary {
  knowledgeBase: string;
  label: string;
  totalCount: number;
  goodCount: number;
  weakCount: number;
  emptyCount: number;
  unusedInPromptCount: number;
}

export interface AdminRagQualityDiagnosticSummary {
  type: string;
  title: string;
  message: string;
  count: number;
}
```

Extend `AdminRagQuality`:

```ts
knowledgeBaseSummary?: AdminRagQualityKnowledgeBaseSummary[];
diagnosticSummary?: AdminRagQualityDiagnosticSummary[];
```

In `frontend/src/stores/admin.ts`, add computed values:

```ts
const agentActionSummary = computed(() => {
  const grouped = new Map<string, number>();
  for (const log of agentLogs.value) {
    const action = log.nextAction || log.next_action || "unknown";
    grouped.set(action, (grouped.get(action) || 0) + 1);
  }
  return Array.from(grouped.entries()).map(([action, count]) => ({ action, count }));
});

const agentDashboardSummary = computed(() => ({
  totalCount: agentLogs.value.length,
  fallbackCount: agentLogs.value.filter((log) => Boolean(log.fallbackUsed || log.fallback_used)).length,
  actionSummary: agentActionSummary.value,
}));

const ragDocumentDashboard = computed(() => {
  const activeDocs = ragDocuments.value.filter((document) => (document.status || "enabled") === "enabled");
  const coverage = new Map<string, { knowledgeBase: string; readyDocumentCount: number; readyChunkCount: number }>();
  for (const document of activeDocs) {
    const knowledgeBase = document.knowledgeBase || document.knowledge_base || "unknown";
    const current = coverage.get(knowledgeBase) || { knowledgeBase, readyDocumentCount: 0, readyChunkCount: 0 };
    current.readyDocumentCount += 1;
    current.readyChunkCount += document.chunkCount || document.chunk_count || 0;
    coverage.set(knowledgeBase, current);
  }
  return {
    readyDocumentCount: activeDocs.length,
    readyChunkCount: activeDocs.reduce((sum, document) => sum + (document.chunkCount || document.chunk_count || 0), 0),
    knowledgeBaseCoverage: Array.from(coverage.values()),
  };
});
```

Return them.

- [ ] **Step 8: Write failing page test for dashboard sections**

In `frontend/src/pages/app/admin-page.test.ts`, update `ragQuality` fixture to include:

```ts
knowledgeBaseSummary: [
  { knowledgeBase: "role_knowledge", label: "岗位知识库", totalCount: 3, goodCount: 1, weakCount: 1, emptyCount: 1, unusedInPromptCount: 0 },
  { knowledgeBase: "question_bank", label: "题库", totalCount: 2, goodCount: 2, weakCount: 0, emptyCount: 0, unusedInPromptCount: 0 }
],
diagnosticSummary: [
  { type: "empty_recall", title: "岗位知识库空召回", message: "补充岗位知识库资料。", count: 2 }
]
```

Add store fixture computed values or let real store tests cover them if mocked store is simple. For page test, set:

```ts
agentDashboardSummary: { totalCount: 2, fallbackCount: 1, actionSummary: [{ action: "deepen", count: 1 }, { action: "switch_topic", count: 1 }] },
ragDocumentDashboard: { readyDocumentCount: 1, readyChunkCount: 8, knowledgeBaseCoverage: [{ knowledgeBase: "role_knowledge", readyDocumentCount: 1, readyChunkCount: 8 }] },
```

Add test:

```ts
it("renders RAG Agent and document dashboards instead of raw-only lists", () => {
  const wrapper = mount(AdminPage, { global: globalConfig });
  const text = wrapper.text();

  expect(text).toContain("知识库质量分布");
  expect(text).toContain("岗位知识库");
  expect(text).toContain("高相关 1");
  expect(text).toContain("主要诊断");
  expect(text).toContain("岗位知识库空召回");
  expect(text).toContain("Agent 动作分布");
  expect(text).toContain("fallback 1");
  expect(text).toContain("RAG 文档覆盖");
  expect(text).toContain("Ready chunk 8");
});
```

- [ ] **Step 9: Run page RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fail because dashboard headings and aggregate rows do not exist.

- [ ] **Step 10: Implement dashboard UI**

In `AdminPage.vue`, update RAG quality section:

- Add top cards for total/high/weak/empty/unused:

```vue
<article>
  <span>高相关</span>
  <strong>{{ admin.ragQuality.summary.goodCount || Math.max(admin.ragQuality.summary.totalLogCount - admin.ragQuality.summary.lowQualityCount, 0) }}</strong>
  <small>可直接支持面试追问的召回</small>
</article>
```

- Add `知识库质量分布` list:

```vue
<div class="dashboard-panel">
  <h3>知识库质量分布</h3>
  <div v-for="item in admin.ragQuality.knowledgeBaseSummary || []" :key="item.knowledgeBase" class="mini-row">
    <strong>{{ item.label || retrieverLabel(item.knowledgeBase) }}</strong>
    <span>高相关 {{ item.goodCount }} / 弱相关 {{ item.weakCount }} / 空召回 {{ item.emptyCount }}</span>
  </div>
</div>
```

- Add `主要诊断` list from `diagnosticSummary`.

Update Agent logs section:

```vue
<div class="quality-grid">
  <article><span>总决策</span><strong>{{ admin.agentDashboardSummary.totalCount }}</strong></article>
  <article><span>fallback</span><strong>{{ admin.agentDashboardSummary.fallbackCount }}</strong></article>
</div>
<div class="dashboard-panel">
  <h3>Agent 动作分布</h3>
  <div v-for="item in admin.agentDashboardSummary.actionSummary" :key="item.action" class="mini-row">
    <strong>{{ normalizeAction(item.action) }}</strong>
    <span>{{ item.count }} 次</span>
  </div>
</div>
```

Update RAG document section:

```vue
<div class="quality-grid">
  <article><span>Ready 文档</span><strong>{{ admin.ragDocumentDashboard.readyDocumentCount }}</strong></article>
  <article><span>Ready chunk</span><strong>{{ admin.ragDocumentDashboard.readyChunkCount }}</strong></article>
  <article><span>Embedding</span><strong>{{ admin.config?.embeddingModel || "未配置" }}</strong></article>
</div>
<div class="dashboard-panel">
  <h3>RAG 文档覆盖</h3>
  <div v-for="item in admin.ragDocumentDashboard.knowledgeBaseCoverage" :key="item.knowledgeBase" class="mini-row">
    <strong>{{ retrieverLabel(item.knowledgeBase) }}</strong>
    <span>Ready 文档 {{ item.readyDocumentCount }} / Ready chunk {{ item.readyChunkCount }}</span>
  </div>
</div>
```

- [ ] **Step 11: Run Task 3 GREEN**

Run:

```bash
python -m pytest tests/test_admin_ai_debug.py -q
cd frontend
npm.cmd run test -- src/api/admin.test.ts src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

If `src/api/admin.test.ts` does not exist, run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: pass.

- [ ] **Step 12: Commit Task 3**

```bash
git add backend_python/routes/admin.py tests/test_admin_ai_debug.py frontend/src/api/admin.ts frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: add admin diagnostics dashboards"
```

**Acceptance:**
- RAG section has summary cards, knowledge-base distribution and top diagnostics.
- Agent section has action/fallback dashboard before raw log items.
- RAG document section has ready document/chunk/embedding coverage.

## Task 4: Humanized Report Evidence

**Files:**
- Modify: `frontend/src/pages/app/ReportPage.vue`
- Modify: `frontend/src/pages/app/report-page.test.ts`

- [ ] **Step 1: Write failing report tests for humanized evidence**

Add to `frontend/src/pages/app/report-page.test.ts`:

```ts
it("turns RAG reasons into candidate-facing evidence and secondary sources", () => {
  const originalSummary = reportStore.record.report.decisionSummary;
  const originalReasons = reportStore.record.report.ragReasons;

  try {
    reportStore.record.report.decisionSummary = "JD 要求 RAG 链路理解，上一轮回答缺少日志字段。";
    reportStore.record.report.ragReasons = [
      "命中岗位知识库：RAG Agent 与 LangGraph 项目知识，命中词包括：rag、prompt、langgraph、agent。",
      "命中题库：PostgreSQL、Redis、Celery 在这个项目里分别承担什么职责？",
      "命中候选人画像：Python 后端开发实习生"
    ];

    const wrapper = mount(ReportPage, {
      global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } }
    });

    expect(wrapper.text()).toContain("这道题主要围绕");
    expect(wrapper.text()).toContain("岗位 JD");
    expect(wrapper.text()).toContain("上一轮回答");
    expect(wrapper.text()).toContain("参考来源");
    expect(wrapper.text()).toContain("岗位知识库：RAG Agent 与 LangGraph 项目知识");
    expect(wrapper.text()).toContain("题库：PostgreSQL、Redis、Celery 在这个项目里分别承担什么职责？");
    expect(wrapper.text()).not.toContain("命中词包括");
  } finally {
    reportStore.record.report.decisionSummary = originalSummary;
    reportStore.record.report.ragReasons = originalReasons;
  }
});
```

Add weak evidence test:

```ts
it("does not pretend weak evidence is strong", () => {
  const originalSummary = reportStore.record.report.decisionSummary;
  const originalReasons = reportStore.record.report.ragReasons;

  try {
    reportStore.record.report.decisionSummary = "";
    reportStore.record.report.ragReasons = ["围绕当前档案、历史回答和检索上下文共同驱动。"];

    const wrapper = mount(ReportPage, {
      global: { stubs: { AppLayout: { template: "<main><slot /></main>" } } }
    });

    expect(wrapper.text()).toContain("当前知识库命中较弱");
    expect(wrapper.text()).not.toContain("命中岗位知识库");
  } finally {
    reportStore.record.report.decisionSummary = originalSummary;
    reportStore.record.report.ragReasons = originalReasons;
  }
});
```

- [ ] **Step 2: Run report RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: fail because the report page currently renders `decisionSummary` and raw `ragReasons`.

- [ ] **Step 3: Implement evidence source normalization**

In `ReportPage.vue`, add:

```ts
interface EvidenceSource {
  label: string;
  title: string;
}

function normalizeEvidenceReason(reason: string): EvidenceSource | null {
  const cleaned = reason.replace(/，?命中词包括[:：].*$/u, "").replace(/^命中/u, "").trim();
  const match = cleaned.match(/^(岗位知识库|题库|候选人画像)[:：](.+)$/u);
  if (match) {
    return { label: match[1], title: match[2].trim() };
  }
  if (/岗位知识库/.test(cleaned)) return { label: "岗位知识库", title: cleaned.replace(/^岗位知识库[:：]?/u, "").trim() };
  if (/题库/.test(cleaned)) return { label: "题库", title: cleaned.replace(/^题库[:：]?/u, "").trim() };
  if (/候选人画像/.test(cleaned)) return { label: "候选人画像", title: cleaned.replace(/^候选人画像[:：]?/u, "").trim() };
  return null;
}
```

Add computed:

```ts
const evidenceSources = computed(() => {
  const reasons = report.value.ragReasons;
  if (!Array.isArray(reasons)) return [];
  const sources = reasons
    .map((reason) => normalizeEvidenceReason(String(reason)))
    .filter((source): source is EvidenceSource => Boolean(source?.title));
  const seen = new Set<string>();
  return sources.filter((source) => {
    const key = `${source.label}:${source.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 3);
});

const hasStrongEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return Boolean(summary && !LOW_VALUE_EVIDENCE.includes(summary) && evidenceSources.value.length > 0);
});

const humanizedEvidenceText = computed(() => {
  const summary = evidenceText.value.trim();
  if (!hasStrongEvidence.value) {
    return "这道题主要根据你的投递档案、岗位 JD 和上一轮回答生成。当前知识库命中较弱，因此系统更多依赖面试上下文来追问。";
  }
  const sourceLabels = evidenceSources.value.map((source) => source.label).join("、");
  return `这道题主要围绕当前岗位要求和上一轮回答展开。${summary} 系统参考了${sourceLabels}中的相关材料，用来检查你能否把概念落到实际排查步骤。`;
});
```

- [ ] **Step 4: Update evidence template**

Replace the evidence section with:

```vue
<section v-if="shouldShowEvidence" class="insight-card">
  <h2>出题依据</h2>
  <p>{{ humanizedEvidenceText }}</p>
  <div v-if="evidenceSources.length" class="source-list">
    <h3>参考来源</h3>
    <ul>
      <li v-for="source in evidenceSources" :key="`${source.label}-${source.title}`">
        {{ source.label }}：{{ source.title }}
      </li>
    </ul>
  </div>
</section>
```

Update `shouldShowEvidence`:

```ts
const shouldShowEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return (summary && !LOW_VALUE_EVIDENCE.includes(summary)) || evidenceSources.value.length > 0;
});
```

Remove direct usage of `evidenceReasons` from the template. Keep a capped source list.

- [ ] **Step 5: Run Task 4 GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add frontend/src/pages/app/ReportPage.vue frontend/src/pages/app/report-page.test.ts
git commit -m "fix: humanize report evidence"
```

**Acceptance:**
- Report evidence main paragraph reads like candidate-facing explanation.
- Source list is secondary and capped.
- Weak evidence shows a weak-evidence message instead of overclaiming.

## Task 5: Verification, Docs, and Deployment Handoff

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
python -m pytest tests/test_auth.py tests/test_admin_users.py tests/test_admin_ai_debug.py -q
python -m pytest tests/test_question_reviews.py -q
```

Expected: pass.

- [ ] **Step 2: Run focused frontend tests**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
npm.cmd run test -- src/pages/app/report-page.test.ts
npm.cmd run test -- src/api/client.test.ts src/stores/admin.test.ts src/app.test.ts
```

Expected: pass.

- [ ] **Step 3: Run full verification**

Run:

```bash
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
docker compose --env-file .env.production.example config --quiet
```

Expected:

```text
backend pytest: all passed
frontend vitest: all passed
frontend build: succeeded
compose config: succeeded
```

- [ ] **Step 4: Update docs status**

In `docs/roadmap/current-state.md`, when implementation is complete:

- Move `Admin & Report Productization V2` from active to completed summary.
- Record actual verification numbers.
- Set next recommended phase back to `Pre-Launch Stabilization V1`.

In `docs/plans/README.md`, update active plan/spec pointers when archiving.

- [ ] **Step 5: Archive active plan/spec**

Move:

```text
docs/specs/active/admin-report-productization-v2-design.md
docs/plans/active/admin-report-productization-v2.md
```

to:

```text
docs/specs/completed/admin-report-productization-v2-design.md
docs/plans/completed/admin-report-productization-v2.md
```

- [ ] **Step 6: Commit docs**

```bash
git add docs/roadmap/current-state.md docs/plans/README.md docs/specs/active/admin-report-productization-v2-design.md docs/specs/completed/admin-report-productization-v2-design.md docs/plans/active/admin-report-productization-v2.md docs/plans/completed/admin-report-productization-v2.md
git commit -m "docs: archive admin report productization plan"
```

- [ ] **Step 7: VPS update commands**

Use on the VPS after the branch is merged and pushed to `main`:

```bash
cd /home/ubuntu/ai-interview
git fetch --prune origin main
git pull --ff-only origin main
git rev-parse --short HEAD
sudo docker run --rm -v "$PWD/frontend":/app -w /app node:20-alpine sh -c "npm ci && npm run build"
sudo docker compose --env-file .env.production up -d --build app worker nginx
sudo docker compose --env-file .env.production ps
curl -s http://127.0.0.1:8080/api/health
```

Expected:

```text
HEAD equals the pushed main commit.
app, worker, nginx, redis, db are Up.
/api/health returns status ok.
```

- [ ] **Step 8: Public smoke test**

Manual verification:

```text
1. Login as admin.
2. Open /vue/app/admin.
3. In AI 调试控制台, click 总览/RAG 召回/Agent 决策/LangGraph/诊断建议/原始日志 and confirm only one tab body is visible each time.
4. Confirm RAG 质量诊断 shows total/high/weak/empty/unused cards, knowledge-base distribution, and main diagnostics.
5. Confirm Agent 决策日志 shows total/fallback/action distribution before raw items.
6. Confirm RAG 文档概览 shows ready documents, ready chunks, embedding model, and knowledge-base coverage.
7. Login as a normal test user in another browser.
8. Admin clicks 强制下线, sees confirmation, confirms, then sees success message with revoked counts.
9. Normal test user refreshes and returns to login with session expired message.
10. Open a report page and confirm 出题依据 is a humanized paragraph plus secondary 参考来源.
```

**Acceptance:**
- Full local verification passes.
- Active plan/spec are archived only after implementation is complete.
- VPS commands and smoke path are ready for deployment.

## Self-Review

- Spec coverage: Task 1 covers force logout and no-`sid` tokens; Task 2 covers true tabs; Task 3 covers RAG/Agent/document dashboards; Task 4 covers humanized report evidence; Task 5 covers full verification and deployment handoff.
- Scope guard: No database relationship redesign, RAG algorithm rewrite, pgvector/Qdrant, full admin rewrite, complex RBAC, or full multi-device page.
- Type consistency: Task names use existing `AdminUser`, `AdminRagQuality`, `AdminAiDebugDetail`, `forceLogoutUser`, `selectedAiDebugTab`, `ragDocumentDashboard`, `agentDashboardSummary`.
- Test strategy: Every behavior task starts with failing tests and has focused GREEN commands plus a commit point.
