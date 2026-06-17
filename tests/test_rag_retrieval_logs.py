import json
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app
from backend_python.rag_logging import serialize_hits


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
    if temperature < 0.3:
        return {
            "score": 86,
            "strengths": ["能说明项目背景"],
            "risks": ["RAG 召回策略还需要更具体"],
            "actions": ["补充命中日志和评估指标"],
        }
    return {
        "stage": "技术追问",
        "stability": "稳定评分",
        "focus": "RAG 召回链路追问",
        "prompt": "你提到做过 RAG，请具体说明 query 构造、召回和重排链路。",
    }


async def fake_call_model_capture_strategy(
    messages: list[dict],
    temperature: float,
    model_name: str = "",
) -> dict[str, Any]:
    fake_call_model_capture_strategy.messages = messages
    return {
        "stage": "技术追问",
        "stability": "稳定评分",
        "focus": "RAG 日志排查",
        "prompt": "你刚才提到 RAG 日志，请说明 hitCount、quality 和 usedInPrompt 分别怎么用于排查问题。",
    }


fake_call_model_capture_strategy.messages = []


def test_serialize_hits_keeps_hybrid_debug_fields() -> None:
    raw = serialize_hits(
        [
            {
                "retrievalMode": "hybrid",
                "matchedRetrievalModes": ["bm25", "vector"],
                "chunkId": 1,
                "documentId": 2,
                "title": "RAG 日志",
                "score": 0.91,
                "hybridScore": 0.91,
                "bm25Score": 2.4,
                "vectorScore": 0.87,
                "matchedTokens": ["rag"],
                "matchedKeywords": ["RAG"],
            }
        ],
        retriever_name="role_knowledge",
    )

    assert '"matchedRetrievalModes": ["bm25", "vector"]' in raw
    assert '"hybridScore": 0.91' in raw
    assert '"bm25Score": 2.4' in raw
    assert '"vectorScore": 0.87' in raw
    data = json.loads(raw)
    assert data[0]["metadata"]["knowledgeBase"] == "role_knowledge"
    assert data[0]["metadata"]["chunkId"] == 1
    assert data[0]["metadata"]["documentId"] == 2


def test_serialize_hits_keeps_rerank_debug_fields() -> None:
    raw = serialize_hits(
        [
            {
                "retrievalMode": "hybrid_rerank",
                "matchedRetrievalModes": ["bm25", "vector", "rerank"],
                "chunkId": 1,
                "documentId": 2,
                "title": "RAG 日志",
                "score": 0.96,
                "hybridScore": 0.71,
                "bm25Score": 2.4,
                "vectorScore": 0.87,
                "rerankScore": 0.96,
                "rerankIndex": 1,
                "preRerankRank": 2,
            }
        ]
    )

    assert '"retrievalMode": "hybrid_rerank"' in raw
    assert '"rerankScore": 0.96' in raw
    assert '"rerankIndex": 1' in raw
    assert '"preRerankRank": 2' in raw


def test_rag_logs_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/rag/logs/recent")

    assert response.status_code == 401


def test_next_question_writes_rag_retrieval_logs(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"rag-log-{suffix}@example.com", f"rag_log_{suffix[:10]}")

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 FastAPI 和 RAG 模拟面试系统",
                "jd": "要求熟悉 Python、FastAPI、大模型 API、RAG",
            },
            "history": [],
            "nextStage": "技术追问",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    assert response.json()["focus"] == "RAG 召回链路追问"

    logs_response = client.get("/api/rag/logs/recent", headers=auth_headers(tokens))

    assert logs_response.status_code == 200
    logs = logs_response.json()["items"]
    retrievers = {item["retrieverName"] for item in logs}
    assert {"role_knowledge", "question_bank", "candidate_memory"}.issubset(retrievers)
    assert all(item["requestType"] == "next_question" for item in logs[:3])
    assert all(item["usedInPrompt"] is True for item in logs[:3])
    assert any(item["hitCount"] > 0 for item in logs)


