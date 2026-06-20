# Admin Observability UX V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the admin backend from a long technical log wall into an interview-centered observability workspace.

**Architecture:** Keep the existing FastAPI admin router and Vue3 admin page. Add small aggregation helpers and two read-only admin endpoints that group `InterviewRecord`, `RagRetrievalLog`, `AgentDecisionLog`, and report payload data into interview diagnostics; then add a frontend store/API layer and a compact "诊断工作台" tabbed UI. Avoid schema redesign in V3.0.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Vue3, Pinia, Vitest, Vite, Docker Compose.

---

## File Map

- `backend_python/routes/admin.py`: add interview observability serializers and two endpoints.
- `tests/test_admin_observability.py`: new backend coverage for interview list/detail grouping, unlinked logs, and admin-only access.
- `frontend/src/api/admin.ts`: add observability response types and API functions.
- `frontend/src/stores/admin.ts`: load observability list/detail, selected record id, and diagnostic workspace tab state.
- `frontend/src/stores/admin.test.ts`: cover loading, selecting and derived observability state.
- `frontend/src/pages/app/AdminPage.vue`: add "诊断工作台" tabs and interview-centered list/detail UI; keep raw AI debug under a secondary tab.
- `frontend/src/pages/app/admin-page.test.ts`: cover default interview diagnostics, detail expansion, tab switching, and long log reduction.
- `docs/roadmap/current-state.md`: already points active spec at V3; update after completion if this phase is finished.
- `docs/plans/README.md`: active plan pointer should be this file while implementation is in progress.

## Task 1: Active Plan Pointer

**Files:**
- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Update active plan pointer**

Set active plan to:

```text
docs/plans/active/admin-observability-ux-v3.md
```

Keep active spec as:

```text
docs/specs/active/admin-observability-ux-v3-design.md
```

- [ ] **Step 2: Verify route docs mention V3**

Run:

```bash
rg "admin-observability-ux-v3" docs/plans/README.md docs/roadmap/current-state.md
```

Expected: both files mention the active spec or plan.

- [ ] **Step 3: Commit**

```bash
git add docs/plans/active/admin-observability-ux-v3.md docs/plans/README.md docs/roadmap/current-state.md
git commit -m "docs: add admin observability implementation plan"
```

## Task 2: Backend Observability API

**Files:**
- Modify: `backend_python/routes/admin.py`
- Create: `tests/test_admin_observability.py`

- [ ] **Step 1: Write failing list endpoint test**

Create `tests/test_admin_observability.py` with:

```python
import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, ApplicationProfile, InterviewRecord, RagRetrievalLog, User
from backend_python.main import app
from tests.helpers import auth_headers, create_admin_headers


client = TestClient(app)


def create_user_and_profile(email_suffix: str = "obs") -> tuple[int, int, str]:
    with SessionLocal() as db:
        user = User(
            email=f"{email_suffix}@example.com",
            username=f"{email_suffix}_user",
            password_hash="x",
            role="user",
        )
        db.add(user)
        db.flush()
        profile = ApplicationProfile(
            user_id=user.id,
            title="Python 后端实习",
            target_role="Python 后端",
            application_type="实习",
            resume="RAG 项目",
            jd="负责 RAG 和 Agent 观测",
            company="Demo",
            position_tag="backend",
        )
        db.add(profile)
        db.commit()
        return int(user.id), int(profile.id), user.email


def test_admin_observability_interviews_groups_by_interview_record() -> None:
    headers, _ = create_admin_headers()
    user_id, profile_id, email = create_user_and_profile("obs-list")
    with SessionLocal() as db:
        record = InterviewRecord(
            user_id=user_id,
            application_profile_id=profile_id,
            candidate_name="Demo",
            target_role="Python 后端",
            application_type="实习",
            mode="coach",
            depth="standard",
            score=80,
            profile_json="{}",
            answers_json=json.dumps(
                [
                    {"question": "RAG 日志字段怎么排查？", "answer": "看 retrieval_mode 和 hit_count"},
                    {"question": "Agent 为什么降难度？", "answer": "因为连续弱回答"},
                ],
                ensure_ascii=False,
            ),
            report_json=json.dumps({"overall": "ok"}, ensure_ascii=False),
        )
        db.add(record)
        db.flush()
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record.id,
                request_type="next_question",
                query_text="RAG 日志字段",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=2,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record.id,
                request_type="next_question",
                query_text="候选人画像",
                retriever_name="candidate_memory",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            AgentDecisionLog(
                user_id=user_id,
                application_profile_id=profile_id,
                request_type="next_question",
                next_action="lower_difficulty",
                stage="技术追问",
                difficulty="basic",
                focus="RAG 日志",
                reason="候选人连续弱回答",
                tools_json="[]",
                state_json=json.dumps({"threadId": "obs-thread"}),
                decision_json="{}",
                fallback_used=1,
            )
        )
        db.commit()

    response = client.get("/api/admin/observability/interviews", headers=headers)

    assert response.status_code == 200
    body = response.json()
    item = next(item for item in body["items"] if item["recordId"] == record.id)
    assert item["userEmail"] == email
    assert item["profileTitle"] == "Python 后端实习"
    assert item["questionCount"] == 2
    assert item["reportStatus"] == "ready"
    assert item["ragSummary"]["goodCount"] == 1
    assert item["ragSummary"]["emptyCount"] == 1
    assert item["agentSummary"]["fallbackCount"] == 1
    assert item["agentSummary"]["lowerDifficultyCount"] == 1
```

