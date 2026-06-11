import json
from typing import Any, Awaitable, Callable

from .agent_policy import apply_agent_policy
from .agent_state import build_interview_agent_state
from .candidate_memory import build_candidate_profile
from .rag_quality import evaluate_retrieval_quality
from .weakness_training_templates import select_training_template_hint
from .weakness_strategy import select_weakness_strategy

WEAK_ANSWER_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")
VALID_AGENT_MODES = {"coach", "interview"}
ALLOWED_ACTIONS = {
    "deep_follow_up",
    "switch_topic",
    "lower_difficulty",
    "raise_difficulty",
    "summarize_feedback",
    "finish_interview",
}
ALLOWED_DIFFICULTIES = {"basic", "medium", "hard"}
ALLOWED_TOOLS = {"retrieve_context", "analyze_answer", "select_action", "generate_question", "update_memory"}

AGENT_SYSTEM_PROMPT = (
    "你是 AI 模拟面试系统的 Interview Orchestrator Agent。"
    "你只负责根据当前面试状态输出结构化 JSON 决策，不能直接生成长篇面试题。"
    "nextAction 必须从 deep_follow_up、switch_topic、lower_difficulty、raise_difficulty、"
    "summarize_feedback、finish_interview 中选择。"
    "agentMode=coach 时优先帮助候选人补基础；agentMode=interview 时保持真实面试压力但不能重复卡死。"
)


def classify_answer_status(answer_text: str) -> str:
    text = str(answer_text or "").strip()
    if not text:
        return "不会"
    if any(marker in text for marker in WEAK_ANSWER_MARKERS):
        return "不会"
    if len(text) < 24:
        return "模糊"
    return "完整"


def normalize_agent_mode(value: str) -> str:
    mode = str(value or "").strip()
    return mode if mode in VALID_AGENT_MODES else "interview"


def detect_topic_lock(history: list[dict[str, Any]], weak_streak: int, window_size: int = 3) -> dict[str, Any]:
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


def analyze_answer_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    weak_streak = 0
    repeated_question_count = 0
    trigger_signals: list[str] = []
    previous_question = ""

    for item in reversed(history):
        status = classify_answer_status(str(item.get("answer") or ""))
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
    topic_lock = detect_topic_lock(history, weak_streak)
    if topic_lock["locked"]:
        trigger_signals.append("topic_lock_guardrail")

    return {
        "weakAnswerStreak": weak_streak,
        "repeatedQuestionCount": repeated_question_count,
        "topicLock": topic_lock,
        "triggerSignals": trigger_signals,
    }


def build_decision_summary(decision: dict[str, Any]) -> str:
    mode_label = "学习辅导模式" if decision.get("agentMode") == "coach" else "真实面试模式"
    action = str(decision.get("nextAction") or "select_action")
    reason = str(decision.get("reason") or "根据当前面试状态选择下一步动作。")
    summary = f"{mode_label}：{action}。{reason}"
    weakness_strategy = decision.get("weaknessStrategy") if isinstance(decision.get("weaknessStrategy"), dict) else {}
    if weakness_strategy.get("enabled"):
        label = str(
            weakness_strategy.get("primaryWeakLabel")
            or weakness_strategy.get("primaryWeakTag")
            or "候选人历史薄弱点"
        )
        mode_policy = str(weakness_strategy.get("modePolicy") or "weakness_strategy")
        summary += f" 本轮参考历史薄弱点：{label}；策略：{mode_policy}。"
    training_hint = decision.get("trainingTemplateHint") if isinstance(decision.get("trainingTemplateHint"), dict) else {}
    if training_hint.get("enabled"):
        label = str(training_hint.get("label") or training_hint.get("weakTag") or "薄弱点")
        question = str(training_hint.get("recommendedQuestion") or "")
        summary += f" 本轮使用训练模板：{label}。"
        if question:
            summary += f" 模板建议问题：{question}"
    policy = decision.get("policy") if isinstance(decision.get("policy"), dict) else {}
    policy_reasons = policy.get("policyReasons") if isinstance(policy.get("policyReasons"), list) else []
    if policy_reasons:
        summary += f" 策略原因：{str(policy_reasons[0])}"
    return summary


