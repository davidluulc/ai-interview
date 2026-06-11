from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app


def register_and_login(client: TestClient, prefix: str) -> dict:
    suffix = uuid4().hex
    email = f"{prefix}-{suffix}@example.com"
    username = f"{prefix}_{suffix[:10]}"
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


def create_document(client: TestClient, tokens: dict, title: str = "AI 应用岗位知识") -> dict:
    response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": title,
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": "FastAPI 用于构建 Python 后端 API。\n\nRAG 需要文档切片、关键词召回和命中日志。",
            "metadata": {"positionTag": "ai_app_intern", "category": "technical"},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_rag_documents_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/rag/documents")

    assert response.status_code == 401


def test_user_can_create_list_get_and_delete_rag_document() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_doc")

    created = create_document(client, tokens)

    assert created["id"]
    assert created["title"] == "AI 应用岗位知识"
    assert created["knowledgeBase"] == "role_knowledge"
    assert created["chunkCount"] == 2

    list_response = client.get("/api/rag/documents", headers=auth_headers(tokens))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [created["id"]]

    detail_response = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["document"]["id"] == created["id"]
    assert len(detail["chunks"]) == 2
    assert detail["chunks"][0]["content"].startswith("FastAPI")
    assert "FastAPI" in detail["chunks"][0]["keywords"]

    delete_response = client.delete(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    empty_response = client.get("/api/rag/documents", headers=auth_headers(tokens))

    assert empty_response.status_code == 200
    assert empty_response.json()["items"] == []


def test_create_rag_document_saves_ready_embedding_status(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_doc_embedding")

    created = create_document(client, tokens, title="带向量的知识库")
    detail_response = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert detail_response.status_code == 200
    chunks = detail_response.json()["chunks"]
    assert chunks[0]["embeddingStatus"] == "ready"
    assert chunks[0]["embeddingModel"]
    assert chunks[0]["embeddingSize"] == 3


def test_create_rag_document_keeps_chunk_when_embedding_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        raise RuntimeError("embedding provider down")

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_doc_embedding_fail")

    created = create_document(client, tokens, title="向量失败仍可保存")
    detail_response = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert detail_response.status_code == 200
    chunks = detail_response.json()["chunks"]
    assert chunks
    assert chunks[0]["embeddingStatus"] == "failed"
    assert chunks[0]["embeddingSize"] == 0


def test_rag_documents_are_isolated_by_user() -> None:
    client = TestClient(app)
    user_a = register_and_login(client, "rag_doc_a")
    user_b = register_and_login(client, "rag_doc_b")
    created = create_document(client, user_a, title="用户 A 的知识库")

    list_b = client.get("/api/rag/documents", headers=auth_headers(user_b))
    get_b = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(user_b))
    delete_b = client.delete(f"/api/rag/documents/{created['id']}", headers=auth_headers(user_b))

    assert list_b.status_code == 200
    assert list_b.json()["items"] == []
    assert get_b.status_code == 404
    assert delete_b.status_code == 404
