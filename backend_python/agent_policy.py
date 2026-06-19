from typing import Any

VALID_AGENT_MODES = {"coach", "interview"}


def normalize_agent_mode(value: str) -> str:
    mode = str(value or "").strip()
    return mode if mode in VALID_AGENT_MODES else "interview"


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _add_unique(items: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def normalize_policy_input(state: dict[str, Any] | None) -> dict[str, Any]:
    source = state if isinstance(state, dict) else {}
    answer_analysis = source.get("answerAnalysis") if isinstance(source.get("answerAnalysis"), dict) else {}
    topic_lock = answer_analysis.get("topicLock") if isinstance(answer_analysis.get("topicLock"), dict) else {}
    return {
        "agentMode": normalize_agent_mode(str(source.get("agentMode") or "interview")),
        "answerStatus": str(answer_analysis.get("answerStatus") or source.get("answerStatus") or ""),
        "weakAnswerStreak": _int_value(answer_analysis.get("weakAnswerStreak")),
        "repeatedQuestionCount": _int_value(answer_analysis.get("repeatedQuestionCount")),
        "topicLock": {
            "locked": bool(topic_lock.get("locked")),
            "topic": str(topic_lock.get("topic") or ""),
            "count": _int_value(topic_lock.get("count")),
        },
        "retrievalQuality": source.get("retrievalQuality") if isinstance(source.get("retrievalQuality"), dict) else {},
        "weaknessStrategy": source.get("weaknessStrategy") if isinstance(source.get("weaknessStrategy"), dict) else {},
        "candidateTrainingTasks": (
            source.get("candidateTrainingTasks") if isinstance(source.get("candidateTrainingTasks"), list) else []
        ),
        "history": source.get("history") if isinstance(source.get("history"), list) else [],
    }


def apply_agent_policy(state: dict[str, Any] | None) -> dict[str, Any]:
    policy_input = normalize_policy_input(state)
    agent_mode = policy_input["agentMode"]
    weak_streak = policy_input["weakAnswerStreak"]
    repeated_count = policy_input["repeatedQuestionCount"]
    topic_lock = policy_input["topicLock"]
    reasons: list[str] = []
    trigger_rules: list[str] = []

    recommended_action = "deep_follow_up"
    difficulty = "medium"
    should_explain = False
    should_switch_topic = False
    should_ask_user_choice = False
    requires_human_review = False

    if policy_input["answerStatus"] == "未开始":
        recommended_action = "deep_follow_up"
        difficulty = "medium"
        _add_unique(trigger_rules, "opening_question")
        reasons.append("面试刚开始，先结合投递档案、岗位 JD 和知识库生成第一题。")
    elif weak_streak >= 3:
        recommended_action = "switch_topic"
        difficulty = "basic"
        should_switch_topic = True
        should_explain = agent_mode == "coach"
        _add_unique(trigger_rules, "weak_answer_streak")
        _add_unique(trigger_rules, "topic_shift")
        if agent_mode == "coach":
            reasons.append("学习辅导模式下候选人连续三轮答不上来，Agent 先解释并切换到基础或相邻话题。")
        else:
            reasons.append("候选人连续三轮答不上来，Agent 不继续机械追问同一知识点，改为切换到基础或相邻话题。")
    elif agent_mode == "interview" and weak_streak >= 2:
        recommended_action = "switch_topic"
        difficulty = "basic"
        should_switch_topic = True
        _add_unique(trigger_rules, "weak_answer_streak")
        _add_unique(trigger_rules, "interview_weak_answer_limit")
        reasons.append("真实面试模式下连续弱回答达到两轮，保持压力但切换话题，避免无效卡死。")
    elif weak_streak == 2:
        recommended_action = "lower_difficulty"
        difficulty = "basic"
        should_explain = agent_mode == "coach"
        should_ask_user_choice = agent_mode == "coach"
        _add_unique(trigger_rules, "weak_answer_streak")
        if agent_mode == "coach":
            _add_unique(trigger_rules, "coach_explain_before_ask")
            reasons.append("候选人连续两轮答不上来，coach 模式先解释或拆小问题，再继续追问。")
        else:
            reasons.append("候选人连续两轮答不上来，先降低难度确认基础。")
    elif weak_streak == 1 or policy_input["answerStatus"] == "不会":
        recommended_action = "lower_difficulty"
        difficulty = "basic"
        _add_unique(trigger_rules, "weak_answer")
        reasons.append("候选人上一轮回答偏弱，先降低难度确认基础概念。")
    else:
        _add_unique(trigger_rules, "normal_follow_up")
        reasons.append("回答不算完全不会，默认继续中等难度追问。")

    if repeated_count >= 2:
        should_switch_topic = True
        recommended_action = "switch_topic"
        difficulty = "basic"
        _add_unique(trigger_rules, "repeat_guard")
        _add_unique(trigger_rules, "topic_shift")
        reasons.append("检测到连续重复追问，触发重复问题保护。")

    if topic_lock["locked"]:
        should_switch_topic = True
        recommended_action = "switch_topic"
        difficulty = "basic"
        _add_unique(trigger_rules, "topic_lock_guardrail")
        _add_unique(trigger_rules, "topic_shift")
        reasons.append(f"检测到话题锁定在“{topic_lock['topic']}”，需要切换话题避免死磕。")

    if weak_streak >= 3 and (topic_lock["locked"] or repeated_count >= 2):
        requires_human_review = True
        _add_unique(trigger_rules, "human_review_precheck")
        reasons.append("连续弱回答叠加重复或话题锁，建议预留人工介入或用户选择。")

    return {
        "recommendedAction": recommended_action,
        "difficulty": difficulty,
        "shouldExplainBeforeAsk": should_explain,
        "shouldSwitchTopic": should_switch_topic,
        "shouldAskUserChoice": should_ask_user_choice,
        "requiresHumanReview": requires_human_review,
        "policyReasons": reasons,
        "triggerRules": trigger_rules,
    }