def build_debug_signals(state: dict[str, Any] | None, decision: dict[str, Any]) -> dict[str, Any]:
    existing = decision.get("debugSignals") if isinstance(decision.get("debugSignals"), dict) else {}
    answer_analysis = state.get("answerAnalysis") if isinstance(state, dict) and isinstance(state.get("answerAnalysis"), dict) else {}
    topic_lock = answer_analysis.get("topicLock") if isinstance(answer_analysis.get("topicLock"), dict) else {}
    trigger_rules = decision.get("triggerRules") if isinstance(decision.get("triggerRules"), list) else []
    return {
        "weakAnswerStreak": int(answer_analysis.get("weakAnswerStreak") or existing.get("weakAnswerStreak") or 0),
        "repeatedQuestionCount": int(answer_analysis.get("repeatedQuestionCount") or existing.get("repeatedQuestionCount") or 0),
        "topicLocked": bool(topic_lock.get("locked", existing.get("topicLocked", False))),
        "topicLockTopic": str(topic_lock.get("topic") or existing.get("topicLockTopic") or ""),
        "guardrailApplied": bool(decision.get("guardrailApplied")),
        "topicShifted": isinstance(decision.get("topicShift"), dict),
        "triggerRules": [str(rule) for rule in trigger_rules if str(rule).strip()],
    }


def merge_trigger_rules(*groups: Any) -> list[str]:
    rules: list[str] = []
    for group in groups:
        if isinstance(group, list):
            values = group
        elif group:
            values = [group]
        else:
            values = []
        for value in values:
            rule = str(value or "").strip()
            if rule and rule not in rules:
                rules.append(rule)
    return rules


def build_agent_state(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    max_rounds: int = 8,
    agent_mode: str = "interview",
) -> dict[str, Any]:
    last_answer = history[-1] if history else {}
    answer_status = classify_answer_status(str(last_answer.get("answer") or ""))
    answer_analysis = analyze_answer_history(history)
    mode = normalize_agent_mode(agent_mode)
    state = build_interview_agent_state(
        profile=profile,
        history=history,
        next_stage=next_stage,
        role_quality=evaluate_retrieval_quality(role_hits),
        question_quality=evaluate_retrieval_quality(question_hits),
        memory_quality=evaluate_retrieval_quality(memory_hits),
        max_rounds=max_rounds,
        agent_mode=mode,
        answer_status=answer_status,
        answer_analysis=answer_analysis,
    )
    candidate_profile = build_candidate_profile(memory_hits)
    state["candidateProfile"] = candidate_profile
    state["weaknessStrategy"] = select_weakness_strategy(
        candidate_profile=candidate_profile,
        agent_mode=mode,
        profile=profile,
        next_stage=next_stage,
        history=history,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memory_hits,
        answer_analysis=answer_analysis,
    )
    return state


