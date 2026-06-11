import asyncio

from backend_python.langgraph_agent.adapters import (
    decide_real_action_for_graph,
    retrieve_real_context_for_graph,
)


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
