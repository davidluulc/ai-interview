# LangGraph Runtime Governance V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing LangGraph side-path into a governable Agent runtime with checkpoint summaries, human-review interrupts, resume support, runtime switching, and AI Debug Console visibility.

**Architecture:** Keep `/api/interview/next-question` and the classic Agent stable. Add focused backend modules for checkpoint summary storage, human review policy, and runtime orchestration, then expose experimental LangGraph runtime APIs and extend the Vue3 admin AI Debug panel to show runtime governance state.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy test fixtures, pytest, LangGraph, Vue3, Pinia, TypeScript, Vitest, Vite.

---

## Source References

Use these official LangGraph docs as the conceptual boundary while implementing:

- LangGraph Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Checkpointers: https://docs.langchain.com/oss/python/langgraph/checkpointers
- LangGraph Interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts

Key rules to preserve:

- A checkpointer persists thread-scoped graph state.
- `thread_id` is the stable pointer used to save and resume a graph thread.
- Interrupt payloads must be JSON-serializable.
- Resume uses `Command(resume=...)` with the same `thread_id`.
- This project keeps classic Agent as the stable default runtime.

---

## File Structure

Create:

- `backend_python/langgraph_agent/checkpoint_store.py`
  - Project-side checkpoint summary store abstraction.
  - Keeps first implementation in memory for tests and local development.
  - Records `threadId`, `currentNode`, `status`, `lastAction`, `requiresHumanReview`, `interrupt`, `resumeDecision`, and `runtimeTrace`.

- `backend_python/human_review_policy.py`
  - Rule-based human review decision module.
  - Converts Agent Policy / answer analysis into interrupt recommendation.

- `backend_python/agent_runtime.py`
  - Runtime orchestration module.
  - Supports `classic`, `langgraph`, and `shadow` modes.
  - First version focuses on experimental LangGraph runtime APIs and shadow summaries.

- `tests/test_langgraph_runtime_checkpoint_store.py`
  - Unit tests for checkpoint summary abstraction.

- `tests/test_human_review_policy.py`
  - Unit tests for human review rules.

- `tests/test_langgraph_runtime_interrupt_resume.py`
  - API tests for runtime run / resume experimental endpoints.

- `tests/test_agent_runtime_switching.py`
  - Runtime orchestration tests for classic / langgraph / shadow behavior.

- `docs/learning/19-LangGraph工作流治理如何理解checkpoint-interrupt-runtime.md`
  - Chinese learning document for interview preparation.

Modify:

- `backend_python/langgraph_agent/checkpoint.py`
  - Delegate summary storage to `checkpoint_store.py`.
  - Keep existing `summarize_checkpoint(thread_id)` compatible.

- `backend_python/langgraph_agent/state.py`
  - Add optional runtime governance fields if they are not already present.

- `backend_python/langgraph_agent/nodes.py`
  - Add a lightweight `human_review` helper for runtime interrupt decisions.

- `backend_python/langgraph_agent/graph.py`
  - Wire human review into the experimental runtime path without breaking V2.

- `backend_python/langgraph_agent/service.py`
  - Add runtime run / resume service functions.

- `backend_python/routes/langgraph_agent.py`
  - Add experimental runtime endpoints.
  - Preserve `/next-question-poc`, `/next-question-v2`, and `/checkpoint/{thread_id}`.

- `backend_python/ai_debug.py`
  - Include runtime, interrupt, resume, checkpoint governance fields in AI Debug payload.

- `backend_python/routes/admin.py`
  - Continue using AI Debug aggregation; update only if new fields need query support.

- `tests/test_admin_ai_debug.py`
  - Verify runtime governance fields surface in admin debug payload.

- `frontend/src/api/admin.ts`
  - Extend AI Debug types with runtime governance fields.

- `frontend/src/stores/admin.ts`
  - Preserve existing store shape; allow new runtime governance data.

- `frontend/src/pages/app/AdminPage.vue`
  - Show runtime, status, current node, interrupt reason, resume decision, and human-review state.

- `frontend/src/stores/admin.test.ts`
  - Verify store accepts AI Debug governance fields.

- `frontend/src/pages/app/admin-page.test.ts`
  - Verify Vue admin page renders runtime governance fields and no `undefined`.

- `docs/specs/README.md`
  - No change needed unless spec is moved.

- `docs/plans/README.md`
  - Mark this plan as the active plan.

- `docs/roadmap/current-state.md`
  - Record active plan path.

---

## Task 1: Checkpoint Summary Store

**Files:**

- Create: `backend_python/langgraph_agent/checkpoint_store.py`
- Modify: `backend_python/langgraph_agent/checkpoint.py`
- Create: `tests/test_langgraph_runtime_checkpoint_store.py`
- Modify: `tests/test_langgraph_agent_checkpoint.py`

- [ ] **Step 1: Write failing checkpoint store tests**

Create `tests/test_langgraph_runtime_checkpoint_store.py` with these tests:

