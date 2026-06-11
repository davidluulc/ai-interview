# Candidate Weakness Driven Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `candidateProfile.frequentWeakTags` enter Agent State, produce a `weaknessStrategy`, influence coach/interview decision behavior, and appear in Agent logs/nodeTrace without breaking `/api/interview/next-question`.

**Architecture:** Add a focused `backend_python/weakness_strategy.py` module for weak-tag strategy selection. Keep candidate memory aggregation in `candidate_memory.py`, keep state and fallback decision wiring in `interview_agent.py`, and keep orchestration/nodeTrace wiring in `agent_orchestrator.py`. Route compatibility is preserved by placing new data inside existing `agentDecision`, `debugSignals`, and `state_json`/`decision_json`.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, existing plain JavaScript frontend tests only if frontend rendering changes.

---

## File Structure

- Create: `backend_python/weakness_strategy.py`
  - Owns weak-tag normalization, tag-to-focus labels, strategy selection, mode policies, and anti-deadlock detection.
- Create: `tests/test_weakness_strategy.py`
  - Unit tests for coach/interview strategy behavior and anti-deadlock rules.
- Modify: `backend_python/interview_agent.py`
  - Build candidate profile from `memory_hits`, attach `candidateProfile` and `weaknessStrategy` to Agent State, and merge strategy into fallback/normalized decisions.
- Modify: `backend_python/agent_orchestrator.py`
  - Add `select_weakness_strategy` nodeTrace between `retrieve_context` and `select_action`.
- Modify: `backend_python/routes/interview.py`
  - Pass `weaknessStrategy` into question-generation payload via existing `agentDecision` and log state/decision as usual.
- Modify: `tests/test_interview_agent.py`
  - Verify Agent State and fallback/normalize behavior.
- Modify: `tests/test_agent_orchestrator.py`
  - Verify nodeTrace includes `select_weakness_strategy` and decision contains strategy.
- Modify: `tests/test_interview_agent_route.py`
  - Verify `/api/interview/next-question` sees historical weak tags, writes strategy to response and `AgentDecisionLog`.
- Create: `docs/learning/07-候选人画像如何驱动Agent决策.md`
  - Chinese learning document explaining weakTags, frequentWeakTags, Agent State, coach/interview policies, guardrails, and interview phrasing.
- Modify: `docs/pre-deployment-progress.md`
  - Record stage completion, tests, risks, and next step.

No git commit is included because this worktree already has many user/project changes and the user did not request a commit.

---

## Task 1: Weakness Strategy Unit

**Files:**
- Create: `tests/test_weakness_strategy.py`
- Create: `backend_python/weakness_strategy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_weakness_strategy.py`:

```python
from backend_python.weakness_strategy import select_weakness_strategy


def test_select_weakness_strategy_returns_disabled_without_history() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": False, "frequentWeakTags": []},
        agent_mode="coach",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="技术追问",
        history=[],
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        answer_analysis={},
    )

    assert strategy["enabled"] is False
    assert strategy["matchedWeakTags"] == []
    assert strategy["primaryWeakTag"] == ""
    assert strategy["modePolicy"] == "none"


def test_select_weakness_strategy_prefers_related_tag_in_coach_mode() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["agent_state", "rag_quality"]},
        agent_mode="coach",
        profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
        next_stage="技术追问",
        history=[{"question": "RAG 质量怎么评估？", "answer": "不知道", "focus": "RAG 质量评估"}],
        role_hits=[{"title": "RAG 质量评估与可观测面板", "content": "Hit@K、MRR、关键词覆盖率"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={"weakAnswerStreak": 1, "topicLock": {"locked": False}},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["modePolicy"] == "coach_remediation"
    assert strategy["recommendedDifficulty"] == "basic"
    assert strategy["recommendedAction"] == "practice_weakness"
    assert "rag_quality" in strategy["matchedWeakTags"]
    assert "学习辅导模式" in strategy["reason"]


def test_select_weakness_strategy_uses_interview_probe_policy() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["agent_state"]},
        agent_mode="interview",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="项目深挖",
        history=[],
        role_hits=[{"title": "Agent State 与 ToolCalls", "content": "Agent State 决策"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "agent_state"
    assert strategy["modePolicy"] == "interview_probe"
    assert strategy["recommendedDifficulty"] == "medium"
    assert strategy["recommendedAction"] == "deep_follow_up"
    assert "真实面试模式" in strategy["reason"]


def test_select_weakness_strategy_avoids_deadlock_after_repeated_weak_tag() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["rag_quality"]},
        agent_mode="interview",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="技术追问",
        history=[
            {"question": "Hit@K 是什么？", "answer": "不知道", "focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
            {"question": "MRR 是什么？", "answer": "不会", "focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
        ],
        role_hits=[{"title": "RAG 质量评估", "content": "Hit@K MRR 关键词覆盖率"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={"weakAnswerStreak": 2, "topicLock": {"locked": True, "topic": "RAG 质量评估"}},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["guardrailApplied"] is True
    assert strategy["modePolicy"] == "avoid_weakness_deadlock"
    assert strategy["recommendedAction"] == "switch_topic"
    assert "weakness_deadlock_guardrail" in strategy["triggerRules"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_weakness_strategy.py -q
```

