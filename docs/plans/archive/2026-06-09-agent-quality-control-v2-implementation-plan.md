# Agent Quality Control V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Agent 质量控制 V2 so the interview Agent can detect weak-answer streaks, topic lock, repeated questions, and apply guardrails without breaking `/api/interview/next-question`.

**Architecture:** Keep the current self-built FastAPI Agent architecture. Strengthen state analysis in `agent_state.py` / `interview_agent.py`, then use decision guardrails to correct unsafe model decisions, and finally verify the route and log payloads still expose compatible fields.

**Tech Stack:** Python, FastAPI, pytest, current backend Agent modules only. No LangGraph, no LangChain, no Docker/Nginx/cloud work.

---

## File Structure

- Modify `backend_python/agent_state.py`
  - Owns reusable state analysis helpers and `build_interview_agent_state`.
  - Add topic-lock analysis while keeping existing top-level state fields.

- Modify `backend_python/interview_agent.py`
  - Owns Agent decision, fallback, normalization, model-decision guardrail.
  - Keep `/api/interview/next-question` compatible by preserving existing decision keys.

- Modify `backend_python/agent_orchestrator.py`
  - Only if needed to pass enriched state/decision through existing orchestration output.

- Modify `backend_python/routes/interview.py`
  - Only in the route/logging round, after state and decision tests pass.

- Modify tests:
  - `tests/test_agent_state.py`
  - `tests/test_interview_agent.py`
  - `tests/test_agent_orchestrator.py`
  - `tests/test_interview_agent_route.py`

---

## Task 1: State Analysis - Topic Lock

**Files:**
- Modify: `backend_python/agent_state.py`
- Modify: `backend_python/interview_agent.py`
- Test: `tests/test_agent_state.py`
- Test: `tests/test_interview_agent.py`

- [ ] **Step 1: Write failing state tests**

Add tests showing that recent repeated focus values produce `topicLock`.

```python
def test_build_interview_agent_state_detects_topic_lock_from_recent_focuses():
    state = build_interview_agent_state(
        profile={},
        history=[
            {"question": "请解释 RAG 日志字段", "answer": "不知道", "focus": "RAG 日志 JSON"},
            {"question": "query_text 怎么写", "answer": "不会", "focus": "RAG 日志 JSON"},
            {"question": "hits_json 怎么写", "answer": "写不出来", "focus": "RAG 日志 JSON"},
        ],
        next_stage="技术追问",
        role_quality={},
        question_quality={},
        memory_quality={},
        agent_mode="coach",
    )

    topic_lock = state["answerAnalysis"]["topicLock"]
    assert topic_lock["locked"] is True
    assert topic_lock["topic"] == "RAG 日志 JSON"
    assert topic_lock["count"] == 3
    assert "topic_lock_guardrail" in state["answerAnalysis"]["triggerSignals"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_agent_state.py tests/test_interview_agent.py -q
```

Expected: failure because `topicLock` is not present.

- [ ] **Step 3: Implement minimal topic-lock analysis**

Add helper logic to inspect the latest 3 history items. Prefer `focus`; fallback to normalized question text.

Expected shape:

```python
{
    "locked": True,
    "topic": "RAG 日志 JSON",
    "count": 3
}
```

If no lock:

```python
{
    "locked": False,
    "topic": "",
    "count": 0
}
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/test_agent_state.py tests/test_interview_agent.py -q
```

Expected: pass.

---

## Task 2: Decision Guardrail - Prevent Unsafe Raise Difficulty

**Files:**
- Modify: `backend_python/interview_agent.py`
- Test: `tests/test_interview_agent.py`

- [ ] **Step 1: Write failing guardrail tests**

Add tests showing that when state says the user is stuck, model output cannot raise difficulty.

```python
def test_normalize_agent_decision_applies_guardrail_when_model_raises_difficulty_during_topic_lock():
    fallback = {
        "nextAction": "switch_topic",
        "stage": "技术追问",
        "difficulty": "basic",
        "focus": "RAG 可观测性设计",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
        "triggerRules": ["topic_lock_guardrail"],
        "agentMode": "coach",
    }
    state = {
        "answerStatus": "不会",
        "answerAnalysis": {
            "weakAnswerStreak": 3,
            "repeatedQuestionCount": 0,
            "topicLock": {"locked": True, "topic": "RAG 日志 JSON", "count": 3},
            "triggerSignals": ["weak_answer_streak", "topic_lock_guardrail"],
        },
    }

    decision = normalize_agent_decision(
        {
            "nextAction": "raise_difficulty",
            "stage": "技术追问",
            "difficulty": "hard",
            "focus": "RAG 日志 JSON",
            "reason": "继续深挖",
            "tools": ["retrieve_context"],
            "shouldUpdateMemory": True,
        },
        fallback,
        state=state,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["guardrailApplied"] is True
    assert "topic_lock_guardrail" in decision["triggerRules"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_interview_agent.py -q
```

Expected: failure because `normalize_agent_decision` does not accept `state`.

- [ ] **Step 3: Implement guardrail**

Update `normalize_agent_decision(raw, fallback, state=None)` to:

- Preserve existing behavior when `state` is not passed.
- If `weakAnswerStreak >= 3` or `topicLock.locked is True`, prevent `raise_difficulty`.
- Replace unsafe decision with fallback-like `switch_topic` decision.
- Add `guardrailApplied: True`.

- [ ] **Step 4: Update `decide_next_action`**

Pass `state=state` into `normalize_agent_decision`.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_interview_agent.py -q
```

Expected: pass.

---

## Task 3: Decision Metadata and Logging Compatibility

**Files:**
- Modify: `backend_python/interview_agent.py`
- Modify: `backend_python/agent_orchestrator.py`
- Test: `tests/test_agent_orchestrator.py`
- Test: `tests/test_agent_logging.py`

- [ ] **Step 1: Write tests for decision metadata**

Assert every decision contains:

```python
assert "guardrailApplied" in decision
assert "triggerRules" in decision
assert "decisionSummary" in decision
```

- [ ] **Step 2: Ensure fallback and valid model decisions include metadata**

Fallback decisions should default:

```python
"guardrailApplied": False
```

Guardrail-corrected decisions should use:

```python
"guardrailApplied": True
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_agent_logging.py -q
```

Expected: pass.

---

## Task 4: Route Integration

**Files:**
- Modify: `backend_python/routes/interview.py`
- Test: `tests/test_interview_agent_route.py`

- [ ] **Step 1: Add or update route test**

Verify repeated-topic history returns a compatible response:

```python
assert "prompt" in body
assert "agentDecision" in body
assert "triggerRules" in body["agentDecision"]
assert "guardrailApplied" in body["agentDecision"]
```

- [ ] **Step 2: Ensure route does not require frontend changes**

Do not rename existing response keys:

```text
stage
focus
prompt
agentDecision
decisionSummary
```

- [ ] **Step 3: Run route tests**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py -q
```

Expected: pass.

---

## Task 5: Full Verification

**Files:**
- No feature files unless previous tests reveal a compatibility issue.

- [ ] **Step 1: Run full backend tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: no error output.

- [ ] **Step 3: Clean test caches**

Remove `.pytest_cache` and `__pycache__` directories inside the workspace only.

---

## Self-Review

- Spec coverage: covers state analysis, topic lock, weak-answer streak, decision guardrail, route compatibility, logs, and test-driven implementation.
- Scope check: does not introduce LangGraph, LangChain, Docker, Nginx, cloud deployment, frontend rewrite, or database table changes.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: `topicLock`, `guardrailApplied`, `triggerRules`, `decisionSummary`, and existing Agent keys are used consistently.

