from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..candidate_memory import build_candidate_profile, retrieve_candidate_memory
from ..database import get_db
from ..db_models import User

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/search")
async def search_memory(
    name: str = "",
    role: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    profile = {
        "candidateName": name,
        "targetRole": role,
        "resume": "",
        "jd": "",
    }
    items = retrieve_candidate_memory(db, profile, limit=5, user_id=current_user.id)
    return {
        "candidateName": name,
        "targetRole": role,
        "items": items,
        "profile": build_candidate_profile(items),
    }
