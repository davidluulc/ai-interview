# weakTag Training Templates V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight weakTag-to-training-template layer so `weaknessStrategy.primaryWeakTag` produces `trainingTemplateHint` in Agent Decision, question generation payload, Agent logs, and nodeTrace.

**Architecture:** Add a focused `backend_python/weakness_training_templates.py` module that owns static training templates and hint selection. Wire it into `interview_agent.py` and `agent_orchestrator.py` after `weaknessStrategy` is selected, then pass the hint through `routes/interview.py` into `questionStrategy`. Keep API compatibility by adding fields inside existing `agentDecision` / `questionStrategy` JSON only.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest. No database migration, no LangGraph/LangChain, no frontend framework change.

---

## File Structure

- Create: `backend_python/weakness_training_templates.py`
  - Owns `WEAKNESS_TRAINING_TEMPLATES`, `get_training_template()`, and `select_training_template_hint()`.
- Create: `tests/test_weakness_training_templates.py`
  - Unit tests for template coverage, unknown weakTag fallback, mode-specific question selection, and difficulty ladder selection.
- Modify: `backend_python/interview_agent.py`
  - Attach `trainingTemplateHint` to fallback and normalized Agent Decision and include it in `decisionSummary`.
- Modify: `backend_python/agent_orchestrator.py`
  - Add `select_training_template` nodeTrace between `select_weakness_strategy` and `select_action`.
- Modify: `backend_python/routes/interview.py`
  - Add `trainingTemplateHint` into `questionStrategy`.
- Modify: `tests/test_interview_agent.py`
  - Verify Agent Decision includes `trainingTemplateHint`.
- Modify: `tests/test_agent_orchestrator.py`
  - Verify nodeTrace includes `select_training_template`.
- Modify: `tests/test_interview_agent_route.py`
  - Verify `/api/interview/next-question` response, LLM payload, and `AgentDecisionLog` include `trainingTemplateHint`.
- Create: `docs/learning/08-weakTag训练模板如何让Agent更会训练.md`
  - Chinese learning document.
- Modify: `docs/pre-deployment-progress.md`
  - Record completion, verification, risks, and next step.

---

## Task 1: Training Template Module

**Files:**
- Create: `tests/test_weakness_training_templates.py`
- Create: `backend_python/weakness_training_templates.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/test_weakness_training_templates.py`:

```python
from backend_python.weakness_training_templates import (
    CORE_WEAK_TAGS,
    get_training_template,
    select_training_template_hint,
)


def test_core_templates_cover_required_weak_tags() -> None:
    assert CORE_WEAK_TAGS == [
        "rag_quality",
        "rag_retrieval",
        "agent_state",
        "backend_fastapi",
        "database_modeling",
        "project_storytelling",
    ]
    for weak_tag in CORE_WEAK_TAGS:
        template = get_training_template(weak_tag)
        assert template["weakTag"] == weak_tag
        assert template["label"]
        assert len(template["coachQuestions"]) >= 2
        assert len(template["interviewQuestions"]) >= 2
        assert set(template["difficultyLadder"]) >= {"basic", "medium", "hard"}
        assert template["answerKeyPoints"]
        assert template["commonMistakes"]
        assert template["oneMinuteTemplate"]


def test_unknown_weak_tag_returns_generic_template() -> None:
    template = get_training_template("unknown_tag")

    assert template["weakTag"] == "communication_expression"
    assert template["fallbackUsed"] is True
    assert "表达" in template["label"]


def test_select_training_template_hint_prefers_coach_basic_question() -> None:
    hint = select_training_template_hint(
        weakness_strategy={
            "enabled": True,
            "primaryWeakTag": "rag_quality",
            "primaryWeakLabel": "RAG 质量评估",
        },
        agent_mode="coach",
        difficulty="basic",
    )

    assert hint["enabled"] is True
    assert hint["weakTag"] == "rag_quality"
    assert hint["mode"] == "coach"
    assert hint["difficulty"] == "basic"
    assert "Hit@K" in hint["recommendedQuestion"]
    assert any("MRR" in point for point in hint["answerKeyPoints"])
    assert hint["fallbackUsed"] is False


def test_select_training_template_hint_prefers_interview_question() -> None:
    hint = select_training_template_hint(
        weakness_strategy={
            "enabled": True,
            "primaryWeakTag": "agent_state",
            "primaryWeakLabel": "Agent State",
        },
        agent_mode="interview",
        difficulty="medium",
    )

    assert hint["enabled"] is True
    assert hint["weakTag"] == "agent_state"
    assert hint["mode"] == "interview"
    assert "Agent State" in hint["recommendedQuestion"]
    assert any("ToolCalls" in point or "Agent Decision" in point for point in hint["answerKeyPoints"])


def test_select_training_template_hint_returns_disabled_without_strategy() -> None:
    hint = select_training_template_hint(
        weakness_strategy={"enabled": False},
        agent_mode="coach",
        difficulty="basic",
    )

    assert hint["enabled"] is False
    assert hint["weakTag"] == ""
    assert hint["recommendedQuestion"] == ""
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
python -m pytest tests/test_weakness_training_templates.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend_python.weakness_training_templates'`.

