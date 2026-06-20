from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..agent_logging import serialize_agent_decision_log
from ..ai_debug import action_label, build_ai_debug_detail, build_ai_debug_recent_item, normalize_rag_name
from ..config import DASHSCOPE_RERANK_MODEL, QWEN_MODEL
from ..database import DATABASE_URL, describe_database_url, get_db
from ..db_models import AgentDecisionLog, InterviewRecord, RagChunk, RagDocument, RagIngestionTask, RagRetrievalLog, RefreshToken, User
from ..embedding_client import current_embedding_model, embedding_provider_summary
from ..infrastructure import get_infrastructure_status
from ..langgraph_agent.checkpoint import summarize_checkpoint
from ..langgraph_agent.checkpoint_persistence import get_latest_checkpoint_summary, list_checkpoint_summaries
from ..rag_ingestion_tasks import serialize_ingestion_task
from ..rag_logging import serialize_rag_log
from ..rag_store import serialize_document
from ..security import build_security_status
from ..session_store import session_store

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


def count_rag_chunks(db: Session, *conditions) -> int:
    statement = select(func.count()).select_from(RagChunk)
    for condition in conditions:
        statement = statement.where(condition)
    return int(db.scalar(statement) or 0)


def build_empty_recall_recommendation(db: Session, log_item: dict[str, Any]) -> str:
    retriever_name = str(log_item.get("retrieverName") or "").strip()
    if retriever_name == "candidate_memory":
        return "候选人画像来自历史面试记录，完成并保存多次面试后会逐步形成。"

    total_chunk_count = count_rag_chunks(db)
    if total_chunk_count == 0:
        return "当前生产知识库尚未初始化，请执行 Production RAG Seed。"

    if not retriever_name:
        return "补充知识库内容，检查 query rewrite、metadata filter 和知识库类型是否匹配。"

    active_model = current_embedding_model()
    ready_current_count = count_rag_chunks(
        db,
        RagChunk.knowledge_base == retriever_name,
        RagChunk.embedding_status == "ready",
        RagChunk.embedding_model == active_model,
    )
    if ready_current_count > 0:
        return "补充知识库内容，检查 query rewrite、metadata filter 和知识库类型是否匹配。"

    ready_other_model_count = count_rag_chunks(
        db,
        RagChunk.knowledge_base == retriever_name,
        RagChunk.embedding_status == "ready",
        RagChunk.embedding_model != "",
        RagChunk.embedding_model != active_model,
    )
    if ready_other_model_count > 0:
        return "当前 embedding 模型与历史 chunk 不一致，需要重新向量化或重新入库。"

    return "该知识库暂无可检索内容。"


def classify_rag_quality_issue(log_item: dict[str, Any], db: Session | None = None) -> tuple[str, str] | None:
    quality = log_item.get("quality") or {}
    if not log_item.get("usedInPrompt", True):
        return "unused_in_prompt", "检查召回结果为什么没有进入 prompt，必要时调整 prompt 组装或过滤规则。"
    if int(log_item.get("hitCount") or 0) == 0 or quality.get("level") == "miss":
        recommendation = (
            build_empty_recall_recommendation(db, log_item)
            if db is not None
            else "补充知识库内容，检查 query rewrite、metadata filter 和知识库类型是否匹配。"
        )
        return "empty_recall", recommendation
    if quality.get("level") == "weak":
        return "weak_recall", "优化 query rewrite、补充关键词或调整 hybrid/rerank 策略。"
    return None


def rag_issue_title(issue_type: str) -> str:
    titles = {
        "empty_recall": "空召回",
        "weak_recall": "弱召回",
        "unused_in_prompt": "未进入 Prompt",
    }
    return titles.get(issue_type, "需要关注")


