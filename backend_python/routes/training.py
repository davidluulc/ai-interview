from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import TrainingTask, User
from ..training_tasks import (
    complete_training_task,
    create_or_update_training_task,
    get_owned_training_task,
    serialize_training_task,
    utc_now_naive,
)
from ..weakness_strategy import normalize_weak_tags
from ..weakness_training_templates import get_training_template

router = APIRouter(prefix="/api/training/tasks", tags=["training"])


class GenerateFromReportRequest(BaseModel):
    applicationProfileId: int | None = None
    sourceInterviewRecordId: int | None = None
    report: dict[str, Any] = Field(default_factory=dict)


class CompleteTaskRequest(BaseModel):
    answerStatus: str = "模糊"


def weak_label_for_tag(weak_tag: str) -> str:
    template = get_training_template(weak_tag)
    return str(template.get("label") or weak_tag)


def task_title_for_tag(weak_tag: str) -> str:
    return f"{weak_label_for_tag(weak_tag)}专项训练"


def task_description_for_tag(weak_tag: str) -> str:
    template = get_training_template(weak_tag)
    return str(template.get("description") or f"围绕 {weak_label_for_tag(weak_tag)} 补齐项目表达。")


def collect_report_weak_tags(report: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for item in report.get("questionReviews") or []:
        tags.extend(normalize_weak_tags(item.get("weakTags")))
    training_plan = report.get("trainingPlan") if isinstance(report.get("trainingPlan"), dict) else {}
    for item in training_plan.get("weakTopics") or []:
        tags.extend(normalize_weak_tags(item.get("weakTags")))
    return list(dict.fromkeys(tags))


@router.get("")
async def list_training_tasks(
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    statement = select(TrainingTask).where(TrainingTask.user_id == current_user.id)
    if status:
        statement = statement.where(TrainingTask.status == status)
    tasks = db.scalars(statement.order_by(TrainingTask.updated_at.desc(), TrainingTask.id.desc())).all()
    return {"items": [serialize_training_task(task) for task in tasks]}


@router.post("/generate-from-report")
async def generate_from_report(
    payload: GenerateFromReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    tasks = []
    for weak_tag in collect_report_weak_tags(payload.report):
        task = create_or_update_training_task(
            db,
            user_id=current_user.id,
            application_profile_id=payload.applicationProfileId,
            source_interview_record_id=payload.sourceInterviewRecordId,
            weak_tag=weak_tag,
            weak_label=weak_label_for_tag(weak_tag),
            title=task_title_for_tag(weak_tag),
            description=task_description_for_tag(weak_tag),
            priority="high",
            mastery_score=45,
            metadata={"source": "report", "reportWeakTag": weak_tag},
        )
        tasks.append(task)
    return {"items": [serialize_training_task(task) for task in tasks]}


@router.get("/{task_id}")
async def get_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return serialize_training_task(get_owned_training_task(db, task_id, user_id=current_user.id))


@router.post("/{task_id}/start")
async def start_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_owned_training_task(db, task_id, user_id=current_user.id)
    task.status = "in_progress"
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return serialize_training_task(task)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: int,
    payload: CompleteTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = complete_training_task(db, task_id, user_id=current_user.id, answer_status=payload.answerStatus)
    return serialize_training_task(task)


@router.post("/{task_id}/archive")
async def archive_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_owned_training_task(db, task_id, user_id=current_user.id)
    task.status = "archived"
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return serialize_training_task(task)