def test_next_question_prompt_payload_includes_quality_strategy(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model_capture_strategy)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"question-strategy-{suffix}@example.com", f"question_strategy_{suffix[:6]}")

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 FastAPI、RAG 命中日志和 quality 评估",
                "jd": "要求理解 RAG 检索、日志排查和模型调用",
            },
            "history": [
                {
                    "stage": "技术基础",
                    "focus": "RAG 召回链路",
                    "question": "请说明 RAG 的基本流程。",
                    "answer": "我会记录命中日志和 quality 字段。",
                }
            ],
            "nextStage": "技术追问",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    user_payload = next(message for message in fake_call_model_capture_strategy.messages if message["role"] == "user")
    data = json.loads(user_payload["content"])

    assert data["lastAnswer"]["answer"] == "我会记录命中日志和 quality 字段。"
    assert data["askedQuestions"] == ["请说明 RAG 的基本流程。"]
    assert data["questionStrategy"]["avoidRepeat"] is True
    assert "优先围绕命中良好" in data["questionStrategy"]["ragGuidance"]
    assert "roleKnowledge" in data["retrievalQuality"]


def test_next_question_rag_logs_keep_application_profile_id(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"rag-profile-log-{suffix}@example.com", f"rag_profile_log_{suffix[:6]}")

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": 12345,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 FastAPI 和 RAG 模拟面试系统",
                "jd": "要求熟悉 Python、FastAPI、大模型 API、RAG",
            },
            "history": [],
            "nextStage": "技术追问",
        },
    )

    assert response.status_code == 200

    logs = client.get("/api/rag/logs/recent", headers=auth_headers(tokens)).json()["items"]

    assert logs
    assert {item["applicationProfileId"] for item in logs[:3]} == {12345}


def test_next_question_logs_bm25_for_database_rag_hits(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"rag-bm25-log-{suffix}@example.com", f"rag_bm25_{suffix[:8]}")

    document_response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": "RAG BM25 日志知识",
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": "RAG 命中日志需要记录 query、retriever、hit_count、quality 和 used_in_prompt。",
            "metadata": {"category": "technical"},
        },
    )
    assert document_response.status_code == 200

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 RAG 命中日志",
                "jd": "要求理解 RAG 命中日志和 quality",
            },
            "history": [],
            "nextStage": "技术追问",
        },
    )
    assert response.status_code == 200

    logs = client.get("/api/rag/logs/recent", headers=auth_headers(tokens)).json()["items"]
    role_log = next(item for item in logs if item["retrieverName"] == "role_knowledge")
    assert role_log["retrievalMode"] == "bm25"


def test_report_writes_report_rag_logs(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"rag-report-{suffix}@example.com", f"rag_report_{suffix[:10]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 FastAPI 和 RAG 模拟面试系统",
                "jd": "要求熟悉 Python、FastAPI、大模型 API、RAG",
            },
            "answers": [{"stage": "技术追问", "answer": "我会记录 RAG 命中日志。"}],
        },
    )

    assert response.status_code == 200

    logs_response = client.get("/api/rag/logs/recent?requestType=report", headers=auth_headers(tokens))

    assert logs_response.status_code == 200
    logs = logs_response.json()["items"]
    assert logs
    assert {item["requestType"] for item in logs} == {"report"}


def test_rag_logs_are_isolated_by_user(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"rag-user-a-{suffix}@example.com", f"rag_user_a_{suffix[:8]}")
    user_b = register_and_login(client, f"rag-user-b-{suffix}@example.com", f"rag_user_b_{suffix[:8]}")

    client.post(
        "/api/interview/next-question",
        headers=auth_headers(user_a),
        json={
            "profile": {
                "candidateName": "A",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "RAG",
                "jd": "RAG",
            },
            "history": [],
            "nextStage": "技术追问",
        },
    )

    response_b = client.get("/api/rag/logs/recent", headers=auth_headers(user_b))

    assert response_b.status_code == 200
    assert response_b.json()["items"] == []
