import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import TrainingTask

ACTIVE_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}
MASTERY_DELTA = {"不会": -5, "模糊": 8, "完整": 15}


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_priority(value: str) -> str:
    return value if value in VALID_PRIORITIES else "medium"


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def serialize_training_task(task: TrainingTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "applicationProfileId": task.application_profile_id,
        "sourceInterviewRecordId": task.source_interview_record_id,
        "weakTag": task.weak_tag,
        "weakLabel": task.weak_label,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "masteryScore": task.mastery_score,
        "attemptCount": task.attempt_count,
        "lastPracticedAt": task.last_practiced_at.isoformat() if task.last_practiced_at else "",
        "nextReviewAt": task.next_review_at.isoformat() if task.next_review_at else "",
        "metadata": parse_json(task.metadata_json, {}),
        "createdAt": task.created_at.isoformat() if task.created_at else "",
        "updatedAt": task.updated_at.isoformat() if task.updated_at else "",
    }


def find_active_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    application_profile_id: int | None = None,
) -> TrainingTask | None:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.weak_tag == weak_tag,
        TrainingTask.status.in_(ACTIVE_STATUSES),
    )
    if application_profile_id is None:
        statement = statement.where(TrainingTask.application_profile_id.is_(None))
    else:
        statement = statement.where(TrainingTask.application_profile_id == application_profile_id)
    return db.scalar(statement.order_by(TrainingTask.updated_at.desc(), TrainingTask.id.desc()))


def create_or_update_training_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    weak_label: str,
    title: str,
    description: str,
    priority: str = "medium",
    mastery_score: int = 40,
    metadata: dict[str, Any] | None = None,
    application_profile_id: int | None = None,
    source_interview_record_id: int | None = None,
) -> TrainingTask:
    task = find_active_task(
        db,
        user_id=user_id,
        weak_tag=weak_tag,
        application_profile_id=application_profile_id,
    )
    if not task:
        task = TrainingTask(user_id=user_id, weak_tag=weak_tag, application_profile_id=application_profile_id)
        db.add(task)

    task.source_interview_record_id = source_interview_record_id or task.source_interview_record_id
    task.weak_label = weak_label
    task.title = title
    task.description = description
    task.priority = normalize_priority(priority)
    task.mastery_score = clamp_score(mastery_score)
    task.metadata_json = dump_json(metadata or {})
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return task


def get_owned_training_task(db: Session, task_id: int, *, user_id: int) -> TrainingTask:
    task = db.scalar(select(TrainingTask).where(TrainingTask.id == task_id, TrainingTask.user_id == user_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training task not found")
    return task


def complete_training_task(db: Session, task_id: int, *, user_id: int, answer_status: str) -> TrainingTask:
    task = get_owned_training_task(db, task_id, user_id=user_id)
    delta = MASTERY_DELTA.get(answer_status, 0)
    task.mastery_score = clamp_score(task.mastery_score + delta)
    task.attempt_count += 1
    task.last_practiced_at = utc_now_naive()
    task.updated_at = utc_now_naive()
    task.status = "done" if task.mastery_score >= 80 else "in_progress"
    db.commit()
    db.refresh(task)
    return task


def list_candidate_training_tasks(
    db: Session,
    *,
    user_id: int,
    application_profile_id: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.status.in_(("todo", "in_progress")),
    )
    tasks = db.scalars(statement).all()
    if application_profile_id is not None:
        tasks = [
            task
            for task in tasks
            if task.application_profile_id in (None, application_profile_id)
        ]

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(
        key=lambda task: (
            priority_rank.get(task.priority, 1),
            task.mastery_score,
            -(task.updated_at.timestamp() if task.updated_at else 0),
            -task.id,
        )
    )
    return [serialize_training_task(task) for task in tasks[: max(1, limit)]]


def select_agent_training_task(tasks: list[dict[str, Any]], *, agent_mode: str) -> dict[str, Any]:
    for task in tasks:
        mastery_score = int(task.get("masteryScore") or 0)
        priority = str(task.get("priority") or "medium")
        if agent_mode == "coach" and priority == "high" and mastery_score < 60:
            return {
                **task,
                "reason": "训练任务显示该薄弱点优先级高且掌握度偏低，coach 模式先拆小训练。",
            }
        if agent_mode == "interview" and mastery_score < 80:
            return {
                **task,
                "reason": "训练任务显示该薄弱点尚未稳定掌握，interview 模式可作为追问参考。",
            }
    return {}
