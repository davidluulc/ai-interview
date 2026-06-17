import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, RagRetrievalLog, User
from backend_python.ai_debug import normalize_checkpoint
from backend_python.langgraph_agent.checkpoint import record_checkpoint_summary
from backend_python.langgraph_agent.checkpoint_store import checkpoint_summary_store
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
    email = f"ai-debug-admin-{suffix}@example.com"
    register_and_login(client, email, f"ai_debug_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return {"Authorization": f"Bearer {admin['accessToken']}"}, user.id


def test_admin_ai_debug_requires_admin() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user = register_and_login(client, f"ai-debug-user-{suffix}@example.com", f"ai_debug_user_{suffix[:8]}")

    no_token = client.get("/api/admin/ai-debug/recent")
    regular_user = client.get(
        "/api/admin/ai-debug/recent",
        headers={"Authorization": f"Bearer {user['accessToken']}"},
    )

    assert no_token.status_code == 401
    assert regular_user.status_code == 403


def test_admin_ai_debug_recent_returns_agent_trace_summary() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        log = AgentDecisionLog(
            user_id=user_id,
            application_profile_id=101,
            request_type="next_question",
            next_action="lower_difficulty",
            stage="技术追问",
            difficulty="basic",
            focus="RAG 日志 JSON",
            reason="连续弱回答，降低难度",
            tools_json=json.dumps(["role_knowledge"], ensure_ascii=False),
            state_json=json.dumps(
                {"agentMode": "coach", "roundCount": 3, "remainingRounds": 5, "threadId": "ai-debug-thread-1"},
                ensure_ascii=False,
            ),
            decision_json=json.dumps(
                {
                    "nextAction": "lower_difficulty",
                    "fallbackUsed": True,
                    "policy": {"triggerRules": ["weak_answer_streak"]},
                },
                ensure_ascii=False,
            ),
            fallback_used=1,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=101,
                request_type="next_question",
                query_text="RAG 日志 JSON",
                retriever_name="role_knowledge",
                retrieval_mode="hybrid",
                hit_count=0,
                hits_json="[]",
            )
        )
        db.commit()

    response = client.get("/api/admin/ai-debug/recent", headers=headers)

    assert response.status_code == 200
    body = response.json()
    item = next(item for item in body["items"] if item["traceId"] == log_id)
    assert item["nextAction"] == "lower_difficulty"
    assert item["nextActionLabel"] == "降低难度"
    assert item["agentMode"] == "coach"
    assert item["fallbackUsed"] is True
    assert item["totalRagHits"] == 0
    assert item["threadId"] == "ai-debug-thread-1"
    assert any(diagnostic["type"] == "fallback_used" for diagnostic in item["diagnostics"])
    assert any(diagnostic["type"] == "empty_recall" for diagnostic in item["diagnostics"])