def build_fallback_decision(state: dict[str, Any]) -> dict[str, Any]:
    agent_mode = normalize_agent_mode(str(state.get("agentMode") or "interview"))
    answer_analysis = state.get("answerAnalysis") if isinstance(state.get("answerAnalysis"), dict) else {}
    weak_streak = int(answer_analysis.get("weakAnswerStreak") or 0)
    repeated_question_count = int(answer_analysis.get("repeatedQuestionCount") or 0)
    trigger_rules: list[str] = []
    weakness_strategy = state.get("weaknessStrategy") if isinstance(state.get("weaknessStrategy"), dict) else {}
    policy = apply_agent_policy(state)

    if int(state.get("remainingRounds") or 0) <= 0:
        action = "finish_interview"
        difficulty = "medium"
        trigger_rules.append("round_limit")
        reason = "剩余轮次已经用完，Agent 结束本轮面试并进入复盘。"
    elif weak_streak >= 3 or repeated_question_count >= 2 or (agent_mode == "interview" and weak_streak >= 2):
        action = "switch_topic"
        difficulty = "basic"
        trigger_rules.extend(["weak_answer_streak", "topic_shift"])
        if agent_mode == "interview" and weak_streak >= 2:
            trigger_rules.append("interview_weak_answer_limit")
        if repeated_question_count >= 2:
            trigger_rules.append("repeat_guard")
        reason = (
            "学习辅导模式下候选人连续答不上来，Agent 不继续卡同一知识点，先切换到更基础或相邻话题。"
            if agent_mode == "coach"
            else "候选人连续答不上来，Agent 保持面试压力但切换话题，避免无效重复追问。"
        )
    elif state.get("answerStatus") == "不会":
        action = "lower_difficulty"
        difficulty = "basic"
        trigger_rules.append("weak_answer")
        reason = (
            "学习辅导模式下上一轮回答偏弱，Agent 先降低难度并引导候选人补基础。"
            if agent_mode == "coach"
            else "上一轮回答偏弱，Agent 先降低难度确认基础概念。"
        )
    elif state.get("answerStatus") == "完整":
        action = "deep_follow_up"
        difficulty = "hard"
        trigger_rules.append("strong_answer")
        reason = "候选人上一轮回答较完整，Agent 可以继续深挖细节并提高追问难度。"
    else:
        action = "deep_follow_up"
        difficulty = "medium"
        trigger_rules.append("normal_follow_up")
        reason = "候选人回答信息不足但不是完全不会，Agent 继续做中等难度追问。"

    if weakness_strategy.get("enabled"):
        trigger_rules = merge_trigger_rules(trigger_rules, weakness_strategy.get("triggerRules"))
        strategy_action = str(weakness_strategy.get("recommendedAction") or "")
        if weakness_strategy.get("modePolicy") == "avoid_weakness_deadlock":
            action = "switch_topic"
            difficulty = "basic"
            reason = str(weakness_strategy.get("reason") or reason)
        elif agent_mode == "coach" and strategy_action == "practice_weakness":
            action = "lower_difficulty"
            difficulty = str(weakness_strategy.get("recommendedDifficulty") or "basic")
            reason = str(weakness_strategy.get("reason") or reason)
        elif agent_mode == "interview" and strategy_action == "deep_follow_up" and state.get("answerStatus") != "不会":
            action = "deep_follow_up"
            difficulty = str(weakness_strategy.get("recommendedDifficulty") or "medium")
            reason = str(weakness_strategy.get("reason") or reason)

    if policy.get("recommendedAction"):
        if policy.get("shouldSwitchTopic"):
            action = "switch_topic"
            difficulty = str(policy.get("difficulty") or difficulty)
        elif policy.get("recommendedAction") == "lower_difficulty" and action != "finish_interview":
            action = "lower_difficulty"
            difficulty = str(policy.get("difficulty") or difficulty)
        trigger_rules = merge_trigger_rules(trigger_rules, policy.get("triggerRules"))
        policy_reasons = policy.get("policyReasons") if isinstance(policy.get("policyReasons"), list) else []
        if policy_reasons and not weakness_strategy.get("enabled"):
            reason = str(policy_reasons[0])

    training_template_hint = select_training_template_hint(
        weakness_strategy=weakness_strategy,
        agent_mode=agent_mode,
        difficulty=difficulty,
    )
    decision = {
        "nextAction": action,
        "stage": str(state.get("nextStage") or "综合追问"),
        "difficulty": difficulty,
        "focus": str(weakness_strategy.get("primaryWeakLabel") or state.get("nextStage") or "综合能力"),
        "reason": reason,
        "tools": ["retrieve_context", "analyze_answer", "generate_question"],
        "shouldUpdateMemory": True,
        "triggerRules": trigger_rules,
        "agentMode": agent_mode,
        "nodeTrace": ["observe_state", "analyze_answer", "select_action"],
        "guardrailApplied": bool(weakness_strategy.get("guardrailApplied")),
        "fallbackUsed": True,
        "weaknessStrategy": weakness_strategy,
        "trainingTemplateHint": training_template_hint,
        "policy": policy,
    }
    decision["debugSignals"] = build_debug_signals(state, decision)
    decision["decisionSummary"] = build_decision_summary(decision)
    return decision


def should_apply_decision_guardrail(decision: dict[str, Any], state: dict[str, Any] | None) -> bool:
    if not isinstance(state, dict):
        return False
    action = str(decision.get("nextAction") or "")
    difficulty = str(decision.get("difficulty") or "")
    is_pressure_action = action == "raise_difficulty" or (action == "deep_follow_up" and difficulty == "hard")
    if not is_pressure_action:
        return False

    answer_analysis = state.get("answerAnalysis") if isinstance(state.get("answerAnalysis"), dict) else {}
    topic_lock = answer_analysis.get("topicLock") if isinstance(answer_analysis.get("topicLock"), dict) else {}
    weak_streak = int(answer_analysis.get("weakAnswerStreak") or 0)
    agent_mode = normalize_agent_mode(str(state.get("agentMode") or decision.get("agentMode") or "interview"))
    return weak_streak >= 3 or bool(topic_lock.get("locked")) or (agent_mode == "interview" and weak_streak >= 2)


