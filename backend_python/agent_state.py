from typing import Any

WEAK_ANSWER_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")
VALID_AGENT_MODES = {"coach", "interview"}

AGENT_SESSION_STATES = (
    "idle",
    "collecting_profile",
    "ready",
    "asking",
    "waiting_answer",
    "analyzing_answer",
    "retrieving_context",
    "deciding_next_action",
    "generating_question",
    "updating_memory",
    "generating_report",
    "completed",
    "failed",
)

AGENT_EVENTS = (
    "START_INTERVIEW",
    "PROFILE_READY",
    "QUESTION_GENERATED",
    "ANSWER_SUBMITTED",
    "ANSWER_ANALYZED",
    "CONTEXT_RETRIEVED",
    "DECISION_SELECTED",
    "MEMORY_UPDATED",
    "REPORT_REQUESTED",
    "REPORT_GENERATED",
    "ERROR_OCCURRED",
    "RESET_SESSION",
)

AGENT_NODES = (
    "observe_state",
    "retrieve_context",
    "analyze_answer",
    "select_action",
    "generate_question",
    "update_memory",
    "write_trace",
)


def _normalize_agent_mode(value: str) -> str:
    mode = str(value or "").strip()
    return mode if mode in VALID_AGENT_MODES else "interview"


def _classify_answer_status(answer_text: str) -> str:
    text = str(answer_text or "").strip()
    if not text:
        return "不会"
    if any(marker in text for marker in WEAK_ANSWER_MARKERS):
        return "不会"
    if len(text) < 24:
        return "模糊"
    return "完整"


def _detect_topic_lock(history: list[dict[str, Any]], weak_streak: int, window_size: int = 3) -> dict[str, Any]:
    if weak_streak < 2:
        return {"locked": False, "topic": "", "count": 0}

    topics: list[str] = []
    for item in list(history or [])[-window_size:]:
        topic = str(item.get("focus") or item.get("stage") or "").strip()
        if not topic:
            topic = " ".join(str(item.get("question") or "").strip().lower().split())
        if topic:
            topics.append(topic)

    if not topics:
        return {"locked": False, "topic": "", "count": 0}

    counts = {topic: topics.count(topic) for topic in set(topics)}
    top_topic, top_count = max(counts.items(), key=lambda item: item[1])
    if top_count < 2:
        return {"locked": False, "topic": "", "count": 0}

    return {"locked": True, "topic": top_topic, "count": top_count}


def _analyze_answer_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    weak_streak = 0
    repeated_question_count = 0
    trigger_signals: list[str] = []
    previous_question = ""

    for item in reversed(history):
        status = _classify_answer_status(str(item.get("answer") or ""))
        if status != "不会":
            break
        weak_streak += 1

    for item in reversed(history):
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        normalized_question = question.replace(" ", "")
        if not previous_question:
            previous_question = normalized_question
            repeated_question_count = 1
            continue
        if normalized_question == previous_question:
            repeated_question_count += 1
        else:
            break

    if weak_streak >= 2:
        trigger_signals.append("weak_answer_streak")
    if repeated_question_count >= 2:
        trigger_signals.append("repeated_question")
    topic_lock = _detect_topic_lock(history, weak_streak)
    if topic_lock["locked"]:
        trigger_signals.append("topic_lock_guardrail")

    return {
        "weakAnswerStreak": weak_streak,
        "repeatedQuestionCount": repeated_question_count,
        "topicLock": topic_lock,
        "triggerSignals": trigger_signals,
    }


def build_interview_agent_state(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    role_quality: dict[str, Any],
    question_quality: dict[str, Any],
    memory_quality: dict[str, Any],
    max_rounds: int = 8,
    agent_mode: str = "interview",
    answer_status: str | None = None,
    answer_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_profile = dict(profile or {})
    safe_history = list(history or [])
    last_answer = safe_history[-1] if safe_history else {}
    round_count = len(safe_history)
    remaining_rounds = max(max_rounds - round_count, 0)
    mode = _normalize_agent_mode(agent_mode)
    stage = str(next_stage or "综合追问")
    status = answer_status or _classify_answer_status(str(last_answer.get("answer") or ""))
    analysis = dict(answer_analysis or _analyze_answer_history(safe_history))

    return {
        "session": {
            "applicationProfileId": safe_profile.get("applicationProfileId"),
            "agentMode": mode,
            "nextStage": stage,
            "roundCount": round_count,
            "remainingRounds": remaining_rounds,
        },
        "profile": safe_profile,
        "history": safe_history,
        "agentMode": mode,
        "nextStage": stage,
        "lastAnswer": last_answer,
        "askedQuestions": [str(item.get("question") or "") for item in safe_history if item.get("question")],
        "roundCount": round_count,
        "remainingRounds": remaining_rounds,
        "answerStatus": status,
        "answerAnalysis": analysis,
        "retrievalQuality": {
            "roleKnowledge": dict(role_quality or {}),
            "questionBank": dict(question_quality or {}),
            "candidateMemory": dict(memory_quality or {}),
        },
        "agentNodes": list(AGENT_NODES),
        "nodeTrace": [],
        "toolCalls": [],
    }
