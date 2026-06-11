# Interview Orchestrator Agent V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 AI 模拟面试流程中加入轻量 Agent 决策层，使系统能根据面试状态动态决定追问、换题、降难度、升难度或结束面试。

**Architecture:** 新增 `backend_python/interview_agent.py` 封装 Agent State、Decision、fallback 规则和模型决策归一化；新增 Agent 决策日志表；在 `/api/interview/next-question` 中接入 Agent 服务，并保留旧流程作为失败降级。

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite, pytest, DashScope-compatible LLM call.

---

## File Structure

- Add: `backend_python/interview_agent.py`
  - Agent State 构建
  - Answer status 分析
  - fallback decision
  - decision normalize
  - prompt payload 构建
- Modify: `backend_python/db_models.py`
  - 新增 `AgentDecisionLog`
- Modify: `backend_python/database.py`
  - SQLite 自动建表/补兼容
- Add: `alembic/versions/20260606_0008_add_agent_decision_logs.py`
  - 迁移脚本
- Add: `backend_python/agent_logging.py`
  - 写入和序列化 Agent 日志
- Modify: `backend_python/routes/interview.py`
  - `/next-question` 接入 Agent
- Add: `tests/test_interview_agent.py`
  - Agent state、decision、fallback 测试
- Add: `tests/test_agent_logging.py`
  - Agent 决策日志测试
- Modify: `tests/test_rag_retrieval_logs.py`
  - next-question 仍能写 RAG 日志并返回问题

## Task 1: Agent State and Decision Basics

**Files:**
- Add: `backend_python/interview_agent.py`
- Add: `tests/test_interview_agent.py`

- [ ] Write failing tests for Agent state and fallback decision.

```python
from backend_python.interview_agent import build_agent_state, build_fallback_decision


def test_build_agent_state_extracts_round_and_last_answer() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[
            {"question": "什么是 RAG？", "answer": "不知道"},
        ],
        next_stage="技术追问",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
    )

    assert state["roundCount"] == 1
    assert state["lastAnswer"]["answer"] == "不知道"
    assert state["askedQuestions"] == ["什么是 RAG？"]
    assert state["answerStatus"] == "不会"


def test_build_fallback_decision_lowers_difficulty_for_weak_answer() -> None:
    state = {
        "nextStage": "技术追问",
        "answerStatus": "不会",
        "remainingRounds": 5,
    }

    decision = build_fallback_decision(state)

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["difficulty"] == "basic"
    assert "retrieve_context" in decision["tools"]
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_interview_agent.py::test_build_agent_state_extracts_round_and_last_answer tests/test_interview_agent.py::test_build_fallback_decision_lowers_difficulty_for_weak_answer -q
```

Expected: missing `backend_python.interview_agent`.

- [ ] Implement minimal Agent state and fallback decision.

```python
from typing import Any

from .rag_quality import evaluate_retrieval_quality

WEAK_ANSWER_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")
ALLOWED_ACTIONS = {
    "deep_follow_up",
    "switch_topic",
    "lower_difficulty",
    "raise_difficulty",
    "summarize_feedback",
    "finish_interview",
}
ALLOWED_DIFFICULTIES = {"basic", "medium", "hard"}
ALLOWED_TOOLS = {"retrieve_context", "analyze_answer", "select_action", "generate_question", "update_memory"}


def classify_answer_status(answer_text: str) -> str:
    text = str(answer_text or "").strip()
    if not text:
        return "不会"
    if any(marker in text for marker in WEAK_ANSWER_MARKERS):
        return "不会"
    if len(text) < 24:
        return "模糊"
    return "完整"


def build_agent_state(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    max_rounds: int = 8,
) -> dict[str, Any]:
    last_answer = history[-1] if history else {}
    round_count = len(history)
    return {
        "profile": profile,
        "history": history,
        "nextStage": next_stage,
        "lastAnswer": last_answer,
        "askedQuestions": [str(item.get("question") or "") for item in history if item.get("question")],
        "roundCount": round_count,
        "remainingRounds": max(max_rounds - round_count, 0),
        "answerStatus": classify_answer_status(str(last_answer.get("answer") or "")),
        "retrievalQuality": {
            "roleKnowledge": evaluate_retrieval_quality(role_hits),
            "questionBank": evaluate_retrieval_quality(question_hits),
            "candidateMemory": evaluate_retrieval_quality(memory_hits),
        },
    }


def build_fallback_decision(state: dict[str, Any]) -> dict[str, Any]:
    if int(state.get("remainingRounds") or 0) <= 0:
        action = "finish_interview"
        difficulty = "medium"
    elif state.get("answerStatus") == "不会":
        action = "lower_difficulty"
        difficulty = "basic"
    elif state.get("answerStatus") == "完整":
        action = "deep_follow_up"
        difficulty = "hard"
    else:
        action = "deep_follow_up"
        difficulty = "medium"
    return {
        "nextAction": action,
        "stage": state.get("nextStage") or "综合追问",
        "difficulty": difficulty,
        "focus": state.get("nextStage") or "综合能力",
        "reason": "基于回答质量、剩余轮次和 RAG 命中质量生成的兜底决策。",
        "tools": ["retrieve_context", "analyze_answer", "generate_question"],
        "shouldUpdateMemory": True,
        "fallbackUsed": True,
    }
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_interview_agent.py -q
```

