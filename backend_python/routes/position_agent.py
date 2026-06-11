from typing import Any

from fastapi import APIRouter

from ..position_agent import match_positions
from ..schemas import PositionMatchRequest

router = APIRouter(prefix="/api/position-agent", tags=["position-agent"])


@router.post("/match")
async def match_position(payload: PositionMatchRequest) -> dict[str, Any]:
    matches = match_positions(payload.profile, payload.targetDirection, limit=3)
    return {
        "matches": matches,
        "recommended": matches[0] if matches else None,
    }