- [ ] **Step 2: Run list endpoint RED**

Run:

```bash
python -m pytest tests/test_admin_observability.py::test_admin_observability_interviews_groups_by_interview_record -q
```

Expected: fails with `404 Not Found`.

- [ ] **Step 3: Implement list helpers and endpoint**

In `backend_python/routes/admin.py`, add JSON parsing helpers:

```python
def safe_json(value: str, fallback: Any) -> Any:
    import json

    try:
        parsed = json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed if parsed is not None else fallback


def count_answers(record: InterviewRecord) -> int:
    answers = safe_json(record.answers_json, [])
    return len(answers) if isinstance(answers, list) else 0


def report_status(record: InterviewRecord) -> str:
    payload = safe_json(record.report_json, {})
    return "ready" if isinstance(payload, dict) and bool(payload) else "missing"
```

Add summary helpers:

```python
def rag_level(log: RagRetrievalLog) -> str:
    if int(log.hit_count or 0) <= 0:
        return "empty"
    if int(log.hit_count or 0) == 1:
        return "weak"
    return "good"


def summarize_rag_logs(logs: list[RagRetrievalLog]) -> dict[str, int]:
    summary = {"goodCount": 0, "weakCount": 0, "emptyCount": 0, "totalCount": len(logs)}
    for log in logs:
        level = rag_level(log)
        if level == "good":
            summary["goodCount"] += 1
        elif level == "weak":
            summary["weakCount"] += 1
        else:
            summary["emptyCount"] += 1
    return summary


def summarize_agent_logs(logs: list[AgentDecisionLog]) -> dict[str, int]:
    return {
        "totalCount": len(logs),
        "fallbackCount": sum(1 for log in logs if int(log.fallback_used or 0)),
        "lowerDifficultyCount": sum(1 for log in logs if log.next_action == "lower_difficulty"),
        "deepenCount": sum(1 for log in logs if log.next_action in {"deepen", "deep_follow_up"}),
        "switchTopicCount": sum(1 for log in logs if log.next_action in {"switch_topic", "shift_topic"}),
    }
```

Add endpoint:

```python
@router.get("/observability/interviews")
async def admin_observability_interviews(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    records = list(
        db.scalars(
            select(InterviewRecord)
            .order_by(InterviewRecord.created_at.desc(), InterviewRecord.id.desc())
            .limit(bounded_limit(limit))
        ).all()
    )
    items = []
    for record in records:
        rag_logs = list(
            db.scalars(select(RagRetrievalLog).where(RagRetrievalLog.interview_record_id == record.id)).all()
        )
        agent_logs = list(
            db.scalars(
                select(AgentDecisionLog).where(
                    AgentDecisionLog.user_id == record.user_id,
                    AgentDecisionLog.application_profile_id == record.application_profile_id,
                )
            ).all()
        )
        items.append(
            {
                "recordId": record.id,
                "userId": record.user_id,
                "userEmail": record.user.email if record.user else "",
                "applicationProfileId": record.application_profile_id,
                "profileTitle": record.application_profile.title if record.application_profile else record.target_role,
                "targetRole": record.target_role,
                "createdAt": serialize_datetime(record.created_at),
                "questionCount": count_answers(record),
                "reportStatus": report_status(record),
                "ragSummary": summarize_rag_logs(rag_logs),
                "agentSummary": summarize_agent_logs(agent_logs),
                "relation": {
                    "rag": "interview_record_id",
                    "agent": "user_id + application_profile_id",
                },
            }
        )
    return {"items": items, "total": len(items)}
```

