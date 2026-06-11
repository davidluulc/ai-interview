import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import AgentDecisionLog


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def create_agent_decision_log(
    db: Session,
    *,
    user_id: int,
    application_profile_id: int | None,
    request_type: str,
    state: dict[str, Any],
    decision: dict[str, Any],
    fallback_used: bool | None = None,
) -> AgentDecisionLog:
    tools = decision.get("tools") if isinstance(decision.get("tools"), list) else []
    log = AgentDecisionLog(
        user_id=user_id,
        application_profile_id=application_profile_id,
        request_type=request_type,
        next_action=str(decision.get("nextAction") or ""),
        stage=str(decision.get("stage") or ""),
        difficulty=str(decision.get("difficulty") or ""),
        focus=str(decision.get("focus") or ""),
        reason=str(decision.get("reason") or ""),
        tools_json=_json_dumps(tools),
        state_json=_json_dumps(state),
        decision_json=_json_dumps(decision),
        fallback_used=1 if (decision.get("fallbackUsed") if fallback_used is None else fallback_used) else 0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def serialize_agent_decision_log(log: AgentDecisionLog) -> dict[str, Any]:
    decision = _json_loads(log.decision_json, {})
    debug_signals = decision.get("debugSignals") if isinstance(decision.get("debugSignals"), dict) else {}
    topic_shift = decision.get("topicShift") if isinstance(decision.get("topicShift"), dict) else {}
    return {
        "id": log.id,
        "userId": log.user_id,
        "applicationProfileId": log.application_profile_id,
        "requestType": log.request_type,
        "nextAction": log.next_action,
        "stage": log.stage,
        "difficulty": log.difficulty,
        "focus": log.focus,
        "reason": log.reason,
        "tools": _json_loads(log.tools_json, []),
        "state": _json_loads(log.state_json, {}),
        "decision": decision,
        "debugSignals": debug_signals,
        "guardrailApplied": bool(decision.get("guardrailApplied")),
        "topicShift": topic_shift,
        "fallbackUsed": bool(log.fallback_used),
        "createdAt": log.created_at.isoformat() if log.created_at else None,
    }


def list_recent_agent_decision_logs(
    db: Session,
    *,
    user_id: int,
    request_type: str = "",
    limit: int = 20,
) -> list[AgentDecisionLog]:
    statement = select(AgentDecisionLog).where(AgentDecisionLog.user_id == user_id)
    if request_type:
        statement = statement.where(AgentDecisionLog.request_type == request_type)
    return db.scalars(
        statement.order_by(AgentDecisionLog.created_at.desc(), AgentDecisionLog.id.desc()).limit(limit)
    ).all()
