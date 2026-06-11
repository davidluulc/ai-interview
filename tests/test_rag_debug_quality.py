from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app


def register_and_login(client: TestClient) -> dict:
    suffix = uuid4().hex
    client.post(
        "/api/auth/register",
        json={
            "email": f"rag-debug-quality-{suffix}@example.com",
            "username": f"rag_debug_quality_{suffix[:8]}",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": f"rag-debug-quality-{suffix}@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def test_rag_debug_returns_quality_summary() -> None:
    client = TestClient(app)
    tokens = register_and_login(client)

    response = client.get(
        "/api/rag/debug?role=AI应用开发实习生&resume=FastAPI%20RAG&jd=RAG%20Agent&stage=技术追问",
        headers=auth_headers(tokens),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body["quality"].keys()) == {"roleKnowledge", "questionBank", "candidateMemory"}
    assert body["quality"]["roleKnowledge"]["level"] in {"good", "weak", "miss"}
    assert "hitCount" in body["quality"]["questionBank"]
    assert "reason" in body["quality"]["candidateMemory"]


def test_rag_debug_treats_empty_application_profile_id_as_none() -> None:
    client = TestClient(app)
    tokens = register_and_login(client)

    response = client.get(
        "/api/rag/debug?applicationProfileId=&role=AI应用开发实习生&stage=技术追问",
        headers=auth_headers(tokens),
    )

    assert response.status_code == 200
    assert response.json()["quality"]["roleKnowledge"]["level"] in {"good", "weak", "miss"}


def test_rag_debug_returns_explanations(monkeypatch) -> None:
    client = TestClient(app)
    tokens = register_and_login(client)

    def fake_role_context(profile, stage, limit=5, db=None, user_id=None):
        return [
            {
                "title": "RAG 质量评估与可观测面板",
                "content": "Hit@K、MRR、关键词覆盖率用于评估 RAG 召回质量。",
                "score": 9,
                "matchedKeywords": ["Hit@K", "MRR", "关键词覆盖率"],
                "metadata": {"positionTag": "ai_app_intern", "interviewStage": "RAG 评估"},
            }
        ]

    monkeypatch.setattr("backend_python.routes.rag.retrieve_role_context", fake_role_context)
    monkeypatch.setattr("backend_python.routes.rag.retrieve_questions", lambda *args, **kwargs: [])
    monkeypatch.setattr("backend_python.routes.rag.retrieve_candidate_memory", lambda *args, **kwargs: [])

    response = client.get(
        "/api/rag/debug",
        params={"role": "AI 应用开发实习生", "jd": "RAG 质量评估", "stage": "RAG 评估"},
        headers=auth_headers(tokens),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["explanations"]["roleKnowledge"]["hitCount"] == 1
    assert "RAG 质量评估与可观测面板" in data["explanations"]["roleKnowledge"]["topTitles"]
    assert "Hit@K" in data["explanations"]["roleKnowledge"]["matchedTerms"]
    assert data["explanations"]["roleKnowledge"]["qualityLevel"] == "good"