- [ ] **Step 4: Run list endpoint GREEN**

Run:

```bash
python -m pytest tests/test_admin_observability.py::test_admin_observability_interviews_groups_by_interview_record -q
```

Expected: pass.

- [ ] **Step 5: Write failing detail endpoint test**

Add:

```python
def test_admin_observability_interview_detail_shows_turns_and_unlinked_logs() -> None:
    headers, _ = create_admin_headers()
    user_id, profile_id, _ = create_user_and_profile("obs-detail")
    with SessionLocal() as db:
        record = InterviewRecord(
            user_id=user_id,
            application_profile_id=profile_id,
            candidate_name="Demo",
            target_role="Python 后端",
            application_type="实习",
            mode="coach",
            depth="standard",
            score=80,
            profile_json="{}",
            answers_json=json.dumps([{"question": "RAG 怎么定位空召回？", "answer": "看 hit_count"}], ensure_ascii=False),
            report_json=json.dumps({"decisionSummary": "围绕 RAG 空召回追问"}, ensure_ascii=False),
        )
        db.add(record)
        db.flush()
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record.id,
                request_type="next_question",
                query_text="RAG 空召回",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=1,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=None,
                request_type="next_question",
                query_text="未归属日志",
                retriever_name="question_bank",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.commit()
        record_id = record.id

    response = client.get(f"/api/admin/observability/interviews/{record_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["recordId"] == record_id
    assert body["overview"]["profileTitle"] == "Python 后端实习"
    assert body["turns"][0]["turnIndex"] == 1
    assert body["turns"][0]["question"] == "RAG 怎么定位空召回？"
    assert body["turns"][0]["ragSummary"][0]["label"] == "岗位知识库"
    assert body["turns"][0]["ragSummary"][0]["qualityLabel"] == "弱相关"
    assert body["unlinkedLogs"]["ragLogCount"] == 1
```

- [ ] **Step 6: Run detail endpoint RED**

Run:

```bash
python -m pytest tests/test_admin_observability.py::test_admin_observability_interview_detail_shows_turns_and_unlinked_logs -q
```

Expected: fails with `404 Not Found`.

- [ ] **Step 7: Implement detail endpoint**

Add turn and detail helpers:

```python
def answer_turns(record: InterviewRecord) -> list[dict[str, Any]]:
    answers = safe_json(record.answers_json, [])
    if not isinstance(answers, list):
        return []
    turns = []
    for index, item in enumerate(answers, start=1):
        data = item if isinstance(item, dict) else {}
        turns.append(
            {
                "turnIndex": index,
                "question": str(data.get("question") or data.get("q") or ""),
                "answer": str(data.get("answer") or data.get("a") or ""),
            }
        )
    return turns


def summarize_rag_for_turn(logs: list[RagRetrievalLog]) -> list[dict[str, Any]]:
    return [
        {
            "knowledgeBase": log.retriever_name,
            "label": normalize_rag_name(log.retriever_name),
            "hitCount": int(log.hit_count or 0),
            "qualityLabel": {"good": "高相关", "weak": "弱相关", "empty": "空召回"}[rag_level(log)],
            "queryText": log.query_text,
        }
        for log in logs[:5]
    ]
```

Add endpoint:

```python
@router.get("/observability/interviews/{record_id}")
async def admin_observability_interview_detail(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    record = db.get(InterviewRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview record not found")
    linked_rag_logs = list(
        db.scalars(
            select(RagRetrievalLog)
            .where(RagRetrievalLog.interview_record_id == record.id)
            .order_by(RagRetrievalLog.created_at.asc(), RagRetrievalLog.id.asc())
        ).all()
    )
    agent_logs = list(
        db.scalars(
            select(AgentDecisionLog)
            .where(
                AgentDecisionLog.user_id == record.user_id,
                AgentDecisionLog.application_profile_id == record.application_profile_id,
            )
            .order_by(AgentDecisionLog.created_at.asc(), AgentDecisionLog.id.asc())
        ).all()
    )
    turns = answer_turns(record)
    for index, turn in enumerate(turns):
        turn["ragSummary"] = summarize_rag_for_turn(linked_rag_logs[index : index + 1])
        agent_log = agent_logs[index] if index < len(agent_logs) else None
        turn["agentDecision"] = (
            {
                "actionLabel": build_ai_debug_recent_item(agent_log, [], {})["nextActionLabel"],
                "reason": agent_log.reason,
                "fallbackUsed": bool(agent_log.fallback_used),
                "relation": "user_id + application_profile_id + order",
            }
            if agent_log
            else None
        )
        turn["diagnostics"] = [
            f"{item['label']}为{item['qualityLabel']}" for item in turn["ragSummary"] if item["qualityLabel"] != "高相关"
        ]
        turn["traceIds"] = [agent_log.id] if agent_log else []
    unlinked_rag_count = int(
        db.scalar(
            select(func.count())
            .select_from(RagRetrievalLog)
            .where(
                RagRetrievalLog.user_id == record.user_id,
                RagRetrievalLog.application_profile_id == record.application_profile_id,
                RagRetrievalLog.interview_record_id.is_(None),
            )
        )
        or 0
    )
    return {
        "recordId": record.id,
        "overview": {
            "userEmail": record.user.email if record.user else "",
            "profileTitle": record.application_profile.title if record.application_profile else record.target_role,
            "targetRole": record.target_role,
            "createdAt": serialize_datetime(record.created_at),
            "reportStatus": report_status(record),
        },
        "summary": {
            "questionCount": len(turns),
            "ragSummary": summarize_rag_logs(linked_rag_logs),
            "agentSummary": summarize_agent_logs(agent_logs),
        },
        "turns": turns,
        "unlinkedLogs": {"ragLogCount": unlinked_rag_count, "agentLogCount": 0},
    }
```

- [ ] **Step 8: Run backend GREEN**

Run:

```bash
python -m pytest tests/test_admin_observability.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit backend API**

```bash
git add backend_python/routes/admin.py tests/test_admin_observability.py
git commit -m "feat: add admin interview observability api"
```

## Task 3: Frontend API and Store

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`

- [ ] **Step 1: Write failing store test**

Add to `frontend/src/stores/admin.test.ts`:

```ts
it("loads interview observability and selects a record detail", async () => {
  vi.mocked(adminApi.fetchAdminObservabilityInterviews).mockResolvedValue({
    items: [
      {
        recordId: 9,
        userEmail: "demo@example.com",
        profileTitle: "Python 后端实习",
        createdAt: "2026-06-20T21:35:00",
        questionCount: 2,
        reportStatus: "ready",
        ragSummary: { totalCount: 2, goodCount: 1, weakCount: 0, emptyCount: 1 },
        agentSummary: { totalCount: 1, fallbackCount: 1, lowerDifficultyCount: 1, deepenCount: 0, switchTopicCount: 0 }
      }
    ],
    total: 1
  });
  vi.mocked(adminApi.fetchAdminObservabilityInterviewDetail).mockResolvedValue({
    recordId: 9,
    overview: { userEmail: "demo@example.com", profileTitle: "Python 后端实习", reportStatus: "ready" },
    summary: {
      questionCount: 2,
      ragSummary: { totalCount: 2, goodCount: 1, weakCount: 0, emptyCount: 1 },
      agentSummary: { totalCount: 1, fallbackCount: 1, lowerDifficultyCount: 1, deepenCount: 0, switchTopicCount: 0 }
    },
    turns: [{ turnIndex: 1, question: "RAG 怎么排查？", answer: "看日志", ragSummary: [], diagnostics: [], traceIds: [] }],
    unlinkedLogs: { ragLogCount: 1, agentLogCount: 0 }
  });

  const store = useAdminStore();
  await store.loadObservability();
  await store.selectObservabilityRecord(9);

  expect(store.observabilityInterviews).toHaveLength(1);
  expect(store.selectedObservabilityDetail?.recordId).toBe(9);
  expect(store.selectedObservabilityTab).toBe("interviews");
});
```