def apply_decision_guardrail(
    decision: dict[str, Any],
    fallback: dict[str, Any],
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    answer_analysis = state.get("answerAnalysis") if isinstance(state, dict) and isinstance(state.get("answerAnalysis"), dict) else {}
    trigger_signals = answer_analysis.get("triggerSignals") if isinstance(answer_analysis.get("triggerSignals"), list) else []
    trigger_rules = [
        *list(fallback.get("triggerRules") or []),
        *list(decision.get("triggerRules") or []),
        *[str(signal) for signal in trigger_signals],
    ]
    safe_trigger_rules = list(dict.fromkeys(rule for rule in trigger_rules if str(rule).strip()))
    if "topic_shift" not in safe_trigger_rules:
        safe_trigger_rules.append("topic_shift")

    corrected = {
        **fallback,
        "nextAction": "switch_topic",
        "difficulty": "basic",
        "triggerRules": safe_trigger_rules,
        "guardrailApplied": True,
        "fallbackUsed": False,
        "policy": fallback.get("policy") if isinstance(fallback.get("policy"), dict) else apply_agent_policy(state),
    }
    from_topic = str(decision.get("focus") or "").strip()
    to_topic = str(corrected.get("focus") or "").strip()
    if from_topic or to_topic:
        corrected["topicShift"] = {"from": from_topic, "to": to_topic}
    corrected["debugSignals"] = build_debug_signals(state, corrected)
    corrected["decisionSummary"] = build_decision_summary(corrected)
    return corrected


def normalize_agent_decision(
    raw: Any,
    fallback: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("nextAction") not in ALLOWED_ACTIONS:
        decision = {**fallback, "fallbackUsed": True}
        decision["guardrailApplied"] = False
        decision["debugSignals"] = build_debug_signals(state, decision)
        decision["decisionSummary"] = build_decision_summary(decision)
        return decision

    difficulty = str(raw.get("difficulty") or fallback.get("difficulty") or "medium")
    if difficulty not in ALLOWED_DIFFICULTIES:
        difficulty = str(fallback.get("difficulty") or "medium")

    raw_tools = raw.get("tools") if isinstance(raw.get("tools"), list) else []
    tools = [str(tool) for tool in raw_tools if str(tool) in ALLOWED_TOOLS]
    trigger_rules = raw.get("triggerRules") if isinstance(raw.get("triggerRules"), list) else fallback.get("triggerRules")
    safe_trigger_rules = [str(rule) for rule in trigger_rules if str(rule).strip()] if isinstance(trigger_rules, list) else []
    agent_mode = normalize_agent_mode(str(raw.get("agentMode") or fallback.get("agentMode") or "interview"))
    weakness_strategy = fallback.get("weaknessStrategy") if isinstance(fallback.get("weaknessStrategy"), dict) else {}
    policy = fallback.get("policy") if isinstance(fallback.get("policy"), dict) else apply_agent_policy(state)
    training_template_hint = (
        fallback.get("trainingTemplateHint")
        if isinstance(fallback.get("trainingTemplateHint"), dict)
        else select_training_template_hint(
            weakness_strategy=weakness_strategy,
            agent_mode=agent_mode,
            difficulty=difficulty,
        )
    )

    decision = {
        "nextAction": str(raw["nextAction"]),
        "stage": str(raw.get("stage") or fallback.get("stage") or "综合追问"),
        "difficulty": difficulty,
        "focus": str(raw.get("focus") or fallback.get("focus") or "综合能力"),
        "reason": str(raw.get("reason") or fallback.get("reason") or ""),
        "tools": tools or list(fallback.get("tools") or []),
        "shouldUpdateMemory": bool(raw.get("shouldUpdateMemory", fallback.get("shouldUpdateMemory", True))),
        "triggerRules": safe_trigger_rules,
        "agentMode": agent_mode,
        "nodeTrace": list(fallback.get("nodeTrace") or ["observe_state", "select_action"]),
        "fallbackUsed": False,
        "guardrailApplied": False,
        "weaknessStrategy": weakness_strategy,
        "trainingTemplateHint": training_template_hint,
        "policy": policy,
    }
    if should_apply_decision_guardrail(decision, state):
        return apply_decision_guardrail(decision, fallback, state)
    decision["debugSignals"] = build_debug_signals(state, decision)
    decision["decisionSummary"] = str(raw.get("decisionSummary") or build_decision_summary(decision))
    return decision


async def decide_next_action(
    state: dict[str, Any],
    *,
    call_model_fn: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    fallback = build_fallback_decision(state)
    try:
        result = await call_model_fn(
            temperature=0.2,
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "state": state,
                            "fallbackDecision": fallback,
                            "outputSchema": {
                                "nextAction": "string",
                                "stage": "string",
                                "difficulty": "basic|medium|hard",
                                "focus": "string",
                                "reason": "string",
                                "tools": "string[]",
                                "triggerRules": "string[]",
                                "agentMode": "coach|interview",
                                "shouldUpdateMemory": "boolean",
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        return normalize_agent_decision(result, fallback, state=state)
    except Exception:
        return {**fallback, "fallbackUsed": True}
