from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app


def register_and_login(client: TestClient, prefix: str) -> dict:
    suffix = uuid4().hex
    email = f"{prefix}-{suffix}@example.com"
    username = f"{prefix}_{suffix[:10]}"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    assert response.status_code == 200
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    return login_response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def create_document(client: TestClient, tokens: dict, *, title: str, content: str) -> dict:
    response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": title,
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": content,
            "metadata": {"category": "technical"},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_same_document_content_generates_same_content_hash(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_dedup_hash")
    content = "RAG deduplication should normalize repeated document content."

    first = create_document(client, tokens, title="Dedup document A", content=content)
    second = create_document(client, tokens, title="Dedup document B", content=f"  {content}  ")

    assert first["contentHash"]
    assert first["contentHash"] == second["contentHash"]


def test_duplicate_chunks_are_counted_and_serialized(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_dedup_chunk")
    repeated_paragraph = "RAG chunk deduplication keeps duplicate statistics."

    created = create_document(
        client,
        tokens,
        title="Duplicate chunk document",
        content=f"{repeated_paragraph}\n\n{repeated_paragraph}",
    )

    assert created["chunkCount"] == 2
    assert created["duplicateChunkCount"] == 1

    detail_response = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert detail_response.status_code == 200
    detail = detail_response.json()
    chunks = detail["chunks"]
    assert detail["document"]["duplicateChunkCount"] == 1
    assert chunks[0]["chunkHash"]
    assert chunks[0]["chunkHash"] == chunks[1]["chunkHash"]
    assert chunks[0]["isDuplicate"] is False
    assert chunks[1]["isDuplicate"] is True
