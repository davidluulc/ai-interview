from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..candidate_memory import build_candidate_profile, retrieve_candidate_memory
from ..database import get_db
from ..db_models import RagRetrievalLog, User
from ..question_rag import retrieve_questions
from ..rag import retrieve_role_context
from ..rag_explain import build_rag_debug_explanation
from ..rag_logging import list_recent_rag_logs, serialize_rag_log
from ..rag_quality import evaluate_retrieval_quality
from ..task_status import create_task_status, get_task_status
from ..tasks.rag_evaluation import run_rag_evaluation_task

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/evaluation/tasks")
async def create_rag_evaluation_task(payload: dict | None = None) -> dict:
    data = payload if isinstance(payload, dict) else {}
    modes = data.get("modes") if isinstance(data.get("modes"), list) else ["bm25"]
    k = int(data.get("k") or 3)
    task = create_task_status(task_type="rag_evaluation", message="RAG evaluation task created.")
    run_rag_evaluation_task.delay(task["taskId"], modes=modes, k=k)
    return get_task_status(task["taskId"]) or task


@router.get("/evaluation/tasks/{task_id}")
async def rag_evaluation_task_status(task_id: str) -> dict:
    task = get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG evaluation task not found")
    return task


@router.get("/search")
async def search_rag(q: str = "", stage: str = "") -> dict:
    profile = {
        "targetRole": q,
        "positionTag": "",
        "resume": q,
        "jd": q,
        "company": "",
    }
    return {
        "query": q,
        "stage": stage,
        "items": retrieve_role_context(profile, stage, limit=5),
    }


@router.get("/debug")
async def debug_rag(
    name: str = "",
    role: str = "",
    positionTag: str = "",
    applicationProfileId: str = "",
    resume: str = "",
    jd: str = "",
    stage: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    profile = {
        "candidateName": name,
        "targetRole": role,
        "positionTag": positionTag,
        "resume": resume,
        "jd": jd,
        "company": "",
    }
    parsed_application_profile_id = int(applicationProfileId) if str(applicationProfileId).strip() else None
    candidate_memory = retrieve_candidate_memory(
        db,
        profile,
        limit=5,
        user_id=current_user.id,
        application_profile_id=parsed_application_profile_id,
    )
    role_hits = retrieve_role_context(profile, stage, limit=5, db=db, user_id=current_user.id)
    question_hits = retrieve_questions(profile, stage, limit=5, db=db, user_id=current_user.id)
    quality = {
        "roleKnowledge": evaluate_retrieval_quality(role_hits),
        "questionBank": evaluate_retrieval_quality(question_hits),
        "candidateMemory": evaluate_retrieval_quality(candidate_memory),
    }
    explanations = {
        "roleKnowledge": build_rag_debug_explanation(
            retriever_name="role_knowledge",
            hits=role_hits,
            quality=quality["roleKnowledge"],
        ),
        "questionBank": build_rag_debug_explanation(
            retriever_name="question_bank",
            hits=question_hits,
            quality=quality["questionBank"],
        ),
        "candidateMemory": build_rag_debug_explanation(
            retriever_name="candidate_memory",
            hits=candidate_memory,
            quality=quality["candidateMemory"],
        ),
    }
    return {
        "profile": profile,
        "stage": stage,
        "roleKnowledge": role_hits,
        "questionBank": question_hits,
        "candidateMemory": candidate_memory,
        "candidateProfile": build_candidate_profile(candidate_memory),
        "quality": quality,
        "explanations": explanations,
    }


@router.get("/logs/recent")
async def recent_rag_logs(
    requestType: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    logs = list_recent_rag_logs(db, user_id=current_user.id, request_type=requestType, limit=safe_limit)
    return {"items": [serialize_rag_log(log) for log in logs]}


@router.get("/logs/{log_id}")
async def rag_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    log = db.scalar(
        select(RagRetrievalLog).where(RagRetrievalLog.id == log_id, RagRetrievalLog.user_id == current_user.id)
    )
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG retrieval log not found")
    return serialize_rag_log(log)