Expected: Agent basics tests pass.

## Task 2: Decision Normalization

**Files:**
- Modify: `backend_python/interview_agent.py`
- Modify: `tests/test_interview_agent.py`

- [ ] Write failing tests for decision normalization.

```python
from backend_python.interview_agent import normalize_agent_decision


def test_normalize_agent_decision_accepts_valid_model_decision() -> None:
    fallback = {
        "nextAction": "deep_follow_up",
        "stage": "技术追问",
        "difficulty": "medium",
        "focus": "RAG",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
    }
    decision = normalize_agent_decision(
        {
            "nextAction": "switch_topic",
            "stage": "项目经历",
            "difficulty": "basic",
            "focus": "FastAPI 模块化",
            "reason": "避免重复卡在 RAG 日志",
            "tools": ["retrieve_context", "generate_question", "bad_tool"],
            "shouldUpdateMemory": False,
        },
        fallback,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["tools"] == ["retrieve_context", "generate_question"]
    assert decision["fallbackUsed"] is False


def test_normalize_agent_decision_uses_fallback_for_invalid_action() -> None:
    fallback = {
        "nextAction": "lower_difficulty",
        "stage": "技术追问",
        "difficulty": "basic",
        "focus": "RAG",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
    }

    decision = normalize_agent_decision({"nextAction": "unknown"}, fallback)

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["fallbackUsed"] is True
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_interview_agent.py::test_normalize_agent_decision_accepts_valid_model_decision tests/test_interview_agent.py::test_normalize_agent_decision_uses_fallback_for_invalid_action -q
```

Expected: missing `normalize_agent_decision`.

- [ ] Implement decision normalization.

```python
def normalize_agent_decision(raw: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("nextAction") not in ALLOWED_ACTIONS:
        return {**fallback, "fallbackUsed": True}
    difficulty = str(raw.get("difficulty") or fallback.get("difficulty") or "medium")
    if difficulty not in ALLOWED_DIFFICULTIES:
        difficulty = str(fallback.get("difficulty") or "medium")
    tools = [str(tool) for tool in raw.get("tools") or [] if str(tool) in ALLOWED_TOOLS]
    return {
        "nextAction": raw["nextAction"],
        "stage": str(raw.get("stage") or fallback.get("stage") or "综合追问"),
        "difficulty": difficulty,
        "focus": str(raw.get("focus") or fallback.get("focus") or "综合能力"),
        "reason": str(raw.get("reason") or fallback.get("reason") or ""),
        "tools": tools or list(fallback.get("tools") or []),
        "shouldUpdateMemory": bool(raw.get("shouldUpdateMemory", fallback.get("shouldUpdateMemory", True))),
        "fallbackUsed": False,
    }
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_interview_agent.py -q
```

Expected: decision normalization tests pass.

## Task 3: Agent Decision Logs

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Add: `alembic/versions/20260606_0008_add_agent_decision_logs.py`
- Add: `backend_python/agent_logging.py`
- Add: `tests/test_agent_logging.py`
- Modify: `tests/test_database_migrations.py`

- [ ] Write failing tests for model fields and log creation.

```python
from backend_python.agent_logging import create_agent_decision_log, serialize_agent_decision_log
from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, User


def test_agent_decision_log_model_declares_expected_columns() -> None:
    columns = AgentDecisionLog.__table__.columns

    assert "next_action" in columns
    assert "decision_json" in columns
    assert "fallback_used" in columns


def test_create_agent_decision_log_persists_decision() -> None:
    with SessionLocal() as db:
        user = User(email="agent-log@example.com", username="agent_log", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        log = create_agent_decision_log(
            db,
            user_id=user.id,
            application_profile_id=None,
            request_type="next_question",
            state={"roundCount": 1},
            decision={"nextAction": "lower_difficulty", "difficulty": "basic", "focus": "RAG", "reason": "test", "tools": []},
            fallback_used=True,
        )
        data = serialize_agent_decision_log(log)

    assert data["nextAction"] == "lower_difficulty"
    assert data["fallbackUsed"] is True
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_agent_logging.py::test_agent_decision_log_model_declares_expected_columns tests/test_agent_logging.py::test_create_agent_decision_log_persists_decision -q
```

Expected: missing `AgentDecisionLog` or `agent_logging`.

- [ ] Implement model, SQLite compatibility, migration, logging helpers.

Core model:

