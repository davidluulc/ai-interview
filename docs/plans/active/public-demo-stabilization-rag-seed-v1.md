# Public Demo Stabilization + Production RAG Seed V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the public demo path so a user can seed production RAG data, start a real interview, finish with a saved report, get generated training tasks, and use simplified profile/knowledge workflows.

**Architecture:** Keep the existing FastAPI + Vue3 + PostgreSQL + Redis + Celery architecture. Add one idempotent backend seed command, tighten the Vue interview state machine, convert profile deletion into archive/restore, and simplify user-facing knowledge controls without removing admin diagnostics.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Vue3, Pinia, Vitest, Vite, Docker Compose, PostgreSQL, Redis, Celery.

---

## File Map

- `backend_python/production_rag_seed.py`: new idempotent seed service for public demo RAG documents.
- `scripts/seed_production_rag.py`: new CLI entrypoint used on the VPS after deployment.
- `tests/test_production_rag_seed.py`: backend tests for seed idempotency, active embedding model, and ready chunks.
- `backend_python/db_models.py`: add `ApplicationProfile.status`.
- `backend_python/database.py`: add SQLite auto-init compatibility for `application_profiles.status`.
- `alembic/versions/*_application_profile_status.py`: add PostgreSQL migration for profile status.
- `backend_python/routes/application_profiles.py`: replace hard delete with archive and add restore/list filters.
- `tests/test_application_profiles.py`: update delete expectations and add archive/restore coverage.
- `frontend/src/api/profiles.ts`: expose archive/restore and status types.
- `frontend/src/stores/profiles.ts`: filter active profiles by default and expose archived list.
- `frontend/src/pages/app/ProfilesPage.vue`: add archive/restore UI.
- `frontend/src/stores/interview.ts`: add explicit session states, first-question start, friendly timeout/HTML error normalization.
- `frontend/src/pages/app/InterviewPage.vue`: wire start button and finish/report/history/training chain.
- `frontend/src/api/history.ts`: add `createHistory`.
- `frontend/src/api/interview.ts`: add `generateReport` if missing.
- `frontend/src/components/interview/InterviewChatPanel.vue`: show thinking/loading bubble.
- `frontend/src/components/interview/InterviewFinishPanel.vue`: show report-generation state and disable repeated finish.
- `frontend/src/stores/interview.test.ts`: store-level tests for start state, placeholder exclusion, and friendly errors.
- `frontend/src/pages/app/interview-page.test.ts`: page-level tests for finish chain and navigation.
- `frontend/src/pages/app/KnowledgePage.vue`: hide metadata JSON and debug panel behind advanced details.
- `frontend/src/pages/app/knowledge-page.test.ts`: update page tests for advanced defaults.
- `frontend/src/api/client.ts`: normalize HTML/504 responses into readable errors.
- `docs/specs/README.md`, `docs/plans/README.md`, `docs/roadmap/current-state.md`: point to the active spec/plan.

---

## Task 1: Production RAG Seed

**Files:**
- Create: `backend_python/production_rag_seed.py`
- Create: `scripts/seed_production_rag.py`
- Create: `tests/test_production_rag_seed.py`

- [ ] **Step 1: Write failing seed tests**

Add tests that monkeypatch embedding calls to avoid network usage:

```python
def test_seed_production_rag_creates_role_and_question_chunks(db_session, monkeypatch):
    monkeypatch.setattr("backend_python.production_rag_seed.current_embedding_model", lambda: "embedding-3")
    monkeypatch.setattr("backend_python.production_rag_seed.embed_text", async_lambda([0.1, 0.2, 0.3]))

    summary = run_production_rag_seed(db_session, user_id=seed_user.id)

    assert summary["createdDocuments"] >= 2
    assert db_session.query(RagChunk).filter_by(knowledge_base="role_knowledge", embedding_model="embedding-3", embedding_status="ready").count() > 0
    assert db_session.query(RagChunk).filter_by(knowledge_base="question_bank", embedding_model="embedding-3", embedding_status="ready").count() > 0
```

Also add an idempotency test:

```python
def test_seed_production_rag_is_idempotent(db_session, monkeypatch):
    run_production_rag_seed(db_session, user_id=seed_user.id)
    first_count = db_session.query(RagDocument).count()

    summary = run_production_rag_seed(db_session, user_id=seed_user.id)

    assert summary["skippedDocuments"] > 0
    assert db_session.query(RagDocument).count() == first_count
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
python -m pytest tests/test_production_rag_seed.py -q
```

