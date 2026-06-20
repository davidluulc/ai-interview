import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, ApplicationProfile, InterviewRecord, RagRetrievalLog, User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()


def promote_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()


def create_admin_headers() -> tuple[dict[str, str], int]:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"observability-admin-{suffix}@example.com"
    register_and_login(client, email, f"observability_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return {"Authorization": f"Bearer {admin['accessToken']}"}, user.id


def create_user_and_profile(email_prefix: str) -> tuple[int, int, str]:
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(
            email=f"{email_prefix}-{suffix}@example.com",
            username=f"{email_prefix}_{suffix[:8]}",
            password_hash="x",
            role="user",
        )
        db.add(user)
        db.flush()
        profile = ApplicationProfile(
            user_id=user.id,
            title="Python 后端实习",
            target_role="Python 后端",
            application_type="实习",
            resume="RAG 项目",
            jd="负责 RAG 和 Agent 观测",
            company="Demo",
            position_tag="backend",
        )
        db.add(profile)
        db.commit()
        return int(user.id), int(profile.id), user.email


def test_admin_observability_interviews_groups_by_interview_record() -> None:
    client = TestClient(app)
    headers, _ = create_admin_headers()
    user_id, profile_id, email = create_user_and_profile("obs-list")
    with SessionLocal() as db:
        record = InterviewRecord(
            user_id=user_id,
            application_profile_id=profile_id,
            candidate_name="Demo",
            target_role="Python 后端",
            application_type="实习",
            mode="coach",
            depth="standard",
            score=80,
            profile_json="{}",
            answers_json=json.dumps(
                [
                    {"question": "RAG 日志字段怎么排查？", "answer": "看 retrieval_mode 和 hit_count"},
                    {"question": "Agent 为什么降难度？", "answer": "因为连续弱回答"},
                ],
                ensure_ascii=False,
            ),
            report_json=json.dumps({"overall": "ok"}, ensure_ascii=False),
        )
        db.add(record)
        db.flush()
        record_id = int(record.id)
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record_id,
                request_type="next_question",
                query_text="RAG 日志字段",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=2,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record_id,
                request_type="next_question",
                query_text="候选人画像",
                retriever_name="candidate_memory",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            AgentDecisionLog(
                user_id=user_id,
                application_profile_id=profile_id,
                request_type="next_question",
                next_action="lower_difficulty",
                stage="技术追问",
                difficulty="basic",
                focus="RAG 日志",
                reason="候选人连续弱回答",
                tools_json="[]",
                state_json=json.dumps({"threadId": "obs-thread"}, ensure_ascii=False),
                decision_json="{}",
                fallback_used=1,
            )
        )
        db.commit()

    response = client.get("/api/admin/observability/interviews", headers=headers)

    assert response.status_code == 200
    body = response.json()
    item = next(item for item in body["items"] if item["recordId"] == record_id)
    assert item["userEmail"] == email
    assert item["profileTitle"] == "Python 后端实习"
    assert item["questionCount"] == 2
    assert item["reportStatus"] == "ready"
    assert item["ragSummary"]["goodCount"] == 1
    assert item["ragSummary"]["emptyCount"] == 1
    assert item["agentSummary"]["fallbackCount"] == 1
    assert item["agentSummary"]["lowerDifficultyCount"] == 1
    assert item["relation"]["rag"] == "interview_record_id"


def test_admin_observability_interview_detail_shows_turns_and_unlinked_logs() -> None:
    client = TestClient(app)
    headers, _ = create_admin_headers()
    user_id, profile_id, _ = create_user_and_profile("obs-detail")
    with SessionLocal() as db:
        record = InterviewRecord(
            user_id=user_id,
            application_profile_id=profile_id,
            candidate_name="Demo",
            target_role="Python 后端",
            application_type="实习",
            mode="coach",
            depth="standard",
            score=80,
            profile_json="{}",
            answers_json=json.dumps([{"question": "RAG 怎么定位空召回？", "answer": "看 hit_count"}], ensure_ascii=False),
            report_json=json.dumps({"decisionSummary": "围绕 RAG 空召回追问"}, ensure_ascii=False),
        )
        db.add(record)
        db.flush()
        record_id = int(record.id)
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=record_id,
                request_type="next_question",
                query_text="RAG 空召回",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=1,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=profile_id,
                interview_record_id=None,
                request_type="next_question",
                query_text="未归属日志",
                retriever_name="question_bank",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
                used_in_prompt=1,
            )
        )
        db.commit()

    response = client.get(f"/api/admin/observability/interviews/{record_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["recordId"] == record_id
    assert body["overview"]["profileTitle"] == "Python 后端实习"
    assert body["turns"][0]["turnIndex"] == 1
    assert body["turns"][0]["question"] == "RAG 怎么定位空召回？"
    assert body["turns"][0]["ragSummary"][0]["label"] == "岗位知识库"
    assert body["turns"][0]["ragSummary"][0]["qualityLabel"] == "弱相关"
    assert body["unlinkedLogs"]["ragLogCount"] == 1