def build_rag_quality_payload(logs: list[RagRetrievalLog], db: Session | None = None) -> dict[str, Any]:
    low_quality_items: list[dict[str, Any]] = []
    summary = {
        "totalLogCount": len(logs),
        "goodCount": 0,
        "lowQualityCount": 0,
        "emptyRecallCount": 0,
        "weakRecallCount": 0,
        "unusedInPromptCount": 0,
    }
    knowledge_base_map: dict[str, dict[str, Any]] = {}
    diagnostic_map: dict[tuple[str, str], dict[str, Any]] = {}
    for log in logs:
        item = serialize_rag_log(log)
        knowledge_base = str(item.get("retrieverName") or "unknown")
        quality = item.get("quality") or {}
        quality_level = str(quality.get("level") or "unknown")
        knowledge_base_item = knowledge_base_map.setdefault(
            knowledge_base,
            {
                "knowledgeBase": knowledge_base,
                "label": normalize_rag_name(knowledge_base),
                "totalCount": 0,
                "goodCount": 0,
                "weakCount": 0,
                "emptyCount": 0,
                "unusedInPromptCount": 0,
                "readyChunkCount": 0,
            },
        )
        knowledge_base_item["totalCount"] += 1
        issue = classify_rag_quality_issue(item, db)
        if not issue:
            summary["goodCount"] += 1
            knowledge_base_item["goodCount"] += 1
            continue
        issue_type, recommendation = issue
        summary["lowQualityCount"] += 1
        if issue_type == "empty_recall":
            summary["emptyRecallCount"] += 1
            knowledge_base_item["emptyCount"] += 1
        elif issue_type == "weak_recall":
            summary["weakRecallCount"] += 1
            knowledge_base_item["weakCount"] += 1
        elif issue_type == "unused_in_prompt":
            summary["unusedInPromptCount"] += 1
            knowledge_base_item["unusedInPromptCount"] += 1
        elif quality_level == "weak":
            knowledge_base_item["weakCount"] += 1
        low_quality_items.append(
            {
                **item,
                "issueType": issue_type,
                "recommendation": recommendation,
            }
        )
        diagnostic_key = (issue_type, knowledge_base)
        diagnostic = diagnostic_map.setdefault(
            diagnostic_key,
            {
                "type": issue_type,
                "knowledgeBase": knowledge_base,
                "label": normalize_rag_name(knowledge_base),
                "title": f"{normalize_rag_name(knowledge_base)}{rag_issue_title(issue_type)}",
                "message": recommendation,
                "count": 0,
            },
        )
        diagnostic["count"] += 1
    if db is not None:
        active_model = current_embedding_model()
        for knowledge_base, item in knowledge_base_map.items():
            item["readyChunkCount"] = count_rag_chunks(
                db,
                RagChunk.knowledge_base == knowledge_base,
                RagChunk.embedding_status == "ready",
                RagChunk.embedding_model == active_model,
            )
    return {
        "summary": summary,
        "items": low_quality_items,
        "knowledgeBaseSummary": sorted(knowledge_base_map.values(), key=lambda item: item["knowledgeBase"]),
        "diagnosticSummary": sorted(diagnostic_map.values(), key=lambda item: item["count"], reverse=True),
    }


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


def safe_json(value: str, fallback: Any) -> Any:
    import json

    try:
        parsed = json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed if parsed is not None else fallback


def count_answers(record: InterviewRecord) -> int:
    answers = safe_json(record.answers_json, [])
    return len(answers) if isinstance(answers, list) else 0


def report_status(record: InterviewRecord) -> str:
    payload = safe_json(record.report_json, {})
    return "ready" if isinstance(payload, dict) and bool(payload) else "missing"


def rag_level(log: RagRetrievalLog) -> str:
    hit_count = int(log.hit_count or 0)
    if hit_count <= 0:
        return "empty"
    if hit_count == 1:
        return "weak"
    return "good"


def summarize_observability_rag_logs(logs: list[RagRetrievalLog]) -> dict[str, int]:
    summary = {"totalCount": len(logs), "goodCount": 0, "weakCount": 0, "emptyCount": 0}
    for log in logs:
        level = rag_level(log)
        if level == "good":
            summary["goodCount"] += 1
        elif level == "weak":
            summary["weakCount"] += 1
        else:
            summary["emptyCount"] += 1
    return summary


def summarize_observability_agent_logs(logs: list[AgentDecisionLog]) -> dict[str, int]:
    return {
        "totalCount": len(logs),
        "fallbackCount": sum(1 for log in logs if int(log.fallback_used or 0)),
        "lowerDifficultyCount": sum(1 for log in logs if log.next_action == "lower_difficulty"),
        "deepenCount": sum(1 for log in logs if log.next_action in {"deepen", "deep_follow_up"}),
        "switchTopicCount": sum(1 for log in logs if log.next_action in {"switch_topic", "shift_topic"}),
    }


def answer_turns(record: InterviewRecord) -> list[dict[str, Any]]:
    answers = safe_json(record.answers_json, [])
    if not isinstance(answers, list):
        return []
    turns: list[dict[str, Any]] = []
    for index, item in enumerate(answers, start=1):
        data = item if isinstance(item, dict) else {}
        turns.append(
            {
                "turnIndex": index,
                "question": str(data.get("question") or data.get("q") or ""),
                "answer": str(data.get("answer") or data.get("a") or ""),
            }
        )
    return turns


def summarize_rag_for_turn(logs: list[RagRetrievalLog]) -> list[dict[str, Any]]:
    labels = {"good": "高相关", "weak": "弱相关", "empty": "空召回"}
    return [
        {
            "knowledgeBase": log.retriever_name,
            "label": normalize_rag_name(log.retriever_name),
            "hitCount": int(log.hit_count or 0),
            "qualityLabel": labels[rag_level(log)],
            "queryText": log.query_text,
        }
        for log in logs[:5]
    ]


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


@router.post("/users/{user_id}/force-logout")
async def admin_force_logout_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active_tokens = list(
        db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        ).all()
    )
    for token in active_tokens:
        token.revoked_at = now
    db.commit()
    revoked_sessions = session_store.revoke_user_sessions(user_id, reason="admin_force_logout")
    return {"ok": True, "revokedSessions": revoked_sessions, "revokedRefreshTokens": len(active_tokens)}


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
    return build_rag_quality_payload(list(logs), db)


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


