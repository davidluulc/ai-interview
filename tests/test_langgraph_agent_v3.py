import asyncio

from backend_python.langgraph_agent.graph_v3 import (
    MAX_PLANNING_STEPS,
    AgentPlanModel,
    apply_policy_guardrail,
    make_plan_node,
)
from backend_python.structured_output import StructuredOutputExhausted


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