Expected: FAIL because `backend_python.weakness_strategy` does not exist.

- [ ] **Step 3: Implement `backend_python/weakness_strategy.py`**

Create:

```python
from typing import Any

TAG_LABELS = {
    "rag_retrieval": "RAG 召回链路",
    "rag_quality": "RAG 质量评估",
    "agent_state": "Agent State",
    "backend_fastapi": "FastAPI 后端模块",
    "database_modeling": "数据库建模",
    "deployment_readiness": "上线部署准备",
    "project_storytelling": "项目讲解",
    "communication_expression": "表达沟通",
}

TAG_KEYWORDS = {
    "rag_retrieval": ("rag", "召回", "检索", "query", "rewrite", "chunk"),
    "rag_quality": ("rag", "质量", "Hit@K", "MRR", "关键词覆盖率", "命中", "评估"),
    "agent_state": ("agent", "state", "tool", "decision", "orchestrator", "决策", "状态"),
    "backend_fastapi": ("fastapi", "router", "schema", "接口", "后端", "模块"),
    "database_modeling": ("sqlalchemy", "mysql", "数据库", "外键", "relationship", "表"),
    "deployment_readiness": ("docker", "nginx", "uvicorn", "redis", "部署", "上线"),
    "project_storytelling": ("项目", "背景", "职责", "难点", "结果", "简历"),
    "communication_expression": ("表达", "沟通", "行为", "规划", "薪资"),
}


def normalize_weak_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value:
        tag = str(item or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _context_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            parts.extend(str(item or "") for item in value.values())
        elif isinstance(value, list):
            for item in value:
                parts.append(_context_text(item))
        else:
            parts.append(str(value or ""))
    return " ".join(parts).lower()


def _tag_matches_context(tag: str, context: str) -> bool:
    label = TAG_LABELS.get(tag, tag)
    if label.lower() in context or tag.lower() in context:
        return True
    return any(keyword.lower() in context for keyword in TAG_KEYWORDS.get(tag, ()))


def _count_recent_weak_tag(history: list[dict[str, Any]], tag: str, window_size: int = 2) -> int:
    count = 0
    for item in list(history or [])[-window_size:]:
        item_tags = normalize_weak_tags(item.get("weakTags"))
        focus_text = _context_text(item.get("focus"), item.get("question"))
        if tag in item_tags or _tag_matches_context(tag, focus_text):
            answer = str(item.get("answer") or "")
            if not answer.strip() or any(marker in answer for marker in ("不会", "不知道", "写不出来", "不清楚")):
                count += 1
    return count


def select_weakness_strategy(
    *,
    candidate_profile: dict[str, Any],
    agent_mode: str,
    profile: dict[str, Any],
    next_stage: str,
    history: list[dict[str, Any]],
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    answer_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frequent_tags = normalize_weak_tags(candidate_profile.get("frequentWeakTags"))
    if not frequent_tags:
        return {
            "enabled": False,
            "matchedWeakTags": [],
            "primaryWeakTag": "",
            "primaryWeakLabel": "",
            "modePolicy": "none",
            "recommendedAction": "",
            "recommendedDifficulty": "",
            "reason": "候选人画像中暂无高频薄弱标签，本轮保持常规 Agent 决策。",
            "triggerRules": [],
            "guardrailApplied": False,
        }

    context = _context_text(profile, next_stage, history[-2:], role_hits, question_hits, memory_hits)
    matched_tags = [tag for tag in frequent_tags if _tag_matches_context(tag, context)]
    primary_tag = matched_tags[0] if matched_tags else frequent_tags[0]
    primary_label = TAG_LABELS.get(primary_tag, primary_tag)
    mode = "coach" if agent_mode == "coach" else "interview"
    weak_streak = int((answer_analysis or {}).get("weakAnswerStreak") or 0)
    recent_tag_weak_count = _count_recent_weak_tag(history, primary_tag)

    if weak_streak >= 2 and recent_tag_weak_count >= 2:
        return {
            "enabled": True,
            "matchedWeakTags": matched_tags or [primary_tag],
            "primaryWeakTag": primary_tag,
            "primaryWeakLabel": primary_label,
            "modePolicy": "avoid_weakness_deadlock",
            "recommendedAction": "switch_topic",
            "recommendedDifficulty": "basic",
            "reason": f"候选人已连续在「{primary_label}」相关问题上回答偏弱，本轮触发防死磕策略，避免继续卡同一个薄弱点。",
            "triggerRules": ["weakness_strategy", "weakness_deadlock_guardrail"],
            "guardrailApplied": True,
        }

    if mode == "coach":
        return {
            "enabled": True,
            "matchedWeakTags": matched_tags or [primary_tag],
            "primaryWeakTag": primary_tag,
            "primaryWeakLabel": primary_label,
            "modePolicy": "coach_remediation",
            "recommendedAction": "practice_weakness",
            "recommendedDifficulty": "basic",
            "reason": f"候选人画像显示「{primary_label}」是高频薄弱点，当前为学习辅导模式，本轮优先拆小问题并补基础。",
            "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
            "guardrailApplied": False,
        }

    return {
        "enabled": True,
        "matchedWeakTags": matched_tags or [primary_tag],
        "primaryWeakTag": primary_tag,
        "primaryWeakLabel": primary_label,
        "modePolicy": "interview_probe",
        "recommendedAction": "deep_follow_up",
        "recommendedDifficulty": "medium",
        "reason": f"候选人画像显示「{primary_label}」是高频薄弱点，当前为真实面试模式，本轮适度围绕该点追问但保留话题切换保护。",
        "triggerRules": ["weakness_strategy", "interview_weakness_probe"],
        "guardrailApplied": False,
    }
```

