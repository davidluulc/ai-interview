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