```python
from backend_python.langgraph_agent.checkpoint_store import (
    InMemoryCheckpointSummaryStore,
    build_checkpoint_summary,
)


def test_checkpoint_summary_store_saves_and_reads_latest_summary():
    store = InMemoryCheckpointSummaryStore()
    summary = build_checkpoint_summary(
        thread_id="thread-a",
        state={
            "nodeTrace": [{"node": "observe_state"}, {"node": "human_review"}],
            "decision": {"nextAction": "lower_difficulty"},
            "policy": {"requiresHumanReview": True, "triggerRules": ["weak_answer_streak"]},
            "runtime": "langgraph",
            "currentNode": "human_review",
        },
    )

    store.save_summary(summary)

    loaded = store.get_summary("thread-a")
    assert loaded["exists"] is True
    assert loaded["threadId"] == "thread-a"
    assert loaded["runtime"] == "langgraph"
    assert loaded["currentNode"] == "human_review"
    assert loaded["lastAction"] == "lower_difficulty"
    assert loaded["requiresHumanReview"] is True
    assert loaded["nodeTraceCount"] == 2
    assert loaded["policyTriggerRules"] == ["weak_answer_streak"]


def test_checkpoint_summary_store_marks_interrupted_and_resumed():
    store = InMemoryCheckpointSummaryStore()
    summary = build_checkpoint_summary(
        thread_id="thread-b",
        state={"nodeTrace": [], "runtime": "langgraph"},
    )
    store.save_summary(summary)

    store.mark_interrupted(
        "thread-b",
        interrupt={
            "reason": "需要人工选择下一步",
            "options": ["continue_interview", "switch_to_coach"],
        },
    )
    interrupted = store.get_summary("thread-b")
    assert interrupted["status"] == "interrupted"
    assert interrupted["interrupt"]["reason"] == "需要人工选择下一步"

    store.mark_resumed("thread-b", resume_decision="switch_to_coach")
    resumed = store.get_summary("thread-b")
    assert resumed["status"] == "resumed"
    assert resumed["resumeDecision"] == "switch_to_coach"
    assert resumed["interrupt"] is None


def test_checkpoint_summary_store_returns_empty_summary_for_missing_thread():
    store = InMemoryCheckpointSummaryStore()

    summary = store.get_summary("missing-thread")

    assert summary["exists"] is False
    assert summary["threadId"] == "missing-thread"
    assert summary["runtime"] == ""
    assert summary["status"] == "missing"
    assert summary["requiresHumanReview"] is False
```

- [ ] **Step 2: Run failing checkpoint tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_checkpoint_store.py -q
```

Expected before implementation:

```text
FAIL because backend_python.langgraph_agent.checkpoint_store does not exist
```

- [ ] **Step 3: Implement checkpoint store**

Create `backend_python/langgraph_agent/checkpoint_store.py`:

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_thread_id(thread_id: str) -> str:
    return str(thread_id or "default-thread").strip() or "default-thread"


def empty_checkpoint_summary(thread_id: str) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    return {
        "enabled": True,
        "exists": False,
        "threadId": safe_thread_id,
        "runtime": "",
        "status": "missing",
        "currentNode": "",
        "roundCount": 0,
        "lastAction": "",
        "lastQuestion": "",
        "nodeTraceCount": 0,
        "stateKeys": [],
        "policyRecommendedAction": "",
        "shouldAskUserChoice": False,
        "requiresHumanReview": False,
        "policyReasons": [],
        "policyTriggerRules": [],
        "interrupt": None,
        "resumeDecision": "",
        "runtimeTrace": [],
    }


def build_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    node_trace = state.get("nodeTrace") if isinstance(state.get("nodeTrace"), list) else []
    decision = state.get("decision") if isinstance(state.get("decision"), dict) else {}
    policy = state.get("policy") if isinstance(state.get("policy"), dict) else {}
    next_question = state.get("nextQuestion") if isinstance(state.get("nextQuestion"), dict) else {}
    runtime_trace = state.get("runtimeTrace") if isinstance(state.get("runtimeTrace"), list) else []
    return {
        "enabled": True,
        "exists": True,
        "threadId": safe_thread_id,
        "runtime": str(state.get("runtime") or state.get("agentRuntime") or ""),
        "status": str(state.get("status") or "completed"),
        "currentNode": str(state.get("currentNode") or ""),
        "roundCount": int(state.get("roundCount") or 0),
        "lastAction": str(decision.get("nextAction") or policy.get("recommendedAction") or ""),
        "lastQuestion": str(next_question.get("prompt") or next_question.get("content") or ""),
        "nodeTraceCount": len(node_trace),
        "stateKeys": sorted(str(key) for key in state.keys()),
        "policyRecommendedAction": str(policy.get("recommendedAction") or ""),
        "shouldAskUserChoice": bool(policy.get("shouldAskUserChoice")),
        "requiresHumanReview": bool(policy.get("requiresHumanReview")),
        "policyReasons": list(policy.get("policyReasons") or [])[:5],
        "policyTriggerRules": list(policy.get("triggerRules") or []),
        "interrupt": state.get("interrupt") if isinstance(state.get("interrupt"), dict) else None,
        "resumeDecision": str(state.get("resumeDecision") or ""),
        "runtimeTrace": runtime_trace,
    }


class InMemoryCheckpointSummaryStore:
    def __init__(self) -> None:
        self._summaries: dict[str, dict[str, Any]] = {}

    def save_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        thread_id = normalize_thread_id(str(summary.get("threadId") or ""))
        stored = deepcopy(summary)
        stored["threadId"] = thread_id
        stored["exists"] = True
        self._summaries[thread_id] = stored
        return deepcopy(stored)

    def get_summary(self, thread_id: str) -> dict[str, Any]:
        safe_thread_id = normalize_thread_id(thread_id)
        if safe_thread_id not in self._summaries:
            return empty_checkpoint_summary(safe_thread_id)
        return deepcopy(self._summaries[safe_thread_id])

    def list_thread_runs(self, thread_id: str) -> list[dict[str, Any]]:
        summary = self.get_summary(thread_id)
        return [] if not summary.get("exists") else [summary]

    def mark_interrupted(self, thread_id: str, *, interrupt: dict[str, Any]) -> dict[str, Any]:
        summary = self.get_summary(thread_id)
        summary["exists"] = True
        summary["status"] = "interrupted"
        summary["currentNode"] = str(summary.get("currentNode") or "human_review")
        summary["requiresHumanReview"] = True
        summary["interrupt"] = deepcopy(interrupt)
        return self.save_summary(summary)

    def mark_resumed(self, thread_id: str, *, resume_decision: str) -> dict[str, Any]:
        summary = self.get_summary(thread_id)
        summary["exists"] = True
        summary["status"] = "resumed"
        summary["resumeDecision"] = str(resume_decision or "")
        summary["interrupt"] = None
        return self.save_summary(summary)


checkpoint_summary_store = InMemoryCheckpointSummaryStore()
```

