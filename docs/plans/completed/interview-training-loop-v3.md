# Interview Training Loop V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把训练中心从“任务列表”升级为“可作答、可反馈、可更新掌握度”的专项练习闭环。

**Architecture:** 后端复用现有 TrainingTask 和 weakTag 模板体系，新增 practice payload 构造与 practice endpoint，并增强 complete endpoint 的可选字段。前端扩展 training API、Pinia store 和训练页面，新增 TrainingPracticePanel 承接用户作答和掌握度更新。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Pytest, Vue3, Vite, TypeScript, Pinia, Vitest, Vue Test Utils.

---

## 0. 执行边界

优先修改：

```text
backend_python/training_tasks.py
backend_python/routes/training.py
tests/test_training_tasks.py
tests/test_training_practice_route.py
frontend/src/api/training.ts
frontend/src/api/training.test.ts
frontend/src/stores/training.ts
frontend/src/stores/training.test.ts
frontend/src/components/training/TrainingPracticePanel.vue
frontend/src/components/training/TrainingPracticePanel.test.ts
frontend/src/pages/app/TrainingPage.vue
frontend/src/pages/app/training-page.test.ts
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

禁止事项：

- 不改 `/api/interview/next-question`。
- 不重写 RAG / Agent / LangGraph 主链路。
- 不新增 LangGraph、LangChain 依赖。
- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不新增复杂数据库表，优先复用 TrainingTask.metadata_json 保存最近一次练习摘要。

每轮开发前先用中文解释本轮要学的后端或前端知识点。

---

## Task 1: Backend Practice Payload

**Files:**

- Modify: `tests/test_training_tasks.py`
- Modify: `backend_python/training_tasks.py`

- [ ] **Step 1: 写 failing tests**

在 `tests/test_training_tasks.py` 增加两个测试：

```python
def test_build_training_practice_payload_uses_weak_tag_template() -> None:
    from backend_python.training_tasks import build_training_practice_payload, create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估专项训练",
            description="练习 RAG 评估指标。",
            priority="high",
            mastery_score=45,
            metadata={"source": "report"},
        )
        payload = build_training_practice_payload(task, mode="coach", difficulty="basic")

    assert payload["weakTag"] == "rag_quality"
    assert payload["weakLabel"] == "RAG 质量评估"
    assert payload["mode"] == "coach"
    assert payload["difficulty"] == "basic"
    assert payload["question"]
    assert "Hit@K" in payload["answerKeyPoints"]
    assert payload["commonMistakes"]
    assert payload["oneMinuteTemplate"]
    assert payload["rubric"]
