# LangGraph Runtime Deepening V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 LangGraph runtime 从“能旁路运行”升级为“能质量评估、能灰度门禁、能持久化摘要、能在 AI Debug 后台解释差异”的候选主链路。

**Architecture:** 保留 classic Agent 作为默认可见主链路，LangGraph 继续通过 `langgraph` 和 `shadow` runtime 进入系统。新增纯函数模块 `runtime_quality_gate.py` 和 `runtime_compare.py`，再把它们接入 `agent_runtime.py`；checkpoint 只持久化项目侧摘要，不承诺完整 graph state 生产级恢复。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pytest, Vue3, Pinia, Vitest, TypeScript.

---

## 0. 本轮要学的 Agent 工程化知识点

这一阶段学习的不是“怎么调用 LangGraph”，而是“怎样把一个新 Agent runtime 安全地推向主链路”。

核心概念：

- **shadow compare**：用户仍看到 classic Agent 的结果，后台同时跑 LangGraph，并记录两边差异。
- **runtime quality gate**：LangGraph 输出进入可见链路前，先检查空问题、非法动作、非法难度、重复问题、缺失 checkpoint、人审标记。
- **fallback classic**：LangGraph 输出不可靠时，系统自动退回 classic Agent，保证主体验稳定。
- **checkpoint summary persistence**：只保存可观测摘要，不急着保存完整 LangGraph 内部状态。
- **AI Debug observability**：后台不只展示 JSON，而要解释“为什么这次用了 classic、LangGraph 结果怎样、是否触发门禁”。

## 1. 文件结构与职责

### 新增文件

- `backend_python/runtime_quality_gate.py`
  - 纯函数模块。
  - 输入 LangGraph runtime result 和 recent questions。
  - 输出 `qualityGate` 字典。
  - 不访问数据库，不调用模型。

- `backend_python/runtime_compare.py`
  - 纯函数模块。
  - 输入 classic result、LangGraph result、quality gate result。
  - 输出 `comparisonSummary` 字典。
  - 只做结构化比较，不决定业务流程。

- `backend_python/langgraph_agent/checkpoint_persistence.py`
  - 项目侧 checkpoint summary 持久化服务。
  - 使用 SQLAlchemy session 保存和查询摘要。
  - 不替换 LangGraph 内部 checkpointer。

- `tests/test_runtime_quality_gate.py`
  - 覆盖空问题、非法 action、非法 difficulty、重复问题、人审拦截、缺失 checkpoint。

- `tests/test_runtime_compare.py`
  - 覆盖 action/difficulty/question 差异和中文原因。

- `tests/test_langgraph_runtime_checkpoint_persistence.py`
  - 覆盖 checkpoint summary 保存、查询最近记录、查询 run history。

- `docs/learning/23-LangGraph从旁路到候选主链路如何灰度迁移.md`
  - 面向学习和面试表达的中文复盘文档。

### 修改文件

- `backend_python/agent_runtime.py`
  - 接入 quality gate。
  - 接入 runtime compare。
  - `shadow` 模式返回 classic 可见结果，同时记录 LangGraph comparison。
  - `langgraph` 模式下 gate 失败时 fallback classic。

- `backend_python/db_models.py`
  - 新增 `LangGraphCheckpointSummary` ORM 表。

- `backend_python/database.py`
  - SQLite 自动建表兼容逻辑补充 `langgraph_checkpoint_summaries`。

- `alembic/versions/<new_revision>_add_langgraph_checkpoint_summaries.py`
  - 新增 checkpoint summary 表迁移。

- `backend_python/langgraph_agent/checkpoint_store.py`
  - 在内存 store 的 summary 字段中保留 `qualityGate`、`comparisonSummary`。

- `backend_python/routes/langgraph_agent.py`
  - runtime/run 和 runtime/resume 保存持久化 summary。
  - 增加 `GET /api/langgraph-agent/runtime/runs/{thread_id}`。

- `backend_python/ai_debug.py`
  - normalizer 增加 quality gate、comparison、visible runtime、fallback 字段。
  - diagnostics 增加 runtime quality gate 相关中文提示。

- `backend_python/routes/admin.py`
  - AI Debug detail 读取最新 checkpoint summary 时优先使用持久化摘要。

- `frontend/src/stores/admin.ts`
  - admin detail 类型和容错展示字段增加 `qualityGate`、`comparisonSummary`。

- `frontend/src/pages/app/AdminPage.vue`
  - AI Debug Console 增加“Runtime 对比”“Quality Gate”“Fallback”中文摘要区。

- `frontend/src/stores/admin.test.ts`
  - 覆盖新增字段不会出现 `undefined`。

- `frontend/src/pages/app/admin-page.test.ts`
  - 覆盖后台页面展示 Runtime 对比和门禁信息。

- `docs/roadmap/current-state.md`
  - 阶段完成后更新 V4 状态。

- `docs/specs/README.md`
  - 阶段完成后把 active spec 移到 completed 时更新。

- `docs/plans/README.md`
  - 阶段完成后把 active plan 移到 completed 时更新。

---

### Task 1: Runtime Quality Gate 纯函数

**Files:**
- Create: `tests/test_runtime_quality_gate.py`
- Create: `backend_python/runtime_quality_gate.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_runtime_quality_gate.py`:

```python
from backend_python.runtime_quality_gate import evaluate_runtime_quality


def test_quality_gate_passes_safe_langgraph_output() -> None:
    result = {
        "status": "completed",
        "nextQuestion": {"content": "请解释 LangGraph checkpoint 的作用。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True, "threadId": "runtime-a"},
    }

    gate = evaluate_runtime_quality(result, recent_questions=["什么是 RAG？"])

    assert gate["passed"] is True
    assert gate["fallbackToClassic"] is False
    assert gate["riskLevel"] == "low"
    assert gate["checks"]["nonEmptyQuestion"] is True
    assert gate["checks"]["validDecision"] is True
    assert gate["checks"]["validDifficulty"] is True
    assert gate["checks"]["notRepeated"] is True
    assert gate["checks"]["checkpointAvailable"] is True
    assert gate["checks"]["humanReviewBlocked"] is False


def test_quality_gate_blocks_empty_question() -> None:
    result = {
        "status": "completed",
        "nextQuestion": {"content": "   "},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["fallbackToClassic"] is True
    assert gate["riskLevel"] == "high"
    assert gate["checks"]["nonEmptyQuestion"] is False
    assert "LangGraph 没有生成可展示的问题" in gate["reasons"]


def test_quality_gate_blocks_invalid_action_and_difficulty() -> None:
    result = {
        "question": {"content": "请继续说明项目。"},
        "decision": {"nextAction": "random_action", "difficulty": "impossible"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["checks"]["validDecision"] is False
    assert gate["checks"]["validDifficulty"] is False
    assert "LangGraph 决策动作不合法：random_action" in gate["reasons"]
    assert "LangGraph 难度等级不合法：impossible" in gate["reasons"]


def test_quality_gate_blocks_repeated_question() -> None:
    result = {
        "nextQuestion": {"content": "请解释 Agent State 的作用。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=["请解释 Agent State 的作用。"])

    assert gate["passed"] is False
    assert gate["checks"]["notRepeated"] is False
    assert "LangGraph 问题与最近问题重复度过高" in gate["reasons"]


def test_quality_gate_blocks_human_review_required() -> None:
    result = {
        "nextQuestion": {"content": "请继续回答。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        "checkpointSummary": {"exists": True, "requiresHumanReview": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["checks"]["humanReviewBlocked"] is True
    assert "LangGraph 标记需要人工复核" in gate["reasons"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_runtime_quality_gate.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'backend_python.runtime_quality_gate'
```

