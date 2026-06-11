# Agent Engineering V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the AI interview system Agent into a traceable, testable, lightweight orchestrator workflow while preserving `/api/interview/next-question` compatibility.

**Architecture:** Keep the current self-built Agent and split responsibilities gradually. Add stable Agent State and Trace data structures first, then wrap RAG and answer-analysis capabilities as lightweight tools, then move route-level orchestration into an Agent orchestrator module, and finally expose the richer trace in the existing frontend debug panels.

**Tech Stack:** Python 3, FastAPI, pytest, plain JavaScript frontend tests with `.mjs`; no LangGraph, no LangChain, no Docker/Nginx/cloud deployment in this stage.

---

## File Structure

- Create `backend_python/agent_state.py`
  - Owns Agent state schema construction, session states, and event constants.
  - Produces JSON-serializable dictionaries only.

- Create `backend_python/agent_trace.py`
  - Owns node trace and tool call summary builders.
  - Provides safe summary helpers that avoid storing long resume/JD/answer text.

- Create `backend_python/agent_tools.py`
  - Wraps current RAG retrieval and answer-analysis capabilities into lightweight Agent Tool calls.
  - Returns a consistent structure for success, failure, elapsed time, input summary, and output summary.

- Create `backend_python/agent_orchestrator.py`
  - Owns high-level `run_next_question_agent(...)` workflow.
  - Gradually pulls orchestration out of `backend_python/routes/interview.py`.

- Modify `backend_python/interview_agent.py`
  - Keep decision, fallback, and normalization logic.
  - Reuse new state/trace helpers instead of building every structure inline.

- Modify `backend_python/routes/interview.py`
  - Keep HTTP request/response, auth, and database dependencies.
  - Delegate Agent workflow to `agent_orchestrator.py` once that module is ready.

- Create or modify tests:
  - `tests/test_agent_state.py`
  - `tests/test_agent_trace.py`
  - `tests/test_agent_tools.py`
  - `tests/test_agent_orchestrator.py`
  - `tests/frontend_agent_logs.test.mjs`

---

### Task 1: Agent State And Trace Foundations

**Files:**
- Create: `backend_python/agent_state.py`
- Create: `backend_python/agent_trace.py`
- Create: `tests/test_agent_state.py`
- Create: `tests/test_agent_trace.py`
- Modify: `backend_python/interview_agent.py`

- [x] **Step 1: Write failing Agent State tests**

Create `tests/test_agent_state.py` with tests that prove:

```python
import json

from backend_python.agent_state import (
    AGENT_EVENTS,
    AGENT_SESSION_STATES,
    build_interview_agent_state,
)


def test_build_interview_agent_state_is_json_serializable():
    state = build_interview_agent_state(
        profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 项目", "jd": "熟悉 Agent"},
        history=[{"question": "什么是 RAG？", "answer": "不知道", "focus": "RAG 基础"}],
        next_stage="技术追问",
        role_quality={"level": "good", "hitCount": 3},
        question_quality={"level": "weak", "hitCount": 1},
        memory_quality={"level": "miss", "hitCount": 0},
        max_rounds=8,
        agent_mode="coach",
    )

    json.dumps(state, ensure_ascii=False)
    assert state["session"]["agentMode"] == "coach"
    assert state["session"]["roundCount"] == 1
    assert state["session"]["remainingRounds"] == 7
    assert state["lastAnswer"]["answer"] == "不知道"
    assert state["retrievalQuality"]["roleKnowledge"]["hitCount"] == 3
    assert "observe_state" in state["agentNodes"]


def test_build_interview_agent_state_normalizes_invalid_mode():
    state = build_interview_agent_state(
        profile={},
        history=[],
        next_stage="综合追问",
        role_quality={},
        question_quality={},
        memory_quality={},
        agent_mode="bad-mode",
    )

    assert state["session"]["agentMode"] == "interview"


def test_agent_state_constants_define_state_machine_vocabulary():
    assert "waiting_answer" in AGENT_SESSION_STATES
    assert "ANSWER_SUBMITTED" in AGENT_EVENTS
```

- [x] **Step 2: Run Agent State tests and confirm they fail**

Run:

```powershell
python -m pytest tests/test_agent_state.py -q
```

Expected result: fail because `backend_python.agent_state` does not exist yet.

- [x] **Step 3: Implement minimal Agent State module**

Create `backend_python/agent_state.py` with:

