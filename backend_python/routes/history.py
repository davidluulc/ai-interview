import json
import logging
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import ApplicationProfile, InterviewRecord, User
from ..schemas import HistoryCreateRequest, HistoryItemResponse

router = APIRouter(prefix="/api/history", tags=["history"])
logger = logging.getLogger(__name__)


def parse_json(value: str, fallback):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def application_profile_summary(profile: ApplicationProfile | None) -> dict | None:
    if not profile:
        return None
    return {
        "id": profile.id,
        "title": profile.title,
        "targetRole": profile.target_role,
        "applicationType": profile.application_type,
        "positionTag": profile.position_tag,
    }


def to_response(record: InterviewRecord) -> dict:
    return {
        "id": record.id,
        "createdAt": record.created_at.isoformat(),
        "applicationProfile": application_profile_summary(record.application_profile),
        "profile": parse_json(record.profile_json, {}),
        "answers": parse_json(record.answers_json, []),
        "report": parse_json(record.report_json, {}),
    }


def get_owned_application_profile(
    application_profile_id: int | None,
    current_user: User,
    db: Session,
) -> ApplicationProfile | None:
    if application_profile_id is None:
        return None

    profile = (
        db.query(ApplicationProfile)
        .filter(ApplicationProfile.id == application_profile_id, ApplicationProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application profile not found")
    return profile


@router.post("", response_model=HistoryItemResponse)
async def create_history(
    payload: HistoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        profile = payload.profile
        report = payload.report
        application_profile = get_owned_application_profile(payload.applicationProfileId, current_user, db)
        record = InterviewRecord(
            user_id=current_user.id,
            application_profile_id=application_profile.id if application_profile else None,
            candidate_name=str(profile.get("candidateName") or ""),
            target_role=str(profile.get("targetRole") or ""),
            application_type=str(profile.get("applicationType") or ""),
            mode=str(profile.get("mode") or ""),
            depth=str(profile.get("depth") or ""),
            score=int(report.get("score") or 0),
            profile_json=json.dumps(profile, ensure_ascii=False),
            answers_json=json.dumps(payload.answers, ensure_ascii=False),
            report_json=json.dumps(report, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return to_response(record)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to save interview history")
        db.rollback()
        raise


@router.get("", response_model=list[HistoryItemResponse])
async def list_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    records = db.scalars(
        select(InterviewRecord)
        .where(InterviewRecord.user_id == current_user.id)
        .order_by(InterviewRecord.created_at.desc())
        .limit(20)
    ).all()
    return [to_response(record) for record in records]


@router.get("/stats")
async def history_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    records = db.scalars(
        select(InterviewRecord)
        .where(InterviewRecord.user_id == current_user.id)
        .order_by(InterviewRecord.created_at.desc())
        .limit(50)
    ).all()
    if not records:
        return {
            "total": 0,
            "averageScore": 0,
            "bestScore": 0,
            "latestScore": 0,
            "latestRole": "",
            "topRisks": [],
            "topActions": [],
        }

    scores = [record.score for record in records]
    risk_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()

    for record in records:
        report = parse_json(record.report_json, {})
        risk_counter.update(report.get("risks") or [])
        action_counter.update(report.get("actions") or [])

    latest = records[0]
    return {
        "total": len(records),
        "averageScore": round(sum(scores) / len(scores)),
        "bestScore": max(scores),
        "latestScore": latest.score,
        "latestRole": latest.target_role,
        "topRisks": [item for item, _ in risk_counter.most_common(3)],
        "topActions": [item for item, _ in action_counter.most_common(3)],
    }


@router.delete("")
async def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    db.execute(delete(InterviewRecord).where(InterviewRecord.user_id == current_user.id))
    db.commit()
    return {"ok": True}
