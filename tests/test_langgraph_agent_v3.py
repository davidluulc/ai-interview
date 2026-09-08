import asyncio

from backend_python.agent_runtime import (
    _build_langgraph_v3_tool_fns,
    normalize_agent_runtime,
    run_agent_runtime,
)
from backend_python.langgraph_agent import graph_v3
from backend_python.langgraph_agent.graph_v3 import (
    MAX_PLANNING_STEPS,
    AgentPlanModel,
    apply_policy_guardrail,
    build_interview_graph_v3,
    build_v3_invoke_config,
    make_plan_node,
    make_tools_node,
    route_after_plan,
    run_interview_graph_v3,
)
from backend_python.langgraph_agent.state import build_initial_graph_state
from backend_python.structured_output import StructuredOutputExhausted, call_model_structured


def _plan_fixture(**overrides):
    plan = {
        "readyToAsk": False,
        "selectedTools": ["retrieve_role_knowledge"],
        "toolQuery": "RAG 检索质量",
        "nextAction": "deep_follow_up",
        "difficulty": "medium",
        "focus": "RAG 基础",
        "reason": "回答比较完整，继续深挖。",
    }
    plan.update(overrides)
    return plan


def _policy_fixture(**overrides):
    policy = {
        "recommendedAction": "deep_follow_up",
        "difficulty": "medium",
        "shouldSwitchTopic": False,
        "policyReasons": ["回答不算完全不会，默认继续中等难度追问。"],
        "triggerRules": ["normal_follow_up"],
    }
    policy.update(overrides)
    return policy


def test_apply_policy_guardrail_overrides_switch_topic():
    plan = _plan_fixture(nextAction="deep_follow_up", difficulty="medium")
    policy = _policy_fixture(
        recommendedAction="switch_topic",
        difficulty="basic",
        shouldSwitchTopic=True,
        policyReasons=[
            "候选人连续三轮答不上来，切换到基础或相邻话题。",
            "检测到连续重复追问，触发重复问题保护。",
        ],
        triggerRules=["weak_answer_streak", "topic_shift"],
    )

    guarded = apply_policy_guardrail(plan, policy)

    assert guarded["nextAction"] == "switch_topic"
    assert guarded["difficulty"] == "basic"
    assert guarded["overrideReason"]
    assert guarded["decisionSource"] == "guardrail"


def test_apply_policy_guardrail_passes_through_without_override():
    plan = _plan_fixture(selectedTools=["retrieve_role_knowledge", "not_a_real_tool"])
    policy = _policy_fixture(recommendedAction="deep_follow_up")

    guarded = apply_policy_guardrail(plan, policy)

    assert guarded["nextAction"] == "deep_follow_up"
    assert guarded["difficulty"] == "medium"
    assert guarded["decisionSource"] == "model"
    assert "overrideReason" not in guarded
    assert guarded["selectedTools"] == ["retrieve_role_knowledge"]