Expected: import failure for `backend_python.production_rag_seed`.

- [ ] **Step 3: Implement seed service**

Create stable seed records with deterministic `seedKey` metadata:

```python
PRODUCTION_RAG_SEED_ITEMS = [
    {
        "seedKey": "role-python-fastapi-rag-agent-v1",
        "knowledgeBase": "role_knowledge",
        "title": "Python 后端与 AI 应用岗位知识",
        "content": "...",
        "metadata": {"positionTag": "python_backend_intern", "category": "technical", "source": "production_seed"},
    },
    {
        "seedKey": "question-rag-agent-langgraph-v1",
        "knowledgeBase": "question_bank",
        "title": "RAG Agent LangGraph 面试题库",
        "content": "...",
        "metadata": {"positionTag": "ai_app_intern", "category": "interview_question", "source": "production_seed"},
    },
]
```

`run_production_rag_seed(db, user_id)` should skip existing `RagDocument` rows whose metadata has the same `seedKey`, create missing documents with `create_rag_document_with_embeddings`, and return document/chunk/ready counts.

- [ ] **Step 4: Add CLI entrypoint**

`scripts/seed_production_rag.py` should open a DB session, choose the first admin user or create/use a system seed owner, call `run_production_rag_seed`, and print JSON summary.

- [ ] **Step 5: Run GREEN**

Run:

```bash
python -m pytest tests/test_production_rag_seed.py -q
```

Expected: pass.

---

## Task 2: Interview Start State Machine

**Files:**
- Modify: `frontend/src/stores/interview.ts`
- Modify: `frontend/src/stores/interview.test.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`
- Modify: `frontend/src/components/interview/InterviewChatPanel.vue`

- [ ] **Step 1: Write failing store tests**

Add tests for:

```ts
it("does not submit the placeholder as answered history before the first backend question", async () => {
  const store = useInterviewStore();
  store.draft = "开始吧";

  await store.submitAnswer({ applicationProfileId: 1 });

  expect(interviewApi.nextQuestion).not.toHaveBeenCalled();
  expect(store.answeredHistory).toEqual([]);
});
```

```ts
it("starts an interview by requesting the first question with empty history", async () => {
  vi.mocked(interviewApi.nextQuestion).mockResolvedValue({ prompt: "请先介绍你的项目背景。" });
  const store = useInterviewStore();

  await store.startInterview({ applicationProfileId: 7, profile: { targetRole: "Python 后端" } });

  expect(interviewApi.nextQuestion).toHaveBeenCalledWith(expect.objectContaining({ history: [] }));
  expect(store.messages.at(-1)?.content).toBe("请先介绍你的项目背景。");
  expect(store.answeredHistory).toEqual([]);
});
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
cd frontend && npm.cmd run test -- src/stores/interview.test.ts
```

Expected: `startInterview` missing and placeholder submission still calls backend.

- [ ] **Step 3: Implement session states**

Add:

```ts
export type InterviewSessionStatus = "idle" | "starting" | "ready" | "answering" | "reporting" | "completed";
const sessionStatus = ref<InterviewSessionStatus>("idle");
const hasStarted = computed(() => sessionStatus.value !== "idle");
const canSubmitAnswer = computed(() => sessionStatus.value === "ready" && !loading.value);
```

Implement `startInterview(options)` to call `/api/interview/next-question` with `history: []`, push only the returned interviewer question, and set state to `ready`.

Change `submitAnswer` to return early unless `canSubmitAnswer` is true.

- [ ] **Step 4: Update page and chat controls**

