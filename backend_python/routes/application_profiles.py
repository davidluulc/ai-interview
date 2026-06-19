from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import ApplicationProfile, User

router = APIRouter(prefix="/api/application-profiles", tags=["application profiles"])


class ApplicationProfilePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    targetRole: str = ""
    applicationType: str = ""
    resume: str = ""
    jd: str = ""
    company: str = ""
    positionTag: str = ""


def serialize_profile(profile: ApplicationProfile) -> dict:
    return {
        "id": profile.id,
        "title": profile.title,
        "targetRole": profile.target_role,
        "applicationType": profile.application_type,
        "resume": profile.resume,
        "jd": profile.jd,
        "company": profile.company,
        "positionTag": profile.position_tag,
        "status": profile.status,
        "createdAt": profile.created_at.isoformat() if profile.created_at else None,
        "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def get_owned_profile(profile_id: int, current_user: User, db: Session) -> ApplicationProfile:
    profile = (
        db.query(ApplicationProfile)
        .filter(ApplicationProfile.id == profile_id, ApplicationProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application profile not found")
    return profile


@router.get("")
async def list_application_profiles(
    status_filter: str = Query("active", alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    normalized_status = str(status_filter or "active").strip().lower()
    if normalized_status not in {"active", "archived", "all"}:
        normalized_status = "active"
    query = db.query(ApplicationProfile).filter(ApplicationProfile.user_id == current_user.id)
    if normalized_status != "all":
        query = query.filter(ApplicationProfile.status == normalized_status)
    profiles = (
        query
        .order_by(ApplicationProfile.updated_at.desc(), ApplicationProfile.id.desc())
        .all()
    )
    return [serialize_profile(profile) for profile in profiles]


@router.post("")
async def create_application_profile(
    payload: ApplicationProfilePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = ApplicationProfile(
        user_id=current_user.id,
        title=payload.title.strip(),
        target_role=payload.targetRole.strip(),
        application_type=payload.applicationType.strip(),
        resume=payload.resume.strip(),
        jd=payload.jd.strip(),
        company=payload.company.strip(),
        position_tag=payload.positionTag.strip(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)


@router.get("/{profile_id}")
async def get_application_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return serialize_profile(get_owned_profile(profile_id, current_user, db))


@router.put("/{profile_id}")
async def update_application_profile(
    profile_id: int,
    payload: ApplicationProfilePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_owned_profile(profile_id, current_user, db)
    profile.title = payload.title.strip()
    profile.target_role = payload.targetRole.strip()
    profile.application_type = payload.applicationType.strip()
    profile.resume = payload.resume.strip()
    profile.jd = payload.jd.strip()
    profile.company = payload.company.strip()
    profile.position_tag = payload.positionTag.strip()
    profile.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)


@router.delete("/{profile_id}")
async def delete_application_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_owned_profile(profile_id, current_user, db)
    profile.status = "archived"
    profile.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)


@router.post("/{profile_id}/restore")
async def restore_application_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_owned_profile(profile_id, current_user, db)
    profile.status = "active"
    profile.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)
