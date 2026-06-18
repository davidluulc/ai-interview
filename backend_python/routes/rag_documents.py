import json
import hashlib
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import RagChunk, RagDocument, RagIngestionTask, User
from ..rag_ingestion import IngestionError, build_ingestion_preview, extract_text_from_upload
from ..rag_ingestion_tasks import (
    can_retry_ingestion_task,
    create_ingestion_task,
    dispatch_rag_ingestion_task,
    fail_ingestion_task,
    find_ingestion_task_by_idempotency_key,
    build_ingestion_idempotency_key,
    json_loads,
    mark_ingestion_text_ready,
    merge_ingestion_task_result,
    merge_ingestion_task_input,
    serialize_ingestion_task,
    update_ingestion_task,
)
from ..rag_store import (
    VALID_KNOWLEDGE_BASES,
    create_rag_document_with_embeddings,
    normalize_document_status,
    normalize_document_visibility,
    serialize_chunk,
    serialize_document,
)
from ..security import client_identity, enforce_rate_limit

router = APIRouter(prefix="/api/rag/documents", tags=["rag documents"])


class RagDocumentPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    knowledgeBase: str
    sourceType: str = "manual"
    content: str = Field(min_length=1)
    visibility: str = "private"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagDocumentStatusPayload(BaseModel):
    status: str


def validate_knowledge_base(value: str) -> str:
    if value not in VALID_KNOWLEDGE_BASES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"knowledgeBase must be one of: {', '.join(sorted(VALID_KNOWLEDGE_BASES))}",
        )
    return value


def get_owned_document(document_id: int, current_user: User, db: Session) -> RagDocument:
    document = db.scalar(
        select(RagDocument).where(RagDocument.id == document_id, RagDocument.user_id == current_user.id)
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG document not found")
    return document


@router.get("")
async def list_rag_documents(
    knowledgeBase: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    statement = select(RagDocument).where(RagDocument.user_id == current_user.id)
    if knowledgeBase:
        statement = statement.where(RagDocument.knowledge_base == validate_knowledge_base(knowledgeBase))
    documents = db.scalars(statement.order_by(RagDocument.updated_at.desc(), RagDocument.id.desc())).all()
    return {"items": [serialize_document(document) for document in documents]}


@router.post("")
async def create_document(
    payload: RagDocumentPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    document = await create_rag_document_with_embeddings(
        db,
        user_id=current_user.id,
        title=payload.title,
        knowledge_base=validate_knowledge_base(payload.knowledgeBase),
        source_type=payload.sourceType,
        content=payload.content,
        metadata=payload.metadata,
        visibility=normalize_document_visibility(payload.visibility),
    )
    return serialize_document(document)


@router.patch("/{document_id}/status")
async def update_document_status(
    document_id: int,
    payload: RagDocumentStatusPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    document = get_owned_document(document_id, current_user, db)
    document.status = normalize_document_status(payload.status)
    db.add(document)
    db.commit()
    db.refresh(document)
    return serialize_document(document)


@router.post("/upload")
async def upload_document(
    request: Request,
    title: str = Form(...),
    knowledgeBase: str = Form(...),
    visibility: str = Form("private"),
    metadata: str = Form("{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    enforce_rate_limit("rag.upload", client_identity(request, user_id=current_user.id))
    knowledge_base = validate_knowledge_base(knowledgeBase)
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    idempotency_key = build_ingestion_idempotency_key(
        user_id=current_user.id,
        knowledge_base=knowledge_base,
        title=title,
        content_hash=content_hash,
    )
    existing_task = find_ingestion_task_by_idempotency_key(
        db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
    )
    if existing_task is not None:
        return {
            **serialize_ingestion_task(existing_task),
            "idempotencyHit": True,
        }
    task = create_ingestion_task(
        db,
        user_id=current_user.id,
        title=title,
        knowledge_base=knowledge_base,
        original_filename=file.filename or title,
        visibility=normalize_document_visibility(visibility),
        metadata={},
    )
    merge_ingestion_task_result(db, task, {"idempotencyKey": idempotency_key, "idempotencyHit": False})
    try:
        parsed_metadata = json.loads(metadata or "{}")
        if not isinstance(parsed_metadata, dict):
            raise IngestionError("metadata must be a JSON object.")
        merge_ingestion_task_input(db, task, {"metadata": parsed_metadata})

        update_ingestion_task(db, task, status="running", progress=20, message="Parsing uploaded file.")
        text = await extract_text_from_upload(filename=file.filename or title, content=content)
        preview = build_ingestion_preview(text, title=title)
        mark_ingestion_text_ready(db, task, text_snapshot=text, preview=preview)

        dispatch_rag_ingestion_task(db, task)
        return serialize_ingestion_task(task)
    except (IngestionError, json.JSONDecodeError) as exc:
        fail_ingestion_task(db, task, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ingestion-tasks")
async def list_ingestion_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    tasks = db.scalars(
        select(RagIngestionTask)
        .where(RagIngestionTask.user_id == current_user.id)
        .order_by(RagIngestionTask.updated_at.desc(), RagIngestionTask.id.desc())
        .limit(30)
    ).all()
    return {"items": [serialize_ingestion_task(task) for task in tasks]}


@router.get("/ingestion-tasks/{task_id}")
async def get_ingestion_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = db.scalar(
        select(RagIngestionTask).where(
            RagIngestionTask.task_id == task_id,
            RagIngestionTask.user_id == current_user.id,
        )
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG ingestion task not found")
    return serialize_ingestion_task(task)


@router.post("/ingestion-tasks/{task_id}/retry")
async def retry_ingestion_task(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    enforce_rate_limit("rag.retry", client_identity(request, user_id=current_user.id))
    task = db.scalar(
        select(RagIngestionTask).where(
            RagIngestionTask.task_id == task_id,
            RagIngestionTask.user_id == current_user.id,
        )
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG ingestion task not found")
    if task.status in {"pending", "queued", "running"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ingestion task is already processing.",
        )
    if not can_retry_ingestion_task(task):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ingestion task cannot be retried. Upload the file again.",
        )

    task.retry_count += 1
    task.document_id = None
    task.result_json = json.dumps({"retryLockedAt": datetime.now(UTC).isoformat()}, ensure_ascii=False)
    task.error_message = ""
    db.add(task)
    db.commit()
    db.refresh(task)
    dispatch_rag_ingestion_task(db, task)
    return serialize_ingestion_task(task)


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    document = get_owned_document(document_id, current_user, db)
    chunks = db.scalars(
        select(RagChunk).where(RagChunk.document_id == document.id).order_by(RagChunk.chunk_index.asc())
    ).all()
    return {
        "document": serialize_document(document),
        "chunks": [serialize_chunk(chunk) for chunk in chunks],
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    document = get_owned_document(document_id, current_user, db)
    db.delete(document)
    db.commit()
    return {"ok": True}