Show a “开始面试” button when `sessionStatus === "idle"`. Disable chat submit until a real first question exists.

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd frontend && npm.cmd run test -- src/stores/interview.test.ts
```

Expected: pass.

---

## Task 3: Finish Report, History, Training Closed Loop

**Files:**
- Modify: `frontend/src/api/interview.ts`
- Modify: `frontend/src/api/history.ts`
- Modify: `frontend/src/api/training.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`
- Create or modify: `frontend/src/pages/app/interview-page.test.ts`

- [ ] **Step 1: Write failing page test**

Mount `InterviewPage.vue` with stores preloaded with one answered item and a current profile. Mock API modules and assert click order:

```ts
expect(interviewApi.generateReport).toHaveBeenCalledWith(expect.objectContaining({ answers: store.answeredHistory }));
expect(historyApi.createHistory).toHaveBeenCalledWith(expect.objectContaining({ applicationProfileId: 7 }));
expect(trainingApi.generateTrainingTasksFromReport).toHaveBeenCalledWith(expect.objectContaining({ sourceInterviewRecordId: 55 }));
expect(router.push).toHaveBeenCalledWith("/vue/app/reports/55");
```

- [ ] **Step 2: Run test and confirm RED**

Run:

```bash
cd frontend && npm.cmd run test -- src/pages/app/interview-page.test.ts
```

Expected: `finishInterview` only routes to history.

- [ ] **Step 3: Add API helpers**

Add `generateReport(payload)` in `frontend/src/api/interview.ts` for `POST /api/interview/report`.

Add `createHistory(payload)` in `frontend/src/api/history.ts` for `POST /api/history`.

- [ ] **Step 4: Implement finish chain**

In `InterviewPage.vue`, make `finishInterview` async:

```ts
const report = await interviewApi.generateReport(...);
const record = await historyApi.createHistory({ applicationProfileId, profile, answers, report });
await trainingApi.generateTrainingTasksFromReport({ applicationProfileId, sourceInterviewRecordId: record.id, report });
await router.push(`/vue/app/reports/${record.id}`);
```

Keep current answers if any request fails and show a readable error.

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd frontend && npm.cmd run test -- src/pages/app/interview-page.test.ts
```

Expected: pass.

---

