# LangGraph Agent V2 Real RAG Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing LangGraph V1 POC into a V2 side-path workflow that supports `threadId`, MemorySaver checkpoint summaries, real/fake RAG adapters, real/fake Agent decision adapters, and V2 experimental routes without replacing `/api/interview/next-question`.

**Architecture:** Keep the existing self-built Interview Orchestrator Agent as the production main path. Add a V2 LangGraph service layer that wraps current RAG tools and Agent decision logic through adapters, compiles a checkpointer-backed graph, and exposes a separate experimental API. Tests must use fake retrievers and fake model decisions so they remain stable without calling real models.

**Tech Stack:** FastAPI, Pydantic, LangGraph `StateGraph`, LangGraph `MemorySaver`, pytest, existing project modules under `backend_python/`.

---

## File Structure

- Modify: `backend_python/langgraph_agent/state.py`
  - Add V2 state fields: `threadId`, `applicationProfileId`, `roundCount`, `remainingRounds`, `checkpointSummary`, `useRealRag`, `useRealDecision`.
- Modify: `backend_python/langgraph_agent/graph.py`
  - Keep V1 `run_interview_graph_poc()` unchanged.
  - Add injectable V2 graph builder and `run_interview_graph_v2()`.
- Modify: `backend_python/langgraph_agent/nodes.py`
  - Keep V1 node behavior compatible.
  - Add V2 node factories or optional dependency injection for retrieval and decision behavior.
- Create: `backend_python/langgraph_agent/adapters.py`
  - Wrap existing `agent_tools.py` and `interview_agent.py` so LangGraph nodes can reuse real RAG and real Agent decision logic without duplicating algorithms.
- Create: `backend_python/langgraph_agent/checkpoint.py`
  - Own the shared `MemorySaver`, graph config builder, and in-process checkpoint summary store.
- Create: `backend_python/langgraph_agent/service.py`
  - Route-facing service functions: `run_langgraph_agent_v2()` and `get_langgraph_checkpoint_summary()`.
- Modify: `backend_python/routes/langgraph_agent.py`
  - Keep `/next-question-poc`.
  - Add `/next-question-v2`.
  - Add `/checkpoint/{thread_id}`.
- Create or modify tests:
  - `tests/test_langgraph_agent_checkpoint.py`
  - `tests/test_langgraph_agent_adapters.py`
  - `tests/test_langgraph_agent_graph_v2.py`
  - `tests/test_langgraph_agent_route.py`
- Create: `docs/learning/09-LangGraph checkpoint和thread state怎么理解.md`
  - Explain checkpoint, thread state, normal DB records, and `AgentDecisionLog`.
- Modify: `docs/roadmap/project-progress.md`
  - Record implementation progress after verification.

---

## Task 1: Checkpoint Foundation

**Files:**
- Test: `tests/test_langgraph_agent_checkpoint.py`
- Create: `backend_python/langgraph_agent/checkpoint.py`
- Modify: `backend_python/langgraph_agent/state.py`
- Modify: `backend_python/langgraph_agent/graph.py`

- [ ] **Step 1: Write failing checkpoint tests**

Create `tests/test_langgraph_agent_checkpoint.py` with tests that prove:

```python
from backend_python.langgraph_agent.checkpoint import (
    build_graph_config,
    record_checkpoint_summary,
    summarize_checkpoint,
)


def test_build_graph_config_uses_thread_id():
    config = build_graph_config("interview-demo-001")

    assert config == {"configurable": {"thread_id": "interview-demo-001"}}


def test_checkpoint_summary_is_recorded_by_thread_id():
    record_checkpoint_summary(
        thread_id="interview-demo-001",
        state={
            "roundCount": 2,
            "decision": {"nextAction": "lower_difficulty"},
            "nextQuestion": {"prompt": "你能先解释 RAG 的基本流程吗？"},
            "nodeTrace": [{"nodeName": "observe_state"}, {"nodeName": "select_action"}],
        },
    )

    summary = summarize_checkpoint("interview-demo-001")

    assert summary["exists"] is True
    assert summary["threadId"] == "interview-demo-001"
    assert summary["roundCount"] == 2
    assert summary["lastAction"] == "lower_difficulty"
    assert summary["lastQuestion"] == "你能先解释 RAG 的基本流程吗？"
    assert summary["nodeTraceCount"] == 2


def test_missing_checkpoint_summary_returns_exists_false():
    summary = summarize_checkpoint("missing-thread")

    assert summary["exists"] is False
    assert summary["threadId"] == "missing-thread"
```