- [ ] **Step 4: Run unit tests and verify pass**

Run:

```powershell
python -m pytest tests/test_weakness_strategy.py -q
```

Expected: PASS.

---

## Task 2: Agent State And Decision Integration

**Files:**
- Modify: `tests/test_interview_agent.py`
- Modify: `backend_python/interview_agent.py`

- [ ] **Step 1: Add failing tests for state and fallback decision**

Append to `tests/test_interview_agent.py`:

```python
def test_build_agent_state_includes_candidate_profile_and_weakness_strategy() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
        history=[{"question": "RAG 质量怎么评估？", "answer": "不知道", "focus": "RAG 质量评估"}],
        next_stage="技术追问",
        role_hits=[{"title": "RAG 质量评估", "content": "Hit@K MRR 关键词覆盖率"}],
        question_hits=[],
        memory_hits=[
            {"score": 60, "weakTags": ["rag_quality", "agent_state"], "risks": [], "actions": [], "recentStages": []}
        ],
        agent_mode="coach",
    )

    assert state["candidateProfile"]["frequentWeakTags"][0] == "rag_quality"
    assert state["weaknessStrategy"]["enabled"] is True
    assert state["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert state["weaknessStrategy"]["modePolicy"] == "coach_remediation"


def test_build_fallback_decision_uses_coach_weakness_strategy() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "模糊",
            "remainingRounds": 5,
            "agentMode": "coach",
            "answerAnalysis": {"weakAnswerStreak": 0, "repeatedQuestionCount": 0},
            "weaknessStrategy": {
                "enabled": True,
                "primaryWeakTag": "rag_quality",
                "primaryWeakLabel": "RAG 质量评估",
                "modePolicy": "coach_remediation",
                "recommendedAction": "practice_weakness",
                "recommendedDifficulty": "basic",
                "reason": "候选人画像显示 RAG 质量评估是高频薄弱点。",
                "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
                "guardrailApplied": False,
            },
        }
    )

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["difficulty"] == "basic"
    assert decision["focus"] == "RAG 质量评估"
    assert decision["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert "weakness_strategy" in decision["triggerRules"]
    assert "候选人画像" in decision["reason"]


def test_build_fallback_decision_switches_topic_when_weakness_strategy_deadlocks() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "不会",
            "remainingRounds": 5,
            "agentMode": "interview",
            "answerAnalysis": {"weakAnswerStreak": 2, "repeatedQuestionCount": 0},
            "weaknessStrategy": {
                "enabled": True,
                "primaryWeakTag": "rag_quality",
                "primaryWeakLabel": "RAG 质量评估",
                "modePolicy": "avoid_weakness_deadlock",
                "recommendedAction": "switch_topic",
                "recommendedDifficulty": "basic",
                "reason": "连续在 RAG 质量评估上回答偏弱，触发防死磕策略。",
                "triggerRules": ["weakness_strategy", "weakness_deadlock_guardrail"],
                "guardrailApplied": True,
            },
        }
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["weaknessStrategy"]["guardrailApplied"] is True
    assert decision["guardrailApplied"] is True
    assert "weakness_deadlock_guardrail" in decision["triggerRules"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_interview_agent.py::test_build_agent_state_includes_candidate_profile_and_weakness_strategy tests/test_interview_agent.py::test_build_fallback_decision_uses_coach_weakness_strategy tests/test_interview_agent.py::test_build_fallback_decision_switches_topic_when_weakness_strategy_deadlocks -q
```