```python
class AgentDecisionLog(Base):
    __tablename__ = "agent_decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(50), index=True)
    next_action: Mapped[str] = mapped_column(String(50), index=True)
    stage: Mapped[str] = mapped_column(String(100), default="")
    difficulty: Mapped[str] = mapped_column(String(50), default="")
    focus: Mapped[str] = mapped_column(String(200), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    decision_json: Mapped[str] = mapped_column(Text, default="{}")
    fallback_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_agent_logging.py tests/test_database_migrations.py -q
```

Expected: Agent logging and migration tests pass.

## Task 4: Agent Service Model Decision

**Files:**
- Modify: `backend_python/interview_agent.py`
- Modify: `tests/test_interview_agent.py`

- [ ] Write failing test for model decision service.

```python
from backend_python.interview_agent import decide_next_action


async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
    return {
        "nextAction": "lower_difficulty",
        "stage": "技术追问",
        "difficulty": "basic",
        "focus": "RAG 日志字段",
        "reason": "候选人回答不知道",
        "tools": ["retrieve_context", "generate_question"],
        "shouldUpdateMemory": True,
    }


def test_decide_next_action_uses_model_decision_when_valid() -> None:
    import asyncio

    state = {"nextStage": "技术追问", "answerStatus": "不会", "remainingRounds": 5}
    decision = asyncio.run(decide_next_action(state, call_model_fn=fake_call_model))

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["fallbackUsed"] is False
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_interview_agent.py::test_decide_next_action_uses_model_decision_when_valid -q
```

Expected: missing `decide_next_action`.

- [ ] Implement model decision service.

```python
import json


AGENT_SYSTEM_PROMPT = "你是 AI 模拟面试流程调度 Agent。请只输出结构化 JSON。"


async def decide_next_action(state: dict[str, Any], *, call_model_fn) -> dict[str, Any]:
    fallback = build_fallback_decision(state)
    try:
        result = await call_model_fn(
            temperature=0.2,
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"state": state, "fallbackDecision": fallback}, ensure_ascii=False)},
            ],
        )
        return normalize_agent_decision(result, fallback)
    except Exception:
        return {**fallback, "fallbackUsed": True}
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_interview_agent.py -q
```

Expected: Agent service tests pass.

## Task 5: Integrate Agent Into Next Question

**Files:**
- Modify: `backend_python/routes/interview.py`
- Modify: `tests/test_rag_retrieval_logs.py`
- Add or modify: `tests/test_interview_agent_route.py`

- [ ] Write failing test that next-question writes Agent decision log.

```python
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog
from backend_python.main import app


def test_next_question_writes_agent_decision_log(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 日志字段",
                "reason": "候选人回答不知道",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 日志字段",
            "prompt": "我们先降低难度：RAG 命中日志通常记录哪些字段？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    client.post("/api/auth/register", json={"email": f"agent-{suffix}@example.com", "username": f"agent_{suffix[:8]}", "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": f"agent-{suffix}@example.com", "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [{"question": "RAG 日志怎么写？", "answer": "不知道"}],
            "nextStage": "技术追问",
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        logs = db.scalars(select(AgentDecisionLog).order_by(AgentDecisionLog.id.desc()).limit(1)).all()
    assert logs
    assert logs[0].next_action == "lower_difficulty"
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_interview_agent_route.py::test_next_question_writes_agent_decision_log -q
```

Expected: no Agent log written.

- [ ] Integrate Agent in `next_question`.

Pseudo steps:

```python
from ..agent_logging import create_agent_decision_log
from ..interview_agent import build_agent_state, decide_next_action
```

After RAG hits are ready:

```python
agent_state = build_agent_state(...)
agent_decision = await decide_next_action(agent_state, call_model_fn=call_model)
create_agent_decision_log(...)
```

Add `agentDecision` to user payload:

```python
"agentDecision": agent_decision
```

Use decision fields as fallback in response:

```python
"stage": result.get("stage") or agent_decision["stage"]
"focus": result.get("focus") or agent_decision["focus"]
"stability": result.get("stability") or f"Agent:{agent_decision['nextAction']}"
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_interview_agent_route.py tests/test_rag_retrieval_logs.py -q
```

Expected: next-question still returns question, RAG logs and Agent logs both written.

## Task 6: Verification

- [ ] Run focused tests.

```powershell
python -m pytest tests/test_interview_agent.py tests/test_agent_logging.py tests/test_interview_agent_route.py tests/test_rag_retrieval_logs.py -q
```

Expected: focused Agent tests pass.

- [ ] Run full backend tests.

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] Run frontend smoke checks.

```powershell
node tests/frontend_rag_documents.test.mjs
node tests/frontend_rag_logs.test.mjs
node --check app.js
```

Expected: each command exits with code 0.

## Self-Review

- Spec coverage: Agent State、Decision、Tools、日志、路由集成、失败降级都有任务覆盖。
- Scope check: V1 不引入 Agent 框架、不做多 Agent、不做前端可视化。
- Type consistency: Action 使用 `deep_follow_up` 等 snake_case；API 返回仍沿用现有 `QuestionResponse`。
- Testing discipline: 每个行为先写失败测试，再实现。