- [ ] **Step 3: Implement module**

Create `backend_python/weakness_training_templates.py` with:

```python
from copy import deepcopy
from typing import Any

CORE_WEAK_TAGS = [
    "rag_quality",
    "rag_retrieval",
    "agent_state",
    "backend_fastapi",
    "database_modeling",
    "project_storytelling",
]

GENERIC_TEMPLATE = {
    "weakTag": "communication_expression",
    "label": "项目表达与沟通",
    "description": "用于兜底训练候选人的结构化表达能力。",
    "coachQuestions": [
        "我们先把回答拆成三段：背景、做法、结果。你能按这个结构讲一遍吗？",
        "先不用追求完整，你先说清这个问题考察的核心概念是什么。",
    ],
    "interviewQuestions": [
        "请用背景、方案、结果的结构回答这个问题，不要只罗列技术名词。",
        "如果让你重新组织刚才的回答，你会补充哪些项目细节？",
    ],
    "difficultyLadder": {
        "basic": ["先用一句话说明这个概念解决什么问题。"],
        "medium": ["请结合项目例子说明你的做法和取舍。"],
        "hard": ["请补充验证方式、风险和后续优化方向。"],
    },
    "answerKeyPoints": ["背景", "做法", "结果", "复盘"],
    "commonMistakes": ["只罗列技术名词", "没有项目例子", "没有结果验证"],
    "oneMinuteTemplate": "可以按背景、任务、做法、结果、复盘五步组织 1 分钟回答。",
    "relatedTags": ["project_storytelling"],
}

WEAKNESS_TRAINING_TEMPLATES = {
    "rag_quality": {
        "weakTag": "rag_quality",
        "label": "RAG 质量评估",
        "description": "训练候选人解释 RAG 评估指标、命中日志和质量面板。",
        "coachQuestions": ["我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？"],
        "interviewQuestions": ["如果你说项目里做了 RAG 质量评估，请说清 Hit@K 和 MRR 分别怎么计算。"],
        "difficultyLadder": {
            "basic": ["Hit@K、MRR、关键词覆盖率分别解决什么问题？"],
            "medium": ["请结合你的项目说明 RAG 命中日志里 quality 字段如何帮助排查问题。"],
            "hard": ["如果线上发现 RAG 问题质量下降，你会如何用 Hit@K、MRR 和日志定位原因？"],
        },
        "answerKeyPoints": ["Hit@K", "MRR", "关键词覆盖率", "空召回率", "metadata 匹配率"],
        "commonMistakes": ["只解释字段名，不解释指标用途"],
        "oneMinuteTemplate": "可以按指标定义、解决问题、项目落地、日志排查四步回答。",
        "relatedTags": ["rag_retrieval"],
    },
}
```

The actual implementation must define all six keys from `CORE_WEAK_TAGS`. Each value must include the same field set shown in the `rag_quality` example: `weakTag`, `label`, `description`, `coachQuestions`, `interviewQuestions`, `difficultyLadder`, `answerKeyPoints`, `commonMistakes`, `oneMinuteTemplate`, and `relatedTags`.

Implement:

```python
def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def get_training_template(weak_tag: str) -> dict[str, Any]:
    key = str(weak_tag or "").strip()
    template = WEAKNESS_TRAINING_TEMPLATES.get(key)
    fallback_used = template is None
    selected = deepcopy(template or GENERIC_TEMPLATE)
    selected["fallbackUsed"] = fallback_used
    return selected


def _select_question(template: dict[str, Any], *, agent_mode: str, difficulty: str) -> str:
    ladder = template.get("difficultyLadder") if isinstance(template.get("difficultyLadder"), dict) else {}
    ladder_questions = _safe_list(ladder.get(difficulty)) or _safe_list(ladder.get("basic"))
    mode_questions = _safe_list(template.get("coachQuestions" if agent_mode == "coach" else "interviewQuestions"))
    return (ladder_questions or mode_questions or _safe_list(template.get("coachQuestions")) or [""])[0]


def select_training_template_hint(
    *,
    weakness_strategy: dict[str, Any],
    agent_mode: str,
    difficulty: str,
) -> dict[str, Any]:
    if not isinstance(weakness_strategy, dict) or not weakness_strategy.get("enabled"):
        return {
            "enabled": False,
            "weakTag": "",
            "label": "",
            "mode": "coach" if agent_mode == "coach" else "interview",
            "difficulty": difficulty if difficulty in {"basic", "medium", "hard"} else "medium",
            "recommendedQuestion": "",
            "answerKeyPoints": [],
            "commonMistakes": [],
            "oneMinuteTemplate": "",
            "fallbackUsed": False,
        }
    mode = "coach" if agent_mode == "coach" else "interview"
    normalized_difficulty = difficulty if difficulty in {"basic", "medium", "hard"} else "medium"
    template = get_training_template(str(weakness_strategy.get("primaryWeakTag") or ""))
    return {
        "enabled": True,
        "weakTag": template["weakTag"],
        "label": template["label"],
        "mode": mode,
        "difficulty": normalized_difficulty,
        "recommendedQuestion": _select_question(template, agent_mode=mode, difficulty=normalized_difficulty),
        "answerKeyPoints": _safe_list(template.get("answerKeyPoints"))[:6],
        "commonMistakes": _safe_list(template.get("commonMistakes"))[:4],
        "oneMinuteTemplate": str(template.get("oneMinuteTemplate") or ""),
        "relatedTags": _safe_list(template.get("relatedTags"))[:4],
        "fallbackUsed": bool(template.get("fallbackUsed")),
    }
```

- [ ] **Step 4: Run unit tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_weakness_training_templates.py -q
```

Expected: PASS.

---

## Task 2: Agent Decision And nodeTrace Integration

**Files:**
- Modify: `tests/test_interview_agent.py`
- Modify: `tests/test_agent_orchestrator.py`
- Modify: `backend_python/interview_agent.py`
- Modify: `backend_python/agent_orchestrator.py`

- [ ] **Step 1: Write failing Agent tests**

Update `tests/test_interview_agent.py`:

```python
def test_build_fallback_decision_includes_training_template_hint_for_weakness_strategy() -> None:
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

    hint = decision["trainingTemplateHint"]
    assert hint["enabled"] is True
    assert hint["weakTag"] == "rag_quality"
    assert hint["mode"] == "coach"
    assert hint["difficulty"] == "basic"
    assert "Hit@K" in hint["recommendedQuestion"]
    assert "训练模板" in decision["decisionSummary"]
```

Update `tests/test_agent_orchestrator.py` expected node order in `test_run_next_question_agent_returns_state_decision_trace_and_hits()`:

```python
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_weakness_strategy",
        "select_training_template",
        "select_action",
    ]
    template_trace = result["nodeTrace"][4]
    assert template_trace["outputSummary"]["enabled"] is True
    assert template_trace["outputSummary"]["weakTag"] == "rag_quality"
    assert result["agentDecision"]["trainingTemplateHint"]["weakTag"] == "rag_quality"
```

- [ ] **Step 2: Run Agent tests and verify RED**

Run:

```powershell
python -m pytest tests/test_interview_agent.py::test_build_fallback_decision_includes_training_template_hint_for_weakness_strategy tests/test_agent_orchestrator.py::test_run_next_question_agent_returns_state_decision_trace_and_hits -q
```

Expected: FAIL because `trainingTemplateHint` and `select_training_template` are missing.

- [ ] **Step 3: Update `backend_python/interview_agent.py`**

Import:

```python
from .weakness_training_templates import select_training_template_hint
```

In `build_decision_summary()`, after weakness strategy summary, append:

```python
    training_hint = decision.get("trainingTemplateHint") if isinstance(decision.get("trainingTemplateHint"), dict) else {}
    if training_hint.get("enabled"):
        label = str(training_hint.get("label") or training_hint.get("weakTag") or "薄弱点")
        question = str(training_hint.get("recommendedQuestion") or "")
        summary += f" 本轮使用训练模板：{label}。"
        if question:
            summary += f" 模板建议问题：{question}"