- [ ] **Step 2: Run store RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected: fails because API functions and store state do not exist.

- [ ] **Step 3: Add frontend API types and functions**

In `frontend/src/api/admin.ts`, add interfaces:

```ts
export interface AdminObservabilityRagSummary {
  totalCount: number;
  goodCount: number;
  weakCount: number;
  emptyCount: number;
}

export interface AdminObservabilityAgentSummary {
  totalCount: number;
  fallbackCount: number;
  lowerDifficultyCount: number;
  deepenCount: number;
  switchTopicCount: number;
}

export interface AdminObservabilityInterviewItem {
  recordId: number;
  userEmail: string;
  profileTitle: string;
  targetRole?: string;
  createdAt: string | null;
  questionCount: number;
  reportStatus: string;
  ragSummary: AdminObservabilityRagSummary;
  agentSummary: AdminObservabilityAgentSummary;
}

export interface AdminObservabilityTurn {
  turnIndex: number;
  question: string;
  answer: string;
  ragSummary: Array<{ knowledgeBase: string; label: string; hitCount: number; qualityLabel: string; queryText?: string }>;
  agentDecision?: { actionLabel: string; reason: string; fallbackUsed: boolean; relation?: string } | null;
  diagnostics: string[];
  traceIds: number[];
}

export interface AdminObservabilityInterviewDetail {
  recordId: number;
  overview: Record<string, unknown>;
  summary: {
    questionCount: number;
    ragSummary: AdminObservabilityRagSummary;
    agentSummary: AdminObservabilityAgentSummary;
  };
  turns: AdminObservabilityTurn[];
  unlinkedLogs: { ragLogCount: number; agentLogCount: number };
}
```

Add functions:

```ts
export function fetchAdminObservabilityInterviews(): Promise<{ items: AdminObservabilityInterviewItem[]; total: number }> {
  return apiRequest("/api/admin/observability/interviews");
}

export function fetchAdminObservabilityInterviewDetail(recordId: number): Promise<AdminObservabilityInterviewDetail> {
  return apiRequest(`/api/admin/observability/interviews/${recordId}`);
}
```

- [ ] **Step 4: Add store state/actions**

In `frontend/src/stores/admin.ts`, add:

```ts
export type AdminObservabilityTab = "interviews" | "knowledge" | "agent" | "ai" | "raw";
const selectedObservabilityTab = ref<AdminObservabilityTab>("interviews");
const observabilityInterviews = ref<adminApi.AdminObservabilityInterviewItem[]>([]);
const observabilityTotal = ref(0);
const selectedObservabilityRecordId = ref<number | null>(null);
const selectedObservabilityDetail = ref<adminApi.AdminObservabilityInterviewDetail | null>(null);
```

Add actions:

```ts
async function loadObservability(): Promise<void> {
  const result = await adminApi.fetchAdminObservabilityInterviews();
  observabilityInterviews.value = result.items;
  observabilityTotal.value = result.total;
}

async function selectObservabilityRecord(recordId: number): Promise<void> {
  selectedObservabilityRecordId.value = recordId;
  selectedObservabilityDetail.value = await adminApi.fetchAdminObservabilityInterviewDetail(recordId);
}

function setObservabilityTab(tab: AdminObservabilityTab): void {
  selectedObservabilityTab.value = tab;
}
```

Call `loadObservability()` in `loadDashboard()` alongside existing admin requests.