def test_admin_ai_debug_detail_contains_rag_agent_langgraph_and_diagnostics() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        log = AgentDecisionLog(
            user_id=user_id,
            application_profile_id=202,
            request_type="next_question",
            next_action="deepen",
            stage="项目追问",
            difficulty="medium",
            focus="Agent Policy",
            reason="回答较完整，继续深挖",
            tools_json=json.dumps(["role_knowledge", "question_bank"], ensure_ascii=False),
            state_json=json.dumps({"agentMode": "interview", "roundCount": 2}, ensure_ascii=False),
            decision_json=json.dumps(
                {
                    "nextAction": "deepen",
                    "policyReasons": ["answer_complete"],
                    "triggerRules": ["answer_complete"],
                    "fallbackUsed": False,
                },
                ensure_ascii=False,
            ),
            fallback_used=0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id
        db.add(
            RagRetrievalLog(
                user_id=user_id,
                application_profile_id=202,
                request_type="next_question",
                query_text="Agent Policy",
                retriever_name="question_bank",
                retrieval_mode="hybrid",
                hit_count=1,
                hits_json=json.dumps([{"title": "Agent Policy", "score": 0.91}], ensure_ascii=False),
            )
        )
        db.commit()

    response = client.get(f"/api/admin/ai-debug/{log_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"summary", "rag", "agent", "langgraph", "diagnostics"}
    assert body["summary"]["traceId"] == log_id
    assert body["rag"]["totalHitCount"] == 1
    assert body["rag"]["items"][0]["retrieverLabel"] == "题库"
    assert body["agent"]["nextActionLabel"] == "继续深挖"
    assert body["agent"]["fallbackUsed"] is False
    assert body["langgraph"]["exists"] is False
    assert "未启用 LangGraph 旁路" in body["langgraph"]["explanation"]
    assert isinstance(body["diagnostics"], list)


def test_admin_ai_debug_detail_handles_missing_trace() -> None:
    client = TestClient(app)
    headers, _ = create_admin_headers()

    response = client.get("/api/admin/ai-debug/999999999", headers=headers)

    assert response.status_code == 404


def test_admin_ai_debug_detail_contains_runtime_governance_fields() -> None:
    client = TestClient(app)
    headers, user_id = create_admin_headers()
    with SessionLocal() as db:
        log = AgentDecisionLog(
            user_id=user_id,
            application_profile_id=303,
            request_type="next_question",
            next_action="lower_difficulty",
            stage="技术追问",
            difficulty="basic",
            focus="LangGraph runtime governance",
            reason="连续弱回答，触发人工复核",
            tools_json=json.dumps(["human_review"], ensure_ascii=False),
            state_json=json.dumps({"threadId": "debug-runtime-1", "agentMode": "coach"}, ensure_ascii=False),
            decision_json=json.dumps({"nextAction": "lower_difficulty"}, ensure_ascii=False),
            fallback_used=0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id

    record_checkpoint_summary(
        thread_id="debug-runtime-1",
        state={
            "runtime": "langgraph",
            "status": "interrupted",
            "currentNode": "human_review",
            "decision": {"nextAction": "lower_difficulty"},
            "policy": {"requiresHumanReview": True, "triggerRules": ["weak_answer_streak"]},
            "nodeTrace": [{"node": "human_review"}],
        },
    )
    checkpoint_summary_store.mark_interrupted(
        "debug-runtime-1",
        interrupt={"reason": "连续弱回答", "options": ["switch_to_coach"]},
    )

    response = client.get(f"/api/admin/ai-debug/{log_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["langgraph"]["runtime"] == "langgraph"
    assert data["langgraph"]["status"] == "interrupted"
    assert data["langgraph"]["currentNode"] == "human_review"
    assert data["langgraph"]["requiresHumanReview"] is True
    assert data["langgraph"]["interrupt"]["reason"] == "连续弱回答"


def test_admin_ai_debug_detail_contains_runtime_quality_and_comparison() -> None:
    checkpoint = {
        "exists": True,
        "threadId": "debug-runtime-v4",
        "runtime": "langgraph",
        "status": "completed",
        "currentNode": "generate_question",
        "qualityGate": {"passed": False, "fallbackToClassic": True, "reasons": ["LangGraph 没有生成可展示的问题"]},
        "comparisonSummary": {
            "visibleRuntime": "classic",
            "comparison": {
                "actionMatched": False,
                "difficultyMatched": False,
                "qualityGatePassed": False,
                "fallbackToClassic": True,
                "reasons": ["两条链路的下一步动作不同"],
            },
        },
    }

    normalized = normalize_checkpoint(checkpoint, "debug-runtime-v4")

    assert normalized["qualityGate"]["passed"] is False
    assert normalized["comparisonSummary"]["comparison"]["fallbackToClassic"] is True
    assert normalized["visibleRuntime"] == "classic"


def test_admin_ai_debug_detail_contains_runtime_audit() -> None:
    checkpoint = {
        "exists": True,
        "threadId": "debug-runtime-v5",
        "runtime": "langgraph",
        "status": "completed",
        "currentNode": "generate_question",
        "runtimeAudit": {
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "visibleRuntime": "classic",
            "fallbackUsed": True,
            "policyReasons": ["管理员账号允许使用 LangGraph 灰度链路"],
            "qualityGateReasons": ["LangGraph 问题与最近问题重复度过高"],
        },
    }

    normalized = normalize_checkpoint(checkpoint, "debug-runtime-v5")

    assert normalized["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert normalized["runtimeAudit"]["allowedRuntime"] == "langgraph"
    assert normalized["runtimeAudit"]["visibleRuntime"] == "classic"
    assert normalized["runtimeAudit"]["fallbackUsed"] is True
