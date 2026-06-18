from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..agent_logging import serialize_agent_decision_log
from ..ai_debug import build_ai_debug_detail, build_ai_debug_recent_item
from ..config import DASHSCOPE_EMBEDDING_MODEL, DASHSCOPE_RERANK_MODEL, QWEN_MODEL
from ..database import DATABASE_URL, describe_database_url, get_db
from ..db_models import AgentDecisionLog, InterviewRecord, RagDocument, RagIngestionTask, RagRetrievalLog, User
from ..infrastructure import get_infrastructure_status
from ..langgraph_agent.checkpoint import summarize_checkpoint
from ..langgraph_agent.checkpoint_persistence import get_latest_checkpoint_summary, list_checkpoint_summaries
from ..rag_ingestion_tasks import serialize_ingestion_task
from ..rag_logging import serialize_rag_log
from ..rag_store import serialize_document
from ..security import build_security_status

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


def build_ingestion_task_quality_payload(tasks: list[RagIngestionTask]) -> dict[str, Any]:
    summary = {
        "totalCount": len(tasks),
        "runningCount": 0,
        "succeededCount": 0,
        "failedCount": 0,
        "retryableCount": 0,
        "failureStages": {},
        "averageDurationMs": 0,
        "maxDurationMs": 0,
        "idempotencyHitCount": 0,
    }
    items: list[dict[str, Any]] = []
    durations: list[int] = []
    for task in tasks:
        item = serialize_ingestion_task(task)
        item["userEmail"] = task.user.email if task.user else ""
        status_value = item.get("status")
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        if status_value in {"queued", "running"}:
            summary["runningCount"] += 1
        elif status_value == "succeeded":
            summary["succeededCount"] += 1
        elif status_value == "failed":
            summary["failedCount"] += 1
            failure_stage = str(result.get("failureStage") or "unknown")
            summary["failureStages"][failure_stage] = summary["failureStages"].get(failure_stage, 0) + 1
        if item.get("canRetry"):
            summary["retryableCount"] += 1
        if item.get("idempotencyHit"):
            summary["idempotencyHitCount"] += 1
        duration_ms = item.get("durationMs")
        if isinstance(duration_ms, int):
            durations.append(duration_ms)
            summary["maxDurationMs"] = max(summary["maxDurationMs"], duration_ms)
        items.append(item)
    if durations:
        summary["averageDurationMs"] = int(sum(durations) / len(durations))
    return {"summary": summary, "items": items}


def list_rag_logs_for_agent_log(db: Session, log: AgentDecisionLog) -> list[RagRetrievalLog]:
    statement = select(RagRetrievalLog).where(RagRetrievalLog.user_id == log.user_id)
    if log.application_profile_id is not None:
        statement = statement.where(RagRetrievalLog.application_profile_id == log.application_profile_id)
    return list(
        db.scalars(
            statement.order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc()).limit(12)
        ).all()
    )


def thread_id_for_agent_log(log: AgentDecisionLog) -> str:
    import json

    try:
        state = json.loads(log.state_json or "{}")
    except json.JSONDecodeError:
        state = {}
    try:
        decision = json.loads(log.decision_json or "{}")
    except json.JSONDecodeError:
        decision = {}
    thread_id = (
        state.get("threadId")
        or state.get("thread_id")
        or decision.get("threadId")
        or decision.get("thread_id")
        or f"agent-log-{log.id}"
    )
    return str(thread_id)


def checkpoint_for_agent_log(log: AgentDecisionLog, db: Session | None = None) -> dict[str, Any]:
    thread_id = thread_id_for_agent_log(log)
    if db is not None:
        persisted = get_latest_checkpoint_summary(db, thread_id)
        if persisted.get("exists"):
            return persisted
    return summarize_checkpoint(thread_id)


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


@router.get("/rag/ingestion-tasks")
async def admin_rag_ingestion_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    tasks = db.scalars(
        select(RagIngestionTask)
        .order_by(RagIngestionTask.updated_at.desc(), RagIngestionTask.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return build_ingestion_task_quality_payload(list(tasks))


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


@router.get("/ai-debug/recent")
async def admin_ai_debug_recent(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, list[dict[str, Any]]]:
    logs = db.scalars(
        select(AgentDecisionLog)
        .order_by(AgentDecisionLog.created_at.desc(), AgentDecisionLog.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return {
        "items": [
            build_ai_debug_recent_item(
                log,
                list_rag_logs_for_agent_log(db, log),
                checkpoint_for_agent_log(log, db),
            )
            for log in logs
        ]
    }


@router.get("/ai-debug/{trace_id}")
async def admin_ai_debug_detail(
    trace_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    log = db.get(AgentDecisionLog, trace_id)
    if log is None:
        raise HTTPException(status_code=404, detail="AI debug trace not found")
    return build_ai_debug_detail(
        log,
        list_rag_logs_for_agent_log(db, log),
        checkpoint_for_agent_log(log, db),
        list_checkpoint_summaries(db, thread_id_for_agent_log(log)),
    )


@router.get("/config")
async def admin_config(_: User = Depends(require_admin_user)) -> dict[str, Any]:
    return {
        "modelName": QWEN_MODEL,
        "embeddingModel": DASHSCOPE_EMBEDDING_MODEL,
        "rerankModel": DASHSCOPE_RERANK_MODEL,
        "databaseUrl": describe_database_url(DATABASE_URL)["maskedUrl"],
        "infrastructure": get_infrastructure_status(),
        "security": build_security_status(),
    }