```python
from typing import Any

from .interview_agent import classify_answer_status, analyze_answer_history, normalize_agent_mode

AGENT_SESSION_STATES = (
    "idle",
    "collecting_profile",
    "ready",
    "asking",
    "waiting_answer",
    "analyzing_answer",
    "retrieving_context",
    "deciding_next_action",
    "generating_question",
    "updating_memory",
    "generating_report",
    "completed",
    "failed",
)

AGENT_EVENTS = (
    "START_INTERVIEW",
    "PROFILE_READY",
    "QUESTION_GENERATED",
    "ANSWER_SUBMITTED",
    "ANSWER_ANALYZED",
    "CONTEXT_RETRIEVED",
    "DECISION_SELECTED",
    "MEMORY_UPDATED",
    "REPORT_REQUESTED",
    "REPORT_GENERATED",
    "ERROR_OCCURRED",
    "RESET_SESSION",
)

AGENT_NODES = (
    "observe_state",
    "retrieve_context",
    "analyze_answer",
    "select_action",
    "generate_question",
    "update_memory",
    "write_trace",
)


def build_interview_agent_state(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    role_quality: dict[str, Any],
    question_quality: dict[str, Any],
    memory_quality: dict[str, Any],
    max_rounds: int = 8,
    agent_mode: str = "interview",
) -> dict[str, Any]:
    safe_history = list(history or [])
    last_answer = safe_history[-1] if safe_history else {}
    round_count = len(safe_history)
    mode = normalize_agent_mode(agent_mode)
    answer_status = classify_answer_status(str(last_answer.get("answer") or ""))
    answer_analysis = analyze_answer_history(safe_history)

    return {
        "session": {
            "applicationProfileId": profile.get("applicationProfileId"),
            "agentMode": mode,
            "nextStage": str(next_stage or "综合追问"),
            "roundCount": round_count,
            "remainingRounds": max(max_rounds - round_count, 0),
        },
        "profile": dict(profile or {}),
        "history": safe_history,
        "agentMode": mode,
        "nextStage": str(next_stage or "综合追问"),
        "lastAnswer": last_answer,
        "askedQuestions": [str(item.get("question") or "") for item in safe_history if item.get("question")],
        "roundCount": round_count,
        "remainingRounds": max(max_rounds - round_count, 0),
        "answerStatus": answer_status,
        "answerAnalysis": answer_analysis,
        "retrievalQuality": {
            "roleKnowledge": dict(role_quality or {}),
            "questionBank": dict(question_quality or {}),
            "candidateMemory": dict(memory_quality or {}),
        },
        "agentNodes": list(AGENT_NODES),
        "nodeTrace": [],
        "toolCalls": [],
    }
```

- [x] **Step 4: Write failing Agent Trace tests**

Create `tests/test_agent_trace.py` with tests that prove:

```python
import json

from backend_python.agent_trace import build_node_trace, build_tool_call_summary, summarize_text


def test_build_node_trace_records_node_input_output_and_fallback():
    trace = build_node_trace(
        node_name="select_action",
        input_summary={"answerStatus": "不会", "remainingRounds": 5},
        output_summary={"nextAction": "lower_difficulty", "difficulty": "basic"},
        fallback_used=True,
        elapsed_ms=12,
    )

    json.dumps(trace, ensure_ascii=False)
    assert trace["nodeName"] == "select_action"
    assert trace["fallbackUsed"] is True
    assert trace["elapsedMs"] == 12
    assert trace["error"] == ""


def test_build_tool_call_summary_records_success_and_error():
    ok = build_tool_call_summary(
        tool_name="retrieve_question_bank",
        input_summary={"query": "RAG", "limit": 4},
        output_summary={"hitCount": 2, "topScores": [0.91, 0.82]},
        success=True,
        elapsed_ms=8,
    )
    failed = build_tool_call_summary(
        tool_name="retrieve_role_knowledge",
        input_summary={"query": "Agent"},
        output_summary={},
        success=False,
        error="timeout",
        elapsed_ms=1000,
    )

    assert ok["success"] is True
    assert failed["success"] is False
    assert failed["error"] == "timeout"


def test_summarize_text_limits_long_sensitive_text():
    text = "A" * 300
    summary = summarize_text(text, limit=40)

    assert len(summary) <= 41
    assert summary.endswith("…")
```

- [x] **Step 5: Run Agent Trace tests and confirm they fail**

Run:

```powershell
python -m pytest tests/test_agent_trace.py -q
```

Expected result: fail because `backend_python.agent_trace` does not exist yet.

- [x] **Step 6: Implement minimal Agent Trace module**

Create `backend_python/agent_trace.py` with:

```python
from typing import Any


def summarize_text(value: Any, *, limit: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def build_node_trace(
    *,
    node_name: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    fallback_used: bool = False,
    elapsed_ms: int = 0,
    error: str = "",
) -> dict[str, Any]:
    return {
        "nodeName": str(node_name),
        "inputSummary": dict(input_summary or {}),
        "outputSummary": dict(output_summary or {}),
        "fallbackUsed": bool(fallback_used),
        "elapsedMs": max(int(elapsed_ms or 0), 0),
        "error": str(error or ""),
    }


def build_tool_call_summary(
    *,
    tool_name: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    success: bool = True,
    error: str = "",
    elapsed_ms: int = 0,
) -> dict[str, Any]:
    return {
        "toolName": str(tool_name),
        "inputSummary": dict(input_summary or {}),
        "outputSummary": dict(output_summary or {}),
        "success": bool(success),
        "error": str(error or ""),
        "elapsedMs": max(int(elapsed_ms or 0), 0),
    }
```

