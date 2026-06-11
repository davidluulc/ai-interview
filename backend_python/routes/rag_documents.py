from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import RagChunk, RagDocument, User
from ..rag_store import (
    VALID_KNOWLEDGE_BASES,
    create_rag_document_with_embeddings,
    normalize_document_status,
    normalize_document_visibility,
    serialize_chunk,
    serialize_document,
)

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