- [ ] **Step 2: Run checkpoint tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_checkpoint.py -q
```

Expected: fail because `backend_python.langgraph_agent.checkpoint` does not exist yet.

- [ ] **Step 3: Implement checkpoint module**

Create `backend_python/langgraph_agent/checkpoint.py`:

```python
from typing import Any

from langgraph.checkpoint.memory import MemorySaver


memory_saver = MemorySaver()
_checkpoint_summaries: dict[str, dict[str, Any]] = {}


def build_graph_config(thread_id: str) -> dict[str, Any]:
    safe_thread_id = str(thread_id or "default-thread").strip() or "default-thread"
    return {"configurable": {"thread_id": safe_thread_id}}


def record_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    safe_thread_id = str(thread_id or "default-thread").strip() or "default-thread"
    node_trace = state.get("nodeTrace") if isinstance(state.get("nodeTrace"), list) else []
    decision = state.get("decision") if isinstance(state.get("decision"), dict) else {}
    next_question = state.get("nextQuestion") if isinstance(state.get("nextQuestion"), dict) else {}
    summary = {
        "enabled": True,
        "exists": True,
        "threadId": safe_thread_id,
        "roundCount": int(state.get("roundCount") or 0),
        "lastAction": str(decision.get("nextAction") or ""),
        "lastQuestion": str(next_question.get("prompt") or ""),
        "nodeTraceCount": len(node_trace),
        "stateKeys": sorted(str(key) for key in state.keys()),
    }
    _checkpoint_summaries[safe_thread_id] = summary
    return summary


def summarize_checkpoint(thread_id: str) -> dict[str, Any]:
    safe_thread_id = str(thread_id or "default-thread").strip() or "default-thread"
    if safe_thread_id not in _checkpoint_summaries:
        return {
            "enabled": True,
            "exists": False,
            "threadId": safe_thread_id,
            "roundCount": 0,
            "lastAction": "",
            "lastQuestion": "",
            "nodeTraceCount": 0,
            "stateKeys": [],
        }
    return dict(_checkpoint_summaries[safe_thread_id])
```

- [ ] **Step 4: Extend graph state for V2 metadata**

Modify `backend_python/langgraph_agent/state.py` so `InterviewGraphState` includes:

```python
threadId: str
applicationProfileId: int | None
roundCount: int
remainingRounds: int
checkpointSummary: dict[str, Any]
useRealRag: bool
useRealDecision: bool
```

Update `build_initial_graph_state()` parameters and returned dict with safe defaults:

```python
thread_id: str = "default-thread",
application_profile_id: int | None = None,
use_real_rag: bool = False,
use_real_decision: bool = False,
```

- [ ] **Step 5: Run checkpoint tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_checkpoint.py tests/test_langgraph_agent_state.py -q
```

Expected: pass.

---

## Task 2: Real/Fake RAG Adapter

**Files:**
- Test: `tests/test_langgraph_agent_adapters.py`
- Create: `backend_python/langgraph_agent/adapters.py`
- Modify: `backend_python/langgraph_agent/nodes.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_langgraph_agent_adapters.py` with:

