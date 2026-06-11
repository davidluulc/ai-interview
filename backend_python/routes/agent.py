from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent_logging import list_recent_agent_decision_logs, serialize_agent_decision_log
from ..auth import get_current_user
from ..database import get_db
from ..db_models import AgentDecisionLog, User

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/logs/recent")
async def recent_agent_logs(
    requestType: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    logs = list_recent_agent_decision_logs(
        db,
        user_id=current_user.id,
        request_type=requestType,
        limit=safe_limit,
    )
    return {"items": [serialize_agent_decision_log(log) for log in logs]}


@router.get("/logs/{log_id}")
async def agent_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    log = db.scalar(
        select(AgentDecisionLog).where(AgentDecisionLog.id == log_id, AgentDecisionLog.user_id == current_user.id)
    )
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent decision log not found")
    return serialize_agent_decision_log(log)
