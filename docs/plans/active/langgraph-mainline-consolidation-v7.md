# LangGraph Mainline Consolidation V7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `/api/interview/next-question` 默认主链路收敛到 LangGraph mainline，classic Agent 降级为 fallback/helper，并让 Vue3 面试页和管理员后台承接工作流观测信息。

**Architecture:** 保持 FastAPI 接口路径和前端调用兼容，在后端新增 LangGraph mainline service 作为主执行入口，复用现有 RAG、Agent policy、decision、question generation、checkpoint、runtime audit 能力。classic Agent 不删除，只作为 fallback，在 LangGraph 节点异常、输出不合规或 quality gate 失败时兜底。前端只做可读展示和文案收敛，不做整站重构。

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph, Pytest, Vue3, Pinia, TypeScript, Vitest, Vite.

---

## File Structure

- Modify: `backend_python/schemas.py`
  - 扩展 `agentRuntime` 描述和 `QuestionResponse` 可选 workflow 字段。
- Modify: `backend_python/runtime_policy.py`
  - 新增 `langgraph_mainline` 默认策略，普通用户也默认走 LangGraph mainline。
- Modify: `backend_python/agent_runtime.py`
  - 新增 `langgraph_mainline` runtime 分支，去掉主流程的双轨比较依赖。
- Create: `backend_python/langgraph_mainline.py`
  - 封装 `/api/interview/next-question` 可调用的 LangGraph mainline service。
- Modify: `backend_python/routes/interview.py`
  - 将主接口内部默认执行 LangGraph mainline，保留 classic fallback。
- Modify: `backend_python/ai_debug.py`
  - 将后台表达从“旁路 / 对比”收敛成“Agent 工作流观测”。
- Modify: `backend_python/routes/admin.py`
  - 如现有 AI debug payload 不足，补充 workflow summary 字段。
- Test: `tests/test_langgraph_mainline_consolidation.py`
  - 覆盖默认 mainline、fallback、响应兼容、日志和 checkpoint。
- Modify tests:
  - `tests/test_interview_agent_route.py`
  - `tests/test_langgraph_agent_graph_v2.py`
  - `tests/test_admin_ai_debug.py`
  - `tests/test_rag_retrieval_logs.py`
- Modify: `frontend/src/api/interview.ts`
  - 扩展 runtime 类型和新增可选响应字段。
- Modify: `frontend/src/stores/interview.ts`
  - 保存轻量 runtime / workflow / fallback 摘要。
- Modify: `frontend/src/pages/app/InterviewPage.vue`
  - 展示用户友好的兜底提示和工作流摘要。
- Modify: `frontend/src/api/admin.ts`
  - 扩展后台 AI debug / workflow payload 类型。
- Modify: `frontend/src/stores/admin.ts`
  - 保存 Agent 工作流观测数据。
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - 把 runtime 对比主叙事改成 Agent 工作流观测。
- Modify frontend tests:
  - `frontend/src/api/interview.test.ts` if added, otherwise `frontend/src/stores/interview.test.ts`
  - `frontend/src/pages/app/interview-page.test.ts`
  - `frontend/src/api/admin.ts` related tests if present
  - `frontend/src/stores/admin.test.ts`
  - `frontend/src/pages/app/admin-page.test.ts`
- Modify docs after completion:
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`
  - Move active spec/plan to completed.

---

### Task 1: Backend Runtime Policy Defaults To LangGraph Mainline

**Files:**
- Modify: `backend_python/runtime_policy.py`
- Modify: `backend_python/agent_runtime.py`
- Modify: `backend_python/schemas.py`
- Test: `tests/test_langgraph_mainline_consolidation.py`

- [ ] **Step 1: Write failing runtime policy tests**

Create `tests/test_langgraph_mainline_consolidation.py` with:

```python
import pytest

from backend_python.runtime_policy import decide_runtime_policy
from backend_python.agent_runtime import normalize_agent_runtime, run_agent_runtime


def test_missing_runtime_defaults_to_langgraph_mainline_for_user():
    policy = decide_runtime_policy(requested_runtime=None, user_role="user", agent_mode="coach")

    assert policy["requestedRuntime"] == "langgraph_mainline"
    assert policy["allowedRuntime"] == "langgraph_mainline"
    assert policy["fallbackRuntime"] == "classic"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph_mainline"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True


def test_normalize_agent_runtime_accepts_langgraph_mainline():
    assert normalize_agent_runtime(None) == "langgraph_mainline"
    assert normalize_agent_runtime("langgraph_mainline") == "langgraph_mainline"
    assert normalize_agent_runtime("unknown") == "langgraph_mainline"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py -q