```

In `build_fallback_decision()`, after final action/difficulty is decided and before building the `decision` dictionary:

```python
    training_template_hint = select_training_template_hint(
        weakness_strategy=weakness_strategy,
        agent_mode=agent_mode,
        difficulty=difficulty,
    )
```

Include in decision:

```python
        "trainingTemplateHint": training_template_hint,
```

In `normalize_agent_decision()`, preserve fallback hint:

```python
    training_template_hint = (
        fallback.get("trainingTemplateHint")
        if isinstance(fallback.get("trainingTemplateHint"), dict)
        else select_training_template_hint(
            weakness_strategy=weakness_strategy,
            agent_mode=agent_mode,
            difficulty=difficulty,
        )
    )
```

Include in normalized decision:

```python
        "trainingTemplateHint": training_template_hint,
```

- [ ] **Step 4: Update `backend_python/agent_orchestrator.py`**

After the `agent_decision` value is returned by `decide_next_action_fn`, read:

```python
    training_template_hint = (
        agent_decision.get("trainingTemplateHint")
        if isinstance(agent_decision.get("trainingTemplateHint"), dict)
        else {}
    )
```

Add `select_training_template` node before `select_action`:

```python
        build_node_trace(
            node_name="select_training_template",
            input_summary={
                "primaryWeakTag": weakness_strategy.get("primaryWeakTag", ""),
                "agentMode": agent_mode,
                "difficulty": agent_decision.get("difficulty"),
            },
            output_summary={
                "enabled": bool(training_template_hint.get("enabled")),
                "weakTag": training_template_hint.get("weakTag", ""),
                "label": training_template_hint.get("label", ""),
                "recommendedQuestion": training_template_hint.get("recommendedQuestion", ""),
            },
            fallback_used=bool(training_template_hint.get("fallbackUsed")),
        ),
```

- [ ] **Step 5: Run Agent tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_weakness_training_templates.py tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py -q
```

Expected: PASS.

---

## Task 3: Route Payload And Agent Log Verification

**Files:**
- Modify: `tests/test_interview_agent_route.py`
- Modify: `backend_python/routes/interview.py`

- [ ] **Step 1: Write failing route test assertions**

In `tests/test_interview_agent_route.py`, update nodeTrace expectations to include `select_training_template`.

In `test_next_question_uses_frequent_weak_tags_in_agent_strategy()`, add assertions:

```python
    template_hint = body["agentDecision"]["trainingTemplateHint"]
    assert template_hint["enabled"] is True
    assert template_hint["weakTag"] == "rag_quality"
    assert "Hit@K" in template_hint["recommendedQuestion"]
    assert captured_question_payloads[0]["agentDecision"]["trainingTemplateHint"]["weakTag"] == "rag_quality"
    assert captured_question_payloads[0]["questionStrategy"]["trainingTemplateHint"]["weakTag"] == "rag_quality"
```

After loading `decision_json`, add:

```python
    assert decision_json["trainingTemplateHint"]["weakTag"] == "rag_quality"
    assert "select_training_template" in [item["nodeName"] for item in decision_json["nodeTrace"]]
```

- [ ] **Step 2: Run route test and verify RED**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py::test_next_question_uses_frequent_weak_tags_in_agent_strategy -q
```

Expected: FAIL because `questionStrategy.trainingTemplateHint` is missing.

- [ ] **Step 3: Update `build_question_strategy_payload()`**

In `backend_python/routes/interview.py`, extract:

```python
    training_template_hint = (
        agent_decision.get("trainingTemplateHint")
        if isinstance(agent_decision, dict) and isinstance(agent_decision.get("trainingTemplateHint"), dict)
        else {}
    )
```

Add to `questionStrategy`:

```python
            "trainingTemplateHint": {
                "enabled": bool(training_template_hint.get("enabled")),
                "weakTag": str(training_template_hint.get("weakTag") or ""),
                "label": str(training_template_hint.get("label") or ""),
                "mode": str(training_template_hint.get("mode") or agent_mode),
                "difficulty": str(training_template_hint.get("difficulty") or ""),
                "recommendedQuestion": str(training_template_hint.get("recommendedQuestion") or ""),
                "answerKeyPoints": list(training_template_hint.get("answerKeyPoints") or [])[:6],
                "commonMistakes": list(training_template_hint.get("commonMistakes") or [])[:4],
                "oneMinuteTemplate": str(training_template_hint.get("oneMinuteTemplate") or ""),
            },