@router.get("/observability/interviews")
async def admin_observability_interviews(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    records = list(
        db.scalars(
            select(InterviewRecord)
            .order_by(InterviewRecord.created_at.desc(), InterviewRecord.id.desc())
            .limit(bounded_limit(limit))
        ).all()
    )
    items: list[dict[str, Any]] = []
    for record in records:
        rag_logs = list(
            db.scalars(
                select(RagRetrievalLog)
                .where(RagRetrievalLog.interview_record_id == record.id)
                .order_by(RagRetrievalLog.created_at.asc(), RagRetrievalLog.id.asc())
            ).all()
        )
        agent_logs = list(
            db.scalars(
                select(AgentDecisionLog)
                .where(
                    AgentDecisionLog.user_id == record.user_id,
                    AgentDecisionLog.application_profile_id == record.application_profile_id,
                )
                .order_by(AgentDecisionLog.created_at.asc(), AgentDecisionLog.id.asc())
            ).all()
        )
        items.append(
            {
                "recordId": record.id,
                "userId": record.user_id,
                "userEmail": record.user.email if record.user else "",
                "applicationProfileId": record.application_profile_id,
                "profileTitle": record.application_profile.title if record.application_profile else record.target_role,
                "targetRole": record.target_role,
                "createdAt": serialize_datetime(record.created_at),
                "questionCount": count_answers(record),
                "reportStatus": report_status(record),
                "ragSummary": summarize_observability_rag_logs(rag_logs),
                "agentSummary": summarize_observability_agent_logs(agent_logs),
                "relation": {
                    "rag": "interview_record_id",
                    "agent": "user_id + application_profile_id",
                },
            }
        )
    return {"items": items, "total": len(items)}


@router.get("/observability/interviews/{record_id}")
async def admin_observability_interview_detail(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    record = db.get(InterviewRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview record not found")
    linked_rag_logs = list(
        db.scalars(
            select(RagRetrievalLog)
            .where(RagRetrievalLog.interview_record_id == record.id)
            .order_by(RagRetrievalLog.created_at.asc(), RagRetrievalLog.id.asc())
        ).all()
    )
    agent_logs = list(
        db.scalars(
            select(AgentDecisionLog)
            .where(
                AgentDecisionLog.user_id == record.user_id,
                AgentDecisionLog.application_profile_id == record.application_profile_id,
            )
            .order_by(AgentDecisionLog.created_at.asc(), AgentDecisionLog.id.asc())
        ).all()
    )
    turns = answer_turns(record)
    for index, turn in enumerate(turns):
        turn["ragSummary"] = summarize_rag_for_turn(linked_rag_logs[index : index + 1])
        agent_log = agent_logs[index] if index < len(agent_logs) else None
        turn["agentDecision"] = (
            {
                "actionLabel": action_label(agent_log.next_action),
                "reason": agent_log.reason,
                "fallbackUsed": bool(agent_log.fallback_used),
                "relation": "user_id + application_profile_id + order",
            }
            if agent_log
            else None
        )
        turn["diagnostics"] = [
            f"{item['label']}为{item['qualityLabel']}" for item in turn["ragSummary"] if item["qualityLabel"] != "高相关"
        ]
        turn["traceIds"] = [agent_log.id] if agent_log else []

    unlinked_rag_count = int(
        db.scalar(
            select(func.count())
            .select_from(RagRetrievalLog)
            .where(
                RagRetrievalLog.user_id == record.user_id,
                RagRetrievalLog.application_profile_id == record.application_profile_id,
                RagRetrievalLog.interview_record_id.is_(None),
            )
        )
        or 0
    )
    return {
        "recordId": record.id,
        "overview": {
            "userEmail": record.user.email if record.user else "",
            "profileTitle": record.application_profile.title if record.application_profile else record.target_role,
            "targetRole": record.target_role,
            "createdAt": serialize_datetime(record.created_at),
            "reportStatus": report_status(record),
        },
        "summary": {
            "questionCount": len(turns),
            "ragSummary": summarize_observability_rag_logs(linked_rag_logs),
            "agentSummary": summarize_observability_agent_logs(agent_logs),
        },
        "turns": turns,
        "unlinkedLogs": {"ragLogCount": unlinked_rag_count, "agentLogCount": 0},
    }


@router.get("/config")
async def admin_config(_: User = Depends(require_admin_user)) -> dict[str, Any]:
    embedding_provider = embedding_provider_summary()
    return {
        "modelName": QWEN_MODEL,
        "embeddingModel": embedding_provider["model"],
        "embeddingProvider": embedding_provider,
        "rerankModel": DASHSCOPE_RERANK_MODEL,
        "databaseUrl": describe_database_url(DATABASE_URL)["maskedUrl"],
        "infrastructure": get_infrastructure_status(),
        "security": build_security_status(),
    }