def test_plan_node_success_writes_state_keys():
    captured = {}

    async def fake_structured_call(**kwargs):
        captured.update(kwargs)
        model = AgentPlanModel(
            readyToAsk=False,
            selectedTools=["retrieve_question_bank"],
            toolQuery="RAG 追问",
            nextAction="deep_follow_up",
            difficulty="medium",
            focus="RAG 检索质量",
            reason="回答质量好，继续深挖。",
        )
        return model, {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    plan_node = make_plan_node(fake_structured_call)
    state = {
        "profile": {"targetRole": "AI 应用开发"},
        "history": [{"question": "讲讲 RAG。", "answer": "RAG 是检索增强生成。"}],
        "nextStage": "技术追问",
        "remainingRounds": 5,
        "policy": _policy_fixture(),
        "planningSteps": 0,
        "nodeTrace": [{"nodeName": "observe_state"}],
    }

    result = asyncio.run(plan_node(state))

    assert captured["schema_model"] is AgentPlanModel
    assert captured["temperature"] == 0.2
    assert result["planningSteps"] == 1
    assert result["planDecision"]["nextAction"] == "deep_follow_up"
    assert result["planDecision"]["decisionSource"] == "model"
    assert result["decision"] == {
        "nextAction": "deep_follow_up",
        "stage": "技术追问",
        "difficulty": "medium",
        "focus": "RAG 检索质量",
        "reason": "回答质量好，继续深挖。",
        "decisionSource": "model",
        "fallbackUsed": False,
    }
    assert [item["nodeName"] for item in result["nodeTrace"]] == ["observe_state", "plan"]


def test_plan_node_falls_back_when_structured_output_exhausted():
    async def exhausted_call(**kwargs):
        raise StructuredOutputExhausted(chain=[{"stage": "json_schema", "status": "format_error", "detail": "bad"}])

    plan_node = make_plan_node(exhausted_call)
    state = {
        "nextStage": "技术追问",
        "policy": _policy_fixture(recommendedAction="lower_difficulty", difficulty="basic"),
        "planningSteps": 0,
    }

    result = asyncio.run(plan_node(state))

    assert result["decision"]["fallbackUsed"] is True
    assert result["decision"]["decisionSource"] == "fallback"
    assert result["decision"]["nextAction"] == "lower_difficulty"
    assert result["planDecision"]["readyToAsk"] is True
    assert result["planDecision"]["nextAction"] == "lower_difficulty"
    assert result["planDecision"]["selectedTools"] == []
    assert result["planDecision"]["decisionSource"] == "fallback"
    assert result["planningSteps"] == 1


def test_plan_node_forces_ready_to_ask_at_max_planning_steps():
    async def not_ready_call(**kwargs):
        model = AgentPlanModel(
            readyToAsk=False,
            selectedTools=["retrieve_role_knowledge"],
            toolQuery="Agent 规划",
            nextAction="deep_follow_up",
            difficulty="medium",
            focus="Agent 基础",
            reason="还想再检索一轮。",
        )
        return model, {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    plan_node = make_plan_node(not_ready_call)
    state = {
        "nextStage": "技术追问",
        "policy": _policy_fixture(),
        "planningSteps": MAX_PLANNING_STEPS - 1,
    }

    result = asyncio.run(plan_node(state))

    assert result["planningSteps"] == MAX_PLANNING_STEPS
    assert result["planDecision"]["readyToAsk"] is True


def _tools_node_state(**plan_overrides):
    plan = {
        "readyToAsk": False,
        "selectedTools": [],
        "toolQuery": "RAG 检索质量",
        "nextAction": "deep_follow_up",
        "difficulty": "medium",
        "focus": "RAG 基础",
        "reason": "继续检索。",
        "decisionSource": "model",
    }
    plan.update(plan_overrides)
    return {
        "profile": {"targetRole": "AI 应用开发"},
        "history": [],
        "nextStage": "项目追问",
        "planningSteps": 1,
        "planDecision": plan,
        "nodeTrace": [],
    }


def _fake_tool(tool_name: str, hit_count: int, calls_log: list):
    def tool_fn(profile: dict, next_stage: str, tool_query: str):
        calls_log.append(
            {
                "toolName": tool_name,
                "profile": profile,
                "nextStage": next_stage,
                "toolQuery": tool_query,
            }
        )
        return [
            {"id": f"{tool_name}-{index}", "content": f"{tool_name} 命中内容 {index}"}
            for index in range(hit_count)
        ]

    return tool_fn


def test_route_after_plan_end_generate_tools_branches():
    end_state = {"planDecision": {"nextAction": "end_interview", "readyToAsk": True}, "planningSteps": 1}
    generate_state = {"planDecision": {"nextAction": "deep_follow_up", "readyToAsk": True}, "planningSteps": 1}
    tools_state = {"planDecision": {"nextAction": "deep_follow_up", "readyToAsk": False}, "planningSteps": 1}

    assert route_after_plan(end_state) == "end"
    assert route_after_plan(generate_state) == "generate"
    assert route_after_plan(tools_state) == "tools"


def test_route_after_plan_max_planning_steps_routes_to_generate():
    state = {
        "planDecision": {"nextAction": "deep_follow_up", "readyToAsk": False},
        "planningSteps": MAX_PLANNING_STEPS,
    }

    assert route_after_plan(state) == "generate"


def test_tools_node_runs_only_selected_tools():
    calls_log = []
    tool_fns = {
        "retrieve_role_knowledge": _fake_tool("retrieve_role_knowledge", 1, calls_log),
        "retrieve_question_bank": _fake_tool("retrieve_question_bank", 2, calls_log),
        "retrieve_candidate_memory": _fake_tool("retrieve_candidate_memory", 3, calls_log),
    }
    state = _tools_node_state(
        selectedTools=["retrieve_role_knowledge", "retrieve_question_bank"],
        toolQuery="RAG 重排",
    )

    result = make_tools_node(tool_fns)(state)

    assert [call["toolName"] for call in calls_log] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
    ]
    assert calls_log[0]["toolQuery"] == "RAG 重排"
    assert calls_log[0]["nextStage"] == "项目追问"
    assert calls_log[0]["profile"] == {"targetRole": "AI 应用开发"}
    assert len(result["selectedToolResults"]["role"]) == 1
    assert len(result["selectedToolResults"]["question"]) == 2
    assert result["selectedToolResults"]["memory"] == []
    tools_trace = result["nodeTrace"][-1]
    assert tools_trace["nodeName"] == "tools"
    assert tools_trace["outputSummary"]["skippedTools"] == ["retrieve_candidate_memory"]
    assert tools_trace["outputSummary"]["toolCalls"][0]["outputSummary"]["hitCount"] == 1
    assert tools_trace["fallbackUsed"] is False


def test_tools_node_isolates_per_tool_failures():
    calls_log = []

    def broken_tool(profile: dict, next_stage: str, tool_query: str):
        calls_log.append({"toolName": "retrieve_question_bank"})
        raise RuntimeError("题库服务超时")

    tool_fns = {
        "retrieve_role_knowledge": _fake_tool("retrieve_role_knowledge", 1, calls_log),
        "retrieve_question_bank": broken_tool,
        "retrieve_candidate_memory": _fake_tool("retrieve_candidate_memory", 2, calls_log),
    }
    state = _tools_node_state(
        selectedTools=[
            "retrieve_role_knowledge",
            "retrieve_question_bank",
            "retrieve_candidate_memory",
        ]
    )

    result = make_tools_node(tool_fns)(state)

    assert [call["toolName"] for call in calls_log] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    ]
    assert len(result["selectedToolResults"]["role"]) == 1
    assert result["selectedToolResults"]["question"] == []
    assert len(result["selectedToolResults"]["memory"]) == 2
    tools_trace = result["nodeTrace"][-1]
    failed_calls = [
        call
        for call in tools_trace["outputSummary"]["toolCalls"]
        if call["toolName"] == "retrieve_question_bank"
    ]
    assert len(failed_calls) == 1
    assert failed_calls[0]["success"] is False
    assert "题库服务超时" in failed_calls[0]["error"]
    assert tools_trace["fallbackUsed"] is True


