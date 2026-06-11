from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.main import app
from backend_python.retrieval_service import retrieve_chunks


def create_user(db, prefix: str) -> User:
    suffix = uuid4().hex
    user = User(email=f"{prefix}-{suffix}@example.com", username=f"{prefix}_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_lifecycle_chunk(
    db,
    *,
    user_id: int,
    title: str,
    content: str,
    status: str = "enabled",
    visibility: str = "private",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base="role_knowledge",
        source_type="manual",
        content=content,
        metadata_json='{"category":"technical"}',
        chunk_count=1,
        status=status,
        visibility=visibility,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    chunk = RagChunk(
        user_id=user_id,
        document_id=document.id,
        knowledge_base="role_knowledge",
        title=title,
        content=content,
        chunk_index=0,
        keywords_json='["lifecycle", "permission"]',
        metadata_json=document.metadata_json,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


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


def test_disabled_document_is_not_retrieved() -> None:
    marker = f"disabled_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_lifecycle_disabled")
        create_lifecycle_chunk(
            db,
            user_id=user.id,
            title="Disabled lifecycle document",
            content=f"lifecycle permission {marker} document must not be retrieved",
            status="disabled",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=3,
        )

    assert hits == []


def test_public_document_is_retrieved_by_another_user() -> None:
    marker = f"public_{uuid4().hex}"
    with SessionLocal() as db:
        owner = create_user(db, "rag_lifecycle_owner")
        reader = create_user(db, "rag_lifecycle_reader")
        create_lifecycle_chunk(
            db,
            user_id=owner.id,
            title="Public lifecycle document",
            content=f"lifecycle permission {marker} document can be retrieved",
            visibility="public",
        )

        hits = retrieve_chunks(
            db,
            user_id=reader.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=3,
        )

    assert [hit["title"] for hit in hits] == ["Public lifecycle document"]
    assert hits[0]["documentVisibility"] == "public"
    assert hits[0]["documentStatus"] == "enabled"


def test_private_document_is_not_retrieved_by_another_user() -> None:
    marker = f"private_{uuid4().hex}"
    with SessionLocal() as db:
        owner = create_user(db, "rag_lifecycle_private_owner")
        reader = create_user(db, "rag_lifecycle_private_reader")
        create_lifecycle_chunk(
            db,
            user_id=owner.id,
            title="Private lifecycle document",
            content=f"lifecycle permission {marker} document belongs to owner only",
            visibility="private",
        )

        hits = retrieve_chunks(
            db,
            user_id=reader.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=3,
        )

    assert hits == []


def test_document_api_returns_status_and_visibility() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_lifecycle_api")

    response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": "API lifecycle document",
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": "lifecycle permission API document",
            "visibility": "public",
            "metadata": {"category": "technical"},
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["status"] == "enabled"
    assert created["visibility"] == "public"

    detail_response = client.get(f"/api/rag/documents/{created['id']}", headers=auth_headers(tokens))

    assert detail_response.status_code == 200
    assert detail_response.json()["document"]["status"] == "enabled"
    assert detail_response.json()["document"]["visibility"] == "public"


def test_document_status_can_be_updated_by_owner() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_lifecycle_status")
    create_response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": "Status update document",
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": "lifecycle permission status update document",
            "metadata": {},
        },
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/rag/documents/{document_id}/status",
        headers=auth_headers(tokens),
        json={"status": "disabled"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "disabled"