- [ ] **Step 3: 实现最小代码**

Create `backend_python/runtime_quality_gate.py`:

```python
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


VALID_ACTIONS = {
    "deepen",
    "deep_follow_up",
    "lower_difficulty",
    "raise_difficulty",
    "shift_topic",
    "switch_topic",
    "finish_interview",
    "end_interview",
    "summarize_feedback",
    "practice_weakness",
}

VALID_DIFFICULTIES = {"basic", "easy", "medium", "hard", "advanced"}


def extract_runtime_question(result: dict[str, Any]) -> str:
    question = result.get("question") if isinstance(result.get("question"), dict) else {}
    next_question = result.get("nextQuestion") if isinstance(result.get("nextQuestion"), dict) else {}
    return str(question.get("content") or question.get("prompt") or next_question.get("content") or next_question.get("prompt") or "").strip()


def extract_runtime_decision(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("decision") if isinstance(result.get("decision"), dict) else {}


def is_repeated_question(question: str, recent_questions: list[str], *, threshold: float = 0.88) -> bool:
    normalized_question = " ".join(str(question or "").split())
    if not normalized_question:
        return False
    for recent in recent_questions[-3:]:
        normalized_recent = " ".join(str(recent or "").split())
        if not normalized_recent:
            continue
        if normalized_question == normalized_recent:
            return True
        if SequenceMatcher(None, normalized_question, normalized_recent).ratio() >= threshold:
            return True
    return False


def evaluate_runtime_quality(result: dict[str, Any], recent_questions: list[str] | None = None) -> dict[str, Any]:
    safe_result = result if isinstance(result, dict) else {}
    recent = recent_questions or []
    question = extract_runtime_question(safe_result)
    decision = extract_runtime_decision(safe_result)
    checkpoint = safe_result.get("checkpointSummary") if isinstance(safe_result.get("checkpointSummary"), dict) else {}

    next_action = str(decision.get("nextAction") or "")
    difficulty = str(decision.get("difficulty") or "")
    requires_human_review = bool(
        safe_result.get("requiresHumanReview")
        or decision.get("requiresHumanReview")
        or checkpoint.get("requiresHumanReview")
    )

    checks = {
        "nonEmptyQuestion": bool(question),
        "validDecision": next_action in VALID_ACTIONS,
        "validDifficulty": difficulty in VALID_DIFFICULTIES,
        "notRepeated": not is_repeated_question(question, recent),
        "checkpointAvailable": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
        "humanReviewBlocked": requires_human_review,
    }

    reasons: list[str] = []
    if not checks["nonEmptyQuestion"]:
        reasons.append("LangGraph 没有生成可展示的问题")
    if not checks["validDecision"]:
        reasons.append(f"LangGraph 决策动作不合法：{next_action or '空'}")
    if not checks["validDifficulty"]:
        reasons.append(f"LangGraph 难度等级不合法：{difficulty or '空'}")
    if not checks["notRepeated"]:
        reasons.append("LangGraph 问题与最近问题重复度过高")
    if not checks["checkpointAvailable"]:
        reasons.append("LangGraph 缺少 checkpoint 摘要")
    if checks["humanReviewBlocked"]:
        reasons.append("LangGraph 标记需要人工复核")

    passed = (
        checks["nonEmptyQuestion"]
        and checks["validDecision"]
        and checks["validDifficulty"]
        and checks["notRepeated"]
        and checks["checkpointAvailable"]
        and not checks["humanReviewBlocked"]
    )

    return {
        "passed": passed,
        "fallbackToClassic": not passed,
        "riskLevel": "low" if passed else "high",
        "reasons": reasons,
        "checks": checks,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
python -m pytest tests/test_runtime_quality_gate.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: 提交本任务**

Run:

```powershell
git add tests/test_runtime_quality_gate.py backend_python/runtime_quality_gate.py
git commit -m "feat: add langgraph runtime quality gate"
```

---

### Task 2: Shadow Compare Evaluator

**Files:**
- Create: `tests/test_runtime_compare.py`
- Create: `backend_python/runtime_compare.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_runtime_compare.py`:

```python
from backend_python.runtime_compare import compare_runtime_outputs


