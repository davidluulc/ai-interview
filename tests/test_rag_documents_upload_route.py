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


def test_upload_text_document_creates_rag_document(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_text")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={
            "title": "FastAPI Depends 资料",
            "knowledgeBase": "role_knowledge",
            "visibility": "private",
            "metadata": '{"positionTag":"python_backend"}',
        },
        files={
            "file": (
                "depends.txt",
                b"FastAPI Depends is dependency injection.\n\nRAG chunk metadata records source.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["document"]["title"] == "FastAPI Depends 资料"
    assert body["document"]["sourceType"] == "upload"
    assert body["document"]["metadata"]["originalFilename"] == "depends.txt"
    assert body["preview"]["chunkCount"] >= 1
    assert body["taskId"].startswith("rag_ingestion-")

    task_response = client.get(
        f"/api/rag/documents/ingestion-tasks/{body['taskId']}",
        headers=auth_headers(tokens),
    )
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "success"
    assert task_response.json()["result"]["document"]["id"] == body["document"]["id"]


def test_upload_markdown_document_preserves_heading_text(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.4, 0.5, 0.6]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_md")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "RAG Markdown", "knowledgeBase": "question_bank", "visibility": "private"},
        files={"file": ("rag.md", "# RAG 标题\n\n## Chunk 切分\n\nmetadata filter", "text/markdown")},
    )

    assert response.status_code == 200
    document_id = response.json()["document"]["id"]
    detail_response = client.get(f"/api/rag/documents/{document_id}", headers=auth_headers(tokens))
    assert detail_response.status_code == 200
    chunk_text = "\n".join(chunk["content"] for chunk in detail_response.json()["chunks"])
    assert "# RAG 标题" in chunk_text
    assert "metadata filter" in chunk_text


def test_upload_rejects_unsupported_file_type() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_bad_type")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "表格", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("bad.xlsx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["error"]["message"]


def test_upload_rejects_invalid_metadata_json() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_bad_metadata")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={
            "title": "Invalid metadata",
            "knowledgeBase": "role_knowledge",
            "visibility": "private",
            "metadata": "[]",
        },
        files={"file": ("metadata.txt", b"RAG metadata must be object.", "text/plain")},
    )

    assert response.status_code == 400
    assert "metadata must be a JSON object" in response.json()["error"]["message"]
