from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..agent_logging import serialize_agent_decision_log
from ..config import DASHSCOPE_EMBEDDING_MODEL, DASHSCOPE_RERANK_MODEL, QWEN_MODEL
from ..database import DATABASE_URL, get_db
from ..db_models import AgentDecisionLog, InterviewRecord, RagDocument, RagRetrievalLog, User
from ..rag_logging import serialize_rag_log
from ..rag_store import serialize_document

router = APIRouter(prefix="/api/admin", tags=["admin"])


def count_rows(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def bounded_limit(limit: int) -> int:
    return max(1, min(limit, 100))


def serialize_admin_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "createdAt": serialize_datetime(user.created_at),
    }


def classify_rag_quality_issue(log_item: dict[str, Any]) -> tuple[str, str] | None:
    quality = log_item.get("quality") or {}
    if not log_item.get("usedInPrompt", True):
        return "unused_in_prompt", "检查召回结果为什么没有进入 prompt，必要时调整 prompt 组装或过滤规则。"
    if int(log_item.get("hitCount") or 0) == 0 or quality.get("level") == "miss":
        return "empty_recall", "补充知识库内容，检查 query rewrite、metadata filter 和知识库类型是否匹配。"
    if quality.get("level") == "weak":
        return "weak_recall", "优化 query rewrite、补充关键词或调整 hybrid/rerank 策略。"
    return None


def build_rag_quality_payload(logs: list[RagRetrievalLog]) -> dict[str, Any]:
    low_quality_items: list[dict[str, Any]] = []
    summary = {
        "totalLogCount": len(logs),
        "lowQualityCount": 0,
        "emptyRecallCount": 0,
        "weakRecallCount": 0,
        "unusedInPromptCount": 0,
    }
    for log in logs:
        item = serialize_rag_log(log)
        issue = classify_rag_quality_issue(item)
        if not issue:
            continue
        issue_type, recommendation = issue
        summary["lowQualityCount"] += 1
        if issue_type == "empty_recall":
            summary["emptyRecallCount"] += 1
        elif issue_type == "weak_recall":
            summary["weakRecallCount"] += 1
        elif issue_type == "unused_in_prompt":
            summary["unusedInPromptCount"] += 1
        low_quality_items.append(
            {
                **item,
                "issueType": issue_type,
                "recommendation": recommendation,
            }
        )
    return {"summary": summary, "items": low_quality_items}


@router.get("/summary")
async def admin_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, int]:
    return {
        "userCount": count_rows(db, User),
        "interviewRecordCount": count_rows(db, InterviewRecord),
        "ragDocumentCount": count_rows(db, RagDocument),
        "ragRetrievalLogCount": count_rows(db, RagRetrievalLog),
        "agentDecisionLogCount": count_rows(db, AgentDecisionLog),
    }


@router.get("/users")
async def admin_users(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(bounded_limit(limit))).all()
    return {"items": [serialize_admin_user(user) for user in users]}


@router.get("/rag/documents")
async def admin_rag_documents(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    documents = db.scalars(
        select(RagDocument).order_by(RagDocument.updated_at.desc(), RagDocument.id.desc()).limit(bounded_limit(limit))
    ).all()
    return {
        "items": [
            {
                **serialize_document(document),
                "userId": document.user_id,
                "userEmail": document.user.email if document.user else "",
            }
            for document in documents
        ]
    }


@router.get("/rag/logs")
async def admin_rag_logs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    logs = db.scalars(
        select(RagRetrievalLog)
        .order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return {"items": [serialize_rag_log(log) for log in logs]}


@router.get("/rag/quality")
async def admin_rag_quality(
    limit: int = Query(default=80, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    logs = db.scalars(
        select(RagRetrievalLog)
        .order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return build_rag_quality_payload(list(logs))


@router.get("/agent/logs")
async def admin_agent_logs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    logs = db.scalars(
        select(AgentDecisionLog)
        .order_by(AgentDecisionLog.created_at.desc(), AgentDecisionLog.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return {"items": [serialize_agent_decision_log(log) for log in logs]}


@router.get("/config")
async def admin_config(_: User = Depends(require_admin_user)) -> dict[str, str]:
    return {
        "modelName": QWEN_MODEL,
        "embeddingModel": DASHSCOPE_EMBEDDING_MODEL,
        "rerankModel": DASHSCOPE_RERANK_MODEL,
        "databaseUrl": DATABASE_URL,
    }