Expected: FAIL because state and decisions do not yet include `candidateProfile` / `weaknessStrategy`.

- [ ] **Step 3: Update `backend_python/interview_agent.py` imports**

Add:

```python
from .candidate_memory import build_candidate_profile
from .weakness_strategy import select_weakness_strategy
```

- [ ] **Step 4: Attach candidate profile and weakness strategy in `build_agent_state()`**

After calling `build_interview_agent_state(...)`, store it in a variable and enrich it:

```python
    state = build_interview_agent_state(...)
    candidate_profile = build_candidate_profile(memory_hits)
    weakness_strategy = select_weakness_strategy(
        candidate_profile=candidate_profile,
        agent_mode=mode,
        profile=profile,
        next_stage=next_stage,
        history=history,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memory_hits,
        answer_analysis=answer_analysis,
    )
    state["candidateProfile"] = candidate_profile
    state["weaknessStrategy"] = weakness_strategy
    return state
```

- [ ] **Step 5: Add helper to merge trigger rules**

Add in `interview_agent.py`:

```python
def merge_trigger_rules(*groups: Any) -> list[str]:
    rules: list[str] = []
    for group in groups:
        if isinstance(group, list):
            values = group
        elif group:
            values = [group]
        else:
            values = []
        for value in values:
            rule = str(value or "").strip()
            if rule and rule not in rules:
                rules.append(rule)
    return rules
```

- [ ] **Step 6: Apply weakness strategy in `build_fallback_decision()`**

Near the end of `build_fallback_decision()`, before building `decision`, read:

```python
    weakness_strategy = state.get("weaknessStrategy") if isinstance(state.get("weaknessStrategy"), dict) else {}
    if weakness_strategy.get("enabled"):
        trigger_rules = merge_trigger_rules(trigger_rules, weakness_strategy.get("triggerRules"))
        if weakness_strategy.get("modePolicy") == "avoid_weakness_deadlock":
            action = "switch_topic"
            difficulty = "basic"
            reason = str(weakness_strategy.get("reason") or reason)
        elif agent_mode == "coach" and weakness_strategy.get("recommendedAction") == "practice_weakness":
            action = "lower_difficulty"
            difficulty = str(weakness_strategy.get("recommendedDifficulty") or "basic")
            reason = str(weakness_strategy.get("reason") or reason)
        elif agent_mode == "interview" and weakness_strategy.get("recommendedAction") == "deep_follow_up" and state.get("answerStatus") != "不会":
            action = "deep_follow_up"
            difficulty = str(weakness_strategy.get("recommendedDifficulty") or "medium")
            reason = str(weakness_strategy.get("reason") or reason)
```

Then include in `decision`:

```python
        "focus": str(weakness_strategy.get("primaryWeakLabel") or state.get("nextStage") or "综合能力"),
        "weaknessStrategy": weakness_strategy,
        "guardrailApplied": bool(weakness_strategy.get("guardrailApplied")),
```

Keep existing behavior when `weakness_strategy.enabled` is false.

- [ ] **Step 7: Preserve weakness strategy in `normalize_agent_decision()`**

When building the normalized decision, include:

```python
    weakness_strategy = fallback.get("weaknessStrategy") if isinstance(fallback.get("weaknessStrategy"), dict) else {}
    decision["weaknessStrategy"] = weakness_strategy
```

When returning invalid fallback, also preserve it through `{**fallback, ...}`.

- [ ] **Step 8: Run tests**

Run:

```powershell
python -m pytest tests/test_weakness_strategy.py tests/test_interview_agent.py -q
```

Expected: PASS.

---

## Task 3: Orchestrator NodeTrace Integration

**Files:**
- Modify: `tests/test_agent_orchestrator.py`
- Modify: `backend_python/agent_orchestrator.py`

- [ ] **Step 1: Update orchestrator test expectation**

In `tests/test_agent_orchestrator.py`, update the node trace assertion in `test_run_next_question_agent_returns_state_decision_trace_and_hits()`:

```python
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_weakness_strategy",
        "select_action",
    ]
```

Add assertions:

```python
    weakness_trace = result["nodeTrace"][3]
    assert weakness_trace["outputSummary"]["enabled"] is True
    assert "primaryWeakTag" in weakness_trace["outputSummary"]
```

Ensure `memory_retrieve_fn` returns a memory with `weakTags`:

```python
memory_retrieve_fn=lambda profile, limit: [{"content": "候选人 RAG 薄弱", "score": 0.7, "weakTags": ["rag_quality"]}],
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m pytest tests/test_agent_orchestrator.py::test_run_next_question_agent_returns_state_decision_trace_and_hits -q
```

Expected: FAIL because `select_weakness_strategy` nodeTrace is missing.

- [ ] **Step 3: Add nodeTrace in `backend_python/agent_orchestrator.py`**

After `retrieve_context` trace and before setting `agent_state["nodeTrace"]`, read:

```python
    weakness_strategy = agent_state.get("weaknessStrategy") if isinstance(agent_state.get("weaknessStrategy"), dict) else {}
```

Append:

```python
        build_node_trace(
            node_name="select_weakness_strategy",
            input_summary={
                "frequentWeakTags": (agent_state.get("candidateProfile") or {}).get("frequentWeakTags", []),
                "agentMode": agent_mode,
            },
            output_summary={
                "enabled": bool(weakness_strategy.get("enabled")),
                "primaryWeakTag": weakness_strategy.get("primaryWeakTag", ""),
                "modePolicy": weakness_strategy.get("modePolicy", "none"),
                "recommendedAction": weakness_strategy.get("recommendedAction", ""),
            },
            fallback_used=bool(weakness_strategy.get("guardrailApplied")),
        ),
```