- [ ] **Step 5: Run store GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/admin.test.ts
```

Expected: pass.

- [ ] **Step 6: Commit frontend API/store**

```bash
git add frontend/src/api/admin.ts frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts
git commit -m "feat: add admin observability store"
```

## Task 4: Admin Observability UI

**Files:**
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing page test**

Update the admin store fixture with:

```ts
selectedObservabilityTab: "interviews",
observabilityInterviews: [
  {
    recordId: 9,
    userEmail: "demo@example.com",
    profileTitle: "Python 后端实习",
    createdAt: "2026-06-20T21:35:00",
    questionCount: 2,
    reportStatus: "ready",
    ragSummary: { totalCount: 2, goodCount: 1, weakCount: 0, emptyCount: 1 },
    agentSummary: { totalCount: 1, fallbackCount: 1, lowerDifficultyCount: 1, deepenCount: 0, switchTopicCount: 0 }
  }
],
observabilityTotal: 1,
selectedObservabilityRecordId: 9,
selectedObservabilityDetail: {
  recordId: 9,
  overview: { userEmail: "demo@example.com", profileTitle: "Python 后端实习", reportStatus: "ready" },
  summary: {
    questionCount: 2,
    ragSummary: { totalCount: 2, goodCount: 1, weakCount: 0, emptyCount: 1 },
    agentSummary: { totalCount: 1, fallbackCount: 1, lowerDifficultyCount: 1, deepenCount: 0, switchTopicCount: 0 }
  },
  turns: [
    {
      turnIndex: 1,
      question: "RAG 怎么定位空召回？",
      answer: "看 hit_count",
      ragSummary: [{ knowledgeBase: "role_knowledge", label: "岗位知识库", hitCount: 1, qualityLabel: "弱相关" }],
      agentDecision: { actionLabel: "降低难度", reason: "连续弱回答", fallbackUsed: true },
      diagnostics: ["岗位知识库为弱相关"],
      traceIds: [1]
    }
  ],
  unlinkedLogs: { ragLogCount: 1, agentLogCount: 0 }
},
setObservabilityTab: vi.fn(),
selectObservabilityRecord: vi.fn(),
```

Add test:

```ts
it("renders interview-centered observability workspace by default", () => {
  const wrapper = mount(AdminPage, { global: globalConfig });
  const text = wrapper.text();

  expect(text).toContain("诊断工作台");
  expect(text).toContain("面试诊断");
  expect(text).toContain("Python 后端实习");
  expect(text).toContain("demo@example.com");
  expect(text).toContain("RAG：高相关 1 / 弱相关 0 / 空召回 1");
  expect(text).toContain("逐题链路");
  expect(text).toContain("RAG 怎么定位空召回？");
  expect(text).toContain("岗位知识库为弱相关");
  expect(text).toContain("未归属日志：RAG 1 / Agent 0");
});
```

- [ ] **Step 2: Run page RED**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fails because the observability workspace does not exist.

- [ ] **Step 3: Implement observability workspace**

In `AdminPage.vue`, add a new section after platform overview:

```vue
<section class="section observability-section">
  <div class="section-title">
    <h2>诊断工作台</h2>
    <span>{{ admin.observabilityTotal }} 次面试</span>
  </div>
  <p class="section-help">按用户、投递档案、面试记录和问题轮次组织 RAG、Agent 和 AI 请求链路。</p>
  <nav class="debug-tabs" aria-label="诊断工作台分区">
    <button type="button" :aria-selected="admin.selectedObservabilityTab === 'interviews'" @click="admin.setObservabilityTab('interviews')">面试诊断</button>
    <button type="button" :aria-selected="admin.selectedObservabilityTab === 'knowledge'" @click="admin.setObservabilityTab('knowledge')">知识库健康</button>
    <button type="button" :aria-selected="admin.selectedObservabilityTab === 'agent'" @click="admin.setObservabilityTab('agent')">Agent 行为</button>
    <button type="button" :aria-selected="admin.selectedObservabilityTab === 'ai'" @click="admin.setObservabilityTab('ai')">AI 请求</button>
    <button type="button" :aria-selected="admin.selectedObservabilityTab === 'raw'" @click="admin.setObservabilityTab('raw')">开发排查</button>
  </nav>
  <div v-if="admin.selectedObservabilityTab === 'interviews'" class="observability-layout">
    <div class="trace-list">
      <button
        v-for="item in admin.observabilityInterviews"
        :key="item.recordId"
        type="button"
        class="trace-card"
        :class="{ active: admin.selectedObservabilityRecordId === item.recordId }"
        @click="admin.selectObservabilityRecord(item.recordId)"
      >
        <span>{{ item.profileTitle || item.targetRole || '未命名档案' }}</span>
        <small>{{ item.userEmail }} · {{ item.questionCount }} 题 · {{ item.reportStatus === 'ready' ? '报告已生成' : '报告缺失' }}</small>
        <small>RAG：高相关 {{ item.ragSummary.goodCount }} / 弱相关 {{ item.ragSummary.weakCount }} / 空召回 {{ item.ragSummary.emptyCount }}</small>
      </button>
    </div>
    <article v-if="admin.selectedObservabilityDetail" class="debug-panel">
      <h3>逐题链路</h3>
      <p>
        未归属日志：RAG {{ admin.selectedObservabilityDetail.unlinkedLogs.ragLogCount }} /
        Agent {{ admin.selectedObservabilityDetail.unlinkedLogs.agentLogCount }}
      </p>
      <div v-for="turn in admin.selectedObservabilityDetail.turns" :key="turn.turnIndex" class="mini-row">
        <strong>{{ turn.turnIndex }}. {{ turn.question || '历史记录缺少问题文本' }}</strong>
        <span>回答：{{ turn.answer || '历史记录缺少回答文本' }}</span>
        <span v-for="rag in turn.ragSummary" :key="`${turn.turnIndex}-${rag.knowledgeBase}`">
          {{ rag.label }} · {{ rag.qualityLabel }} · 命中 {{ rag.hitCount }}
        </span>
        <span v-if="turn.agentDecision">
          Agent：{{ turn.agentDecision.actionLabel }} · {{ turn.agentDecision.reason }}
        </span>
        <span v-for="diagnostic in turn.diagnostics" :key="diagnostic">{{ diagnostic }}</span>
      </div>
    </article>
  </div>
  <div v-else-if="admin.selectedObservabilityTab === 'knowledge'" class="debug-panel">复用下方知识库健康摘要。</div>
  <div v-else-if="admin.selectedObservabilityTab === 'agent'" class="debug-panel">复用下方 Agent 行为摘要。</div>
  <div v-else-if="admin.selectedObservabilityTab === 'ai'" class="debug-panel">复用下方 AI 请求调试台。</div>
  <div v-else class="debug-panel">原始日志保留在各详情的原始日志 tab 中，默认不展开。</div>