```python
import pytest

from backend_python.langgraph_agent.adapters import retrieve_real_context_for_graph


def test_retrieve_real_context_for_graph_uses_injected_retrievers():
    def role_retrieve(profile, next_stage, limit=3):
        return [{"id": "role-1", "content": "岗位要求 RAG 和 Agent", "score": 0.9}]

    def question_retrieve(profile, next_stage, limit=3):
        return [{"id": "question-1", "content": "请解释 checkpoint", "score": 0.8}]

    def memory_retrieve(profile, limit=5):
        return [{"id": "memory-1", "content": "候选人 RAG 基础较弱", "score": 0.7}]

    result = retrieve_real_context_for_graph(
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="技术追问",
        role_retrieve_fn=role_retrieve,
        question_retrieve_fn=question_retrieve,
        memory_retrieve_fn=memory_retrieve,
    )

    assert result["roleHits"][0]["id"] == "role-1"
    assert result["questionHits"][0]["id"] == "question-1"
    assert result["memoryHits"][0]["id"] == "memory-1"
    assert [call["toolName"] for call in result["toolCalls"]] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    ]
    assert result["retrievalQuality"]["roleKnowledge"]["hitCount"] == 1


def test_retrieve_real_context_for_graph_falls_back_when_retriever_fails():
    def broken_role(profile, next_stage, limit=3):
        raise RuntimeError("role retriever failed")

    result = retrieve_real_context_for_graph(
        profile={},
        next_stage="技术追问",
        role_retrieve_fn=broken_role,
        question_retrieve_fn=lambda profile, next_stage, limit=3: [],
        memory_retrieve_fn=lambda profile, limit=5: [],
    )

    assert result["roleHits"] == []
    assert result["toolCalls"][0]["success"] is False
    assert result["retrievalQuality"]["roleKnowledge"]["hitCount"] == 0
```

- [ ] **Step 2: Run adapter tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_adapters.py -q
```

Expected: fail because `adapters.py` does not exist.

- [ ] **Step 3: Implement RAG adapter**

Create `backend_python/langgraph_agent/adapters.py` and implement `retrieve_real_context_for_graph()` using existing:

```python
retrieve_role_knowledge_tool()
retrieve_question_bank_tool()
retrieve_candidate_memory_tool()
evaluate_retrieval_quality()
```

Return exactly:

```python
{
    "roleHits": role_hits,
    "questionHits": question_hits,
    "memoryHits": memory_hits,
    "toolCalls": tool_calls,
    "retrievalQuality": {
        "roleKnowledge": evaluate_retrieval_quality(role_hits),
        "questionBank": evaluate_retrieval_quality(question_hits),
        "candidateMemory": evaluate_retrieval_quality(memory_hits),
    },
}
```

- [ ] **Step 4: Add injectable V2 retrieve node**

Modify `backend_python/langgraph_agent/nodes.py` to add:

```python
def make_retrieve_context_v2_node(retrieve_context_fn):
    def retrieve_context_v2_node(state):
        result = retrieve_context_fn(
            profile=dict(state.get("profile") or {}),
            next_stage=str(state.get("nextStage") or ""),
        )
        return {
            **result,
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="retrieve_context",
                    input_summary={"nextStage": state.get("nextStage", "")},
                    output_summary={
                        "roleHitCount": len(result.get("roleHits") or []),
                        "questionHitCount": len(result.get("questionHits") or []),
                        "memoryHitCount": len(result.get("memoryHits") or []),
                    },
                    fallback_used=any(not call.get("success") for call in result.get("toolCalls", [])),
                ),
            ],
        }
    return retrieve_context_v2_node
```

- [ ] **Step 5: Run adapter tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_adapters.py tests/test_langgraph_agent_nodes.py -q
```

Expected: pass.

---

## Task 3: Real/Fake Agent Decision Adapter

**Files:**
- Test: `tests/test_langgraph_agent_adapters.py`
- Modify: `backend_python/langgraph_agent/adapters.py`
- Modify: `backend_python/langgraph_agent/nodes.py`

- [ ] **Step 1: Add failing decision adapter tests**

Append to `tests/test_langgraph_agent_adapters.py`:

```python
import asyncio

from backend_python.langgraph_agent.adapters import decide_real_action_for_graph


def test_decide_real_action_for_graph_uses_injected_model_decision():
    async def fake_model(**kwargs):
        return {
            "nextAction": "deep_follow_up",
            "stage": "技术追问",
            "difficulty": "medium",
            "focus": "LangGraph checkpoint",
            "reason": "候选人回答较完整，可以追问 checkpoint。",
            "tools": ["retrieve_context", "analyze_answer"],
            "triggerRules": ["strong_answer"],
            "agentMode": "coach",
            "shouldUpdateMemory": True,
        }

    result = asyncio.run(
        decide_real_action_for_graph(
            profile={"targetRole": "AI 应用开发实习生"},
            history=[{"question": "什么是 checkpoint？", "answer": "它能保存图状态，方便恢复。"}],
            next_stage="技术追问",
            agent_mode="coach",
            role_hits=[],
            question_hits=[],
            memory_hits=[],
            call_model_fn=fake_model,
        )
    )

    assert result["decision"]["nextAction"] == "deep_follow_up"
    assert result["decision"]["fallbackUsed"] is False
    assert result["decision"]["decisionSummary"]


def test_decide_real_action_for_graph_falls_back_for_invalid_model_output():
    async def invalid_model(**kwargs):
        return {"nextAction": "invalid_action"}

    result = asyncio.run(
        decide_real_action_for_graph(
            profile={},
            history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
            next_stage="技术追问",
            agent_mode="coach",
            role_hits=[],
            question_hits=[],
            memory_hits=[],
            call_model_fn=invalid_model,
        )
    )

    assert result["decision"]["nextAction"] in {"lower_difficulty", "switch_topic"}
    assert result["decision"]["fallbackUsed"] is True
    assert result["agentState"]["answerStatus"] == "不会"
```

- [ ] **Step 2: Run adapter tests and verify decision tests fail**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_adapters.py -q
```

Expected: fail because `decide_real_action_for_graph()` does not exist.

- [ ] **Step 3: Implement decision adapter**

Add `decide_real_action_for_graph()` to `backend_python/langgraph_agent/adapters.py`.

It must:

- Build state with `build_agent_state()`.
- Call existing `decide_next_action()`.
- Return both `agentState` and `decision`.
- Never raise if the model output is invalid; existing normalize/fallback handles that.

- [ ] **Step 4: Add injectable V2 select action node**

Modify `backend_python/langgraph_agent/nodes.py` to add an async-capable node factory:

```python
def make_select_action_v2_node(decide_action_fn):
    async def select_action_v2_node(state):
        result = await decide_action_fn(
            profile=dict(state.get("profile") or {}),
            history=list(state.get("history") or []),
            next_stage=str(state.get("nextStage") or ""),
            agent_mode=str(state.get("agentMode") or "interview"),
            role_hits=list(state.get("roleHits") or []),
            question_hits=list(state.get("questionHits") or []),
            memory_hits=list(state.get("memoryHits") or []),
        )
        decision = dict(result.get("decision") or {})
        return {
            "decision": decision,
            "agentState": result.get("agentState", {}),
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="select_action",
                    input_summary={"answerStatus": (result.get("agentState") or {}).get("answerStatus", "")},
                    output_summary={
                        "nextAction": decision.get("nextAction", ""),
                        "difficulty": decision.get("difficulty", ""),
                        "focus": decision.get("focus", ""),
                    },
                    fallback_used=bool(decision.get("fallbackUsed")),
                ),
            ],
        }
    return select_action_v2_node
```

- [ ] **Step 5: Run adapter tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_adapters.py -q
```

Expected: pass.

---

## Task 4: V2 Graph Service and Routes

**Files:**
- Test: `tests/test_langgraph_agent_graph_v2.py`
- Test: `tests/test_langgraph_agent_route.py`
- Create: `backend_python/langgraph_agent/service.py`
- Modify: `backend_python/langgraph_agent/graph.py`
- Modify: `backend_python/routes/langgraph_agent.py`

- [ ] **Step 1: Write failing graph V2 tests**

Create `tests/test_langgraph_agent_graph_v2.py`:

```python
import asyncio

from backend_python.langgraph_agent.graph import run_interview_graph_v2


def test_run_interview_graph_v2_returns_checkpoint_summary():
    async def fake_decide(**kwargs):
        return {
            "decision": {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 基础",
                "reason": "候选人答不上来，先降低难度。",
                "tools": ["retrieve_context", "analyze_answer"],
                "fallbackUsed": False,
                "decisionSummary": "学习辅导模式：lower_difficulty。候选人答不上来，先降低难度。",
            },
            "agentState": {"answerStatus": "不会"},
        }

    def fake_retrieve(profile, next_stage):
        return {
            "roleHits": [{"id": "role-1", "content": "RAG"}],
            "questionHits": [],
            "memoryHits": [],
            "toolCalls": [{"toolName": "retrieve_role_knowledge", "success": True}],
            "retrievalQuality": {
                "roleKnowledge": {"hitCount": 1},
                "questionBank": {"hitCount": 0},
                "candidateMemory": {"hitCount": 0},
            },
        }

    result = asyncio.run(
        run_interview_graph_v2(
            thread_id="thread-v2-001",
            profile={"targetRole": "AI 应用开发实习生"},
            history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
            next_stage="技术追问",
            agent_mode="coach",
            retrieve_context_fn=fake_retrieve,
            decide_action_fn=fake_decide,
        )
    )

    assert result["threadId"] == "thread-v2-001"
    assert result["checkpointSummary"]["exists"] is True
    assert result["decision"]["nextAction"] == "lower_difficulty"
    assert result["nextQuestion"]["prompt"]
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_action",
        "generate_question",
        "update_memory",
    ]
```

- [ ] **Step 2: Write failing route V2 tests**

Append to `tests/test_langgraph_agent_route.py`:

```python
def test_langgraph_agent_v2_route_returns_thread_and_checkpoint():
    response = client.post(
        "/api/langgraph-agent/next-question-v2",
        json={
            "threadId": "route-thread-001",
            "profile": {"targetRole": "AI 应用开发实习生"},
            "history": [{"question": "讲讲 RAG。", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "useRealRag": False,
            "useRealDecision": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threadId"] == "route-thread-001"
    assert payload["checkpointSummary"]["exists"] is True
    assert payload["decision"]["nextAction"]
    assert payload["nextQuestion"]["prompt"]


def test_langgraph_checkpoint_route_returns_summary():
    client.post(
        "/api/langgraph-agent/next-question-v2",
        json={
            "threadId": "route-thread-002",
            "profile": {},
            "history": [],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "useRealRag": False,
            "useRealDecision": False,
        },
    )

    response = client.get("/api/langgraph-agent/checkpoint/route-thread-002")

    assert response.status_code == 200
    payload = response.json()
    assert payload["exists"] is True
    assert payload["threadId"] == "route-thread-002"
```

- [ ] **Step 3: Run V2 graph/route tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_graph_v2.py tests/test_langgraph_agent_route.py -q
```

Expected: fail because V2 graph and routes do not exist.

- [ ] **Step 4: Implement V2 graph**

Modify `backend_python/langgraph_agent/graph.py`:

- Keep `build_interview_graph()` and `run_interview_graph_poc()` compatible.
- Add `build_interview_graph_v2(retrieve_context_fn, decide_action_fn)`.
- Compile with `memory_saver`.
- Invoke with `build_graph_config(thread_id)`.
- Record and attach checkpoint summary with `record_checkpoint_summary()`.

- [ ] **Step 5: Implement V2 service**

Create `backend_python/langgraph_agent/service.py`:

```python
from typing import Any

from .checkpoint import summarize_checkpoint
from .graph import run_interview_graph_v2


async def run_langgraph_agent_v2(**kwargs: Any) -> dict[str, Any]:
    return await run_interview_graph_v2(**kwargs)


def get_langgraph_checkpoint_summary(thread_id: str) -> dict[str, Any]:
    return summarize_checkpoint(thread_id)
```

- [ ] **Step 6: Implement V2 routes**

Modify `backend_python/routes/langgraph_agent.py`:

- Add request fields:
  - `threadId: str = "default-thread"`
  - `applicationProfileId: int | None = None`
  - `useRealRag: bool = False`
  - `useRealDecision: bool = False`
- Add `POST /next-question-v2`.
- Add `GET /checkpoint/{thread_id}`.
- For this phase, when `useRealRag=False` or `useRealDecision=False`, use stable fake defaults through graph-level injection.
- Keep `/next-question-poc` unchanged.

- [ ] **Step 7: Run V2 graph/route tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_graph_v2.py tests/test_langgraph_agent_route.py -q
```

Expected: pass.

---

## Task 5: Learning Doc and Progress Record

**Files:**
- Create: `docs/learning/09-LangGraph checkpoint和thread state怎么理解.md`
- Modify: `docs/roadmap/project-progress.md`