Update any tests that assert exact node trace order to include the new node.

- [ ] **Step 4: Run orchestrator tests**

Run:

```powershell
python -m pytest tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py -q
```

Expected: PASS.

---

## Task 4: Route And Log Verification

**Files:**
- Modify: `tests/test_interview_agent_route.py`
- Modify: `backend_python/routes/interview.py`

- [ ] **Step 1: Add failing route/log test**

Append to `tests/test_interview_agent_route.py`:

```python
def test_next_question_uses_frequent_weak_tags_in_agent_strategy(monkeypatch) -> None:
    from backend_python.routes import interview

    captured_question_payloads = []

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 质量评估",
                "reason": "模型返回基础降难度，normalize 应保留 weaknessStrategy。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        captured_question_payloads.append(json.loads(messages[-1]["content"]))
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 质量评估",
            "prompt": "我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"weakness-route-{suffix}@example.com"
    username = f"weakness_route_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    client.post(
        "/api/history",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"candidateName": "测试用户", "targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
            "answers": [{"stage": "技术追问", "focus": "RAG 质量评估", "question": "Hit@K 是什么？", "answer": "不知道"}],
            "report": {
                "score": 55,
                "risks": ["RAG 质量评估表达薄弱"],
                "actions": ["复练 Hit@K、MRR、关键词覆盖率"],
                "questionReviews": [{"focus": "RAG 质量评估", "weakTags": ["rag_quality"]}],
                "trainingPlan": {"weakTopics": [{"focus": "RAG 质量评估", "weakTags": ["rag_quality"]}]},
            },
        },
    )

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
            "history": [{"question": "RAG 质量怎么评估？", "answer": "不清楚", "focus": "RAG 质量评估"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    body = response.json()
    strategy = body["agentDecision"]["weaknessStrategy"]
    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["modePolicy"] == "coach_remediation"
    assert "weakness_strategy" in body["agentDecision"]["triggerRules"]
    assert "RAG 质量评估" in body["decisionSummary"]
    assert captured_question_payloads[0]["agentDecision"]["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"

    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        log = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).first()

    assert log is not None
    state_json = json.loads(log.state_json)
    decision_json = json.loads(log.decision_json)
    assert state_json["candidateProfile"]["frequentWeakTags"][0] == "rag_quality"
    assert decision_json["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert "select_weakness_strategy" in [item["nodeName"] for item in decision_json["nodeTrace"]]
```