def test_compare_runtime_outputs_detects_matching_action_and_difficulty() -> None:
    classic = {
        "runtime": "classic",
        "question": {"content": "请解释 Agent State。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {},
    }
    langgraph = {
        "runtime": "langgraph",
        "nextQuestion": {"content": "请解释 Agent State。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True, "threadId": "runtime-a"},
    }
    gate = {"passed": True, "fallbackToClassic": False, "reasons": [], "checks": {"checkpointAvailable": True}}

    summary = compare_runtime_outputs(classic, langgraph, gate, thread_id="runtime-a", runtime_mode="shadow")

    assert summary["threadId"] == "runtime-a"
    assert summary["runtimeMode"] == "shadow"
    assert summary["visibleRuntime"] == "classic"
    assert summary["comparison"]["actionMatched"] is True
    assert summary["comparison"]["difficultyMatched"] is True
    assert summary["comparison"]["qualityGatePassed"] is True
    assert summary["langgraph"]["checkpointExists"] is True


def test_compare_runtime_outputs_records_difference_reasons() -> None:
    classic = {
        "question": {"content": "请继续解释 RAG 日志 JSON。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "hard"},
    }
    langgraph = {
        "nextQuestion": {"content": "我们先换一个基础问题，什么是 RAG？"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True},
    }
    gate = {"passed": False, "fallbackToClassic": True, "reasons": ["LangGraph 标记需要人工复核"], "checks": {}}

    summary = compare_runtime_outputs(classic, langgraph, gate, thread_id="runtime-b", runtime_mode="shadow")

    assert summary["comparison"]["actionMatched"] is False
    assert summary["comparison"]["difficultyMatched"] is False
    assert summary["comparison"]["fallbackToClassic"] is True
    assert "两条链路的下一步动作不同" in summary["comparison"]["reasons"]
    assert "两条链路的难度选择不同" in summary["comparison"]["reasons"]
    assert "LangGraph 标记需要人工复核" in summary["comparison"]["reasons"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_runtime_compare.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'backend_python.runtime_compare'
```

- [ ] **Step 3: 实现最小代码**

Create `backend_python/runtime_compare.py`:

```python
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .runtime_quality_gate import extract_runtime_decision, extract_runtime_question


def _difficulty(result: dict[str, Any]) -> str:
    return str(extract_runtime_decision(result).get("difficulty") or "")


def _next_action(result: dict[str, Any]) -> str:
    return str(extract_runtime_decision(result).get("nextAction") or "")


def _question_similarity(left: str, right: str) -> float:
    left_normalized = " ".join(str(left or "").split())
    right_normalized = " ".join(str(right or "").split())
    if not left_normalized or not right_normalized:
        return 0.0
    return round(SequenceMatcher(None, left_normalized, right_normalized).ratio(), 2)


def compare_runtime_outputs(
    classic_result: dict[str, Any],
    langgraph_result: dict[str, Any],
    quality_gate: dict[str, Any],
    *,
    thread_id: str,
    runtime_mode: str,
) -> dict[str, Any]:
    classic_question = extract_runtime_question(classic_result)
    langgraph_question = extract_runtime_question(langgraph_result)
    classic_action = _next_action(classic_result)
    langgraph_action = _next_action(langgraph_result)
    classic_difficulty = _difficulty(classic_result)
    langgraph_difficulty = _difficulty(langgraph_result)
    checkpoint = langgraph_result.get("checkpointSummary") if isinstance(langgraph_result.get("checkpointSummary"), dict) else {}

    action_matched = classic_action == langgraph_action
    difficulty_matched = classic_difficulty == langgraph_difficulty
    reasons: list[str] = []
    if not action_matched:
        reasons.append("两条链路的下一步动作不同")
    if not difficulty_matched:
        reasons.append("两条链路的难度选择不同")
    reasons.extend(str(reason) for reason in quality_gate.get("reasons", []) if str(reason).strip())
    if not reasons:
        reasons.append("LangGraph 与 classic 本轮关键决策一致")

    return {
        "threadId": str(thread_id or ""),
        "runtimeMode": str(runtime_mode or ""),
        "visibleRuntime": "classic" if runtime_mode == "shadow" else str(runtime_mode or ""),
        "classic": {
            "status": str(classic_result.get("status") or "completed"),
            "nextAction": classic_action,
            "difficulty": classic_difficulty,
            "questionText": classic_question,
        },
        "langgraph": {
            "status": str(langgraph_result.get("status") or "completed"),
            "nextAction": langgraph_action,
            "difficulty": langgraph_difficulty,
            "questionText": langgraph_question,
            "checkpointExists": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
            "requiresHumanReview": bool(
                langgraph_result.get("requiresHumanReview")
                or extract_runtime_decision(langgraph_result).get("requiresHumanReview")
                or checkpoint.get("requiresHumanReview")
            ),
        },
        "comparison": {
            "actionMatched": action_matched,
            "difficultyMatched": difficulty_matched,
            "questionSimilarity": _question_similarity(classic_question, langgraph_question),
            "qualityGatePassed": bool(quality_gate.get("passed")),
            "fallbackToClassic": bool(quality_gate.get("fallbackToClassic")),
            "reasons": reasons,
        },
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
python -m pytest tests/test_runtime_compare.py tests/test_runtime_quality_gate.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 5: 提交本任务**

Run:

```powershell
git add tests/test_runtime_compare.py backend_python/runtime_compare.py
git commit -m "feat: compare classic and langgraph runtime outputs"
```

---

### Task 3: Agent Runtime 集成 Gate 与 Compare

**Files:**
- Modify: `tests/test_agent_runtime_switching.py`
- Modify: `backend_python/agent_runtime.py`

- [ ] **Step 1: 扩展失败测试**

Append to `tests/test_agent_runtime_switching.py`:

```python
def test_agent_runtime_langgraph_falls_back_to_classic_when_gate_fails() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": ""},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph",
            thread_id="runtime-gate-fail",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 RAG？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["fallbackRuntime"] == "langgraph"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert result["comparisonSummary"]["comparison"]["fallbackToClassic"] is True


def test_agent_runtime_shadow_records_quality_gate_and_comparison_summary() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic visible question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "langgraph shadow question"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="shadow",
            thread_id="runtime-shadow-v4",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": []},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["shadow"]["runtime"] == "langgraph"
    assert result["shadow"]["qualityGate"]["passed"] is True
    assert result["shadow"]["comparisonSummary"]["threadId"] == "runtime-shadow-v4"
    assert result["comparisonSummary"]["comparison"]["actionMatched"] is False
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py -q
```

Expected:

```text
KeyError: 'visibleRuntime'
```

- [ ] **Step 3: 修改 `agent_runtime.py`**

Modify `backend_python/agent_runtime.py`:

```python
from __future__ import annotations

from typing import Any, Awaitable, Callable

from .runtime_compare import compare_runtime_outputs
from .runtime_quality_gate import evaluate_runtime_quality


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


def _extract_recent_questions(payload: dict[str, Any]) -> list[str]:
    recent = payload.get("recentQuestions") or payload.get("recent_questions") or []
    if not isinstance(recent, list):
        return []
    return [str(item) for item in recent if str(item or "").strip()]


def _runtime_response(*, runtime: str, thread_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": runtime,
        "visibleRuntime": runtime,
        "threadId": thread_id,
        "status": str(result.get("status") or "completed"),
        "question": _extract_question(result),
        "decision": result.get("decision") if isinstance(result.get("decision"), dict) else {},
        "checkpointSummary": result.get("checkpointSummary") if isinstance(result.get("checkpointSummary"), dict) else {},
        "interrupt": result.get("interrupt") if isinstance(result.get("interrupt"), dict) else None,
        "runtimeTrace": result.get("runtimeTrace") if isinstance(result.get("runtimeTrace"), list) else [],
        "qualityGate": result.get("qualityGate") if isinstance(result.get("qualityGate"), dict) else None,
        "comparisonSummary": result.get("comparisonSummary") if isinstance(result.get("comparisonSummary"), dict) else None,
        "fallbackRuntime": "",
        "shadow": None,
    }
```

Then keep the existing `run_agent_runtime()` structure, but replace the body with:

```python
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
    recent_questions = _extract_recent_questions(payload)

    if runtime == "classic":
        classic_result = await classic_runner(**common)
        return _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)

    if runtime == "langgraph":
        langgraph_result = await langgraph_runner(**common)
        quality_gate = evaluate_runtime_quality(langgraph_result, recent_questions=recent_questions)
        if quality_gate["passed"]:
            response = _runtime_response(runtime="langgraph", thread_id=thread_id, result=langgraph_result)
            response["qualityGate"] = quality_gate
            response["comparisonSummary"] = compare_runtime_outputs(
                langgraph_result,
                langgraph_result,
                quality_gate,
                thread_id=thread_id,
                runtime_mode="langgraph",
            )
            return response

        classic_result = await classic_runner(**common)
        response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
        response["fallbackRuntime"] = "langgraph"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = compare_runtime_outputs(
            classic_result,
            langgraph_result,
            quality_gate,
            thread_id=thread_id,
            runtime_mode="langgraph",
        )
        return response

    classic_result = await classic_runner(**common)
    response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
    if runtime == "shadow":
        shadow_result = await langgraph_runner(**common)
        quality_gate = evaluate_runtime_quality(shadow_result, recent_questions=recent_questions)
        comparison = compare_runtime_outputs(
            classic_result,
            shadow_result,
            quality_gate,
            thread_id=thread_id,
            runtime_mode="shadow",
        )
        response["visibleRuntime"] = "classic"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = comparison
        response["shadow"] = {
            "runtime": "langgraph",
            "status": str(shadow_result.get("status") or "completed"),
            "question": _extract_question(shadow_result),
            "decision": shadow_result.get("decision") if isinstance(shadow_result.get("decision"), dict) else {},
            "checkpointSummary": shadow_result.get("checkpointSummary")
            if isinstance(shadow_result.get("checkpointSummary"), dict)
            else {},
            "qualityGate": quality_gate,
            "comparisonSummary": comparison,
            "runtimeTrace": shadow_result.get("runtimeTrace") if isinstance(shadow_result.get("runtimeTrace"), list) else [],
        }
    return response
```

- [ ] **Step 4: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py tests/test_runtime_quality_gate.py tests/test_runtime_compare.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: 提交本任务**

Run:

```powershell
git add backend_python/agent_runtime.py tests/test_agent_runtime_switching.py
git commit -m "feat: gate and compare langgraph runtime outputs"
```

---

### Task 4: Checkpoint Summary 项目侧持久化

**Files:**
- Create: `tests/test_langgraph_runtime_checkpoint_persistence.py`
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Create: `backend_python/langgraph_agent/checkpoint_persistence.py`
- Create: `alembic/versions/20260614_0001_add_langgraph_checkpoint_summaries.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_langgraph_runtime_checkpoint_persistence.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend_python.database import Base
from backend_python.langgraph_agent.checkpoint_persistence import (
    get_latest_checkpoint_summary,
    list_checkpoint_summaries,
    save_checkpoint_summary,
)


def build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_save_and_get_latest_checkpoint_summary() -> None:
    db = build_session()
    try:
        saved = save_checkpoint_summary(
            db,
            {
                "threadId": "thread-a",
                "runtime": "langgraph",
                "status": "completed",
                "currentNode": "generate_question",
                "roundCount": 2,
                "lastAction": "lower_difficulty",
                "lastQuestion": "什么是 Agent State？",
                "requiresHumanReview": False,
                "runtimeTrace": [{"node": "observe_state"}],
                "qualityGate": {"passed": True},
                "comparisonSummary": {"comparison": {"actionMatched": False}},
            },
        )

        latest = get_latest_checkpoint_summary(db, "thread-a")

        assert saved["threadId"] == "thread-a"
        assert latest["exists"] is True
        assert latest["threadId"] == "thread-a"
        assert latest["runtime"] == "langgraph"
        assert latest["qualityGate"]["passed"] is True
        assert latest["comparisonSummary"]["comparison"]["actionMatched"] is False
    finally:
        db.close()


def test_list_checkpoint_summaries_returns_newest_first() -> None:
    db = build_session()
    try:
        save_checkpoint_summary(db, {"threadId": "thread-b", "runtime": "langgraph", "status": "completed", "roundCount": 1})
        save_checkpoint_summary(db, {"threadId": "thread-b", "runtime": "langgraph", "status": "interrupted", "roundCount": 2})

        runs = list_checkpoint_summaries(db, "thread-b")

        assert len(runs) == 2
        assert runs[0]["roundCount"] == 2
        assert runs[1]["roundCount"] == 1
    finally:
        db.close()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_checkpoint_persistence.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'backend_python.langgraph_agent.checkpoint_persistence'
```

- [ ] **Step 3: 新增 ORM 模型**

Add to `backend_python/db_models.py` after `AgentDecisionLog`:

```python
class LangGraphCheckpointSummary(Base):
    __tablename__ = "langgraph_checkpoint_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(200), index=True)
    runtime: Mapped[str] = mapped_column(String(50), default="langgraph", index=True)
    status: Mapped[str] = mapped_column(String(50), default="completed", index=True)
    current_node: Mapped[str] = mapped_column(String(100), default="")
    round_count: Mapped[int] = mapped_column(Integer, default=0)
    last_action: Mapped[str] = mapped_column(String(80), default="")
    last_question: Mapped[str] = mapped_column(Text, default="")
    requires_human_review: Mapped[int] = mapped_column(Integer, default=0)
    interrupt_json: Mapped[str] = mapped_column(Text, default="")
    resume_decision: Mapped[str] = mapped_column(Text, default="")
    runtime_trace_json: Mapped[str] = mapped_column(Text, default="[]")
    quality_gate_json: Mapped[str] = mapped_column(Text, default="{}")
    comparison_json: Mapped[str] = mapped_column(Text, default="{}")
    raw_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: 新增持久化服务**

Create `backend_python/langgraph_agent/checkpoint_persistence.py`:

```python
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend_python.db_models import LangGraphCheckpointSummary
from backend_python.langgraph_agent.checkpoint_store import empty_checkpoint_summary, normalize_thread_id


def _json_dumps(value: Any, fallback: Any) -> str:
    safe_value = value if value is not None else fallback
    return json.dumps(safe_value, ensure_ascii=False)


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def serialize_checkpoint_summary(row: LangGraphCheckpointSummary) -> dict[str, Any]:
    return {
        "enabled": True,
        "exists": True,
        "id": row.id,
        "threadId": row.thread_id,
        "runtime": row.runtime,
        "status": row.status,
        "currentNode": row.current_node,
        "roundCount": row.round_count,
        "lastAction": row.last_action,
        "lastQuestion": row.last_question,
        "requiresHumanReview": bool(row.requires_human_review),
        "interrupt": _json_loads(row.interrupt_json, None) if row.interrupt_json else None,
        "resumeDecision": row.resume_decision,
        "runtimeTrace": _json_loads(row.runtime_trace_json, []),
        "qualityGate": _json_loads(row.quality_gate_json, {}),
        "comparisonSummary": _json_loads(row.comparison_json, {}),
        "rawSummary": _json_loads(row.raw_summary_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def save_checkpoint_summary(db: Session, summary: dict[str, Any]) -> dict[str, Any]:
    safe = summary if isinstance(summary, dict) else {}
    thread_id = normalize_thread_id(str(safe.get("threadId") or ""))
    row = LangGraphCheckpointSummary(
        thread_id=thread_id,
        runtime=str(safe.get("runtime") or "langgraph"),
        status=str(safe.get("status") or "completed"),
        current_node=str(safe.get("currentNode") or ""),
        round_count=int(safe.get("roundCount") or 0),
        last_action=str(safe.get("lastAction") or ""),
        last_question=str(safe.get("lastQuestion") or ""),
        requires_human_review=1 if safe.get("requiresHumanReview") else 0,
        interrupt_json=_json_dumps(safe.get("interrupt"), None) if safe.get("interrupt") else "",
        resume_decision=str(safe.get("resumeDecision") or ""),
        runtime_trace_json=_json_dumps(safe.get("runtimeTrace"), []),
        quality_gate_json=_json_dumps(safe.get("qualityGate"), {}),
        comparison_json=_json_dumps(safe.get("comparisonSummary"), {}),
        raw_summary_json=_json_dumps(safe, {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_checkpoint_summary(row)


def get_latest_checkpoint_summary(db: Session, thread_id: str) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    row = (
        db.query(LangGraphCheckpointSummary)
        .filter(LangGraphCheckpointSummary.thread_id == safe_thread_id)
        .order_by(LangGraphCheckpointSummary.id.desc())
        .first()
    )
    return serialize_checkpoint_summary(row) if row else empty_checkpoint_summary(safe_thread_id)


def list_checkpoint_summaries(db: Session, thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    safe_thread_id = normalize_thread_id(thread_id)
    rows = (
        db.query(LangGraphCheckpointSummary)
        .filter(LangGraphCheckpointSummary.thread_id == safe_thread_id)
        .order_by(LangGraphCheckpointSummary.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_checkpoint_summary(row) for row in rows]
```

- [ ] **Step 5: 补 SQLite 自动建表兼容**

Modify `backend_python/database.py` inside `ensure_sqlite_compatibility_schema()` before the final `if "interview_records" not in table_names:` block:

```python
        if "langgraph_checkpoint_summaries" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE langgraph_checkpoint_summaries (
                        id INTEGER NOT NULL PRIMARY KEY,
                        thread_id VARCHAR(200) NOT NULL,
                        runtime VARCHAR(50) NOT NULL DEFAULT 'langgraph',
                        status VARCHAR(50) NOT NULL DEFAULT 'completed',
                        current_node VARCHAR(100) NOT NULL DEFAULT '',
                        round_count INTEGER NOT NULL DEFAULT 0,
                        last_action VARCHAR(80) NOT NULL DEFAULT '',
                        last_question TEXT NOT NULL DEFAULT '',
                        requires_human_review INTEGER NOT NULL DEFAULT 0,
                        interrupt_json TEXT NOT NULL DEFAULT '',
                        resume_decision TEXT NOT NULL DEFAULT '',
                        runtime_trace_json TEXT NOT NULL DEFAULT '[]',
                        quality_gate_json TEXT NOT NULL DEFAULT '{}',
                        comparison_json TEXT NOT NULL DEFAULT '{}',
                        raw_summary_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_id ON langgraph_checkpoint_summaries (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_thread_id ON langgraph_checkpoint_summaries (thread_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_runtime ON langgraph_checkpoint_summaries (runtime)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_status ON langgraph_checkpoint_summaries (status)"))
```

- [ ] **Step 6: 新增 Alembic migration**

Create `alembic/versions/20260614_0001_add_langgraph_checkpoint_summaries.py`:

```python
"""add langgraph checkpoint summaries

Revision ID: 20260614_0001
Revises: 20260613_0001
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0001"
down_revision = "20260613_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "langgraph_checkpoint_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("runtime", sa.String(length=50), nullable=False, server_default="langgraph"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column("current_node", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("round_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_action", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("last_question", sa.Text(), nullable=False, server_default=""),
        sa.Column("requires_human_review", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupt_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("resume_decision", sa.Text(), nullable=False, server_default=""),
        sa.Column("runtime_trace_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("quality_gate_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("comparison_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("raw_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_langgraph_checkpoint_summaries_id"), "langgraph_checkpoint_summaries", ["id"], unique=False)
    op.create_index(op.f("ix_langgraph_checkpoint_summaries_thread_id"), "langgraph_checkpoint_summaries", ["thread_id"], unique=False)
    op.create_index(op.f("ix_langgraph_checkpoint_summaries_runtime"), "langgraph_checkpoint_summaries", ["runtime"], unique=False)
    op.create_index(op.f("ix_langgraph_checkpoint_summaries_status"), "langgraph_checkpoint_summaries", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_status"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_runtime"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_thread_id"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_id"), table_name="langgraph_checkpoint_summaries")
    op.drop_table("langgraph_checkpoint_summaries")
```

Before creating the migration file, run:

```powershell
Get-ChildItem alembic\versions | Sort-Object Name | Select-Object -Last 5
```

If the latest revision is not `20260613_0001`, set `down_revision` to the actual latest revision.

- [ ] **Step 7: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_checkpoint_persistence.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 8: 提交本任务**

Run:

```powershell
git add backend_python/db_models.py backend_python/database.py backend_python/langgraph_agent/checkpoint_persistence.py alembic/versions tests/test_langgraph_runtime_checkpoint_persistence.py
git commit -m "feat: persist langgraph checkpoint summaries"
```

---

### Task 5: LangGraph Runtime Routes 持久化与查询

**Files:**
- Modify: `tests/test_langgraph_runtime_interrupt_resume.py`
- Modify: `backend_python/routes/langgraph_agent.py`

- [ ] **Step 1: 扩展 route 测试**

Add a test to `tests/test_langgraph_runtime_interrupt_resume.py`:

```python
def test_langgraph_runtime_runs_endpoint_lists_thread_runs(client, admin_token_headers) -> None:
    payload = {
        "threadId": "route-runtime-runs",
        "agentRuntime": "langgraph",
        "answer": "我不知道 checkpoint 是什么",
        "agentMode": "coach",
    }

    run_response = client.post("/api/langgraph-agent/runtime/run", json=payload, headers=admin_token_headers)
    assert run_response.status_code == 200

    runs_response = client.get("/api/langgraph-agent/runtime/runs/route-runtime-runs", headers=admin_token_headers)
    assert runs_response.status_code == 200
    body = runs_response.json()
    assert body["threadId"] == "route-runtime-runs"
    assert len(body["items"]) >= 1
    assert body["items"][0]["threadId"] == "route-runtime-runs"
    assert "runtime" in body["items"][0]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_interrupt_resume.py -q
```

Expected:

```text
404 Not Found
```

- [ ] **Step 3: 修改 route 保存 summary**

Modify `backend_python/routes/langgraph_agent.py`:

```python
from backend_python.database import get_db
from backend_python.langgraph_agent.checkpoint_persistence import (
    get_latest_checkpoint_summary,
    list_checkpoint_summaries,
    save_checkpoint_summary,
)
from sqlalchemy.orm import Session
from fastapi import Depends
```

For `runtime_run`, add `db: Session = Depends(get_db)` to the function parameters. After `checkpoint = record_checkpoint_summary(...)`, merge runtime fields:

```python
    checkpoint["qualityGate"] = result.get("qualityGate") if isinstance(result.get("qualityGate"), dict) else {}
    checkpoint["comparisonSummary"] = result.get("comparisonSummary") if isinstance(result.get("comparisonSummary"), dict) else {}
    persisted_checkpoint = save_checkpoint_summary(db, checkpoint)
```

Return `persisted_checkpoint` as `checkpointSummary`.

For resume route, add `db: Session = Depends(get_db)` and after `resumed = checkpoint_summary_store.mark_resumed(...)` call:

```python
    persisted_checkpoint = save_checkpoint_summary(db, resumed)
```

Return `persisted_checkpoint` as `checkpointSummary`.

Add route:

```python
@router.get("/runtime/runs/{thread_id}")
async def runtime_runs(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "items": list_checkpoint_summaries(db, thread_id),
    }
```

Update existing checkpoint route so it tries persisted summary first:

```python
@router.get("/checkpoint/{thread_id}")
async def checkpoint_summary(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    persisted = get_latest_checkpoint_summary(db, thread_id)
    return persisted if persisted.get("exists") else summarize_checkpoint(thread_id)
```

- [ ] **Step 4: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_langgraph_runtime_interrupt_resume.py tests/test_langgraph_runtime_checkpoint_persistence.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: 提交本任务**

Run:

```powershell
git add backend_python/routes/langgraph_agent.py tests/test_langgraph_runtime_interrupt_resume.py
git commit -m "feat: expose langgraph runtime run history"
```

---

### Task 6: AI Debug 后端增强

**Files:**
- Modify: `tests/test_admin_ai_debug.py`
- Modify: `backend_python/ai_debug.py`
- Modify: `backend_python/routes/admin.py`

- [ ] **Step 1: 扩展 AI Debug 测试**

Add to `tests/test_admin_ai_debug.py`:

```python
def test_admin_ai_debug_detail_contains_runtime_quality_and_comparison() -> None:
    checkpoint = {
        "exists": True,
        "threadId": "debug-runtime-v4",
        "runtime": "langgraph",
        "status": "completed",
        "currentNode": "generate_question",
        "qualityGate": {"passed": False, "fallbackToClassic": True, "reasons": ["LangGraph 没有生成可展示的问题"]},
        "comparisonSummary": {
            "visibleRuntime": "classic",
            "comparison": {
                "actionMatched": False,
                "difficultyMatched": False,
                "qualityGatePassed": False,
                "fallbackToClassic": True,
                "reasons": ["两条链路的下一步动作不同"],
            },
        },
    }

    normalized = normalize_checkpoint(checkpoint, "debug-runtime-v4")

    assert normalized["qualityGate"]["passed"] is False
    assert normalized["comparisonSummary"]["comparison"]["fallbackToClassic"] is True
    assert normalized["visibleRuntime"] == "classic"
```

If `normalize_checkpoint` is not imported in this test file, add:

```python
from backend_python.ai_debug import normalize_checkpoint
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
```

Expected:

```text
KeyError: 'qualityGate'
```

- [ ] **Step 3: 修改 `normalize_checkpoint`**

Modify `backend_python/ai_debug.py` inside `normalize_checkpoint()` return dict:

```python
        "qualityGate": checkpoint.get("qualityGate") if isinstance(checkpoint.get("qualityGate"), dict) else {},
        "comparisonSummary": checkpoint.get("comparisonSummary")
        if isinstance(checkpoint.get("comparisonSummary"), dict)
        else {},
        "visibleRuntime": (
            checkpoint.get("comparisonSummary", {}).get("visibleRuntime")
            if isinstance(checkpoint.get("comparisonSummary"), dict)
            else ""
        )
        or checkpoint.get("visibleRuntime")
        or checkpoint.get("runtime")
        or "",
```

Modify `build_ai_debug_diagnostics()`:

```python
    quality_gate = langgraph.get("qualityGate") if isinstance(langgraph.get("qualityGate"), dict) else {}
    if quality_gate and not quality_gate.get("passed", True):
        diagnostics.append(
            _diagnostic(
                "runtime_quality_gate_failed",
                "warning",
                "LangGraph 输出未通过门禁",
                "本轮 LangGraph 结果没有进入可见链路，系统应回退 classic Agent。",
            )
        )
```

- [ ] **Step 4: 修改 admin route 优先读取持久化 summary**

Modify `backend_python/routes/admin.py` where checkpoint is built for AI Debug detail:

```python
from ..langgraph_agent.checkpoint_persistence import get_latest_checkpoint_summary
```

When there is a `db` session and `thread_id`, prefer:

```python
persisted_checkpoint = get_latest_checkpoint_summary(db, str(thread_id))
checkpoint = persisted_checkpoint if persisted_checkpoint.get("exists") else checkpoint_for_agent_log(log)
```

- [ ] **Step 5: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py tests/test_langgraph_runtime_checkpoint_persistence.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: 提交本任务**

Run:

```powershell
git add backend_python/ai_debug.py backend_python/routes/admin.py tests/test_admin_ai_debug.py
git commit -m "feat: surface langgraph runtime quality in ai debug"
```

---

### Task 7: Vue3 管理员后台展示 Runtime 对比

**Files:**
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/stores/admin.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: 扩展 store 测试**

Add to `frontend/src/stores/admin.test.ts`:

```ts
it("keeps runtime quality and comparison fields in ai debug detail", async () => {
  const store = useAdminStore();
  vi.spyOn(adminApi, "fetchAiDebugDetail").mockResolvedValue({
    summary: { traceId: 1, threadId: "debug-runtime-v4" },
    rag: { items: [], totalHitCount: 0 },
    agent: {},
    langgraph: {
      exists: true,
      runtime: "langgraph",
      visibleRuntime: "classic",
      qualityGate: { passed: false, fallbackToClassic: true, reasons: ["LangGraph 没有生成可展示的问题"] },
      comparisonSummary: {
        comparison: {
          actionMatched: false,
          difficultyMatched: false,
          fallbackToClassic: true,
          reasons: ["两条链路的下一步动作不同"],
        },
      },
    },
    diagnostics: [],
  });

  await store.loadAiDebugDetail(1);

  expect(store.selectedAiDebugDetail?.langgraph?.qualityGate?.passed).toBe(false);
  expect(store.selectedAiDebugDetail?.langgraph?.comparisonSummary?.comparison?.fallbackToClassic).toBe(true);
});
```

- [ ] **Step 2: 扩展页面测试**

Add to `frontend/src/pages/app/admin-page.test.ts`:

```ts
it("renders langgraph runtime quality gate and comparison summary", async () => {
  const admin = useAdminStore();
  admin.selectedAiDebugDetail = {
    summary: { traceId: 1, threadId: "debug-runtime-v4" },
    rag: { items: [], totalHitCount: 0 },
    agent: {},
    langgraph: {
      exists: true,
      runtime: "langgraph",
      visibleRuntime: "classic",
      status: "completed",
      qualityGate: { passed: false, fallbackToClassic: true, reasons: ["LangGraph 没有生成可展示的问题"] },
      comparisonSummary: {
        comparison: {
          actionMatched: false,
          difficultyMatched: false,
          fallbackToClassic: true,
          reasons: ["两条链路的下一步动作不同"],
        },
      },
    },
    diagnostics: [],
  };

  render(AdminPage);

  expect(screen.getByText("Runtime 对比")).toBeTruthy();
  expect(screen.getByText(/可见链路：classic/)).toBeTruthy();
  expect(screen.getByText(/Quality Gate：未通过/)).toBeTruthy();
  expect(screen.getByText(/Fallback：已回退 classic/)).toBeTruthy();
});
```

- [ ] **Step 3: 运行前端 focused tests 确认失败**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected:

```text
Unable to find an element with the text: Runtime 对比
```

- [ ] **Step 4: 修改 store 类型**

In `frontend/src/stores/admin.ts`, extend the debug detail type:

```ts
type RuntimeQualityGate = {
  passed?: boolean;
  fallbackToClassic?: boolean;
  riskLevel?: string;
  reasons?: string[];
  checks?: Record<string, boolean>;
};

type RuntimeComparisonSummary = {
  visibleRuntime?: string;
  comparison?: {
    actionMatched?: boolean;
    difficultyMatched?: boolean;
    qualityGatePassed?: boolean;
    fallbackToClassic?: boolean;
    reasons?: string[];
  };
};
```

Add these fields to the existing `langgraph` detail type:

```ts
qualityGate?: RuntimeQualityGate;
comparisonSummary?: RuntimeComparisonSummary;
visibleRuntime?: string;
```

- [ ] **Step 5: 修改 AdminPage 展示**

In `frontend/src/pages/app/AdminPage.vue`, under the existing LangGraph debug block, add:

```vue
<div class="debug-subsection">
  <h4>Runtime 对比</h4>
  <p>可见链路：{{ debugText(admin.selectedAiDebugDetail.langgraph, "visibleRuntime", "未记录") }}</p>
  <p>
    Quality Gate：{{
      runtimeQualityPassed ? "通过" : "未通过"
    }}
  </p>
  <p>
    Fallback：{{
      runtimeFallbackToClassic ? "已回退 classic" : "未触发"
    }}
  </p>
  <ul v-if="runtimeComparisonReasons.length" class="debug-list">
    <li v-for="reason in runtimeComparisonReasons" :key="reason">{{ reason }}</li>
  </ul>
</div>
```

In `<script setup>`, add:

```ts
const runtimeQualityPassed = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const gate = langgraph?.qualityGate as DebugRecord | undefined;
  return Boolean(gate?.passed);
});

const runtimeFallbackToClassic = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const gate = langgraph?.qualityGate as DebugRecord | undefined;
  const comparisonSummary = langgraph?.comparisonSummary as DebugRecord | undefined;
  const comparison = comparisonSummary?.comparison as DebugRecord | undefined;
  return Boolean(gate?.fallbackToClassic || comparison?.fallbackToClassic);
});

const runtimeComparisonReasons = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const comparisonSummary = langgraph?.comparisonSummary as DebugRecord | undefined;
  const comparison = comparisonSummary?.comparison as DebugRecord | undefined;
  const reasons = comparison?.reasons;
  return Array.isArray(reasons) ? reasons.map(String).filter(Boolean) : [];
});
```

- [ ] **Step 6: 运行前端 focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected:

```text
selected tests passed
```

- [ ] **Step 7: 提交本任务**

Run:

```powershell
git add frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: show langgraph runtime comparison in admin"
```

---

### Task 8: 学习文档与路线更新

**Files:**
- Create: `docs/learning/23-LangGraph从旁路到候选主链路如何灰度迁移.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: 新增学习文档**

Create `docs/learning/23-LangGraph从旁路到候选主链路如何灰度迁移.md`:

```markdown
# LangGraph 从旁路到候选主链路如何灰度迁移

## 1. 这一阶段解决什么问题

项目里已经有 classic Agent，也已经有 LangGraph 旁路 runtime。V4 不是重新接入 LangGraph，而是解决一个更工程化的问题：

```text
一个新 runtime 要怎样证明自己足够稳定，才能慢慢进入主链路？
```

答案是三件事：

- shadow compare：先后台对比，不直接影响用户。
- runtime quality gate：质量门禁不过就不展示。
- fallback classic：新链路异常时退回旧链路。

## 2. 为什么不直接替换主链路

面试主链路不只负责生成一句问题，还串着 RAG 检索、Agent 决策、历史记录、报告、训练任务、前端展示和后台日志。

直接替换的风险是：LangGraph 某一轮输出异常，就可能影响真实用户的完整面试体验。

所以更稳的路线是：

```text
classic Agent 继续服务用户
LangGraph 在 shadow 模式运行
系统记录两边差异
质量稳定后再考虑灰度迁移
```

## 3. shadow compare 是什么

shadow compare 的意思是：同一份 Agent State 同时给 classic Agent 和 LangGraph runtime 使用。

用户看到 classic Agent 的问题，后台记录 LangGraph 生成的问题和决策。

系统会比较：

- nextAction 是否一致。
- difficulty 是否一致。
- question 是否接近。
- LangGraph 是否触发 human review。
- LangGraph 是否缺少 checkpoint。
- LangGraph 是否需要 fallback。

## 4. runtime quality gate 是什么

quality gate 是一道门禁。LangGraph 结果想进入用户可见链路，必须先通过检查。

典型检查包括：

- 问题不能为空。
- 问题不能和最近几轮高度重复。
- nextAction 必须合法。
- difficulty 必须合法。
- checkpoint summary 必须存在。
- requiresHumanReview=true 时不能直接展示。

## 5. checkpoint summary 和完整 graph state 的区别

checkpoint summary 是项目侧用于观察和调试的摘要。

它记录：

- threadId。
- runtime。
- status。
- currentNode。
- lastAction。
- lastQuestion。
- qualityGate。
- comparisonSummary。

完整 graph state 是 LangGraph 内部用于恢复执行状态的数据。V4 先做 summary 持久化，不承诺完整 graph state 生产级恢复。

## 6. 面试时怎么讲

可以这样表达：

```text
我的项目没有为了写 LangGraph 而强行替换原有 Agent 主链路。我采用了渐进迁移：classic Agent 保持稳定可见链路，LangGraph 先作为 shadow runtime 跑同一份状态。

系统会比较两条链路的 action、difficulty、question 和 checkpoint，并用 quality gate 判断 LangGraph 输出是否可见。如果 LangGraph 输出为空、重复、非法或需要人工复核，就 fallback classic。

这种设计体现的是 Agent 工程化治理能力，而不是简单框架接入。
```
```

- [ ] **Step 2: 更新路线文档**

Update `docs/roadmap/current-state.md`:

```text
当前 active plan：
docs/plans/active/langgraph-runtime-deepening-v4.md
```

Keep V4 as active until all implementation tasks and verification pass.

- [ ] **Step 3: 更新 README 状态**

Update `docs/plans/README.md`:

```text
当前 active plan：
docs/plans/active/langgraph-runtime-deepening-v4.md

当前 active spec：
docs/specs/active/langgraph-runtime-deepening-v4-design.md
```

- [ ] **Step 4: 提交本任务**

Run:

```powershell
git add docs/learning/23-LangGraph从旁路到候选主链路如何灰度迁移.md docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md
git commit -m "docs: explain langgraph runtime migration"
```

---

### Task 9: 全量验证与浏览器检查

**Files:**
- No source file changes unless verification finds a defect.

- [ ] **Step 1: 后端全量测试**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 2: 前端全量测试**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: 前端构建**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected:

```text
built successfully
```

- [ ] **Step 4: 启动本地服务**

Run backend:

```powershell
.\start-backend.cmd
```

Run frontend:

```powershell
.\start-frontend.cmd
```

Expected:

```text
FastAPI backend listens on 127.0.0.1:8000
Vue frontend listens on 127.0.0.1:5173
```

- [ ] **Step 5: 浏览器验证管理员后台**

Open:

```text
http://127.0.0.1:5173/vue/app/admin
```

Verify:

```text
AI Debug Console 能看到 Runtime 对比。
Quality Gate 能显示通过或未通过。
Fallback 能显示是否回退 classic。
页面没有 undefined。
移动端宽度 390px 左右没有横向溢出。
```

- [ ] **Step 6: 完成归档**

After all tests pass and browser verification is complete:

```powershell
Move-Item docs\specs\active\langgraph-runtime-deepening-v4-design.md docs\specs\completed\langgraph-runtime-deepening-v4-design.md
Move-Item docs\plans\active\langgraph-runtime-deepening-v4.md docs\plans\completed\langgraph-runtime-deepening-v4.md
```

Then update:

```text
docs/specs/README.md
docs/plans/README.md
docs/roadmap/current-state.md
```

State that LangGraph Runtime Deepening V4 is completed, and list the verification commands that passed.

- [ ] **Step 7: 最终提交**

Run:

```powershell
git add docs/specs docs/plans docs/roadmap
git commit -m "docs: complete langgraph runtime deepening v4"
```

---

## Self-Review

### Spec coverage

- Shadow compare：Task 2、Task 3、Task 7 覆盖。
- Runtime quality gate：Task 1、Task 3、Task 6、Task 7 覆盖。
- Checkpoint summary persistence：Task 4、Task 5 覆盖。
- AI Debug Console comparison visibility：Task 6、Task 7 覆盖。
- Migration learning doc：Task 8 覆盖。
- Compatibility with `/api/interview/next-question`：本计划不改该接口。
- No direct LangGraph main-chain replacement：Task 3 保持 classic 默认，shadow 仍返回 classic 可见结果。

### Placeholder scan

本计划未保留占位表达。每个开发任务均包含测试、实现、运行命令和提交命令。

### Type consistency

统一字段名：

- `qualityGate`
- `comparisonSummary`
- `visibleRuntime`
- `fallbackRuntime`
- `threadId`
- `checkpointSummary`

这些字段在后端 runtime、checkpoint persistence、AI Debug 和 Vue3 管理员后台中保持一致。