def test_tools_node_empty_selection_skips_all_tools():
    calls_log = []
    tool_fns = {
        "retrieve_role_knowledge": _fake_tool("retrieve_role_knowledge", 1, calls_log),
        "retrieve_question_bank": _fake_tool("retrieve_question_bank", 2, calls_log),
        "retrieve_candidate_memory": _fake_tool("retrieve_candidate_memory", 3, calls_log),
    }
    state = _tools_node_state(selectedTools=[])

    result = make_tools_node(tool_fns)(state)

    assert calls_log == []
    assert result["selectedToolResults"] == {"role": [], "question": [], "memory": []}
    tools_trace = result["nodeTrace"][-1]
    assert sorted(tools_trace["outputSummary"]["skippedTools"]) == [
        "retrieve_candidate_memory",
        "retrieve_question_bank",
        "retrieve_role_knowledge",
    ]
    assert tools_trace["outputSummary"]["toolCalls"] == []


def test_v3_graph_integration_plan_tools_loop_then_generate():
    plan_call_count = []

    async def fake_structured_call(**kwargs):
        plan_call_count.append(kwargs)
        if len(plan_call_count) == 1:
            model = AgentPlanModel(
                readyToAsk=False,
                selectedTools=["retrieve_question_bank"],
                toolQuery="RAG 追问",
                nextAction="deep_follow_up",
                difficulty="medium",
                focus="RAG 检索质量",
                reason="第一轮先查题库再决定。",
            )
        else:
            model = AgentPlanModel(
                readyToAsk=True,
                selectedTools=[],
                toolQuery="",
                nextAction="deep_follow_up",
                difficulty="medium",
                focus="RAG 检索质量",
                reason="题库命中已足够出题。",
            )
        return model, {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    tool_calls_log = []

    def fake_role_tool(profile: dict, next_stage: str, tool_query: str):
        tool_calls_log.append("retrieve_role_knowledge")
        return [{"id": "role-1", "content": "岗位知识命中"}]

    def fake_question_tool(profile: dict, next_stage: str, tool_query: str):
        tool_calls_log.append("retrieve_question_bank")
        return [{"id": "question-1", "content": "题库命中题目"}]

    def fake_memory_tool(profile: dict, next_stage: str, tool_query: str):
        tool_calls_log.append("retrieve_candidate_memory")
        return [{"id": "memory-1", "content": "画像命中"}]

    graph = build_interview_graph_v3(
        structured_call_fn=fake_structured_call,
        tool_fns={
            "retrieve_role_knowledge": fake_role_tool,
            "retrieve_question_bank": fake_question_tool,
            "retrieve_candidate_memory": fake_memory_tool,
        },
    )

    state = build_initial_graph_state(
        profile={"targetRole": "AI 应用开发"},
        history=[],
        next_stage="项目追问",
    )
    state["policy"] = {}

    result = asyncio.run(graph.ainvoke(state))

    assert result["nextQuestion"].get("prompt")
    assert [entry["nodeName"] for entry in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "plan",
        "tools",
        "plan",
        "generate_question",
        "update_memory",
    ]
    assert result["planningSteps"] == 2
    assert result["selectedToolResults"]["question"]
    assert tool_calls_log == ["retrieve_question_bank"]


def test_v3_graph_terminates_when_plan_never_ready():
    async def never_ready_call(**kwargs):
        model = AgentPlanModel(
            readyToAsk=False,
            selectedTools=["retrieve_question_bank"],
            toolQuery="RAG 追问",
            nextAction="deep_follow_up",
            difficulty="medium",
            focus="RAG 检索质量",
            reason="无论检索到什么都判定信息不足。",
        )
        return model, {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    tool_calls_log = []

    # 若 MAX_PLANNING_STEPS 兜底失效，plan ⇄ tools 会无限循环，
    # asyncio.run 会抛出 GraphRecursionError 而不是正常返回。
    result = asyncio.run(
        run_interview_graph_v3(
            thread_id="t",
            profile={"targetRole": "AI 应用开发"},
            history=[],
            next_stage="技术追问",
            structured_call_fn=never_ready_call,
            tool_fns={
                "retrieve_role_knowledge": _fake_tool("retrieve_role_knowledge", 1, tool_calls_log),
                "retrieve_question_bank": _fake_tool("retrieve_question_bank", 2, tool_calls_log),
                "retrieve_candidate_memory": _fake_tool("retrieve_candidate_memory", 3, tool_calls_log),
            },
        )
    )

    assert result["planningSteps"] == MAX_PLANNING_STEPS
    node_names = [entry["nodeName"] for entry in result["nodeTrace"]]
    assert node_names.count("tools") == 1
    assert node_names[-2:] == ["generate_question", "update_memory"]
    assert result["nextQuestion"].get("prompt")


def test_v3_runner_passes_recursion_limit():
    assert build_v3_invoke_config("t") == {
        "recursion_limit": 25,
        "configurable": {"thread_id": "t"},
    }
    assert build_v3_invoke_config("")["configurable"]["thread_id"] == "default-thread"

    async def ready_call(**kwargs):
        model = AgentPlanModel(
            readyToAsk=True,
            selectedTools=[],
            toolQuery="",
            nextAction="deep_follow_up",
            difficulty="medium",
            focus="RAG 基础",
            reason="画像信息已足够出题。",
        )
        return model, {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    result = asyncio.run(
        run_interview_graph_v3(
            thread_id="t",
            profile={"targetRole": "AI 应用开发"},
            history=[],
            next_stage="技术追问",
            structured_call_fn=ready_call,
            tool_fns={"retrieve_question_bank": _fake_tool("retrieve_question_bank", 1, [])},
        )
    )

    assert result["threadId"] == "t"
    assert result["checkpointSummary"]["enabled"] is False
    assert result["checkpointSummary"]["exists"] is False
    assert result["checkpointSummary"]["threadId"] == "t"


# ---------------------------------------------------------------------------
# Task 4（S4）：runtime 注册 + shadow 分派（agent_runtime 分派层接线）
# ---------------------------------------------------------------------------


def test_normalize_agent_runtime_accepts_langgraph_agent_v3() -> None:
    assert normalize_agent_runtime("langgraph_agent_v3") == "langgraph_agent_v3"
    # 未知 runtime 仍然回退默认 mainline
    assert normalize_agent_runtime("totally_unknown_runtime") == "langgraph_mainline"


def test_agent_runtime_dispatches_langgraph_agent_v3(monkeypatch) -> None:
    captured: dict = {}

    async def fake_run_interview_graph_v3(**kwargs):
        captured.update(kwargs)
        return {
            "question": {"content": "v3 dispatch question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    monkeypatch.setattr(graph_v3, "run_interview_graph_v3", fake_run_interview_graph_v3)

    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "v2 question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_agent_v3",
            thread_id="runtime-v3",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={
                "answer": "还可以",
                "profile": {"targetRole": "AI 应用开发"},
                "history": [{"question": "什么是 RAG？", "answer": "检索增强生成"}],
                "next_stage": "技术追问",
                "agent_mode": "interview",
                "application_profile_id": 7,
            },
        )
    )

    assert result["runtime"] == "langgraph_agent_v3"
    assert result["visibleRuntime"] == "langgraph_agent_v3"
    assert result["question"]["content"] == "v3 dispatch question"
    assert result["qualityGate"]["passed"] is True
    assert result["fallbackRuntime"] == ""
    # 分派层必须把 v3 需要的依赖原样传给 run_interview_graph_v3
    assert captured["thread_id"] == "runtime-v3"
    assert captured["structured_call_fn"] is call_model_structured
    assert set(captured["tool_fns"]) == {
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    }
    assert captured["profile"] == {"targetRole": "AI 应用开发"}
    assert captured["history"] == [{"question": "什么是 RAG？", "answer": "检索增强生成"}]
    assert captured["next_stage"] == "技术追问"
    assert captured["agent_mode"] == "interview"
    assert captured["application_profile_id"] == 7


def test_agent_runtime_v3_failure_falls_back_to_classic(monkeypatch) -> None:
    async def fake_run_interview_graph_v3(**kwargs):
        raise RuntimeError("v3 graph exploded")

    monkeypatch.setattr(graph_v3, "run_interview_graph_v3", fake_run_interview_graph_v3)

    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "v2 question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_agent_v3",
            thread_id="runtime-v3-error",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 RAG？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["fallbackRuntime"] == "classic"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert "LangGraph runtime 执行失败" in result["qualityGate"]["reasons"]
    assert result["runtimeAudit"]["fallbackUsed"] is True


def test_build_langgraph_v3_tool_fns_scopes_retrieval_with_user_and_db(monkeypatch) -> None:
    import backend_python.candidate_memory as candidate_memory_module
    import backend_python.question_rag as question_rag_module
    import backend_python.rag as rag_module

    calls: list[tuple[str, dict]] = []

    def fake_role_context(*args, **kwargs):
        calls.append(("role", {"args": args, "kwargs": kwargs}))
        return [{"title": "role hit"}]

    def fake_questions(*args, **kwargs):
        calls.append(("question", {"args": args, "kwargs": kwargs}))
        return [{"question": "bank hit"}]

    def fake_memory(*args, **kwargs):
        calls.append(("memory", {"args": args, "kwargs": kwargs}))
        return [{"memory": "hit"}]

    # 闭包内部是惰性 import（from .rag import ...），每次调用都从源模块
    # 取属性，因此 patch 源模块属性即可拦截。
    monkeypatch.setattr(rag_module, "retrieve_role_context", fake_role_context)
    monkeypatch.setattr(question_rag_module, "retrieve_questions", fake_questions)
    monkeypatch.setattr(candidate_memory_module, "retrieve_candidate_memory", fake_memory)

    sentinel_db = object()
    tool_fns = _build_langgraph_v3_tool_fns(application_profile_id=9, user_id=7, db=sentinel_db)

    assert tool_fns["retrieve_role_knowledge"](profile={}, next_stage="s", tool_query="q") == [{"title": "role hit"}]
    assert tool_fns["retrieve_question_bank"](profile={}, next_stage="s", tool_query="q") == [{"question": "bank hit"}]
    assert tool_fns["retrieve_candidate_memory"](profile={}, next_stage="s", tool_query="q") == [{"memory": "hit"}]

    by_tool = dict(calls)
    assert set(by_tool) == {"role", "question", "memory"}

    # role/question：tool_query 作为检索词，db + user_id 透传（签名均支持）
    assert by_tool["role"]["args"] == ({}, "q")
    assert by_tool["role"]["kwargs"] == {"limit": 3, "db": sentinel_db, "user_id": 7}
    assert by_tool["question"]["args"] == ({}, "q")
    assert by_tool["question"]["kwargs"] == {"limit": 3, "db": sentinel_db, "user_id": 7}

    # memory：传入的 db 必须被复用（不得另开 SessionLocal），且 user_id +
    # application_profile_id 一并下发，保证用户隔离
    assert by_tool["memory"]["args"] == (sentinel_db, {})
    assert by_tool["memory"]["kwargs"] == {"limit": 3, "user_id": 7, "application_profile_id": 9}
