import json
import asyncio

from backend_python.agent_orchestrator import run_next_question_agent


def test_run_next_question_agent_returns_state_decision_trace_and_hits():
    async def fake_decide_next_action(state, *, call_model_fn):
        return {
            "nextAction": "lower_difficulty",
            "stage": state["nextStage"],
            "difficulty": "basic",
            "focus": "RAG 基础",
            "reason": "候选人上一轮回答不知道，先降难度。",
            "tools": ["retrieve_context", "generate_question"],
            "agentMode": state["agentMode"],
            "fallbackUsed": False,
        }

    result = asyncio.run(
        run_next_question_agent(
            profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            history=[{"question": "RAG 是什么？", "answer": "不知道"}],
            next_stage="技术追问",
            agent_mode="coach",
            role_retrieve_fn=lambda profile, next_stage, limit: [{"title": "RAG 召回", "score": 0.9}],
            question_retrieve_fn=lambda profile, next_stage, limit: [{"question": "解释 RAG", "score": 0.8}],
            memory_retrieve_fn=lambda profile, limit: [{"content": "候选人 RAG 薄弱", "score": 0.7, "weakTags": ["rag_quality"]}],
            decide_next_action_fn=fake_decide_next_action,
            call_model_fn=lambda **kwargs: {},
        )
    )

    json.dumps(result, ensure_ascii=False)
    assert result["roleHits"][0]["title"] == "RAG 召回"
    assert result["questionHits"][0]["question"] == "解释 RAG"
    assert result["memoryHits"][0]["content"] == "候选人 RAG 薄弱"
    assert result["agentState"]["agentMode"] == "coach"
    assert result["agentDecision"]["nextAction"] == "lower_difficulty"
    assert result["toolCalls"][0]["toolName"] == "retrieve_role_knowledge"
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_weakness_strategy",
        "apply_policy",
        "select_training_template",
        "select_action",
    ]
    analyze_trace = result["nodeTrace"][1]
    assert analyze_trace["outputSummary"]["answerStatus"] == "不会"
    assert analyze_trace["outputSummary"]["weakAnswerStreak"] == 1
    weakness_trace = result["nodeTrace"][3]
    assert weakness_trace["outputSummary"]["enabled"] is True
    assert "primaryWeakTag" in weakness_trace["outputSummary"]
    policy_trace = result["nodeTrace"][4]
    assert policy_trace["outputSummary"]["recommendedAction"] == "lower_difficulty"
    assert "policyReasons" in result["agentDecision"]["policy"]
    template_trace = result["nodeTrace"][5]
    assert template_trace["outputSummary"]["enabled"] is True
    assert template_trace["outputSummary"]["weakTag"] == "rag_quality"
    assert result["agentDecision"]["trainingTemplateHint"]["weakTag"] == "rag_quality"
    assert result["agentDecision"]["toolCalls"] == result["toolCalls"]
    assert result["agentDecision"]["nodeTrace"] == result["nodeTrace"]


def test_run_next_question_agent_marks_failed_retrieval_in_trace():
    def broken_role_retriever(profile, next_stage, limit):
        raise RuntimeError("role rag unavailable")

    async def fake_decide_next_action(state, *, call_model_fn):
        return {
            "nextAction": "switch_topic",
            "stage": "技术追问",
            "difficulty": "basic",
            "focus": "后端模块设计",
            "reason": "岗位知识库失败时先使用其它上下文兜底。",
            "tools": ["retrieve_context"],
            "agentMode": state["agentMode"],
            "fallbackUsed": True,
        }

    result = asyncio.run(
        run_next_question_agent(
            profile={"targetRole": "AI 应用开发实习生"},
            history=[],
            next_stage="技术追问",
            agent_mode="interview",
            role_retrieve_fn=broken_role_retriever,
            question_retrieve_fn=lambda profile, next_stage, limit: [],
            memory_retrieve_fn=lambda profile, limit: [],
            decide_next_action_fn=fake_decide_next_action,
            call_model_fn=lambda **kwargs: {},
        )
    )

    retrieve_trace = result["nodeTrace"][2]
    assert result["roleHits"] == []
    assert result["toolCalls"][0]["success"] is False
    assert "role rag unavailable" in result["toolCalls"][0]["error"]
    assert retrieve_trace["nodeName"] == "retrieve_context"
    assert retrieve_trace["fallbackUsed"] is True
    assert result["agentDecision"]["fallbackUsed"] is True


def test_run_next_question_agent_adds_default_guardrail_metadata_to_decision():
    async def fake_decide_next_action(state, *, call_model_fn):
        return {
            "nextAction": "lower_difficulty",
            "stage": "technical_follow_up",
            "difficulty": "basic",
            "focus": "rag_basic",
            "reason": "test",
            "tools": ["retrieve_context"],
            "agentMode": state["agentMode"],
            "fallbackUsed": False,
        }

    result = asyncio.run(
        run_next_question_agent(
            profile={"targetRole": "AI application intern"},
            history=[{"question": "What is RAG?", "answer": ""}],
            next_stage="technical_follow_up",
            agent_mode="coach",
            role_retrieve_fn=lambda profile, next_stage, limit: [],
            question_retrieve_fn=lambda profile, next_stage, limit: [],
            memory_retrieve_fn=lambda profile, limit: [],
            decide_next_action_fn=fake_decide_next_action,
            call_model_fn=lambda **kwargs: {},
        )
    )

    assert result["agentDecision"]["guardrailApplied"] is False
    assert "triggerRules" in result["agentDecision"]
    assert "decisionSummary" in result["agentDecision"]