```

- [ ] **Step 4: Run route and targeted tests**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_interview_agent.py tests/test_weakness_training_templates.py -q
```

Expected: PASS.

---

## Task 4: Learning Document, Progress Record, Full Verification

**Files:**
- Create: `docs/learning/08-weakTag训练模板如何让Agent更会训练.md`
- Modify: `docs/pre-deployment-progress.md`

- [ ] **Step 1: Create learning document**

Create `docs/learning/08-weakTag训练模板如何让Agent更会训练.md` with sections:

```markdown
# 08 weakTag 训练模板如何让 Agent 更会训练

## 1. 本阶段解决什么问题

上一阶段系统已经能识别候选人长期薄弱点，本阶段继续让每个 weakTag 对应一套训练模板。

## 2. weakTag、weaknessStrategy、trainingTemplateHint 的关系

weakTag 回答“哪里弱”，weaknessStrategy 回答“本轮是否围绕这个弱点训练”，trainingTemplateHint 回答“这个弱点本轮怎么练”。

## 3. 为什么训练模板不是题库 RAG

题库 RAG 偏真实面试题召回，训练模板偏训练策略和答题要点。

## 4. coach 和 interview 怎么使用模板

coach 模式更偏拆小、降难度和给框架；interview 模式更偏真实追问和项目核验。

## 5. 日志和 nodeTrace 怎么证明不是黑箱

Agent Decision 和 nodeTrace 中可以看到 trainingTemplateHint 和 select_training_template。

## 6. 面试时怎么讲

我把候选人历史 weakTags 映射成训练模板，让系统不仅知道用户哪里薄弱，还知道这个薄弱点应该怎么训练。
```

- [ ] **Step 2: Update progress record**

Append a new section to `docs/pre-deployment-progress.md`:

```markdown
## 阶段 6：weakTag 训练模板系统 V1

状态：已完成阶段性版本。

本阶段新增 weakTag 到训练模板的映射，让 `weaknessStrategy.primaryWeakTag` 能生成 `trainingTemplateHint`，并进入 Agent Decision、questionStrategy、Agent 日志和 nodeTrace。

已完成内容：

- 新增 `backend_python/weakness_training_templates.py`。
- 覆盖 6 个核心 weakTags。
- Agent Decision 已包含 `trainingTemplateHint`。
- `nodeTrace` 已增加 `select_training_template`。
- `/api/interview/next-question` 的 `questionStrategy` 已包含 `trainingTemplateHint`。
- 新增学习文档 `docs/learning/08-weakTag训练模板如何让Agent更会训练.md`。

验证命令：

```text
python -m pytest tests/test_weakness_training_templates.py tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_interview_agent_route.py -q
python -m pytest -q
```

结果：填写实际 pytest 输出，例如 `183 passed in 21.48s`。

当前风险：

- 模板仍是静态规则，没有做掌握度评分。
- 暂未做前端专项展示。
- 后续可进入阶段性项目讲解 B。
```

- [ ] **Step 3: Run targeted backend tests**

Run:

```powershell
python -m pytest tests/test_weakness_training_templates.py tests/test_interview_agent.py tests/test_agent_orchestrator.py tests/test_interview_agent_route.py -q
```

Expected: PASS.

- [ ] **Step 4: Run full backend test suite**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 5: Frontend test note**

If no frontend files changed, do not run `.mjs` tests. Record this in final answer and progress record.

---

## Self-Review

- Spec coverage:
  - Training template module: Task 1.
  - Six weakTags: Task 1.
  - `get_training_template()` and `select_training_template_hint()`: Task 1.
  - Agent Decision `trainingTemplateHint`: Task 2.
  - `questionStrategy.trainingTemplateHint`: Task 3.
  - Agent logs/nodeTrace observable with `select_training_template`: Task 2 and Task 3.
  - No DB migration/new table: all tasks avoid DB schema changes.
  - No frontend framework migration: no frontend changes planned.
  - Learning document and progress record: Task 4.
- Placeholder scan:
  - Implementation code must not contain ellipses from this plan.
  - Tests contain concrete assertions and paths.
- Type consistency:
  - Field name is always `trainingTemplateHint`.
  - Node name is always `select_training_template`.
  - Function names are always `get_training_template()` and `select_training_template_hint()`.