## Task 4: Loading and Friendly Errors

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/interview.ts`
- Modify: `frontend/src/components/interview/InterviewChatPanel.vue`
- Modify: `frontend/src/stores/interview.test.ts`

- [ ] **Step 1: Write failing tests**

Add API/client or store tests proving HTML gateway errors are converted:

```ts
it("turns gateway HTML into a friendly timeout error", async () => {
  vi.mocked(interviewApi.nextQuestion).mockRejectedValue(new Error("<html><h1>504 Gateway Time-out</h1></html>"));
  const store = useInterviewStore();
  await store.startInterview({ applicationProfileId: 1 });
  expect(store.error).toContain("模型响应超时");
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd frontend && npm.cmd run test -- src/stores/interview.test.ts
```

Expected: raw HTML is exposed.

- [ ] **Step 3: Normalize errors**

Add a helper such as:

```ts
export function normalizeApiErrorMessage(message: string): string {
  if (/504|Gateway Time-out|Gateway Timeout|timed out/i.test(message)) return "模型响应超时，请稍后重试。本轮回答已保留。";
  if (/<html|<body|Bad Gateway|502/i.test(message)) return "服务暂时不可用，请稍后重试。";
  return message || "请求失败";
}
```

Use it in `apiRequest` and in interview store catch blocks.

- [ ] **Step 4: Add loading bubble**

`InterviewChatPanel.vue` should render a visible interviewer loading message while `loading` is true and disable submit.

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd frontend && npm.cmd run test -- src/stores/interview.test.ts
```

Expected: pass.

---

## Task 5: Knowledge Page Simplification

**Files:**
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
- Modify: `frontend/src/pages/app/knowledge-page.test.ts`

- [ ] **Step 1: Write failing tests**

Update tests so `metadata JSON` and `RAG 调试与解释` are not visible by default:

```ts
expect(wrapper.text()).not.toContain("metadata JSON");
expect(wrapper.text()).not.toContain("RAG 调试与解释");
await wrapper.get('[data-testid="knowledge-advanced-toggle"]').trigger("click");
expect(wrapper.text()).toContain("metadata JSON");
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd frontend && npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected: metadata/debug content is currently visible.

- [ ] **Step 3: Move developer controls into details**

Wrap manual metadata fields and upload metadata fields in “高级设置”. Wrap RAG debug panel in “高级调试”.

- [ ] **Step 4: Keep default metadata `{}`**

Ensure empty metadata JSON still submits `{}` and invalid metadata still shows the existing validation error when advanced fields are used.

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd frontend && npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected: pass.

---

## Task 6: Application Profile Archive and Restore

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Create: `alembic/versions/20260619_application_profile_status.py`
- Modify: `backend_python/routes/application_profiles.py`
- Modify: `tests/test_application_profiles.py`
- Modify: `frontend/src/api/profiles.ts`
- Modify: `frontend/src/stores/profiles.ts`
- Modify: `frontend/src/pages/app/ProfilesPage.vue`

- [ ] **Step 1: Write failing backend tests**

Change delete test to archive behavior:

```python
delete_response = client.delete(f"/api/application-profiles/{created['id']}", headers=auth_headers(tokens))
assert delete_response.json()["status"] == "archived"
assert client.get("/api/application-profiles", headers=auth_headers(tokens)).json() == []
archived = client.get("/api/application-profiles?status=archived", headers=auth_headers(tokens)).json()
assert archived[0]["id"] == created["id"]
```

Add restore test:

```python
restore_response = client.post(f"/api/application-profiles/{created['id']}/restore", headers=auth_headers(tokens))
assert restore_response.json()["status"] == "active"
```

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/test_application_profiles.py -q
```

Expected: status field and restore route missing.

- [ ] **Step 3: Add backend archive model**

Add `status = mapped_column(String(40), default="active", index=True)` to `ApplicationProfile`. Serialize it. Default list endpoint filters active profiles; `?status=archived` lists archived profiles.

- [ ] **Step 4: Add migration and SQLite compatibility**

Alembic migration:

```python
op.add_column("application_profiles", sa.Column("status", sa.String(length=40), nullable=False, server_default="active"))
op.create_index("ix_application_profiles_status", "application_profiles", ["status"])
```

SQLite auto-init should add the column if missing.

- [ ] **Step 5: Replace hard delete**

`DELETE /api/application-profiles/{id}` sets status to `archived` and updates `updated_at`. Add `POST /api/application-profiles/{id}/restore`.

- [ ] **Step 6: Run backend GREEN**

Run:

```bash
python -m pytest tests/test_application_profiles.py -q
```

Expected: pass.

- [ ] **Step 7: Add frontend archive/restore UI**

Default profile page shows active profiles. Add a secondary “查看已归档” section and restore action.

---

## Task 7: Full Verification and Deployment Handoff

**Files:**
- Modify docs only if deployment commands or current-state details change.

- [ ] **Step 1: Run backend tests**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd frontend && npm.cmd run test
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd frontend && npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 4: Validate compose**

Run:

```bash
docker compose --env-file .env.production.example config --quiet
```

Expected: no output and exit code 0.

- [ ] **Step 5: VPS deployment commands**

Use:

```bash
cd /home/ubuntu/ai-interview
git pull origin main
sudo docker compose --env-file .env.production up -d --build app worker nginx
sudo docker compose --env-file .env.production exec app alembic upgrade head
sudo docker compose --env-file .env.production exec app python scripts/seed_production_rag.py
```

- [ ] **Step 6: Public smoke verification**

Verify:

```bash
curl http://127.0.0.1:8080/api/health
sudo docker compose --env-file .env.production exec db psql -U ai_interview -d ai_interview -c "select knowledge_base, embedding_model, embedding_status, count(*) from rag_chunks group by knowledge_base, embedding_model, embedding_status;"
```

Expected: `role_knowledge` and `question_bank` have `embedding-3 / ready` chunks.

Then manually verify:

```text
1. Login as normal user.
2. Create/select active profile.
3. Start interview; first question is generated by backend.
4. Answer 2 rounds.
5. Click finish and review.
6. Land on /vue/app/reports/:recordId.
7. Confirm history contains the new interview.
8. Confirm training center contains generated tasks.
9. Confirm knowledge page hides metadata/debug by default.
10. Confirm profile archive hides active item and restore brings it back.
```

---

## Self-Review

- Spec coverage: This plan covers production RAG seed, interview start, finish/report/history/training closed loop, loading/friendly errors, knowledge page simplification, profile archive/restore, and final deployment verification.
- Placeholder scan: No implementation step relies on “TBD” behavior; each task defines the file, expected failing test, implementation direction, and verification command.
- Type consistency: Frontend names use existing `applicationProfileId`, `answeredHistory`, `generateTrainingTasksFromReport`, `agentMode`, and `agentRuntime`. Backend names use existing `ApplicationProfile`, `RagDocument`, `RagChunk`, and `create_rag_document_with_embeddings`.