```

Expected: FAIL because default runtime is still `classic` and `langgraph_mainline` is not accepted.

- [ ] **Step 3: Implement runtime policy default**

Modify `backend_python/runtime_policy.py`:

```python
VALID_REQUESTED_RUNTIMES = {"classic", "shadow", "langgraph_canary", "langgraph_mainline"}


def _mainline_policy(*, requested: str, mode: str) -> dict[str, Any]:
    return {
        "requestedRuntime": requested,
        "allowedRuntime": "langgraph_mainline",
        "fallbackRuntime": "classic",
        "visibleRuntimeOnSuccess": "langgraph_mainline",
        "visibleRuntimeOnFailure": "classic",
        "canUseLangGraph": True,
        "requiresAudit": True,
        "agentMode": mode,
        "reasons": ["默认使用 LangGraph mainline，classic Agent 仅作为 fallback"],
    }
```

Then update `decide_runtime_policy()`:

```python
requested = (requested_runtime or "langgraph_mainline").strip() or "langgraph_mainline"
...
if requested not in VALID_REQUESTED_RUNTIMES:
    return _mainline_policy(requested="langgraph_mainline", mode=mode)

if requested == "langgraph_mainline":
    return _mainline_policy(requested="langgraph_mainline", mode=mode)
```

Keep explicit `"classic"` as an allowed debug fallback:

```python
if requested == "classic":
    return {
        "requestedRuntime": "classic",
        "allowedRuntime": "classic",
        "fallbackRuntime": "classic",
        "visibleRuntimeOnSuccess": "classic",
        "visibleRuntimeOnFailure": "classic",
        "canUseLangGraph": False,
        "requiresAudit": True,
        "agentMode": mode,
        "reasons": ["显式请求 classic fallback/debug runtime"],
    }
```

- [ ] **Step 4: Implement runtime normalization**

Modify `backend_python/agent_runtime.py`:

```python
def normalize_agent_runtime(value: str | None) -> str:
    runtime = str(value or "langgraph_mainline").strip().lower()
    allowed = {"classic", "langgraph", "shadow", "langgraph_canary", "langgraph_mainline"}
    return runtime if runtime in allowed else "langgraph_mainline"
