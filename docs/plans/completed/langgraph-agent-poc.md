# LangGraph Agent POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a side-path LangGraph proof of concept that maps the existing Interview Orchestrator Agent into a testable `StateGraph` workflow without replacing `/api/interview/next-question`.

**Architecture:** Add a new isolated `backend_python/langgraph_agent/` package with state, nodes, graph builder, and adapters. The POC reuses existing Agent concepts and trace helpers, but it does not mutate the current interview route or RAG internals. A new experimental route exposes the POC for backend verification only.

**Tech Stack:** Python 3.13, FastAPI, pytest, LangGraph, existing Agent modules, existing frontend `.mjs` tests for regression.

---

## Learning Focus

本阶段要学的是：LangGraph 不是替你“自动写 Agent”的魔法框架，它更像一个可测试的工作流编排器。你需要先定义 `State`，再把每一步拆成 `node`，然后用 `edge` 规定节点顺序。这样 Agent 的状态、工具调用、决策、问题生成和记忆更新都能被拆开测试，而不是全部塞进一次大模型调用里。

## Scope Rules

Implement:

- Add `langgraph` dependency.
- Add a side-path LangGraph POC package.
- Add state, node, graph, and route tests first.
- Add `POST /api/langgraph-agent/next-question-poc`.
- Return `graphState`, `nodeTrace`, `toolCalls`, `decision`, `nextQuestion`, and `memoryUpdate`.
- Keep existing `/api/interview/next-question` unchanged.
- Add one concise learning document.
- Update `docs/roadmap/project-progress.md`.

Do not implement:

- Do not replace the existing Interview Orchestrator Agent.
- Do not delete or rename existing Agent modules.
- Do not change the current frontend main flow.
- Do not rebuild RAG retrieval internals.
- Do not add checkpoint or human-in-the-loop runtime behavior in V1.
- Do not do Docker, Nginx, or cloud deployment.
- Do not add Vue3 in this phase.

## File Map

Create:

- `backend_python/langgraph_agent/__init__.py`
  - Exports POC entry points.

- `backend_python/langgraph_agent/state.py`
  - Defines `InterviewGraphState`.
  - Provides `build_initial_graph_state()`.
  - Provides `assert_graph_state_jsonable()`.

- `backend_python/langgraph_agent/nodes.py`
  - Defines node functions:
    - `observe_state_node`
    - `analyze_answer_node`
    - `retrieve_context_node`
    - `select_action_node`
    - `generate_question_node`
    - `update_memory_node`

- `backend_python/langgraph_agent/graph.py`
  - Builds and compiles a `StateGraph`.
  - Exposes `build_interview_graph()` and `run_interview_graph_poc()`.

- `backend_python/routes/langgraph_agent.py`
  - Adds experimental POC route.

- `tests/test_langgraph_agent_state.py`
- `tests/test_langgraph_agent_nodes.py`
- `tests/test_langgraph_agent_graph.py`
- `tests/test_langgraph_agent_route.py`
- `docs/learning/08-LangGraph如何承接自研Agent.md`

Modify:

- `requirements.txt`
  - Add `langgraph`.

- `backend_python/main.py`
  - Include `langgraph_agent` router.

- `docs/roadmap/project-progress.md`
  - Record each phase and verification result.

---

### Task 1: Add LangGraph Dependency And State Tests

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_langgraph_agent_state.py`
- Create: `backend_python/langgraph_agent/__init__.py`
- Create: `backend_python/langgraph_agent/state.py`

- [ ] **Step 1: Add dependency**

Add this line to `requirements.txt`:

```text
langgraph==0.2.76
```

- [ ] **Step 2: Install dependencies if needed**

Run:

```powershell
python -m pip install -r requirements.txt
```

Expected:

```text
Successfully installed ...
```

If the environment already has dependencies, the command may report `Requirement already satisfied`.

- [ ] **Step 3: Write failing state tests**

Create `tests/test_langgraph_agent_state.py`:

```python
import json

from backend_python.langgraph_agent.state import (
    assert_graph_state_jsonable,
    build_initial_graph_state,
)


