import json
from typing import Any, TypedDict


class InterviewGraphState(TypedDict, total=False):
    threadId: str
    applicationProfileId: int | None
    profile: dict[str, Any]
    history: list[dict[str, Any]]
    nextStage: str
    agentMode: str
    roundCount: int
    remainingRounds: int
    useRealRag: bool
    useRealDecision: bool
    answerAnalysis: dict[str, Any]
    retrievalQuality: dict[str, Any]
    policy: dict[str, Any]
    policySummary: dict[str, Any]
    roleHits: list[dict[str, Any]]
    questionHits: list[dict[str, Any]]
    memoryHits: list[dict[str, Any]]
    toolCalls: list[dict[str, Any]]
    decision: dict[str, Any]
    nextQuestion: dict[str, Any]
    memoryUpdate: dict[str, Any]
    checkpointSummary: dict[str, Any]
    nodeTrace: list[dict[str, Any]]


def build_initial_graph_state(
    *,
    thread_id: str = "default-thread",
    application_profile_id: int | None = None,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
    use_real_rag: bool = False,
    use_real_decision: bool = False,
) -> InterviewGraphState:
    history_items = list(history or [])
    round_count = len(history_items)
    state: InterviewGraphState = {
        "threadId": str(thread_id or "default-thread"),
        "applicationProfileId": application_profile_id,
        "profile": dict(profile or {}),
        "history": history_items,
        "nextStage": str(next_stage or "综合追问"),
        "agentMode": str(agent_mode or "interview"),
        "roundCount": round_count,
        "remainingRounds": max(8 - round_count, 0),
        "useRealRag": bool(use_real_rag),
        "useRealDecision": bool(use_real_decision),
        "answerAnalysis": {},
        "retrievalQuality": {},
        "policy": {},
        "policySummary": {},
        "roleHits": [],
        "questionHits": [],
        "memoryHits": [],
        "toolCalls": [],
        "decision": {},
        "nextQuestion": {},
        "memoryUpdate": {},
        "checkpointSummary": {},
        "nodeTrace": [],
    }
    assert_graph_state_jsonable(state)
    return state


def assert_graph_state_jsonable(state: dict[str, Any]) -> None:
    try:
        json.dumps(state, ensure_ascii=False)
    except TypeError as exc:
        raise TypeError("Graph state must be JSON serializable") from exc