- [ ] **Step 1: Add learning document**

Create `docs/learning/09-LangGraph checkpoint和thread state怎么理解.md` with these sections:

```markdown
# LangGraph checkpoint 和 thread state 怎么理解

## 1. 一句话理解

checkpoint 是 LangGraph 在某个 threadId 维度下保存的图状态快照。thread state 是当前图运行时携带的状态数据。普通数据库记录是业务持久化数据。AgentDecisionLog 是为了排查 Agent 决策而记录的可观测日志。

## 2. 为什么 AI 模拟面试需要 threadId

同一个用户可以有多场面试，同一场面试又有多轮问答。threadId 用来标识“同一条 LangGraph 实验流程”，让 checkpoint 知道这几轮状态属于同一场实验。

## 3. checkpoint 和数据库记录的区别

checkpoint 偏运行时恢复和调试，数据库记录偏业务事实保存。MemorySaver 是内存版 checkpoint，服务重启会丢失；数据库记录不会因为 Python 进程重启自动丢失。

## 4. checkpoint 和 AgentDecisionLog 的区别

checkpoint 保存图状态，方便恢复和继续跑图。AgentDecisionLog 保存 Agent 为什么这么决策，方便排查黑箱问题。二者可以互补，但不是同一个东西。

## 5. 当前项目怎么落地

当前 V2 使用旁路接口，不替换主流程。它通过 threadId 调用 LangGraph，并返回 checkpointSummary、nodeTrace、toolCalls 和 decision。

## 6. 面试表达

我先保留自研 Agent 主流程，再用 LangGraph V2 做旁路验证。V2 通过 adapter 接入真实 RAG 和真实 Agent 决策，并用 threadId + MemorySaver 演示 checkpoint。这样既控制风险，又能证明项目具备迁移到标准 Agent 工作流框架的能力。
```

- [ ] **Step 2: Update project progress**

Append a new implementation note under stage 24 in `docs/roadmap/project-progress.md` after code verification:

```markdown
阶段 24 实现进度：

- 已完成 checkpoint 基础。
- 已完成真实/fake RAG adapter。
- 已完成真实/fake Agent decision adapter。
- 已完成 V2 实验接口和 checkpoint 查询接口。
- 已新增 LangGraph checkpoint 学习文档。

验证：

```text
python -m pytest -q
结果：...

Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
结果：...
```
```

- [ ] **Step 3: Run placeholder scan**

Run:

```powershell
rg -n "T[B]D|T[O]DO|F[IX]ME|待[补]|稍[后]补|x[x]x" docs/learning/09-LangGraph checkpoint和thread state怎么理解.md docs/plans/active/langgraph-agent-v2-real-rag-checkpoint.md
```

Expected: no matches.

---

## Task 6: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused LangGraph tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_state.py tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_checkpoint.py tests/test_langgraph_agent_adapters.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_graph_v2.py tests/test_langgraph_agent_route.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full backend test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Run all frontend `.mjs` tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend tests pass with no failure output.

- [ ] **Step 4: Confirm main route was not replaced**

Run:

```powershell
rg -n "next-question-v2|next-question-poc|/api/interview/next-question|run_interview_graph_v2" backend_python tests docs
```

Expected:

- `/api/interview/next-question` remains in existing interview route/tests.
- `/api/langgraph-agent/next-question-poc` still exists.
- `/api/langgraph-agent/next-question-v2` exists separately.
- V2 references are isolated to `backend_python/langgraph_agent/`, `backend_python/routes/langgraph_agent.py`, tests, and docs.

---

## Completion Criteria

The phase is complete only when:

- `docs/plans/active/langgraph-agent-v2-real-rag-checkpoint.md` exists and matches the active spec.
- `POST /api/langgraph-agent/next-question-v2` works.
- `GET /api/langgraph-agent/checkpoint/{thread_id}` works.
- V1 POC route still works.
- `/api/interview/next-question` is not replaced.
- V2 can run with fake retriever/fake decision for stable tests.
- V2 has adapters for real RAG and real Agent decision logic.
- Checkpoint summary can be queried by `threadId`.
- Learning doc exists.
- `python -m pytest -q` passes.
- All frontend `.mjs` tests pass.