```

- [ ] **Step 5: Update schema description**

Modify `backend_python/schemas.py`:

```python
agentRuntime: str | None = Field(
    default=None,
    description="Agent runtime preference: langgraph_mainline, classic, shadow, or langgraph_canary",
)
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py -q
```

Expected: PASS for runtime policy tests.

---

### Task 2: LangGraph Mainline Runtime Runner And Fallback

**Files:**
- Modify: `backend_python/agent_runtime.py`
- Test: `tests/test_langgraph_mainline_consolidation.py`

- [ ] **Step 1: Add failing runtime runner tests**

Append to `tests/test_langgraph_mainline_consolidation.py`:

```python
@pytest.mark.asyncio
async def test_run_agent_runtime_mainline_uses_langgraph_when_quality_passes():
    async def classic_runner(**kwargs):
        return {
            "question": {"prompt": "classic fallback question", "stage": "classic", "focus": "fallback"},
            "decision": {"nextAction": "deepen", "difficulty": "medium"},
            "status": "completed",
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {
                "prompt": "langgraph mainline question",
                "content": "langgraph mainline question",
                "stage": "技术追问",
                "focus": "LangGraph",
            },
            "decision": {"nextAction": "deepen", "difficulty": "medium", "reason": "mainline"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"], "currentNode": "update_memory"},
            "runtimeTrace": [{"node": "observe_state"}, {"node": "retrieve_context"}],
            "status": "completed",
        }

    result = await run_agent_runtime(
        agent_runtime="langgraph_mainline",
        thread_id="thread-mainline-pass",
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={"recentQuestions": []},
    )

    assert result["visibleRuntime"] == "langgraph_mainline"
    assert result["question"]["prompt"] == "langgraph mainline question"
    assert result["fallbackRuntime"] == ""
    assert result["runtimeAudit"]["fallbackUsed"] is False


@pytest.mark.asyncio
async def test_run_agent_runtime_mainline_falls_back_to_classic_when_langgraph_fails():
    async def classic_runner(**kwargs):
        return {
            "question": {"prompt": "classic fallback question", "stage": "fallback", "focus": "stability"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "status": "completed",
        }

    async def langgraph_runner(**kwargs):
        raise RuntimeError("graph exploded")

    result = await run_agent_runtime(
        agent_runtime="langgraph_mainline",
        thread_id="thread-mainline-fallback",
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={"recentQuestions": []},
    )

    assert result["visibleRuntime"] == "classic"
    assert result["question"]["prompt"] == "classic fallback question"
    assert result["fallbackRuntime"] == "classic"
    assert result["runtimeAudit"]["fallbackUsed"] is True
    assert "LangGraph runtime 执行失败" in result["runtimeAudit"]["qualityGateReasons"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py -q
```

Expected: FAIL because `run_agent_runtime()` has no `langgraph_mainline` branch.

- [ ] **Step 3: Add `_failed_langgraph_result()` helper**

Modify `backend_python/agent_runtime.py`:

```python
def _failed_langgraph_result(thread_id: str, error: Exception | str) -> dict[str, Any]:
    return {
        "status": "failed",
        "nextQuestion": {},
        "decision": {},
        "checkpointSummary": {"exists": False, "threadId": thread_id},
        "runtimeTrace": [],
        "error": str(error),
    }
```

- [ ] **Step 4: Add `_failed_quality_gate()` helper**

Modify `backend_python/agent_runtime.py`:

```python
def _failed_quality_gate(reason: str) -> dict[str, Any]:
    return {
        "passed": False,
        "fallbackToClassic": True,
        "riskLevel": "high",
        "reasons": [reason],
        "checks": {
            "runtimeCompleted": False,
            "nonEmptyQuestion": False,
            "validDecision": False,
            "validDifficulty": False,
            "checkpointAvailable": False,
        },
    }
```

- [ ] **Step 5: Add `langgraph_mainline` branch before canary branch**

Modify `run_agent_runtime()` in `backend_python/agent_runtime.py`:

```python
if runtime == "langgraph_mainline":
    try:
        langgraph_result = await langgraph_runner(**common)
        quality_gate = evaluate_runtime_quality(langgraph_result, recent_questions=recent_questions)
    except Exception as exc:
        langgraph_result = _failed_langgraph_result(thread_id, exc)
        quality_gate = _failed_quality_gate("LangGraph runtime 执行失败")

    if quality_gate["passed"]:
        response = _runtime_response(runtime="langgraph_mainline", thread_id=thread_id, result=langgraph_result)
        response["visibleRuntime"] = "langgraph_mainline"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = None
        response["runtimeAudit"] = build_runtime_audit(
            policy={
                "requestedRuntime": "langgraph_mainline",
                "allowedRuntime": "langgraph_mainline",
                "fallbackRuntime": "classic",
                "reasons": ["默认使用 LangGraph mainline"],
            },
            quality_gate=quality_gate,
            checkpoint_summary=response["checkpointSummary"],
            comparison_summary=None,
            visible_runtime="langgraph_mainline",
        )
        return response

    classic_result = await classic_runner(**common)
    response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
    response["visibleRuntime"] = "classic"
    response["fallbackRuntime"] = "classic"
    response["qualityGate"] = quality_gate
    response["comparisonSummary"] = None
    response["runtimeAudit"] = build_runtime_audit(
        policy={
            "requestedRuntime": "langgraph_mainline",
            "allowedRuntime": "langgraph_mainline",
            "fallbackRuntime": "classic",
            "reasons": ["LangGraph mainline 未通过质量门禁，已回退 classic"],
        },
        quality_gate=quality_gate,
        checkpoint_summary=langgraph_result.get("checkpointSummary")
        if isinstance(langgraph_result.get("checkpointSummary"), dict)
        else {},
        comparison_summary=None,
        visible_runtime="classic",
    )
    return response
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py -q
```

Expected: PASS.

---

### Task 3: Route Integration For `/api/interview/next-question`

**Files:**
- Modify: `backend_python/routes/interview.py`
- Modify: `backend_python/schemas.py`
- Test: `tests/test_langgraph_mainline_consolidation.py`
- Test: `tests/test_interview_agent_route.py`
- Test: `tests/test_rag_retrieval_logs.py`

- [ ] **Step 1: Add route-level failing tests**

Append to `tests/test_langgraph_mainline_consolidation.py`:

```python
def test_next_question_defaults_to_langgraph_mainline(monkeypatch):
    from fastapi.testclient import TestClient
    from backend_python.main import app

    captured = {}

    async def fake_run_agent_runtime(**kwargs):
        captured["agent_runtime"] = kwargs["agent_runtime"]
        return {
            "visibleRuntime": "langgraph_mainline",
            "question": {
                "stage": "技术追问",
                "stability": "stable",
                "focus": "LangGraph 工作流",
                "prompt": "请解释 LangGraph 如何编排面试 Agent。",
                "content": "请解释 LangGraph 如何编排面试 Agent。",
            },
            "decision": {"nextAction": "deepen", "difficulty": "medium", "reason": "mainline"},
            "checkpointSummary": {"exists": True, "threadId": "fake-thread"},
            "runtimeTrace": [{"node": "observe_state"}],
            "qualityGate": {"passed": True, "reasons": []},
            "runtimeAudit": {
                "requestedRuntime": "langgraph_mainline",
                "visibleRuntime": "langgraph_mainline",
                "fallbackUsed": False,
                "fallbackReason": "",
                "qualityGateReasons": [],
            },
        }

    monkeypatch.setattr("backend_python.routes.interview.run_agent_runtime", fake_run_agent_runtime)

    client = TestClient(app)
    email = "mainline-default@example.com"
    client.post("/api/auth/register", json={"email": email, "username": "mainline_default", "password": "password123"})
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["accessToken"]

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "profile": {"targetRole": "AI 应用开发"},
            "history": [{"question": "什么是 Agent？", "answer": "是能根据状态决策的系统"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert captured["agent_runtime"] == "langgraph_mainline"
    assert body["prompt"] == "请解释 LangGraph 如何编排面试 Agent。"
    assert body["runtimeAudit"]["visibleRuntime"] == "langgraph_mainline"
```

- [ ] **Step 2: Run route test and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py::test_next_question_defaults_to_langgraph_mainline -q
```

Expected: FAIL because route still passes `shadow` / `langgraph_canary` only when policy allows, and default policy is not yet integrated.

- [ ] **Step 3: Add `QuestionResponse` optional workflow fields**

Modify `backend_python/schemas.py`:

```python
class QuestionResponse(BaseModel):
    stage: str
    stability: str
    focus: str = ""
    prompt: str
    agentDecision: dict[str, Any] = Field(default_factory=dict)
    decisionSummary: str = ""
    ragReasons: list[str] = Field(default_factory=list)
    runtimeAudit: dict[str, Any] = Field(default_factory=dict)
    workflowTrace: list[dict[str, Any]] = Field(default_factory=list)
    checkpointSummary: dict[str, Any] = Field(default_factory=dict)
    qualityGate: dict[str, Any] = Field(default_factory=dict)
    fallbackSummary: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Route should call runtime layer for mainline too**

Modify `backend_python/routes/interview.py` around the current runtime block:

```python
should_run_runtime = runtime_policy["allowedRuntime"] in {"shadow", "langgraph", "langgraph_mainline"}
if should_run_runtime:
    ...
    runtime_request = (
        "shadow"
        if runtime_policy["allowedRuntime"] == "shadow"
        else "langgraph_canary"
        if runtime_policy["requestedRuntime"] == "langgraph_canary"
        else "langgraph_mainline"
    )
    runtime_result = await run_agent_runtime(
        agent_runtime=runtime_request,
        thread_id=runtime_thread_id,
        classic_runner=classic_runner,
        langgraph_runner=langgraph_runner,
        payload={...},
    )
```

- [ ] **Step 5: Return workflow fields when LangGraph is visible**

In the `visibleRuntime in {"langgraph", "langgraph_mainline"}` response branch, return:

```python
return {
    "stage": str(question.get("stage") or classic_response["stage"]),
    "stability": str(question.get("stability") or classic_response["stability"]),
    "focus": str(question.get("focus") or classic_response["focus"]),
    "prompt": prompt,
    "agentDecision": {
        **decision,
        "runtimeAudit": runtime_audit,
        "qualityGate": runtime_result.get("qualityGate") or {},
    },
    "decisionSummary": str(decision.get("decisionSummary") or decision.get("reason") or classic_response["decisionSummary"]),
    "ragReasons": rag_reasons,
    "runtimeAudit": runtime_audit,
    "workflowTrace": runtime_result.get("runtimeTrace") if isinstance(runtime_result.get("runtimeTrace"), list) else [],
    "checkpointSummary": runtime_result.get("checkpointSummary") if isinstance(runtime_result.get("checkpointSummary"), dict) else {},
    "qualityGate": runtime_result.get("qualityGate") if isinstance(runtime_result.get("qualityGate"), dict) else {},
    "fallbackSummary": {"used": False, "reason": ""},
}
```

- [ ] **Step 6: Return workflow fields when classic fallback is visible**

Before returning `classic_response`, add:

```python
classic_response["workflowTrace"] = runtime_result.get("runtimeTrace") if "runtime_result" in locals() and isinstance(runtime_result.get("runtimeTrace"), list) else []
classic_response["checkpointSummary"] = (
    runtime_result.get("checkpointSummary")
    if "runtime_result" in locals() and isinstance(runtime_result.get("checkpointSummary"), dict)
    else {}
)
classic_response["qualityGate"] = (
    runtime_result.get("qualityGate")
    if "runtime_result" in locals() and isinstance(runtime_result.get("qualityGate"), dict)
    else {}
)
classic_response["fallbackSummary"] = {
    "used": bool(classic_response.get("runtimeAudit", {}).get("fallbackUsed")),
    "reason": str(classic_response.get("runtimeAudit", {}).get("fallbackReason") or ""),
}
```

- [ ] **Step 7: Run focused route and log tests**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py tests/test_interview_agent_route.py tests/test_rag_retrieval_logs.py -q
```

Expected: PASS. This proves mainline route compatibility and RAG/Agent logs still work.

---

### Task 4: Checkpoint Summary Persistence And Admin Workflow Payload

**Files:**
- Modify: `backend_python/routes/interview.py`
- Modify: `backend_python/ai_debug.py`
- Modify: `backend_python/routes/admin.py`
- Test: `tests/test_admin_ai_debug.py`
- Test: `tests/test_langgraph_runtime_checkpoint_persistence.py`

- [ ] **Step 1: Add failing admin workflow tests**

Append to `tests/test_admin_ai_debug.py`:

```python
def test_ai_debug_detail_exposes_agent_workflow_observation(db_session, admin_client):
    from backend_python.db_models import AgentDecisionLog, User
    import json

    user = User(email="workflow-owner@example.com", username="workflow_owner", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    log = AgentDecisionLog(
        user_id=user.id,
        request_type="next_question",
        next_action="deepen",
        stage="技术追问",
        difficulty="medium",
        focus="LangGraph",
        reason="mainline",
        tools_json="[]",
        state_json=json.dumps(
            {
                "threadId": "workflow-thread-1",
                "runtimeAudit": {"visibleRuntime": "langgraph_mainline", "fallbackUsed": False},
                "nodeTrace": [{"nodeName": "observe_state"}, {"nodeName": "retrieve_context"}],
            },
            ensure_ascii=False,
        ),
        decision_json=json.dumps({"nextAction": "deepen"}, ensure_ascii=False),
        fallback_used=0,
    )
    db_session.add(log)
    db_session.commit()

    response = admin_client.get(f"/api/admin/ai-debug/{log.id}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["workflowObservation"]["title"] == "Agent 工作流观测"
    assert detail["workflowObservation"]["runtime"] == "langgraph_mainline"
    assert detail["workflowObservation"]["fallbackUsed"] is False
```

- [ ] **Step 2: Run admin test and verify failure**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py::test_ai_debug_detail_exposes_agent_workflow_observation -q
```

Expected: FAIL because `workflowObservation` does not exist.

- [ ] **Step 3: Add `build_workflow_observation()` helper**

Modify `backend_python/ai_debug.py`:

```python
def build_workflow_observation(agent: dict[str, Any], langgraph: dict[str, Any], rag_items: list[dict[str, Any]]) -> dict[str, Any]:
    state = agent.get("state") if isinstance(agent.get("state"), dict) else {}
    runtime_audit = (
        state.get("runtimeAudit")
        if isinstance(state.get("runtimeAudit"), dict)
        else langgraph.get("runtimeAudit")
        if isinstance(langgraph.get("runtimeAudit"), dict)
        else {}
    )
    node_trace = state.get("nodeTrace") if isinstance(state.get("nodeTrace"), list) else langgraph.get("runtimeTrace") or []
    return {
        "title": "Agent 工作流观测",
        "runtime": str(runtime_audit.get("visibleRuntime") or langgraph.get("visibleRuntime") or ""),
        "fallbackUsed": bool(runtime_audit.get("fallbackUsed") or agent.get("fallbackUsed")),
        "fallbackReason": str(runtime_audit.get("fallbackReason") or ""),
        "qualityGate": langgraph.get("qualityGate") if isinstance(langgraph.get("qualityGate"), dict) else {},
        "checkpoint": {
            "exists": bool(langgraph.get("exists")),
            "threadId": langgraph.get("threadId") or "",
            "currentNode": langgraph.get("currentNode") or "",
            "roundCount": int(langgraph.get("roundCount") or 0),
            "lastAction": langgraph.get("lastAction") or agent.get("nextAction") or "",
            "requiresHumanReview": bool(langgraph.get("requiresHumanReview")),
        },
        "nodes": node_trace if isinstance(node_trace, list) else [],
        "ragSummary": [
            {
                "retrieverLabel": item.get("retrieverLabel") or item.get("retrieverName") or "",
                "hitCount": int(item.get("hitCount") or 0),
                "qualityLevel": item.get("qualityLevel") or "",
            }
            for item in rag_items[:3]
        ],
    }
```

- [ ] **Step 4: Include workflow observation in debug detail**

Modify `build_ai_debug_detail()` in `backend_python/ai_debug.py` so the returned dict includes:

```python
"workflowObservation": build_workflow_observation(agent=agent, langgraph=langgraph, rag_items=rag_items),
```

- [ ] **Step 5: Run admin tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py tests/test_langgraph_runtime_checkpoint_persistence.py -q
```

Expected: PASS.

---

### Task 5: Frontend Interview Runtime Summary

**Files:**
- Modify: `frontend/src/api/interview.ts`
- Modify: `frontend/src/stores/interview.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`
- Test: `frontend/src/stores/interview.test.ts`
- Test: `frontend/src/pages/app/interview-page.test.ts`

- [ ] **Step 1: Add failing store tests**

Modify `frontend/src/stores/interview.test.ts`:

```ts
it("stores runtime summary from next question response", async () => {
  vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
    prompt: "请解释 LangGraph 主链路。",
    decisionSummary: "围绕工作流继续追问",
    ragReasons: [],
    runtimeAudit: {
      visibleRuntime: "langgraph_mainline",
      fallbackUsed: false
    },
    workflowTrace: [{ nodeName: "observe_state" }, { nodeName: "retrieve_context" }],
    checkpointSummary: { exists: true, threadId: "thread-1" },
    fallbackSummary: { used: false, reason: "" }
  });

  const store = useInterviewStore();
  store.draft = "我知道一点";
  await store.submitAnswer({ profile: { targetRole: "AI 应用开发" } });

  expect(store.lastRuntimeAudit?.visibleRuntime).toBe("langgraph_mainline");
  expect(store.lastWorkflowTrace).toHaveLength(2);
  expect(store.lastCheckpointSummary?.threadId).toBe("thread-1");
});
```

- [ ] **Step 2: Run frontend store test and verify failure**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts
```

Expected: FAIL because runtime summary refs do not exist.

- [ ] **Step 3: Extend frontend API types**

Modify `frontend/src/api/interview.ts`:

```ts
export type AgentRuntime = "langgraph_mainline" | "classic" | "shadow" | "langgraph_canary";

export interface RuntimeAuditSummary {
  visibleRuntime?: string;
  fallbackUsed?: boolean;
  fallbackReason?: string;
  qualityGateReasons?: string[];
}

export interface WorkflowTraceItem {
  nodeName?: string;
  node?: string;
  inputSummary?: Record<string, unknown>;
  outputSummary?: Record<string, unknown>;
  fallbackUsed?: boolean;
}
```

Then extend `NextQuestionResponse`:

```ts
runtimeAudit?: RuntimeAuditSummary;
workflowTrace?: WorkflowTraceItem[];
checkpointSummary?: Record<string, unknown>;
qualityGate?: Record<string, unknown>;
fallbackSummary?: { used?: boolean; reason?: string };
```

Set default payload runtime:

```ts
agentRuntime: payload.agentRuntime || "langgraph_mainline",
```

- [ ] **Step 4: Store runtime summary**

Modify `frontend/src/stores/interview.ts`:

```ts
const lastRuntimeAudit = ref<interviewApi.RuntimeAuditSummary | null>(null);
const lastWorkflowTrace = ref<interviewApi.WorkflowTraceItem[]>([]);
const lastCheckpointSummary = ref<Record<string, unknown> | null>(null);
const lastFallbackSummary = ref<{ used?: boolean; reason?: string } | null>(null);
```

In `resetSession()`:

```ts
lastRuntimeAudit.value = null;
lastWorkflowTrace.value = [];
lastCheckpointSummary.value = null;
lastFallbackSummary.value = null;
```

After response:

```ts
lastRuntimeAudit.value = response.runtimeAudit || null;
lastWorkflowTrace.value = response.workflowTrace || [];
lastCheckpointSummary.value = response.checkpointSummary || null;
lastFallbackSummary.value = response.fallbackSummary || null;
```

Return these refs from the store.

- [ ] **Step 5: Update InterviewPage user-facing display**

Modify `frontend/src/pages/app/InterviewPage.vue` to add a compact runtime note near the evidence panel:

```vue
<section v-if="interview.lastRuntimeAudit || interview.lastWorkflowTrace.length" class="interview-insight-panel">
  <p class="eyebrow">提问依据</p>
  <h2>为什么这样问</h2>
  <p v-if="interview.decisionSummary">{{ interview.decisionSummary }}</p>
  <p v-if="interview.lastFallbackSummary?.used" class="runtime-note">
    系统已使用稳定兜底策略保证面试继续。
  </p>
  <p v-else-if="interview.lastWorkflowTrace.length" class="runtime-note">
    本轮已完成状态观察、资料检索、回答分析和问题生成。
  </p>
</section>
```

Use existing page class naming style. Do not show raw JSON.

- [ ] **Step 6: Add page test**

Modify `frontend/src/pages/app/interview-page.test.ts`:

```ts
it("shows friendly fallback note without raw workflow json", async () => {
  const interviewStore = useInterviewStore();
  interviewStore.decisionSummary = "候选人回答偏弱，先降低难度。";
  interviewStore.lastRuntimeAudit = { visibleRuntime: "classic", fallbackUsed: true };
  interviewStore.lastFallbackSummary = { used: true, reason: "quality gate failed" };
  interviewStore.lastWorkflowTrace = [{ nodeName: "observe_state" }];

  const wrapper = mount(InterviewPage, { global: { plugins: [pinia, router] } });

  expect(wrapper.text()).toContain("为什么这样问");
  expect(wrapper.text()).toContain("系统已使用稳定兜底策略保证面试继续");
  expect(wrapper.text()).not.toContain("quality gate failed");
  expect(wrapper.text()).not.toContain("observe_state");
});
```

- [ ] **Step 7: Run focused frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts src/pages/app/interview-page.test.ts
```

Expected: PASS.

---

### Task 6: Frontend Admin Agent Workflow Observation

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Test: `frontend/src/stores/admin.test.ts`
- Test: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Add failing admin frontend tests**

Modify `frontend/src/pages/app/admin-page.test.ts`:

```ts
it("renders agent workflow observation instead of runtime comparison as the main runtime section", async () => {
  const adminStore = useAdminStore();
  adminStore.aiDebugDetail = {
    id: 1,
    workflowObservation: {
      title: "Agent 工作流观测",
      runtime: "langgraph_mainline",
      fallbackUsed: true,
      fallbackReason: "LangGraph runtime 执行失败",
      nodes: [{ nodeName: "observe_state" }, { nodeName: "retrieve_context" }],
      ragSummary: [
        { retrieverLabel: "岗位知识库", hitCount: 2, qualityLevel: "good" },
        { retrieverLabel: "题库", hitCount: 1, qualityLevel: "weak" },
        { retrieverLabel: "候选人画像", hitCount: 0, qualityLevel: "miss" }
      ],
      checkpoint: { exists: true, threadId: "thread-1", currentNode: "update_memory" },
      qualityGate: { passed: false, reasons: ["问题为空"] }
    }
  } as never;

  const wrapper = mount(AdminPage, { global: { plugins: [pinia, router] } });

  expect(wrapper.text()).toContain("Agent 工作流观测");
  expect(wrapper.text()).toContain("langgraph_mainline");
  expect(wrapper.text()).toContain("岗位知识库");
  expect(wrapper.text()).toContain("稳定兜底");
  expect(wrapper.text()).not.toContain("classic vs LangGraph");
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: FAIL because the page does not render `workflowObservation` yet.

- [ ] **Step 3: Add admin API types**

Modify `frontend/src/api/admin.ts`:

```ts
export interface AdminWorkflowObservation {
  title: string;
  runtime: string;
  fallbackUsed: boolean;
  fallbackReason?: string;
  nodes: Array<{ nodeName?: string; node?: string; fallbackUsed?: boolean }>;
  ragSummary: Array<{ retrieverLabel: string; hitCount: number; qualityLevel: string }>;
  checkpoint: {
    exists: boolean;
    threadId?: string;
    currentNode?: string;
    roundCount?: number;
    lastAction?: string;
    requiresHumanReview?: boolean;
  };
  qualityGate?: { passed?: boolean; reasons?: string[] };
}
```

Add `workflowObservation?: AdminWorkflowObservation;` to the AI debug detail response type.

- [ ] **Step 4: Render workflow observation in AdminPage**

Modify `frontend/src/pages/app/AdminPage.vue` near the existing AI debug detail/runtime area:

```vue
<section v-if="admin.aiDebugDetail?.workflowObservation" class="admin-section">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Agent Workflow</p>
      <h2>Agent 工作流观测</h2>
    </div>
  </div>
  <div class="metric-grid">
    <article class="metric-card">
      <span>当前 runtime</span>
      <strong>{{ admin.aiDebugDetail.workflowObservation.runtime || "未记录" }}</strong>
    </article>
    <article class="metric-card warning">
      <span>稳定兜底</span>
      <strong>{{ admin.aiDebugDetail.workflowObservation.fallbackUsed ? "已触发" : "未触发" }}</strong>
    </article>
    <article class="metric-card">
      <span>Checkpoint</span>
      <strong>{{ admin.aiDebugDetail.workflowObservation.checkpoint?.exists ? "已保存" : "未保存" }}</strong>
    </article>
  </div>
  <div class="workflow-node-list">
    <span v-for="node in admin.aiDebugDetail.workflowObservation.nodes" :key="node.nodeName || node.node">
      {{ node.nodeName || node.node }}
    </span>
  </div>
  <div class="rag-summary-list">
    <span v-for="item in admin.aiDebugDetail.workflowObservation.ragSummary" :key="item.retrieverLabel">
      {{ item.retrieverLabel }} · 命中 {{ item.hitCount }} · {{ item.qualityLevel }}
    </span>
  </div>
</section>
```

Use existing CSS classes where possible. Add small scoped CSS only if necessary.

- [ ] **Step 5: Run focused admin frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: PASS.

---

### Task 7: Docs State And Completion Verification

**Files:**
- Modify after implementation: `docs/roadmap/current-state.md`
- Modify after implementation: `docs/specs/README.md`
- Modify after implementation: `docs/plans/README.md`
- Move after implementation:
  - `docs/specs/active/langgraph-mainline-consolidation-v7-design.md` -> `docs/specs/completed/langgraph-mainline-consolidation-v7-design.md`
  - `docs/plans/active/langgraph-mainline-consolidation-v7.md` -> `docs/plans/completed/langgraph-mainline-consolidation-v7.md`

- [ ] **Step 1: Run backend focused tests**

Run:

```powershell
python -m pytest tests/test_langgraph_mainline_consolidation.py tests/test_interview_agent_route.py tests/test_rag_retrieval_logs.py tests/test_admin_ai_debug.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend full tests**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts src/pages/app/interview-page.test.ts src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: PASS.

- [ ] **Step 4: Run frontend full tests and build**

Run:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 5: Browser verification**

Use the in-app browser to verify:

```text
http://127.0.0.1:5173/vue/app/interview
http://127.0.0.1:5173/vue/app/admin
```

Expected:

- `/vue/app/interview` desktop: can show interview page, submit answer when a profile exists, no `undefined`.
- `/vue/app/interview` mobile around 390px: no horizontal overflow.
- `/vue/app/admin` desktop: shows “Agent 工作流观测”, node trace, RAG node summary, checkpoint, fallback / quality gate summary.
- `/vue/app/admin` mobile around 390px: no horizontal overflow.

- [ ] **Step 6: Archive docs**

Update `docs/roadmap/current-state.md`:

```text
LangGraph Mainline Consolidation V7 已完成：/api/interview/next-question 默认走 LangGraph mainline，classic Agent 降级为 fallback/helper，管理员后台显示 Agent 工作流观测。
```

Update `docs/specs/README.md` and `docs/plans/README.md` to say active spec/plan are empty and latest completed docs are:

```text
docs/specs/completed/langgraph-mainline-consolidation-v7-design.md
docs/plans/completed/langgraph-mainline-consolidation-v7.md
```

Move active docs to completed paths.

- [ ] **Step 7: Final git commit**

Run:

```powershell
git status --short
git add backend_python tests frontend docs
git commit -m "feat: consolidate langgraph mainline"
```

Expected: commit succeeds and worktree is clean.

---

## Self-Review Checklist

- Spec coverage: This plan covers default LangGraph mainline, classic fallback, route compatibility, RAG node reuse, logs, checkpoint, frontend interview display, admin workflow observation, tests, browser verification and docs archival.
- Scope control: This plan does not rewrite BM25, hybrid search, rerank, RAG document management, ingestion tasks, Docker/Nginx/VPS, OCR, Word/Excel/web parsing, Qdrant or pgvector.
- Compatibility: `/api/interview/next-question` path remains unchanged. `QuestionResponse` gains only optional fields.
- Frontend coverage: `/vue/app/interview` and `/vue/app/admin` are both explicitly covered.
- Risk control: classic Agent remains as fallback/helper and is not deleted.