- [ ] **Step 4: Wire existing checkpoint module**

Modify `backend_python/langgraph_agent/checkpoint.py` so public functions remain compatible:

```python
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .checkpoint_store import (
    build_checkpoint_summary,
    checkpoint_summary_store,
    normalize_thread_id,
)


memory_saver = MemorySaver()


def build_graph_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": normalize_thread_id(thread_id)}}


def record_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    summary = build_checkpoint_summary(thread_id=thread_id, state=state)
    return checkpoint_summary_store.save_summary(summary)


def summarize_checkpoint(thread_id: str) -> dict[str, Any]:
    return checkpoint_summary_store.get_summary(thread_id)
```

- [ ] **Step 5: Run checkpoint tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_checkpoint_store.py tests/test_langgraph_agent_checkpoint.py -q
```

Expected:

```text
all selected tests pass
```

---

## Task 2: Human Review Policy

**Files:**

- Create: `backend_python/human_review_policy.py`
- Create: `tests/test_human_review_policy.py`

- [ ] **Step 1: Write failing human review policy tests**

Create `tests/test_human_review_policy.py`:

```python
from backend_python.human_review_policy import evaluate_human_review


def test_requires_human_review_when_agent_policy_requests_it():
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": True, "recommendedAction": "lower_difficulty"},
        answer_analysis={"weakAnswerStreak": 1},
        history=[],
    )

    assert result["shouldInterrupt"] is True
    assert result["reason"]
    assert "continue_interview" in result["options"]
    assert "policy_requires_human_review" in result["triggerRules"]


def test_requires_human_review_after_three_weak_answers():
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": False},
        answer_analysis={"weakAnswerStreak": 3},
        history=[{"answer": "不会"}, {"answer": "不知道"}, {"answer": "还是不会"}],
    )

    assert result["shouldInterrupt"] is True
    assert "switch_to_coach" in result["options"]
    assert "weak_answer_streak" in result["triggerRules"]


def test_does_not_interrupt_normal_answer_flow():
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": False, "recommendedAction": "deep_follow_up"},
        answer_analysis={"weakAnswerStreak": 0},
        history=[{"answer": "我会从 checkpoint 和 thread_id 两层解释"}],
    )

    assert result["shouldInterrupt"] is False
    assert result["reason"] == ""
    assert result["options"] == []
    assert result["triggerRules"] == []
```

- [ ] **Step 2: Run failing policy tests**

Run:

```powershell
python -m pytest tests/test_human_review_policy.py -q
```

Expected before implementation:

```text
FAIL because backend_python.human_review_policy does not exist
```

- [ ] **Step 3: Implement human review policy**

Create `backend_python/human_review_policy.py`:

```python
from __future__ import annotations

from typing import Any


DEFAULT_REVIEW_OPTIONS = ["continue_interview", "switch_to_coach", "end_interview"]