```

```python
def test_build_training_practice_payload_normalizes_mode_and_difficulty() -> None:
    from backend_python.training_tasks import build_training_practice_payload, create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="unknown_tag",
            weak_label="未知薄弱点",
            title="兜底训练",
            description="兜底表达训练。",
            priority="medium",
            mastery_score=30,
            metadata={},
        )
        payload = build_training_practice_payload(task, mode="bad", difficulty="bad")

    assert payload["mode"] == "coach"
    assert payload["difficulty"] == "basic"
    assert payload["question"]
    assert payload["fallbackUsed"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_training_tasks.py::test_build_training_practice_payload_uses_weak_tag_template tests/test_training_tasks.py::test_build_training_practice_payload_normalizes_mode_and_difficulty -q
```

Expected: FAIL，原因是 `build_training_practice_payload` 尚不存在。

- [ ] **Step 3: 实现 practice payload 构造**

在 `backend_python/training_tasks.py` 增加：

```python
VALID_PRACTICE_MODES = {"coach", "interview"}
VALID_PRACTICE_DIFFICULTIES = {"basic", "medium", "hard"}


def normalize_practice_mode(value: str) -> str:
    return value if value in VALID_PRACTICE_MODES else "coach"


def normalize_practice_difficulty(value: str) -> str:
    return value if value in VALID_PRACTICE_DIFFICULTIES else "basic"
```

再实现：

```python
def build_training_practice_payload(task: TrainingTask, *, mode: str = "coach", difficulty: str = "basic") -> dict[str, Any]:
    from .weakness_training_templates import get_training_template

    normalized_mode = normalize_practice_mode(mode)
    normalized_difficulty = normalize_practice_difficulty(difficulty)
    template = get_training_template(task.weak_tag)
    ladder = template.get("difficultyLadder") if isinstance(template.get("difficultyLadder"), dict) else {}
    ladder_questions = _safe_template_list(ladder.get(normalized_difficulty)) or _safe_template_list(ladder.get("basic"))
    mode_key = "coachQuestions" if normalized_mode == "coach" else "interviewQuestions"
    mode_questions = _safe_template_list(template.get(mode_key))
    question = (ladder_questions or mode_questions or _safe_template_list(template.get("coachQuestions")) or ["请结合项目讲清这个薄弱点。"])[0]
    answer_key_points = _safe_template_list(template.get("answerKeyPoints"))[:8]
    common_mistakes = _safe_template_list(template.get("commonMistakes"))[:6]
    return {
        "weakTag": task.weak_tag,
        "weakLabel": task.weak_label or str(template.get("label") or task.weak_tag),
        "mode": normalized_mode,
        "difficulty": normalized_difficulty,
        "question": question,
        "answerKeyPoints": answer_key_points,
        "commonMistakes": common_mistakes,
        "oneMinuteTemplate": str(template.get("oneMinuteTemplate") or ""),
        "relatedTags": _safe_template_list(template.get("relatedTags"))[:6],
        "rubric": _build_practice_rubric(answer_key_points),
        "fallbackUsed": bool(template.get("fallbackUsed")),
    }
```

同时增加：

```python
def _safe_template_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _build_practice_rubric(answer_key_points: list[str]) -> list[str]:
    if not answer_key_points:
        return ["是否讲清背景", "是否结合项目做法", "是否说明结果和复盘"]
    return [f"是否覆盖：{point}" for point in answer_key_points[:4]]
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
python -m pytest tests/test_training_tasks.py::test_build_training_practice_payload_uses_weak_tag_template tests/test_training_tasks.py::test_build_training_practice_payload_normalizes_mode_and_difficulty -q
```

Expected: PASS。

---

## Task 2: Backend Practice Route And Enhanced Complete

**Files:**

- Create: `tests/test_training_practice_route.py`
- Modify: `backend_python/routes/training.py`
- Modify: `backend_python/training_tasks.py`

- [ ] **Step 1: 写 failing route tests**

新建 `tests/test_training_practice_route.py`，覆盖：

```python
def test_get_training_practice_returns_template_payload() -> None:
    client, headers = create_authenticated_client()
    task = create_task_for_current_user("rag_quality")

    response = client.get(f"/api/training/tasks/{task.id}/practice?mode=coach&difficulty=basic", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["id"] == task.id
    assert body["practice"]["weakTag"] == "rag_quality"
    assert body["practice"]["question"]
    assert body["practice"]["answerKeyPoints"]
```

```python
def test_complete_training_task_accepts_answer_text_and_self_rating() -> None:
    client, headers = create_authenticated_client()
    task = create_task_for_current_user("agent_state")

    response = client.post(
        f"/api/training/tasks/{task.id}/complete",
        headers=headers,
        json={
            "answerStatus": "完整",
            "answerText": "Agent State 是当前面试局面的事实快照。",
            "selfRating": 4,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["attemptCount"] == 1
    assert body["masteryScore"] > 40
    assert body["metadata"]["lastPractice"]["answerStatus"] == "完整"
    assert body["metadata"]["lastPractice"]["selfRating"] == 4
    assert "Agent State" in body["metadata"]["lastPractice"]["answerPreview"]
```

测试里的 helper 可以参考 `tests/test_training_tasks.py` 和其他 route 测试的注册登录写法，必须创建真实登录用户，不能绕过鉴权。

- [ ] **Step 2: 运行 route 测试确认失败**

Run:

```powershell
python -m pytest tests/test_training_practice_route.py -q
```

Expected: FAIL，原因是 practice endpoint 不存在，complete schema 尚不接收新字段。

- [ ] **Step 3: 增强 complete_training_task**

在 `backend_python/training_tasks.py` 中把函数签名扩展为：

```python
def complete_training_task(
    db: Session,
    task_id: int,
    *,
    user_id: int,
    answer_status: str,
    answer_text: str = "",
    self_rating: int | None = None,
) -> TrainingTask:
```

在更新掌握度后，把 metadata 合并写回：

```python
metadata = parse_json(task.metadata_json, {})
metadata["lastPractice"] = {
    "answerStatus": answer_status,
    "answerPreview": str(answer_text or "")[:300],
    "selfRating": self_rating,
    "completedAt": task.last_practiced_at.isoformat() if task.last_practiced_at else "",
}
task.metadata_json = dump_json(metadata)
```

- [ ] **Step 4: 增加 route schema 和 endpoint**

在 `backend_python/routes/training.py` 中：

```python
class CompleteTaskRequest(BaseModel):
    answerStatus: str = "模糊"
    answerText: str = ""
    selfRating: int | None = Field(default=None, ge=1, le=5)
```

新增：

```python
@router.get("/{task_id}/practice")
async def get_task_practice(
    task_id: int,
    mode: str = "coach",
    difficulty: str = "basic",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_owned_training_task(db, task_id, user_id=current_user.id)
    return {
        "task": serialize_training_task(task),
        "practice": build_training_practice_payload(task, mode=mode, difficulty=difficulty),
    }
```

更新 complete route 调用：

```python
task = complete_training_task(
    db,
    task_id,
    user_id=current_user.id,
    answer_status=payload.answerStatus,
    answer_text=payload.answerText,
    self_rating=payload.selfRating,
)
```

- [ ] **Step 5: 运行后端聚焦测试**

Run:

```powershell
python -m pytest tests/test_training_tasks.py tests/test_training_practice_route.py -q
```

Expected: PASS。

---

## Task 3: Frontend API And Store

**Files:**

- Modify: `frontend/src/api/training.test.ts`
- Modify: `frontend/src/api/training.ts`
- Modify: `frontend/src/stores/training.test.ts`
- Modify: `frontend/src/stores/training.ts`

- [ ] **Step 1: 写 failing API tests**

在 `frontend/src/api/training.test.ts` 增加：

```ts
it("loads a training practice payload", async () => {
  const request = vi.mocked(apiClient.apiRequest);
  request.mockResolvedValueOnce({
    task: { id: 1, weakTag: "rag_quality", title: "RAG", description: "", status: "todo", priority: "high", masteryScore: 45 },
    practice: { weakTag: "rag_quality", question: "什么是 Hit@K？", answerKeyPoints: ["Hit@K"], commonMistakes: [], rubric: [] }
  });

  await getTrainingPractice(1, "coach", "basic");

  expect(request).toHaveBeenCalledWith("/api/training/tasks/1/practice?mode=coach&difficulty=basic");
});
```

```ts
it("completes a task with practice answer payload", async () => {
  const request = vi.mocked(apiClient.apiRequest);
  request.mockResolvedValueOnce({ id: 1 });

  await completeTrainingTask(1, {
    answerStatus: "完整",
    answerText: "我的回答",
    selfRating: 4
  });

  expect(request).toHaveBeenCalledWith("/api/training/tasks/1/complete", {
    method: "POST",
    body: JSON.stringify({ answerStatus: "完整", answerText: "我的回答", selfRating: 4 })
  });
});
```

- [ ] **Step 2: 实现 API 类型和函数**

在 `frontend/src/api/training.ts` 增加：

```ts
export type TrainingAnswerStatus = "不会" | "模糊" | "完整";

export interface TrainingPractice {
  weakTag: string;
  weakLabel?: string;
  mode: "coach" | "interview";
  difficulty: "basic" | "medium" | "hard";
  question: string;
  answerKeyPoints: string[];
  commonMistakes: string[];
  oneMinuteTemplate?: string;
  relatedTags?: string[];
  rubric: string[];
  fallbackUsed?: boolean;
}

export interface TrainingPracticeResponse {
  task: TrainingTask;
  practice: TrainingPractice;
}

export interface CompleteTrainingTaskPayload {
  answerStatus: TrainingAnswerStatus;
  answerText?: string;
  selfRating?: number | null;
}
```

新增：

```ts
export async function getTrainingPractice(
  taskId: number,
  mode = "coach",
  difficulty = "basic"
): Promise<TrainingPracticeResponse> {
  return apiRequest<TrainingPracticeResponse>(
    `/api/training/tasks/${taskId}/practice?mode=${encodeURIComponent(mode)}&difficulty=${encodeURIComponent(difficulty)}`
  );
}
```

把 `completeTrainingTask` 改成兼容字符串和对象：

```ts
export async function completeTrainingTask(
  taskId: number,
  payload: TrainingAnswerStatus | CompleteTrainingTaskPayload = "完整"
): Promise<TrainingTask> {
  const body = typeof payload === "string" ? { answerStatus: payload } : payload;
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/complete`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}
```

- [ ] **Step 3: 写 failing store tests**

在 `frontend/src/stores/training.test.ts` 增加：

```ts
it("opens a practice payload for a task", async () => {
  vi.mocked(trainingApi.getTrainingPractice).mockResolvedValueOnce({
    task: makeTask({ id: 1, weakTag: "rag_quality" }),
    practice: makePractice({ weakTag: "rag_quality", question: "什么是 Hit@K？" })
  });
  const store = useTrainingStore();

  await store.openPractice(1);

  expect(store.selectedTaskId).toBe(1);
  expect(store.practiceDetail?.question).toBe("什么是 Hit@K？");
  expect(store.practiceError).toBe("");
});
```

```ts
it("submits practice and updates the task list", async () => {
  const updated = makeTask({ id: 1, status: "done", masteryScore: 85, attemptCount: 1 });
  vi.mocked(trainingApi.completeTrainingTask).mockResolvedValueOnce(updated);
  const store = useTrainingStore();
  store.tasks = [makeTask({ id: 1, status: "in_progress", masteryScore: 70, attemptCount: 0 })];
  store.selectedTaskId = 1;
  store.practiceAnswerText = "我的回答";
  store.practiceAnswerStatus = "完整";
  store.selfRating = 4;

  await store.submitPractice();

  expect(store.tasks[0].masteryScore).toBe(85);
  expect(store.lastPracticeResult?.masteryScore).toBe(85);
  expect(trainingApi.completeTrainingTask).toHaveBeenCalledWith(1, {
    answerStatus: "完整",
    answerText: "我的回答",
    selfRating: 4
  });
});
```

- [ ] **Step 4: 实现 store 状态和 actions**

在 `frontend/src/stores/training.ts` 增加 refs：

```ts
const selectedTaskId = ref<number | null>(null);
const practiceLoading = ref(false);
const practiceError = ref("");
const practiceDetail = ref<trainingApi.TrainingPractice | null>(null);
const practiceAnswerText = ref("");
const practiceAnswerStatus = ref<trainingApi.TrainingAnswerStatus>("模糊");
const selfRating = ref<number | null>(null);
const lastPracticeResult = ref<trainingApi.TrainingTask | null>(null);
```

新增 actions：

```ts
async function openPractice(taskId: number): Promise<void> {
  selectedTaskId.value = taskId;
  practiceLoading.value = true;
  practiceError.value = "";
  lastPracticeResult.value = null;
  try {
    const result = await trainingApi.getTrainingPractice(taskId, "coach", "basic");
    practiceDetail.value = result.practice;
    tasks.value = replaceTask(tasks.value, result.task);
  } catch (err) {
    practiceError.value = err instanceof Error ? err.message : "训练练习加载失败";
  } finally {
    practiceLoading.value = false;
  }
}
```

```ts
async function submitPractice(): Promise<void> {
  if (!selectedTaskId.value) {
    practiceError.value = "请先选择训练任务";
    return;
  }
  const updated = await trainingApi.completeTrainingTask(selectedTaskId.value, {
    answerStatus: practiceAnswerStatus.value,
    answerText: practiceAnswerText.value,
    selfRating: selfRating.value
  });
  tasks.value = replaceTask(tasks.value, updated);
  lastPracticeResult.value = updated;
}
```

同时补齐 setter 和 reset，并 return 新状态。

- [ ] **Step 5: 运行前端聚焦测试**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/training.test.ts src/stores/training.test.ts
```

Expected: PASS。

---

## Task 4: Training Practice Panel

**Files:**

- Create: `frontend/src/components/training/TrainingPracticePanel.vue`
- Create: `frontend/src/components/training/TrainingPracticePanel.test.ts`

- [ ] **Step 1: 写 failing component tests**

新建测试覆盖：

```ts
it("renders practice question and guidance", () => {
  const wrapper = mount(TrainingPracticePanel, {
    props: {
      practice: makePractice({
        question: "什么是 Hit@K？",
        answerKeyPoints: ["Hit@K", "MRR"],
        commonMistakes: ["只解释字段名"],
        oneMinuteTemplate: "按指标定义、用途、项目落地回答。"
      }),
      answerText: "",
      answerStatus: "模糊",
      selfRating: null,
      loading: false,
      error: "",
      result: null
    }
  });

  expect(wrapper.text()).toContain("什么是 Hit@K？");
  expect(wrapper.text()).toContain("Hit@K");
  expect(wrapper.text()).toContain("只解释字段名");
  expect(wrapper.text()).toContain("按指标定义");
});
```

```ts
it("emits answer updates and submit", async () => {
  const wrapper = mount(TrainingPracticePanel, { props: validProps() });

  await wrapper.get('[data-testid="practice-answer"]').setValue("我的回答");
  await wrapper.get('[data-testid="answer-status-complete"]').trigger("click");
  await wrapper.get('[data-testid="self-rating-4"]').trigger("click");
  await wrapper.get('[data-testid="submit-practice"]').trigger("click");

  expect(wrapper.emitted("update:answerText")?.[0]).toEqual(["我的回答"]);
  expect(wrapper.emitted("update:answerStatus")?.[0]).toEqual(["完整"]);
  expect(wrapper.emitted("update:selfRating")?.[0]).toEqual([4]);
  expect(wrapper.emitted("submit")).toHaveLength(1);
});
```

- [ ] **Step 2: 运行组件测试确认失败**

Run:

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingPracticePanel.test.ts
```

Expected: FAIL，组件尚不存在。

- [ ] **Step 3: 实现 TrainingPracticePanel**

组件 props：

```ts
practice: trainingApi.TrainingPractice | null;
answerText: string;
answerStatus: trainingApi.TrainingAnswerStatus;
selfRating: number | null;
loading: boolean;
error: string;
result: trainingApi.TrainingTask | null;
```

组件 emits：

```ts
"update:answerText"
"update:answerStatus"
"update:selfRating"
"submit"
"reset"
```

UI 要求：

- 没有 practice 时显示“选择一个训练任务开始专项练习”。
- loading 时显示加载态。
- error 时显示错误。
- practice 存在时展示问题、回答要点、常见错误、表达模板。
- textarea 使用 `data-testid="practice-answer"`。
- 三个状态按钮使用：
  - `answer-status-unknown`
  - `answer-status-fuzzy`
  - `answer-status-complete`
- 自评分按钮使用 `self-rating-1` 到 `self-rating-5`。
- 提交按钮使用 `submit-practice`。
- result 存在时展示最新掌握度和尝试次数。

- [ ] **Step 4: 运行组件测试**

Run:

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingPracticePanel.test.ts
```

Expected: PASS。

---

## Task 5: Compose Training Page V3

**Files:**

- Modify: `frontend/src/components/training/TrainingTaskList.vue`
- Modify: `frontend/src/pages/app/TrainingPage.vue`
- Modify: `frontend/src/pages/app/training-page.test.ts`

- [ ] **Step 1: 更新页面测试**

在 `frontend/src/pages/app/training-page.test.ts` 中 mock training store 新增：

```ts
selectedTaskId
practiceLoading
practiceError
practiceDetail
practiceAnswerText
practiceAnswerStatus
selfRating
lastPracticeResult
openPractice
submitPractice
resetPractice
setPracticeAnswerText
setPracticeAnswerStatus
setSelfRating
```

新增断言：

```ts
expect(wrapper.text()).toContain("专项练习");
```

新增交互：

```ts
await wrapper.get('[data-testid="start-task-1"]').trigger("click");
expect(trainingStore.startTask).toHaveBeenCalledWith(1);
expect(trainingStore.openPractice).toHaveBeenCalledWith(1);
```

- [ ] **Step 2: 更新 TrainingTaskList 事件语义**

保持原有 `start` 事件名称，不改组件对外接口。页面层把它解释为：

```text
开始训练 -> startTask -> openPractice
```

- [ ] **Step 3: 集成 TrainingPracticePanel**

在 `TrainingPage.vue` 引入：

```ts
import TrainingPracticePanel from "@/components/training/TrainingPracticePanel.vue";
```

新增方法：

```ts
async function startPractice(id: number): Promise<void> {
  await training.startTask(id);
  await training.openPractice(id);
}
```

把 `TrainingTaskList` 的 start 事件改为：

```vue
@start="startPractice"
```

在任务列表下方加入：

```vue
<TrainingPracticePanel
  :answer-status="training.practiceAnswerStatus"
  :answer-text="training.practiceAnswerText"
  :error="training.practiceError"
  :loading="training.practiceLoading"
  :practice="training.practiceDetail"
  :result="training.lastPracticeResult"
  :self-rating="training.selfRating"
  @reset="training.resetPractice"
  @submit="training.submitPractice"
  @update:answer-status="training.setPracticeAnswerStatus"
  @update:answer-text="training.setPracticeAnswerText"
  @update:self-rating="training.setSelfRating"
/>
```

- [ ] **Step 4: 运行页面测试**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/training-page.test.ts
```

Expected: PASS。

---

## Task 6: Verification, Docs, And Archive Readiness

**Files:**

- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: 运行后端聚焦测试**

Run:

```powershell
python -m pytest tests/test_training_tasks.py tests/test_training_practice_route.py -q
```

Expected: PASS。

- [ ] **Step 2: 运行后端全量测试**

Run:

```powershell
python -m pytest -q
```

Expected: PASS。

- [ ] **Step 3: 运行前端聚焦测试**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/training.test.ts src/stores/training.test.ts src/components/training/TrainingPracticePanel.test.ts src/pages/app/training-page.test.ts
```

Expected: PASS。

- [ ] **Step 4: 运行前端全量测试和构建**

Run:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: PASS。

- [ ] **Step 5: 浏览器验证**

打开：

```text
http://127.0.0.1:5173/vue/app/training
```

检查：

- 点击“开始训练”后出现专项练习面板。
- 练习题、回答要点、常见错误、一分钟表达模板可见。
- 输入回答、选择回答状态、自评分后能提交。
- 提交后掌握度、尝试次数和任务状态更新。
- 桌面端无横向溢出。
- 移动端 390px 无横向溢出。
- 页面无 `undefined`。

- [ ] **Step 6: 更新路线文档**

如果所有验证通过，把 `docs/roadmap/current-state.md` 的当前状态改为：

```text
面试训练闭环增强 V3 已完成并归档，下一阶段建议讨论是否进入 LangGraph / Agent 工作流深化 B 阶段。
```

并把 active spec / active plan 改回：

```text
暂无
```

同时更新 `docs/specs/README.md` 和 `docs/plans/README.md`。

- [ ] **Step 7: 归档文档**

验证通过后执行：

```powershell
Move-Item -LiteralPath 'docs\specs\active\interview-training-loop-v3-design.md' -Destination 'docs\specs\completed\interview-training-loop-v3-design.md'
Move-Item -LiteralPath 'docs\plans\active\interview-training-loop-v3.md' -Destination 'docs\plans\completed\interview-training-loop-v3.md'
```

- [ ] **Step 8: 提交**

Run:

```powershell
git status --short
git add backend_python/training_tasks.py backend_python/routes/training.py tests/test_training_tasks.py tests/test_training_practice_route.py frontend/src/api/training.ts frontend/src/api/training.test.ts frontend/src/stores/training.ts frontend/src/stores/training.test.ts frontend/src/components/training/TrainingPracticePanel.vue frontend/src/components/training/TrainingPracticePanel.test.ts frontend/src/components/training/TrainingTaskList.vue frontend/src/pages/app/TrainingPage.vue frontend/src/pages/app/training-page.test.ts docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md docs/specs/completed/interview-training-loop-v3-design.md docs/plans/completed/interview-training-loop-v3.md
git commit -m "feat: add training practice loop v3"
```

Expected: commit succeeds.

