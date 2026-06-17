from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend_python.db_models import LangGraphCheckpointSummary
from backend_python.langgraph_agent.checkpoint_store import empty_checkpoint_summary, normalize_thread_id


def _json_dumps(value: Any, fallback: Any) -> str:
    safe_value = value if value is not None else fallback
    return json.dumps(safe_value, ensure_ascii=False)


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def serialize_checkpoint_summary(row: LangGraphCheckpointSummary) -> dict[str, Any]:
    raw_summary = _json_loads(row.raw_summary_json, {})
    return {
        "enabled": True,
        "exists": True,
        "id": row.id,
        "threadId": row.thread_id,
        "runtime": row.runtime,
        "status": row.status,
        "currentNode": row.current_node,
        "roundCount": row.round_count,
        "lastAction": row.last_action,
        "lastQuestion": row.last_question,
        "requiresHumanReview": bool(row.requires_human_review),
        "interrupt": _json_loads(row.interrupt_json, None) if row.interrupt_json else None,
        "resumeDecision": row.resume_decision,
        "runtimeTrace": _json_loads(row.runtime_trace_json, []),
        "qualityGate": _json_loads(row.quality_gate_json, {}),
        "comparisonSummary": _json_loads(row.comparison_json, {}),
        "runtimeAudit": raw_summary.get("runtimeAudit") if isinstance(raw_summary.get("runtimeAudit"), dict) else {},
        "rawSummary": raw_summary,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def save_checkpoint_summary(db: Session, summary: dict[str, Any]) -> dict[str, Any]:
    safe = summary if isinstance(summary, dict) else {}
    thread_id = normalize_thread_id(str(safe.get("threadId") or ""))
    row = LangGraphCheckpointSummary(
        thread_id=thread_id,
        runtime=str(safe.get("runtime") or "langgraph"),
        status=str(safe.get("status") or "completed"),
        current_node=str(safe.get("currentNode") or ""),
        round_count=int(safe.get("roundCount") or 0),
        last_action=str(safe.get("lastAction") or ""),
        last_question=str(safe.get("lastQuestion") or ""),
        requires_human_review=1 if safe.get("requiresHumanReview") else 0,
        interrupt_json=_json_dumps(safe.get("interrupt"), None) if safe.get("interrupt") else "",
        resume_decision=str(safe.get("resumeDecision") or ""),
        runtime_trace_json=_json_dumps(safe.get("runtimeTrace"), []),
        quality_gate_json=_json_dumps(safe.get("qualityGate"), {}),
        comparison_json=_json_dumps(safe.get("comparisonSummary"), {}),
        raw_summary_json=_json_dumps(safe, {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_checkpoint_summary(row)


def get_latest_checkpoint_summary(db: Session, thread_id: str) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    row = (
        db.query(LangGraphCheckpointSummary)
        .filter(LangGraphCheckpointSummary.thread_id == safe_thread_id)
        .order_by(LangGraphCheckpointSummary.id.desc())
        .first()
    )
    return serialize_checkpoint_summary(row) if row else empty_checkpoint_summary(safe_thread_id)


def list_checkpoint_summaries(db: Session, thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    safe_thread_id = normalize_thread_id(thread_id)
    rows = (
        db.query(LangGraphCheckpointSummary)
        .filter(LangGraphCheckpointSummary.thread_id == safe_thread_id)
        .order_by(LangGraphCheckpointSummary.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_checkpoint_summary(row) for row in rows]
