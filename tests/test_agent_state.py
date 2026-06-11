import json

from backend_python.agent_state import (
    AGENT_EVENTS,
    AGENT_SESSION_STATES,
    build_interview_agent_state,
)


def test_build_interview_agent_state_is_json_serializable():
    state = build_interview_agent_state(
        profile={
            "applicationProfileId": 1,
            "targetRole": "AI 应用开发实习生",
            "resume": "做过 RAG 项目",
            "jd": "熟悉 Agent",
        },
        history=[{"question": "什么是 RAG？", "answer": "不知道", "focus": "RAG 基础"}],
        next_stage="技术追问",
        role_quality={"level": "good", "hitCount": 3},
        question_quality={"level": "weak", "hitCount": 1},
        memory_quality={"level": "miss", "hitCount": 0},
        max_rounds=8,
        agent_mode="coach",
    )

    json.dumps(state, ensure_ascii=False)
    assert state["session"]["agentMode"] == "coach"
    assert state["session"]["roundCount"] == 1
    assert state["session"]["remainingRounds"] == 7
    assert state["lastAnswer"]["answer"] == "不知道"
    assert state["retrievalQuality"]["roleKnowledge"]["hitCount"] == 3
    assert "observe_state" in state["agentNodes"]


def test_build_interview_agent_state_keeps_legacy_top_level_fields():
    state = build_interview_agent_state(
        profile={},
        history=[{"question": "讲讲 FastAPI", "answer": "它是 Python 后端框架"}],
        next_stage="项目追问",
        role_quality={},
        question_quality={},
        memory_quality={},
        agent_mode="interview",
    )

    assert state["agentMode"] == "interview"
    assert state["nextStage"] == "项目追问"
    assert state["roundCount"] == 1
    assert state["remainingRounds"] == 7
    assert state["answerStatus"] in {"不会", "模糊", "完整"}
    assert state["askedQuestions"] == ["讲讲 FastAPI"]


def test_build_interview_agent_state_normalizes_invalid_mode():
    state = build_interview_agent_state(
        profile={},
        history=[],
        next_stage="综合追问",
        role_quality={},
        question_quality={},
        memory_quality={},
        agent_mode="bad-mode",
    )

    assert state["session"]["agentMode"] == "interview"
    assert state["agentMode"] == "interview"


def test_agent_state_constants_define_state_machine_vocabulary():
    assert "waiting_answer" in AGENT_SESSION_STATES
    assert "ANSWER_SUBMITTED" in AGENT_EVENTS


def test_build_interview_agent_state_detects_topic_lock_from_recent_focuses():
    state = build_interview_agent_state(
        profile={},
        history=[
            {"question": "Explain query_text", "answer": "", "focus": "rag_log_json"},
            {"question": "Explain hit_count", "answer": "", "focus": "rag_log_json"},
            {"question": "Explain hits_json", "answer": "", "focus": "rag_log_json"},
        ],
        next_stage="technical_follow_up",
        role_quality={},
        question_quality={},
        memory_quality={},
        agent_mode="coach",
    )

    topic_lock = state["answerAnalysis"]["topicLock"]
    assert topic_lock["locked"] is True
    assert topic_lock["topic"] == "rag_log_json"
    assert topic_lock["count"] == 3
    assert "topic_lock_guardrail" in state["answerAnalysis"]["triggerSignals"]