def test_build_initial_graph_state_is_json_serializable():
    state = build_initial_graph_state(
        profile={"candidateName": "David", "targetRole": "AI 应用开发实习生"},
        history=[{"question": "什么是 RAG？", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    assert state["profile"]["candidateName"] == "David"
    assert state["history"][0]["answer"] == "不知道"
    assert state["nextStage"] == "技术追问"
    assert state["agentMode"] == "coach"
    assert state["nodeTrace"] == []
    assert state["toolCalls"] == []
    json.dumps(state, ensure_ascii=False)


def test_assert_graph_state_jsonable_rejects_runtime_objects():
    class RuntimeObject:
        pass

    bad_state = {"profile": {"runtime": RuntimeObject()}}

    try:
        assert_graph_state_jsonable(bad_state)
    except TypeError as exc:
        assert "Graph state must be JSON serializable" in str(exc)
    else:
        raise AssertionError("expected non-jsonable graph state to be rejected")
```

- [ ] **Step 4: Run state tests and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_state.py -q
```

Expected before implementation:

```text
ModuleNotFoundError: No module named 'backend_python.langgraph_agent'
```

- [ ] **Step 5: Implement state module**

Create `backend_python/langgraph_agent/__init__.py`:

```python
"""LangGraph proof-of-concept modules for the AI interview agent."""
```

Create `backend_python/langgraph_agent/state.py`:

```python
from typing import Any, TypedDict
import json


class InterviewGraphState(TypedDict, total=False):
    profile: dict[str, Any]
    history: list[dict[str, Any]]
    nextStage: str
    agentMode: str
    answerAnalysis: dict[str, Any]
    retrievalQuality: dict[str, Any]
    roleHits: list[dict[str, Any]]
    questionHits: list[dict[str, Any]]
    memoryHits: list[dict[str, Any]]
    toolCalls: list[dict[str, Any]]
    decision: dict[str, Any]
    nextQuestion: dict[str, Any]
    memoryUpdate: dict[str, Any]
    nodeTrace: list[dict[str, Any]]


def build_initial_graph_state(
    *,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
) -> InterviewGraphState:
    state: InterviewGraphState = {
        "profile": dict(profile or {}),
        "history": list(history or []),
        "nextStage": str(next_stage or "综合追问"),
        "agentMode": str(agent_mode or "interview"),
        "answerAnalysis": {},
        "retrievalQuality": {},
        "roleHits": [],
        "questionHits": [],
        "memoryHits": [],
        "toolCalls": [],
        "decision": {},
        "nextQuestion": {},
        "memoryUpdate": {},
        "nodeTrace": [],
    }
    assert_graph_state_jsonable(state)
    return state


def assert_graph_state_jsonable(state: dict[str, Any]) -> None:
    try:
        json.dumps(state, ensure_ascii=False)
    except TypeError as exc:
        raise TypeError("Graph state must be JSON serializable") from exc
```

- [ ] **Step 6: Run state tests and verify pass**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_state.py -q
```

Expected:

```text
2 passed
```

---

### Task 2: Add Node Tests And Minimal Node Implementation

**Files:**
- Create: `tests/test_langgraph_agent_nodes.py`
- Create: `backend_python/langgraph_agent/nodes.py`

- [ ] **Step 1: Write failing node tests**

Create `tests/test_langgraph_agent_nodes.py`:

```python
from backend_python.langgraph_agent.nodes import (
    analyze_answer_node,
    generate_question_node,
    observe_state_node,
    retrieve_context_node,
    select_action_node,
    update_memory_node,
)
from backend_python.langgraph_agent.state import build_initial_graph_state


def test_observe_and_analyze_answer_nodes_append_trace():
    state = build_initial_graph_state(
        profile={"candidateName": "David"},
        history=[{"question": "什么是 RAG？", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    observed = observe_state_node(state)
    analyzed = analyze_answer_node({**state, **observed})

    assert observed["nodeTrace"][0]["nodeName"] == "observe_state"
    assert analyzed["answerAnalysis"]["weakAnswerStreak"] == 1
    assert analyzed["answerAnalysis"]["answerStatus"] == "不会"
    assert analyzed["nodeTrace"][-1]["nodeName"] == "analyze_answer"


def test_retrieve_context_node_returns_three_tool_calls():
    state = build_initial_graph_state(profile={"targetRole": "AI 应用开发"}, history=[])

    update = retrieve_context_node(state)

    assert len(update["roleHits"]) == 1
    assert len(update["questionHits"]) == 1
    assert len(update["memoryHits"]) == 1
    assert [call["toolName"] for call in update["toolCalls"]] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    ]
    assert update["nodeTrace"][-1]["nodeName"] == "retrieve_context"


def test_decision_question_and_memory_nodes_build_outputs():
    state = build_initial_graph_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
        agent_mode="coach",
    )
    for node in (observe_state_node, analyze_answer_node, retrieve_context_node, select_action_node, generate_question_node, update_memory_node):
        state = {**state, **node(state)}

    assert state["decision"]["nextAction"] == "lower_difficulty"
    assert state["decision"]["fallbackUsed"] is False
    assert "RAG" in state["nextQuestion"]["prompt"]
    assert state["memoryUpdate"]["status"] == "deferred"
    assert [item["nodeName"] for item in state["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_action",
        "generate_question",
        "update_memory",
    ]
```

- [ ] **Step 2: Run node tests and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_nodes.py -q
```

Expected before implementation:

```text
ModuleNotFoundError: No module named 'backend_python.langgraph_agent.nodes'
```

- [ ] **Step 3: Implement node module**

Create `backend_python/langgraph_agent/nodes.py`:

```python
from typing import Any

from backend_python.agent_state import _analyze_answer_history, _classify_answer_status
from backend_python.agent_trace import build_node_trace, build_tool_call_summary


def _trace_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("nodeTrace") or [])


def observe_state_node(state: dict[str, Any]) -> dict[str, Any]:
    history = list(state.get("history") or [])
    update = {
        "roundCount": len(history),
        "remainingRounds": max(8 - len(history), 0),
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="observe_state",
                input_summary={"historyCount": len(history), "agentMode": state.get("agentMode", "interview")},
                output_summary={"roundCount": len(history), "remainingRounds": max(8 - len(history), 0)},
            ),
        ],
    }
    return update


def analyze_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    history = list(state.get("history") or [])
    last_answer = history[-1] if history else {}
    answer_status = _classify_answer_status(str(last_answer.get("answer") or ""))
    analysis = dict(_analyze_answer_history(history))
    analysis["answerStatus"] = answer_status
    return {
        "answerAnalysis": analysis,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="analyze_answer",
                input_summary={"historyCount": len(history)},
                output_summary={
                    "answerStatus": answer_status,
                    "weakAnswerStreak": analysis.get("weakAnswerStreak", 0),
                    "triggerSignals": analysis.get("triggerSignals", []),
                },
            ),
        ],
    }


def retrieve_context_node(state: dict[str, Any]) -> dict[str, Any]:
    target_role = str((state.get("profile") or {}).get("targetRole") or "AI 应用开发")
    role_hits = [{"id": "role-poc-1", "title": "岗位知识库样例", "content": f"{target_role} 需要理解 Agent、RAG 和工具调用。"}]
    question_hits = [{"id": "question-poc-1", "title": "题库样例", "content": "请解释 RAG 的检索、重排和引用来源。"}]
    memory_hits = [{"id": "memory-poc-1", "title": "候选人画像样例", "content": "候选人最近在 RAG 和 Agent 概念上需要降低难度训练。"}]
    tool_calls = [
        build_tool_call_summary(tool_name="retrieve_role_knowledge", output_summary={"hitCount": len(role_hits)}),
        build_tool_call_summary(tool_name="retrieve_question_bank", output_summary={"hitCount": len(question_hits)}),
        build_tool_call_summary(tool_name="retrieve_candidate_memory", output_summary={"hitCount": len(memory_hits)}),
    ]
    return {
        "roleHits": role_hits,
        "questionHits": question_hits,
        "memoryHits": memory_hits,
        "toolCalls": tool_calls,
        "retrievalQuality": {
            "roleKnowledge": {"level": "good", "hitCount": len(role_hits)},
            "questionBank": {"level": "good", "hitCount": len(question_hits)},
            "candidateMemory": {"level": "good", "hitCount": len(memory_hits)},
        },
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="retrieve_context",
                input_summary={"nextStage": state.get("nextStage", "")},
                output_summary={"roleHitCount": len(role_hits), "questionHitCount": len(question_hits), "memoryHitCount": len(memory_hits)},
            ),
        ],
    }


def select_action_node(state: dict[str, Any]) -> dict[str, Any]:
    analysis = dict(state.get("answerAnalysis") or {})
    answer_status = str(analysis.get("answerStatus") or "模糊")
    next_action = "lower_difficulty" if answer_status == "不会" else "deep_follow_up"
    difficulty = "basic" if next_action == "lower_difficulty" else "medium"
    decision = {
        "nextAction": next_action,
        "stage": state.get("nextStage") or "综合追问",
        "difficulty": difficulty,
        "focus": "RAG 与 Agent 基础理解",
        "reason": "LangGraph POC 根据回答状态选择下一步动作。",
        "tools": ["retrieve_role_knowledge", "retrieve_question_bank", "retrieve_candidate_memory"],
        "fallbackUsed": False,
    }
    return {
        "decision": decision,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="select_action",
                input_summary={"answerStatus": answer_status},
                output_summary={"nextAction": next_action, "difficulty": difficulty, "focus": decision["focus"]},
            ),
        ],
    }


def generate_question_node(state: dict[str, Any]) -> dict[str, Any]:
    decision = dict(state.get("decision") or {})
    prompt = "我们先把难度降下来：你能用自己的话解释 RAG 为什么需要检索、重排和引用来源吗？"
    if decision.get("nextAction") == "deep_follow_up":
        prompt = "你刚才的回答比较完整，继续追问：如果 RAG 召回结果质量差，你会怎么定位问题？"
    next_question = {
        "stage": decision.get("stage") or state.get("nextStage") or "综合追问",
        "focus": decision.get("focus") or "RAG 与 Agent 基础理解",
        "stability": "stable",
        "prompt": prompt,
    }
    return {
        "nextQuestion": next_question,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="generate_question",
                input_summary={"nextAction": decision.get("nextAction", "")},
                output_summary={"stage": next_question["stage"], "focus": next_question["focus"]},
            ),
        ],
    }


def update_memory_node(state: dict[str, Any]) -> dict[str, Any]:
    memory_update = {
        "status": "deferred",
        "reason": "LangGraph POC 只记录记忆更新意图，不直接写入候选人画像。",
        "weakSignals": (state.get("answerAnalysis") or {}).get("triggerSignals", []),
    }
    return {
        "memoryUpdate": memory_update,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="update_memory",
                input_summary={"hasNextQuestion": bool(state.get("nextQuestion"))},
                output_summary={"status": memory_update["status"]},
            ),
        ],
    }
```

- [ ] **Step 4: Run node tests and verify pass**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_nodes.py -q
```

Expected:

```text
3 passed
```

---

### Task 3: Add Graph Builder And Graph Tests

**Files:**
- Create: `tests/test_langgraph_agent_graph.py`
- Create: `backend_python/langgraph_agent/graph.py`

- [ ] **Step 1: Write failing graph tests**

Create `tests/test_langgraph_agent_graph.py`:

```python
from backend_python.langgraph_agent.graph import build_interview_graph, run_interview_graph_poc


def test_build_interview_graph_compiles():
    graph = build_interview_graph()

    assert graph is not None


def test_run_interview_graph_poc_returns_trace_and_question():
    result = run_interview_graph_poc(
        profile={"candidateName": "David", "targetRole": "AI 应用开发实习生"},
        history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    assert result["decision"]["nextAction"] == "lower_difficulty"
    assert result["nextQuestion"]["prompt"]
    assert result["memoryUpdate"]["status"] == "deferred"
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_action",
        "generate_question",
        "update_memory",
    ]
```

- [ ] **Step 2: Run graph tests and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_graph.py -q
```

Expected before implementation:

```text
ModuleNotFoundError: No module named 'backend_python.langgraph_agent.graph'
```

- [ ] **Step 3: Implement graph module**

Create `backend_python/langgraph_agent/graph.py`:

```python
from typing import Any

from langgraph.graph import END, START, StateGraph

from .nodes import (
    analyze_answer_node,
    generate_question_node,
    observe_state_node,
    retrieve_context_node,
    select_action_node,
    update_memory_node,
)
from .state import InterviewGraphState, build_initial_graph_state, assert_graph_state_jsonable


def build_interview_graph():
    graph = StateGraph(InterviewGraphState)
    graph.add_node("observe_state", observe_state_node)
    graph.add_node("analyze_answer", analyze_answer_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("select_action", select_action_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("update_memory", update_memory_node)

    graph.add_edge(START, "observe_state")
    graph.add_edge("observe_state", "analyze_answer")
    graph.add_edge("analyze_answer", "retrieve_context")
    graph.add_edge("retrieve_context", "select_action")
    graph.add_edge("select_action", "generate_question")
    graph.add_edge("generate_question", "update_memory")
    graph.add_edge("update_memory", END)
    return graph.compile()


def run_interview_graph_poc(
    *,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
) -> dict[str, Any]:
    state = build_initial_graph_state(
        profile=profile,
        history=history,
        next_stage=next_stage,
        agent_mode=agent_mode,
    )
    graph = build_interview_graph()
    result = dict(graph.invoke(state))
    assert_graph_state_jsonable(result)
    return result
```

- [ ] **Step 4: Run graph tests and verify pass**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_graph.py -q
```

Expected:

```text
2 passed
```

---

### Task 4: Add Experimental Route And Route Tests

**Files:**
- Create: `tests/test_langgraph_agent_route.py`
- Create: `backend_python/routes/langgraph_agent.py`
- Modify: `backend_python/main.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_langgraph_agent_route.py`:

```python
from fastapi.testclient import TestClient

from backend_python.main import app


client = TestClient(app)


def test_langgraph_agent_poc_route_returns_graph_result():
    response = client.post(
        "/api/langgraph-agent/next-question-poc",
        json={
            "profile": {"candidateName": "David", "targetRole": "AI 应用开发实习生"},
            "history": [{"question": "讲讲 RAG。", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["nextAction"] == "lower_difficulty"
    assert payload["nextQuestion"]["prompt"]
    assert payload["memoryUpdate"]["status"] == "deferred"
    assert payload["graphState"]["agentMode"] == "coach"
    assert [item["nodeName"] for item in payload["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_action",
        "generate_question",
        "update_memory",
    ]


def test_existing_next_question_route_still_exists():
    response = client.post(
        "/api/interview/next-question",
        json={
            "profile": {"candidateName": "David", "targetRole": "AI 应用开发实习生"},
            "history": [],
            "nextStage": "自我介绍",
            "agentMode": "coach",
        },
    )

    assert response.status_code in {200, 500}
    assert response.status_code != 404
```

- [ ] **Step 2: Run route tests and verify failure**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_route.py -q
```

Expected before implementation:

```text
404 Not Found
```

- [ ] **Step 3: Implement experimental route**

Create `backend_python/routes/langgraph_agent.py`:

```python
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend_python.langgraph_agent.graph import run_interview_graph_poc


router = APIRouter(prefix="/api/langgraph-agent", tags=["langgraph-agent"])


class LangGraphQuestionRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    nextStage: str = ""
    agentMode: str = "interview"


@router.post("/next-question-poc")
async def next_question_poc(payload: LangGraphQuestionRequest) -> dict[str, Any]:
    result = run_interview_graph_poc(
        profile=payload.profile,
        history=payload.history,
        next_stage=payload.nextStage,
        agent_mode=payload.agentMode,
    )
    return {
        "graphState": result,
        "nodeTrace": result.get("nodeTrace", []),
        "toolCalls": result.get("toolCalls", []),
        "decision": result.get("decision", {}),
        "nextQuestion": result.get("nextQuestion", {}),
        "memoryUpdate": result.get("memoryUpdate", {}),
    }
```

Modify `backend_python/main.py` imports:

```python
from .routes import (
    admin,
    agent,
    application_profiles,
    auth,
    history,
    interview,
    langgraph_agent,
    memory,
    position_agent,
    rag,
    rag_documents,
    resume,
    training,
)
```

Add router registration after existing agent router:

```python
app.include_router(langgraph_agent.router)
```

- [ ] **Step 4: Run route tests and verify pass**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_route.py -q
```

Expected:

```text
2 passed
```

---

### Task 5: Add Learning Document And Progress Update

**Files:**
- Create: `docs/learning/08-LangGraph如何承接自研Agent.md`
- Modify: `docs/roadmap/project-progress.md`

- [ ] **Step 1: Create concise learning document**

Create `docs/learning/08-LangGraph如何承接自研Agent.md`:

```markdown
# LangGraph 如何承接自研 Agent

## 1. 为什么先做自研 Agent

本项目先做自研 Interview Orchestrator Agent，是为了把 Agent 的底层机制学清楚：

- State：当前面试看到了什么。
- Tool：三类 RAG 怎样被调用。
- Decision：为什么降难度、深挖、换话题或结束。
- Trace：每个节点做了什么。
- Guardrail：模型输出不稳定时怎样兜底。

如果一开始直接用框架，容易只会调用框架 API，却讲不清 Agent 的状态和决策。

## 2. LangGraph POC 做了什么

LangGraph POC 没有替换主流程，而是新增旁路实验链路：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
```

这个链路证明：现有自研 Agent 的节点可以映射成 LangGraph StateGraph。

## 3. StateGraph 怎么理解

可以把 StateGraph 理解成“带状态的流程图”：

- State 是整场流程共享的数据包。
- Node 是每一步处理逻辑。
- Edge 是节点之间的流转顺序。
- compile 是把设计好的图变成可运行对象。

## 4. 为什么是旁路 POC

主流程继续使用自研 Agent，保证面试功能稳定。

LangGraph POC 只用于验证迁移方向。这样就算 POC 有问题，也不会影响用户正常模拟面试。

## 5. 面试时怎么讲

可以这样说：

> 我先自研了一个 Interview Orchestrator Agent，用来理解 state、tool、decision、trace 和 fallback。后续我又做了 LangGraph POC，把自研 Agent 的 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory 映射成 StateGraph 节点。这个 POC 不替换主流程，而是验证项目未来可以迁移到更标准的 Agent 工作流框架。
```

- [ ] **Step 2: Update progress document**

Append a phase entry to `docs/roadmap/project-progress.md`:

```markdown
## 阶段 23：LangGraph Agent POC - 第一版实现

状态：已完成阶段性版本。

本阶段新增旁路 LangGraph POC，不替换现有 `/api/interview/next-question` 主流程。

已完成内容：

- 新增 `langgraph` 依赖。
- 新增 `backend_python/langgraph_agent/` 包。
- 新增 `InterviewGraphState` 和初始 state 构造。
- 新增 6 个 LangGraph 节点：
  - `observe_state`
  - `analyze_answer`
  - `retrieve_context`
  - `select_action`
  - `generate_question`
  - `update_memory`
- 新增 `StateGraph` 编排。
- 新增实验接口：`POST /api/langgraph-agent/next-question-poc`。
- 新增学习文档：`docs/learning/08-LangGraph如何承接自研Agent.md`。

验证命令：

```text
python -m pytest tests/test_langgraph_agent_state.py tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_route.py -q
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

当前边界：

- POC 使用独立路由，不影响主面试接口。
- checkpoint 和 human-in-the-loop 只做文档预留。
- 第一版 `generate_question` 使用 stub 文案，不直接调用真实模型。
```

---

### Task 6: Full Verification

**Files:**
- No source file changes unless verification reveals a real failure.

- [ ] **Step 1: Run focused LangGraph POC tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_state.py tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_route.py -q
```

Expected:

```text
9 passed
```

- [ ] **Step 2: Run full backend tests**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All backend tests pass.
```

- [ ] **Step 3: Run all frontend tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
Exit code 0, no failure output.
```

- [ ] **Step 4: Verify no forbidden scope was introduced**

Run:

```powershell
rg -n "Vue|React|Next\\.js|Dockerfile|docker-compose|checkpoint|interrupt" backend_python tests docs/plans/active/langgraph-agent-poc.md
```

Expected:

```text
Only documentation mentions for non-goals or future reserved work; no frontend framework or deployment implementation added.
```

---

## Completion Summary Template

After completing all tasks, summarize in Chinese:

```text
本阶段新增了旁路 LangGraph POC，没有替换现有自研 Agent 主流程。

你面试时可以这样讲：
我先自研了 Interview Orchestrator Agent，用它管理 state、toolCalls、decision、trace 和 fallback；然后做了 LangGraph POC，把这些节点映射成 StateGraph，证明系统后续可以迁移到标准 Agent 工作流框架。第一版 POC 不影响真实面试接口，只验证图工作流、节点顺序和可观测输出。
```