</section>
```

Add CSS:

```css
.observability-layout {
  display: grid;
  grid-template-columns: minmax(240px, 340px) minmax(0, 1fr);
  gap: 16px;
  margin-top: 14px;
}
```

- [ ] **Step 4: Run page GREEN**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: pass.

- [ ] **Step 5: Commit UI**

```bash
git add frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: add interview observability workspace"
```

## Task 5: Verification and Handoff

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python -m pytest tests/test_admin_observability.py tests/test_admin_ai_debug.py tests/test_admin_routes.py -q
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts src/stores/admin.test.ts
```

Expected: pass.

- [ ] **Step 2: Run full verification**

Run:

```bash
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
docker compose --env-file .env.production.example config --quiet
```

Expected: all pass.

- [ ] **Step 3: Decide archive vs keep active**

If V3 implementation is complete, move:

```text
docs/specs/active/admin-observability-ux-v3-design.md
docs/plans/active/admin-observability-ux-v3.md
```

to completed and update `docs/roadmap/current-state.md`.

If only the first increment is complete, keep them active and record the completed slice.

- [ ] **Step 4: VPS update commands**

After merge to `main` and push:

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

- [ ] **Step 5: Public smoke**

```text
1. 打开管理员后台。
2. 强制下线弹窗中确认按钮文字可见。
3. 打开诊断工作台，默认是面试诊断。
4. 点击一条面试记录，右侧出现逐题链路。
5. 确认 RAG/Agent 诊断按轮次归属。
6. 确认原始日志没有默认铺满页面。
```

## Self-Review

- Spec coverage: Task 2 covers interview list/detail API; Task 3 covers frontend data layer; Task 4 covers UI; Task 5 covers verification and deployment. Button token bug was already fixed before this plan and is covered by `admin-page.test.ts`.
- Scope guard: no database redesign, no RAG algorithm rewrite, no Qdrant/pgvector, no full admin rewrite.
- Type consistency: API names use `AdminObservabilityInterviewItem`, `AdminObservabilityInterviewDetail`, `selectedObservabilityTab`, `observabilityInterviews`, and `selectedObservabilityDetail` consistently.
- Risk handling: unlinked logs are explicit; Agent relation is marked as approximate until a later schema pass.

