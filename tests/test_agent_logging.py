from uuid import uuid4

from backend_python.agent_logging import create_agent_decision_log, serialize_agent_decision_log
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import AgentDecisionLog, User


def test_agent_decision_log_model_declares_expected_columns() -> None:
    columns = AgentDecisionLog.__table__.columns

    assert "next_action" in columns
    assert "decision_json" in columns
    assert "fallback_used" in columns


def test_create_agent_decision_log_persists_decision() -> None:
    init_db()
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(email=f"agent-log-{suffix}@example.com", username=f"agent_log_{suffix[:10]}", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        log = create_agent_decision_log(
            db,
            user_id=user.id,
            application_profile_id=None,
            request_type="next_question",
            state={"roundCount": 1},
            decision={
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG",
                "reason": "test",
                "tools": [],
            },
            fallback_used=True,
        )
        data = serialize_agent_decision_log(log)

    assert data["nextAction"] == "lower_difficulty"
    assert data["fallbackUsed"] is True
    assert data["state"]["roundCount"] == 1


def test_serialize_agent_decision_log_exposes_debug_signals_for_debug_panel() -> None:
    init_db()
    suffix = uuid4().hex
    debug_signals = {
        "weakAnswerStreak": 2,
        "repeatedQuestionCount": 0,
        "topicLocked": False,
        "topicLockTopic": "",
        "guardrailApplied": True,
        "topicShifted": True,
        "triggerRules": ["interview_weak_answer_limit", "topic_shift"],
    }
    with SessionLocal() as db:
        user = User(email=f"agent-debug-{suffix}@example.com", username=f"agent_debug_{suffix[:10]}", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        log = create_agent_decision_log(
            db,
            user_id=user.id,
            application_profile_id=None,
            request_type="next_question",
            state={"roundCount": 2},
            decision={
                "nextAction": "switch_topic",
                "stage": "technical_follow_up",
                "difficulty": "basic",
                "focus": "rag_basic",
                "reason": "test",
                "tools": ["retrieve_context"],
                "guardrailApplied": True,
                "topicShift": {"from": "rag_log_json", "to": "rag_basic"},
                "debugSignals": debug_signals,
            },
        )
        data = serialize_agent_decision_log(log)

    assert data["debugSignals"] == debug_signals
    assert data["guardrailApplied"] is True
    assert data["topicShift"] == {"from": "rag_log_json", "to": "rag_basic"}
    assert data["decision"]["debugSignals"] == debug_signals