def evaluate_human_review(
    *,
    agent_policy: dict[str, Any] | None,
    answer_analysis: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    policy = agent_policy if isinstance(agent_policy, dict) else {}
    analysis = answer_analysis if isinstance(answer_analysis, dict) else {}
    trigger_rules: list[str] = []

    if bool(policy.get("requiresHumanReview")):
        trigger_rules.append("policy_requires_human_review")

    weak_streak = int(analysis.get("weakAnswerStreak") or 0)
    if weak_streak >= 3:
        trigger_rules.append("weak_answer_streak")

    recent_history = list(history or [])[-3:]
    repeated_empty = len(recent_history) >= 2 and all(not str(item.get("answer") or "").strip() for item in recent_history)
    if repeated_empty:
        trigger_rules.append("repeated_empty_answer")

    if not trigger_rules:
        return {
            "shouldInterrupt": False,
            "reason": "",
            "options": [],
            "triggerRules": [],
        }

    reason = "Agent 工作流触发人工复核："
    if "weak_answer_streak" in trigger_rules:
        reason += "候选人连续弱回答，建议选择继续面试、切到学习辅导或结束面试。"
    elif "policy_requires_human_review" in trigger_rules:
        reason += "Agent Policy 标记本轮决策需要人工确认。"
    else:
        reason += "候选人连续空回答，建议人工确认下一步。"

    return {
        "shouldInterrupt": True,
        "reason": reason,
        "options": list(DEFAULT_REVIEW_OPTIONS),
        "triggerRules": trigger_rules,
    }
```

- [ ] **Step 4: Run policy tests**

Run:

```powershell
python -m pytest tests/test_human_review_policy.py -q
```

Expected:

```text
3 passed
```

---

## Task 3: Runtime Service and Runtime Switching

**Files:**

- Create: `backend_python/agent_runtime.py`
- Create: `tests/test_agent_runtime_switching.py`
- Modify: `backend_python/langgraph_agent/service.py`

- [ ] **Step 1: Write failing runtime switching tests**

Create `tests/test_agent_runtime_switching.py`:

```python
import pytest

from backend_python.agent_runtime import run_agent_runtime


@pytest.mark.asyncio
async def test_agent_runtime_defaults_to_classic():
    async def classic_runner(**kwargs):
        return {"question": {"content": "classic question"}, "decision": {"nextAction": "deep_follow_up"}}

    async def langgraph_runner(**kwargs):
        raise AssertionError("langgraph runner should not be called")

    result = await run_agent_runtime(
        agent_runtime="",
        thread_id="runtime-a",
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={"answer": "ok"},
    )

    assert result["runtime"] == "classic"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "classic question"
    assert result["shadow"] is None


@pytest.mark.asyncio
async def test_agent_runtime_runs_langgraph_mode():
    async def classic_runner(**kwargs):
        raise AssertionError("classic runner should not be called")

    async def langgraph_runner(**kwargs):
        return {"nextQuestion": {"content": "langgraph question"}, "decision": {"nextAction": "lower_difficulty"}}

    result = await run_agent_runtime(
        agent_runtime="langgraph",
        thread_id="runtime-b",
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={"answer": "不会"},
    )

    assert result["runtime"] == "langgraph"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "langgraph question"
    assert result["decision"]["nextAction"] == "lower_difficulty"


@pytest.mark.asyncio
async def test_agent_runtime_shadow_returns_classic_and_records_langgraph_summary():
    async def classic_runner(**kwargs):
        return {"question": {"content": "classic visible question"}, "decision": {"nextAction": "deep_follow_up"}}

    async def langgraph_runner(**kwargs):
        return {"nextQuestion": {"content": "shadow question"}, "decision": {"nextAction": "lower_difficulty"}}

    result = await run_agent_runtime(
        agent_runtime="shadow",
        thread_id="runtime-c",
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={"answer": "不会"},
    )

    assert result["runtime"] == "classic"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "classic visible question"
    assert result["shadow"]["runtime"] == "langgraph"
    assert result["shadow"]["question"]["content"] == "shadow question"
```

- [ ] **Step 2: Run failing runtime tests**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py -q
```

Expected before implementation:

```text
FAIL because backend_python.agent_runtime does not exist
```

- [ ] **Step 3: Implement runtime service**

Create `backend_python/agent_runtime.py`:

```python
from __future__ import annotations

from typing import Any, Awaitable, Callable


RuntimeRunner = Callable[..., Awaitable[dict[str, Any]]]


def normalize_agent_runtime(value: str | None) -> str:
    runtime = str(value or "classic").strip().lower()
    return runtime if runtime in {"classic", "langgraph", "shadow"} else "classic"


def _extract_question(result: dict[str, Any]) -> dict[str, Any]:
    question = result.get("question")
    if isinstance(question, dict):
        return question
    next_question = result.get("nextQuestion")
    if isinstance(next_question, dict):
        return next_question
    return {}


async def run_agent_runtime(
    *,
    agent_runtime: str | None,
    thread_id: str,
    classic_runner: RuntimeRunner,
    langgraph_runner: RuntimeRunner,
    payload: dict[str, Any],
) -> dict[str, Any]:
    runtime = normalize_agent_runtime(agent_runtime)
    common = {"thread_id": thread_id, **payload}

    if runtime == "langgraph":
        result = await langgraph_runner(**common)
        return {
            "runtime": "langgraph",
            "threadId": thread_id,
            "status": str(result.get("status") or "completed"),
            "question": _extract_question(result),
            "decision": result.get("decision") if isinstance(result.get("decision"), dict) else {},
            "checkpointSummary": result.get("checkpointSummary") if isinstance(result.get("checkpointSummary"), dict) else {},
            "interrupt": result.get("interrupt") if isinstance(result.get("interrupt"), dict) else None,
            "runtimeTrace": result.get("runtimeTrace") if isinstance(result.get("runtimeTrace"), list) else [],
            "shadow": None,
        }

    classic_result = await classic_runner(**common)
    response = {
        "runtime": "classic",
        "threadId": thread_id,
        "status": str(classic_result.get("status") or "completed"),
        "question": _extract_question(classic_result),
        "decision": classic_result.get("decision") if isinstance(classic_result.get("decision"), dict) else {},
        "checkpointSummary": classic_result.get("checkpointSummary") if isinstance(classic_result.get("checkpointSummary"), dict) else {},
        "interrupt": classic_result.get("interrupt") if isinstance(classic_result.get("interrupt"), dict) else None,
        "runtimeTrace": classic_result.get("runtimeTrace") if isinstance(classic_result.get("runtimeTrace"), list) else [],
        "shadow": None,
    }

    if runtime == "shadow":
        shadow_result = await langgraph_runner(**common)
        response["shadow"] = {
            "runtime": "langgraph",
            "status": str(shadow_result.get("status") or "completed"),
            "question": _extract_question(shadow_result),
            "decision": shadow_result.get("decision") if isinstance(shadow_result.get("decision"), dict) else {},
            "checkpointSummary": shadow_result.get("checkpointSummary")
            if isinstance(shadow_result.get("checkpointSummary"), dict)
            else {},
        }

    return response
```

- [ ] **Step 4: Run runtime tests**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py -q
```

Expected:

```text
3 passed
```

---

## Task 4: LangGraph Runtime Interrupt and Resume API

**Files:**

- Modify: `backend_python/langgraph_agent/service.py`
- Modify: `backend_python/routes/langgraph_agent.py`
- Create: `tests/test_langgraph_runtime_interrupt_resume.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_langgraph_runtime_interrupt_resume.py`:

```python
def test_langgraph_runtime_run_can_interrupt(client):
    payload = {
        "threadId": "runtime-interrupt-1",
        "agentRuntime": "langgraph",
        "agentMode": "coach",
        "history": [{"answer": "不会"}, {"answer": "不知道"}, {"answer": "还是不会"}],
        "answer": "不会",
        "nextStage": "技术追问",
        "enableInterrupt": True,
    }

    response = client.post("/api/langgraph-agent/runtime/run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["threadId"] == "runtime-interrupt-1"
    assert data["runtime"] == "langgraph"
    assert data["status"] == "interrupted"
    assert data["interrupt"]["options"]
    assert data["checkpointSummary"]["requiresHumanReview"] is True


def test_langgraph_runtime_resume_uses_existing_thread(client):
    client.post(
        "/api/langgraph-agent/runtime/run",
        json={
            "threadId": "runtime-resume-1",
            "agentRuntime": "langgraph",
            "history": [{"answer": "不会"}, {"answer": "不知道"}, {"answer": "不会"}],
            "answer": "不会",
            "enableInterrupt": True,
        },
    )

    response = client.post(
        "/api/langgraph-agent/runtime/resume",
        json={
            "threadId": "runtime-resume-1",
            "decision": "switch_to_coach",
            "comment": "先进入学习辅导",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threadId"] == "runtime-resume-1"
    assert data["status"] == "completed"
    assert data["resumeDecision"] == "switch_to_coach"
    assert data["checkpointSummary"]["resumeDecision"] == "switch_to_coach"


def test_langgraph_runtime_resume_missing_thread_returns_404(client):
    response = client.post(
        "/api/langgraph-agent/runtime/resume",
        json={"threadId": "missing-runtime-thread", "decision": "continue_interview"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run failing API tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_interrupt_resume.py -q
```

Expected before implementation:

```text
FAIL because /api/langgraph-agent/runtime/run and /api/langgraph-agent/runtime/resume do not exist
```

- [ ] **Step 3: Add runtime request schemas and endpoints**

Modify `backend_python/routes/langgraph_agent.py` by adding:

```python
from fastapi import HTTPException
from backend_python.human_review_policy import evaluate_human_review
from backend_python.langgraph_agent.checkpoint import record_checkpoint_summary, summarize_checkpoint
from backend_python.langgraph_agent.checkpoint_store import checkpoint_summary_store
```

Add request models:

```python
class LangGraphRuntimeRunRequest(BaseModel):
    threadId: str = "default-thread"
    agentRuntime: str = "langgraph"
    agentMode: str = "interview"
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    answer: str = ""
    nextStage: str = ""
    enableInterrupt: bool = False


class LangGraphRuntimeResumeRequest(BaseModel):
    threadId: str
    decision: str
    comment: str = ""
```

Add endpoints:

```python
@router.post("/runtime/run")
async def runtime_run(payload: LangGraphRuntimeRunRequest) -> dict[str, Any]:
    weak_streak = 0
    for item in reversed(payload.history):
        answer = str(item.get("answer") or "")
        if answer.strip() and "不会" not in answer and "不知道" not in answer:
            break
        weak_streak += 1
    if payload.answer and ("不会" in payload.answer or "不知道" in payload.answer):
        weak_streak = max(weak_streak, 1)

    policy = {
        "requiresHumanReview": weak_streak >= 3,
        "recommendedAction": "lower_difficulty" if weak_streak else "deep_follow_up",
        "triggerRules": ["weak_answer_streak"] if weak_streak >= 3 else [],
    }
    review = evaluate_human_review(
        agent_policy=policy,
        answer_analysis={"weakAnswerStreak": weak_streak},
        history=payload.history,
    )

    state = {
        "runtime": payload.agentRuntime,
        "status": "interrupted" if payload.enableInterrupt and review["shouldInterrupt"] else "completed",
        "currentNode": "human_review" if payload.enableInterrupt and review["shouldInterrupt"] else "generate_question",
        "roundCount": len(payload.history),
        "decision": {"nextAction": policy["recommendedAction"]},
        "policy": policy,
        "interrupt": review if payload.enableInterrupt and review["shouldInterrupt"] else None,
        "nodeTrace": [
            {"node": "observe_state"},
            {"node": "human_review" if payload.enableInterrupt and review["shouldInterrupt"] else "generate_question"},
        ],
        "runtimeTrace": [{"runtime": payload.agentRuntime, "status": "started"}],
        "nextQuestion": {} if payload.enableInterrupt and review["shouldInterrupt"] else {"content": "请继续解释 LangGraph checkpoint 和 thread_id 的关系。"},
    }
    checkpoint = record_checkpoint_summary(thread_id=payload.threadId, state=state)
    if payload.enableInterrupt and review["shouldInterrupt"]:
        checkpoint = checkpoint_summary_store.mark_interrupted(payload.threadId, interrupt=review)
        return {
            "threadId": payload.threadId,
            "runtime": payload.agentRuntime,
            "status": "interrupted",
            "question": None,
            "decision": state["decision"],
            "interrupt": review,
            "checkpointSummary": checkpoint,
            "runtimeTrace": state["runtimeTrace"],
        }

    return {
        "threadId": payload.threadId,
        "runtime": payload.agentRuntime,
        "status": "completed",
        "question": state["nextQuestion"],
        "decision": state["decision"],
        "interrupt": None,
        "checkpointSummary": checkpoint,
        "runtimeTrace": state["runtimeTrace"],
    }


@router.post("/runtime/resume")
async def runtime_resume(payload: LangGraphRuntimeResumeRequest) -> dict[str, Any]:
    checkpoint = summarize_checkpoint(payload.threadId)
    if not checkpoint.get("exists"):
        raise HTTPException(status_code=404, detail="LangGraph runtime thread not found")
    if checkpoint.get("status") != "interrupted":
        raise HTTPException(status_code=400, detail="LangGraph runtime thread is not interrupted")

    resumed = checkpoint_summary_store.mark_resumed(payload.threadId, resume_decision=payload.decision)
    question = {
        "content": "根据人工选择，系统将继续生成下一轮面试问题。"
        if payload.decision == "continue_interview"
        else "根据人工选择，系统先切换到学习辅导模式，拆解当前知识点。"
    }
    return {
        "threadId": payload.threadId,
        "runtime": resumed.get("runtime") or "langgraph",
        "status": "completed",
        "question": question,
        "resumeDecision": payload.decision,
        "checkpointSummary": resumed,
        "runtimeTrace": resumed.get("runtimeTrace", []),
    }
```

- [ ] **Step 4: Run runtime API tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_interrupt_resume.py -q
```

Expected:

```text
3 passed
```

---

## Task 5: AI Debug Backend Runtime Fields

**Files:**

- Modify: `backend_python/ai_debug.py`
- Modify: `tests/test_admin_ai_debug.py`

- [ ] **Step 1: Add failing AI Debug runtime field test**

Append to `tests/test_admin_ai_debug.py`:

```python
from backend_python.langgraph_agent.checkpoint import record_checkpoint_summary
from backend_python.langgraph_agent.checkpoint_store import checkpoint_summary_store


def test_admin_ai_debug_detail_contains_runtime_governance_fields() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        log = AgentDecisionLog(
            user_id=user_id,
            application_profile_id=303,
            request_type="next_question",
            next_action="lower_difficulty",
            stage="技术追问",
            difficulty="basic",
            focus="LangGraph runtime governance",
            reason="连续弱回答，触发人工复核",
            tools_json=json.dumps(["human_review"], ensure_ascii=False),
            state_json=json.dumps({"threadId": "debug-runtime-1", "agentMode": "coach"}, ensure_ascii=False),
            decision_json=json.dumps({"nextAction": "lower_difficulty"}, ensure_ascii=False),
            fallback_used=0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id

    record_checkpoint_summary(
        thread_id="debug-runtime-1",
        state={
            "runtime": "langgraph",
            "status": "interrupted",
            "currentNode": "human_review",
            "decision": {"nextAction": "lower_difficulty"},
            "policy": {"requiresHumanReview": True, "triggerRules": ["weak_answer_streak"]},
            "nodeTrace": [{"node": "human_review"}],
        },
    )
    checkpoint_summary_store.mark_interrupted(
        "debug-runtime-1",
        interrupt={"reason": "连续弱回答", "options": ["switch_to_coach"]},
    )

    response = client.get(f"/api/admin/ai-debug/{log_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["langgraph"]["runtime"] == "langgraph"
    assert data["langgraph"]["status"] == "interrupted"
    assert data["langgraph"]["currentNode"] == "human_review"
    assert data["langgraph"]["requiresHumanReview"] is True
    assert data["langgraph"]["interrupt"]["reason"] == "连续弱回答"
```

- [ ] **Step 2: Run focused AI Debug test**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected before implementation:

```text
FAIL because AI Debug langgraph payload does not expose all runtime governance fields
```

- [ ] **Step 3: Extend LangGraph normalization in AI Debug**

Modify `normalize_checkpoint()` in `backend_python/ai_debug.py` to include:

```python
"runtime": checkpoint.get("runtime") or "",
"status": checkpoint.get("status") or ("available" if exists else "missing"),
"currentNode": checkpoint.get("currentNode") or "",
"requiresHumanReview": bool(checkpoint.get("requiresHumanReview")),
"interrupt": checkpoint.get("interrupt") if isinstance(checkpoint.get("interrupt"), dict) else None,
"resumeDecision": checkpoint.get("resumeDecision") or "",
"runtimeTrace": checkpoint.get("runtimeTrace") if isinstance(checkpoint.get("runtimeTrace"), list) else [],
```

Keep existing keys such as `threadId`, `roundCount`, `nodeTraceCount`, `policyReasons`, and `policyTriggerRules`.

- [ ] **Step 4: Run AI Debug tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected:

```text
all selected tests pass
```

---

## Task 6: Vue3 Admin Runtime Governance Display

**Files:**

- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/stores/admin.test.ts`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Update frontend tests first**

Update `frontend/src/pages/app/admin-page.test.ts` to include an AI Debug detail fixture with:

```ts
selectedAiDebugDetail: {
  summary: { traceId: 1 },
  rag: { items: [], totalHitCount: 0 },
  agent: { nextActionLabel: "降低难度", reason: "连续弱回答" },
  langgraph: {
    exists: true,
    runtime: "langgraph",
    status: "interrupted",
    currentNode: "human_review",
    requiresHumanReview: true,
    interrupt: { reason: "连续弱回答", options: ["switch_to_coach"] },
    resumeDecision: ""
  },
  diagnostics: []
}
```

Add assertions:

```ts
expect(wrapper.text()).toContain("Runtime");
expect(wrapper.text()).toContain("langgraph");
expect(wrapper.text()).toContain("interrupted");
expect(wrapper.text()).toContain("human_review");
expect(wrapper.text()).toContain("需要人工介入");
expect(wrapper.text()).toContain("连续弱回答");
expect(wrapper.text()).not.toContain("undefined");
```

- [ ] **Step 2: Run failing frontend admin tests**

Run:

```powershell
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected before implementation:

```text
FAIL because runtime governance fields are not rendered
```

- [ ] **Step 3: Extend TypeScript interfaces**

Modify `frontend/src/api/admin.ts`:

```ts
export interface AdminAiDebugLangGraph {
  exists?: boolean;
  runtime?: string;
  status?: string;
  currentNode?: string;
  threadId?: string;
  nodeTraceCount?: number;
  requiresHumanReview?: boolean;
  interrupt?: Record<string, unknown> | null;
  resumeDecision?: string;
  runtimeTrace?: Record<string, unknown>[];
  explanation?: string;
}
```

Then update `AdminAiDebugDetail`:

```ts
langgraph: AdminAiDebugLangGraph;
```

- [ ] **Step 4: Render runtime governance in admin page**

Modify the LangGraph panel in `frontend/src/pages/app/AdminPage.vue` to show:

```vue
<p>Runtime：{{ debugText(admin.selectedAiDebugDetail.langgraph, "runtime", "未记录") }}</p>
<p>状态：{{ debugText(admin.selectedAiDebugDetail.langgraph, "status", "未记录") }}</p>
<p>当前节点：{{ debugText(admin.selectedAiDebugDetail.langgraph, "currentNode", "暂无") }}</p>
<p>
  人工介入：
  {{ debugBoolean(admin.selectedAiDebugDetail.langgraph, "requiresHumanReview") ? "需要人工介入" : "无需人工介入" }}
</p>
<p>恢复决策：{{ debugText(admin.selectedAiDebugDetail.langgraph, "resumeDecision", "暂无") }}</p>
<p v-if="debugInterruptReason" class="warning-pill">{{ debugInterruptReason }}</p>
```

Add computed helper:

```ts
const debugInterruptReason = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const interrupt = langgraph?.interrupt as DebugRecord | undefined;
  return typeof interrupt?.reason === "string" ? interrupt.reason : "";
});
```

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected:

```text
selected frontend tests pass
```

---

## Task 7: Learning Document

**Files:**

- Create: `docs/learning/19-LangGraph工作流治理如何理解checkpoint-interrupt-runtime.md`

- [ ] **Step 1: Create the learning document**

Write the document with these sections:

```markdown
# LangGraph 工作流治理如何理解 checkpoint、interrupt 和 runtime

## 1. 这阶段到底在做什么

本阶段不是重复接入 LangGraph，而是把 LangGraph 从旁路实验升级为可治理的 Agent Runtime。

## 2. thread_id 是什么

thread_id 是一场 LangGraph 工作流的会话编号。它告诉 checkpointer 当前应该保存或恢复哪一条 graph state。

## 3. checkpoint 和日志有什么区别

日志用于事后观察，checkpoint 用于恢复执行。日志回答“发生了什么”，checkpoint 还能支持“从哪里继续”。

## 4. interrupt / resume 为什么需要 checkpoint

interrupt 会暂停图执行。暂停时必须保存 graph state，否则 resume 时系统不知道从哪个节点、带着什么状态继续。

## 5. classic / langgraph / shadow 三种 runtime

classic 是稳定主流程；langgraph 是实验工作流；shadow 是主流程仍用 classic，同时旁路跑 langgraph 做对比。

## 6. 面试时怎么讲

我没有直接替换稳定主流程，而是用 runtime governance 渐进接入 LangGraph。这样既保证线上稳定，又能展示 Agent 工作流状态恢复、人工介入、灰度切换和可观测能力。
```

- [ ] **Step 2: Verify document exists**

Run:

```powershell
Test-Path 'docs/learning/19-LangGraph工作流治理如何理解checkpoint-interrupt-runtime.md'
```

Expected:

```text
True
```

---

## Task 8: Documentation State and Final Verification

**Files:**

- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Update active plan pointers**

In `docs/plans/README.md`, ensure current active plan is:

```text
docs/plans/active/langgraph-runtime-governance-v3.md
```

In `docs/roadmap/current-state.md`, ensure `docs/plans/active/` status says:

```text
docs/plans/active/langgraph-runtime-governance-v3.md
```

- [ ] **Step 2: Run focused backend tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_checkpoint_store.py tests/test_human_review_policy.py tests/test_agent_runtime_switching.py tests/test_langgraph_runtime_interrupt_resume.py tests/test_admin_ai_debug.py -q
```

Expected:

```text
all selected backend tests pass
```

- [ ] **Step 3: Run full backend tests**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
all backend tests pass
```

- [ ] **Step 4: Run full frontend tests**

Run from `frontend/`:

```powershell
npm.cmd run test
```

Expected:

```text
all frontend tests pass
```

- [ ] **Step 5: Run frontend build**

Run from `frontend/`:

```powershell
npm.cmd run build
```

Expected:

```text
build succeeds
```

- [ ] **Step 6: Browser verification**

Open:

```text
http://127.0.0.1:5173/vue/app/admin
```

Verify:

```text
AI 调试控制台可见
LangGraph 执行链路可见
Runtime 可见
状态可见
当前节点可见
人工介入状态可见
页面没有 Not Found
页面没有 undefined
桌面端无横向溢出
移动端 390px 左右无横向溢出
```

---

## Final Completion Criteria

This stage is complete only when all of the following are true:

- `docs/plans/active/langgraph-runtime-governance-v3.md` exists.
- Checkpoint summary store tests pass.
- Human review policy tests pass.
- Runtime switching tests pass.
- Runtime interrupt / resume API tests pass.
- AI Debug backend exposes runtime governance fields.
- Vue3 admin page renders runtime governance fields.
- Learning document 19 exists.
- `python -m pytest -q` passes.
- `npm.cmd run test` passes.
- `npm.cmd run build` passes.
- Browser verification passes on the Vue3 admin page.