- [ ] **Step 2: Run route test and verify failure**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py::test_next_question_uses_frequent_weak_tags_in_agent_strategy -q
```

Expected: FAIL before integration is complete.

- [ ] **Step 3: Update `build_question_strategy_payload()` signature**

In `backend_python/routes/interview.py`, add optional `agent_decision`:

```python
def build_question_strategy_payload(
    *,
    history: list[dict[str, Any]],
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    agent_mode: str,
    agent_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Inside the returned `questionStrategy`, include a `weaknessStrategy` summary:

```python
    weakness_strategy = agent_decision.get("weaknessStrategy") if isinstance(agent_decision, dict) and isinstance(agent_decision.get("weaknessStrategy"), dict) else {}
```

Return:

```python
        "weaknessStrategy": {
            "enabled": bool(weakness_strategy.get("enabled")),
            "primaryWeakTag": weakness_strategy.get("primaryWeakTag", ""),
            "primaryWeakLabel": weakness_strategy.get("primaryWeakLabel", ""),
            "modePolicy": weakness_strategy.get("modePolicy", "none"),
            "reason": weakness_strategy.get("reason", ""),
        },
```

Then pass `agent_decision=agent_decision` from `next_question()`.

- [ ] **Step 4: Ensure prompt receives strategy through existing `agentDecision`**

No new response field is needed. Confirm the user payload still contains:

```python
"agentDecision": agent_decision
```

and now `agentDecision["weaknessStrategy"]` is populated.

- [ ] **Step 5: Run route tests**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_interview_agent.py tests/test_weakness_strategy.py -q
```

Expected: PASS.

---

## Task 5: Learning Document And Progress Record

**Files:**
- Create: `docs/learning/07-候选人画像如何驱动Agent决策.md`
- Modify: `docs/pre-deployment-progress.md`

- [ ] **Step 1: Create learning document**

Create `docs/learning/07-候选人画像如何驱动Agent决策.md`:

```markdown
# 07 候选人画像如何驱动 Agent 决策

## 1. 本阶段解决什么问题

上一阶段系统已经能从报告中提取 weakTags，并聚合出 candidateProfile.frequentWeakTags。
本阶段继续往前走一步：让这些长期薄弱点进入 Agent State，并影响下一题策略。

## 2. weakTags 和 frequentWeakTags 的区别

weakTags 表示单次回答暴露出的薄弱点。
frequentWeakTags 表示多轮历史中反复出现的高频薄弱点。

## 3. 数据流

```text
questionReviews / trainingPlan
-> weakTags
-> 历史记录
-> 候选人画像 RAG
-> frequentWeakTags
-> Agent State
-> weaknessStrategy
-> Agent Decision
-> 下一题
```

## 4. coach 和 interview 的策略差异

coach 模式下，系统会更偏向降难度、拆解概念、补薄弱点。
interview 模式下，系统会更像真实面试官，围绕薄弱点适度追问，但不能连续死磕。

## 5. 防死磕规则

如果用户连续在同一个 weakTag 上回答偏弱，Agent 会触发 weakness_deadlock_guardrail，切换到相邻话题或更基础的解释。

## 6. 面试时怎么讲

我把历史报告里的 weakTags 聚合成 candidateProfile.frequentWeakTags，并让它进入 Agent State。
Agent 会根据当前模式选择 weaknessStrategy：
coach 模式用于补弱点，interview 模式用于真实追问。
同时策略会写入 nodeTrace 和 Agent 日志，所以系统不是黑箱生成下一题，而是能解释为什么围绕某个薄弱点追问。
```

- [ ] **Step 2: Update progress record**

Append a section to `docs/pre-deployment-progress.md`:

```markdown
## 候选人画像弱点驱动 Agent 决策 V1

状态：进行中 / 已完成。

本阶段目标是让 `candidateProfile.frequentWeakTags` 进入 Agent State，并通过 `weaknessStrategy` 影响 coach / interview 两种模式下的下一题策略。

验证命令：

```text
python -m pytest tests/test_weakness_strategy.py tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_interview_agent_route.py -q
python -m pytest -q
```

结果：执行后记录。
```

After final verification, replace `进行中 / 已完成` and `执行后记录` with actual status/output.

---

## Full Verification

Run after implementation:

```powershell
python -m pytest tests/test_weakness_strategy.py tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_interview_agent_route.py -q
```

Expected: all targeted tests pass.

Run full backend suite:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

Run frontend tests only if frontend code changes:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend tests pass.

---

## Self-Review

- Spec coverage:
  - Agent State gets `candidateProfile.frequentWeakTags`: Task 2.
  - `weaknessStrategy` exists and differs by mode: Task 1 and Task 2.
  - coach mode favors remediation: Task 1 and Task 2.
  - interview mode favors realistic probing: Task 1 and Task 2.
  - anti-deadlock rule: Task 1 and Task 2.
  - Agent logs/nodeTrace expose strategy: Task 3 and Task 4.
  - `/api/interview/next-question` compatibility: Task 4.
  - Chinese learning doc: Task 5.
- Scope check:
  - No new database table.
  - No LangGraph / LangChain.
  - No Docker / Nginx / cloud deployment.
  - No React / Vue / Next.js migration.
- Placeholder scan:
  - No unfinished placeholder markers are intentionally left in implementation steps.
- Type consistency:
  - `weaknessStrategy.primaryWeakTag`, `matchedWeakTags`, `modePolicy`, `recommendedAction`, and `recommendedDifficulty` are consistent across tests, state, decision, and logs.
