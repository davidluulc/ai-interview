from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, RagRetrievalLog, User
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


def create_admin_headers(client: TestClient, suffix: str) -> tuple[dict[str, str], int]:
    email = f"rag-quality-admin-{suffix}@example.com"
    register_and_login(client, email, f"rag_quality_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}
    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.email == email))
        assert admin_user is not None
        return headers, admin_user.id


def add_empty_recall_log(db, *, user_id: int, query_text: str, retriever_name: str) -> None:
    db.add(
        RagRetrievalLog(
            user_id=user_id,
            request_type="interview",
            query_text=query_text,
            retriever_name=retriever_name,
            retrieval_mode="hybrid",
            hit_count=0,
            hits_json="[]",
            used_in_prompt=1,
        )
    )


def add_chunk(
    db,
    *,
    user_id: int,
    knowledge_base: str,
    embedding_model: str,
    embedding_status: str = "ready",
) -> None:
    document = RagDocument(
        user_id=user_id,
        title=f"{knowledge_base} document",
        knowledge_base=knowledge_base,
        source_type="manual",
        status="enabled",
        visibility="public",
        content="demo content",
        metadata_json="{}",
        chunk_count=1,
    )
    db.add(document)
    db.flush()
    db.add(
        RagChunk(
            user_id=user_id,
            document_id=document.id,
            knowledge_base=knowledge_base,
            title=document.title,
            content="demo chunk",
            chunk_index=0,
            chunk_hash=f"{knowledge_base}-{embedding_model}-{uuid4().hex}",
            keywords_json="[]",
            metadata_json="{}",
            embedding_json="[0.1, 0.2]",
            embedding_model=embedding_model,
            embedding_status=embedding_status,
        )
    )


def test_admin_rag_quality_summary_returns_low_quality_recall_items() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"rag-quality-admin-{suffix}@example.com"
    register_and_login(client, email, f"rag_quality_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}

    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.email == email))
        assert admin_user is not None
        db.add_all(
            [
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="empty recall query",
                    retriever_name="role_knowledge",
                    retrieval_mode="bm25",
                    hit_count=0,
                    hits_json="[]",
                    used_in_prompt=1,
                ),
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="weak recall query",
                    retriever_name="question_bank",
                    retrieval_mode="hybrid",
                    hit_count=1,
                    hits_json='[{"title":"weak","score":0.1}]',
                    used_in_prompt=1,
                ),
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="unused recall query",
                    retriever_name="candidate_memory",
                    retrieval_mode="bm25",
                    hit_count=1,
                    hits_json='[{"title":"unused","score":9.0}]',
                    used_in_prompt=0,
                ),
            ]
        )
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["totalLogCount"] >= 3
    assert body["summary"]["emptyRecallCount"] >= 1
    assert body["summary"]["weakRecallCount"] >= 1
    assert body["summary"]["unusedInPromptCount"] >= 1
    assert body["summary"]["lowQualityCount"] >= 3
    item_by_query = {item["queryText"]: item for item in body["items"]}
    assert item_by_query["empty recall query"]["issueType"] == "empty_recall"
    assert item_by_query["weak recall query"]["issueType"] == "weak_recall"
    assert item_by_query["unused recall query"]["issueType"] == "unused_in_prompt"


def test_admin_rag_quality_recommends_production_seed_when_all_chunks_are_empty(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.routes.admin.current_embedding_model", lambda: "embedding-3", raising=False)
    client = TestClient(app)
    suffix = uuid4().hex
    headers, user_id = create_admin_headers(client, suffix)
    query_text = f"empty production seed {suffix}"

    with SessionLocal() as db:
        db.query(RagChunk).delete()
        db.query(RagDocument).delete()
        add_empty_recall_log(db, user_id=user_id, query_text=query_text, retriever_name="role_knowledge")
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    item_by_query = {item["queryText"]: item for item in response.json()["items"]}
    assert item_by_query[query_text]["recommendation"] == "当前生产知识库尚未初始化，请执行 Production RAG Seed。"


def test_admin_rag_quality_explains_candidate_memory_empty_recall(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.routes.admin.current_embedding_model", lambda: "embedding-3", raising=False)
    client = TestClient(app)
    suffix = uuid4().hex
    headers, user_id = create_admin_headers(client, suffix)
    query_text = f"candidate memory miss {suffix}"

    with SessionLocal() as db:
        add_empty_recall_log(db, user_id=user_id, query_text=query_text, retriever_name="candidate_memory")
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    item_by_query = {item["queryText"]: item for item in response.json()["items"]}
    assert item_by_query[query_text]["recommendation"] == "候选人画像来自历史面试记录，完成并保存多次面试后会逐步形成。"


def test_admin_rag_quality_reports_embedding_model_mismatch(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.routes.admin.current_embedding_model", lambda: "embedding-3", raising=False)
    client = TestClient(app)
    suffix = uuid4().hex
    headers, user_id = create_admin_headers(client, suffix)
    query_text = f"embedding mismatch {suffix}"

    with SessionLocal() as db:
        add_chunk(db, user_id=user_id, knowledge_base="question_bank", embedding_model="text-embedding-v4")
        add_empty_recall_log(db, user_id=user_id, query_text=query_text, retriever_name="question_bank")
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    item_by_query = {item["queryText"]: item for item in response.json()["items"]}
    assert item_by_query[query_text]["recommendation"] == "当前 embedding 模型与历史 chunk 不一致，需要重新向量化或重新入库。"


def test_admin_rag_quality_reports_knowledge_base_without_ready_chunks(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.routes.admin.current_embedding_model", lambda: "embedding-3", raising=False)
    client = TestClient(app)
    suffix = uuid4().hex
    headers, user_id = create_admin_headers(client, suffix)
    query_text = f"knowledge base not ready {suffix}"

    with SessionLocal() as db:
        db.query(RagChunk).filter(RagChunk.knowledge_base == "question_bank").delete()
        db.query(RagDocument).filter(RagDocument.knowledge_base == "question_bank").delete()
        add_chunk(db, user_id=user_id, knowledge_base="role_knowledge", embedding_model="embedding-3")
        add_empty_recall_log(db, user_id=user_id, query_text=query_text, retriever_name="question_bank")
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    item_by_query = {item["queryText"]: item for item in response.json()["items"]}
    assert item_by_query[query_text]["recommendation"] == "该知识库暂无可检索内容。"