- [x] **Step 7: Integrate Agent State helper without breaking old callers**

Modify `backend_python/interview_agent.py` so `build_agent_state(...)` computes retrieval quality as it does today, then delegates final shape to `build_interview_agent_state(...)`. Preserve existing top-level fields such as `agentMode`, `roundCount`, `remainingRounds`, `answerStatus`, and `retrievalQuality`.

- [x] **Step 8: Run focused backend tests**

Run:

```powershell
python -m pytest tests/test_agent_state.py tests/test_agent_trace.py tests/test_interview_agent.py -q
```

Expected result: all focused tests pass.

---

### Task 2: Lightweight Agent Tool Abstraction

**Files:**
- Create: `backend_python/agent_tools.py`
- Create: `tests/test_agent_tools.py`
- Modify: `backend_python/routes/interview.py` only if needed for integration

- [x] **Step 1: Write failing tool tests**

Create tests that verify:

- successful tool calls return `toolName`, `inputSummary`, `outputSummary`, `success=True`, `error=""`, `elapsedMs>=0`.
- empty retrieval returns `hitCount=0` and still counts as success.
- exceptions return `success=False`, `error` text, and do not crash the caller.

- [x] **Step 2: Implement tool wrapper**

Create a generic helper `run_agent_tool(tool_name, input_summary, fn)` that times the call, catches errors, and returns both `result` and `toolCall`.

- [x] **Step 3: Add RAG-specific wrappers**

Add wrappers named:

- `retrieve_role_knowledge_tool`
- `retrieve_question_bank_tool`
- `retrieve_candidate_memory_tool`

Each wrapper should call the existing retrieval function passed into it, not import database-heavy route code.

- [x] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_agent_tools.py -q
```

Expected result: pass.

---

### Task 3: Agent Orchestrator Extraction

**Files:**
- Create: `backend_python/agent_orchestrator.py`
- Create: `tests/test_agent_orchestrator.py`
- Modify: `backend_python/routes/interview.py`

- [x] **Step 1: Write failing orchestrator tests**

Tests must verify that `run_next_question_agent(...)` returns:

- `agentState`
- `agentDecision`
- `nodeTrace`
- `toolCalls`
- the next question text or enough data for route code to generate it

- [x] **Step 2: Implement orchestrator as a thin workflow**

Start with the existing route behavior and move only the Agent workflow into `agent_orchestrator.py`.

- [x] **Step 3: Preserve route compatibility**

`/api/interview/next-question` must still return existing fields already consumed by `app.js`, including `question`, `agentDecision` or `decisionSummary` if currently present.

- [x] **Step 4: Run route compatibility tests**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py -q
```

Expected result: pass.

---

### Task 4: Agent Debug Display Enhancement

**Files:**
- Modify: `app.js`
- Modify: `styles.css` only for display polish if necessary
- Modify: `tests/frontend_agent_logs.test.mjs`

- [x] **Step 1: Update frontend tests first**

Add assertions that the Agent log/debug rendering can display:

- `triggerRules`
- `nodeTrace`
- `toolCalls`
- fallback status

- [x] **Step 2: Implement minimal rendering**

Show ordinary users a short “为什么这么问” summary, and keep raw `nodeTrace` / `toolCalls` in the existing debug panel.

- [x] **Step 3: Run frontend tests**

Run:

```powershell
node tests/frontend_agent_logs.test.mjs
```

Expected result: pass.

---

### Task 5: Full Verification

**Files:**
- No new files expected.

- [x] **Step 1: Run all backend tests**

Run:

```powershell
python -m pytest -q
```

Expected result: all tests pass.

- [x] **Step 2: Run all frontend `.mjs` tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected result: all scripts pass.

- [x] **Step 3: Manual compatibility check**

Open [http://localhost:8000/](http://localhost:8000/) and complete at least one next-question flow. Verify:

- the page still receives a question.
- Agent mode still works.
- Agent log/debug panel can explain the decision path.

---

## Self-Review

- Spec coverage: This plan covers Agent State, Agent Trace, Tool abstraction, Orchestrator split, frontend debug display, compatibility, and verification.
- Scope control: This plan does not introduce LangGraph, LangChain, Docker, Nginx, cloud deployment, frontend framework migration, or a large RAG algorithm rewrite.
- TDD: Every implementation task starts with focused tests before code changes.
- Compatibility: Route behavior is explicitly protected by existing route tests and full backend/frontend verification.
