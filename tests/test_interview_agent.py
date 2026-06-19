import asyncio

from backend_python.interview_agent import (
    build_agent_state,
    build_fallback_decision,
    decide_next_action,
    normalize_agent_decision,
)


def test_build_agent_state_extracts_round_and_last_answer() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[
            {"question": "什么是 RAG？", "answer": "不知道"},
        ],
        next_stage="技术追问",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
    )

    assert state["roundCount"] == 1
    assert state["lastAnswer"]["answer"] == "不知道"
    assert state["askedQuestions"] == ["什么是 RAG？"]
    assert state["answerStatus"] == "不会"
    assert state["agentMode"] == "interview"
    assert state["answerAnalysis"]["weakAnswerStreak"] == 1


def test_build_agent_state_marks_empty_history_as_not_started() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[],
        next_stage="技术追问",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        agent_mode="coach",
    )

    assert state["roundCount"] == 0
    assert state["answerStatus"] == "未开始"
    assert state["answerAnalysis"]["answerStatus"] == "未开始"
    assert state["answerAnalysis"]["weakAnswerStreak"] == 0


def test_build_agent_state_tracks_coach_mode_and_weak_answer_streak() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[
            {"question": "RAG 日志怎么写？", "answer": "不知道"},
            {"question": "那先说 query_text 是什么？", "answer": "不会"},
            {"question": "请换个角度解释 hit_count。", "answer": "写不出来"},
        ],
        next_stage="技术追问",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        agent_mode="coach",
    )

    assert state["agentMode"] == "coach"
    assert state["answerAnalysis"]["weakAnswerStreak"] == 3
    assert "weak_answer_streak" in state["answerAnalysis"]["triggerSignals"]


def test_build_agent_state_includes_candidate_profile_and_weakness_strategy() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
        history=[{"question": "RAG 质量怎么评估？", "answer": "不知道", "focus": "RAG 质量评估"}],
        next_stage="技术追问",
        role_hits=[{"title": "RAG 质量评估", "content": "Hit@K MRR 关键词覆盖率"}],
        question_hits=[],
        memory_hits=[
            {"score": 60, "weakTags": ["rag_quality", "agent_state"], "risks": [], "actions": [], "recentStages": []}
        ],
        agent_mode="coach",
    )

    assert state["candidateProfile"]["frequentWeakTags"][0] == "rag_quality"
    assert state["weaknessStrategy"]["enabled"] is True
    assert state["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert state["weaknessStrategy"]["modePolicy"] == "coach_remediation"


def test_build_fallback_decision_lowers_difficulty_for_weak_answer() -> None:
    state = {
        "nextStage": "技术追问",
        "answerStatus": "不会",
        "remainingRounds": 5,
        "agentMode": "interview",
        "answerAnalysis": {"weakAnswerStreak": 1, "repeatedQuestionCount": 0},
    }

    decision = build_fallback_decision(state)

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["difficulty"] == "basic"
    assert "retrieve_context" in decision["tools"]
    assert decision["agentMode"] == "interview"
    assert decision["policy"]["recommendedAction"] == "lower_difficulty"
    assert decision["policy"]["policyReasons"]


def test_build_fallback_decision_uses_opening_reason_before_any_answer() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "未开始",
            "roundCount": 0,
            "remainingRounds": 8,
            "agentMode": "coach",
            "answerAnalysis": {"answerStatus": "未开始", "weakAnswerStreak": 0, "repeatedQuestionCount": 0},
        }
    )

    assert decision["nextAction"] == "deep_follow_up"
    assert decision["difficulty"] == "medium"
    assert "opening_question" in decision["triggerRules"]
    assert "面试刚开始" in decision["reason"]
    assert "上一轮回答" not in decision["reason"]


def test_build_fallback_decision_switches_topic_after_repeated_weak_answers() -> None:
    state = {
        "nextStage": "技术追问",
        "answerStatus": "不会",
        "remainingRounds": 5,
        "agentMode": "coach",
        "answerAnalysis": {"weakAnswerStreak": 3, "repeatedQuestionCount": 0},
    }

    decision = build_fallback_decision(state)

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["agentMode"] == "coach"
    assert "weak_answer_streak" in decision["triggerRules"]
    assert "topic_shift" in decision["triggerRules"]
    assert "学习辅导" in decision["reason"]
    assert decision["policy"]["shouldSwitchTopic"] is True
    assert decision["policy"]["shouldExplainBeforeAsk"] is True


def test_build_fallback_decision_uses_coach_weakness_strategy() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "模糊",
            "remainingRounds": 5,
            "agentMode": "coach",
            "answerAnalysis": {"weakAnswerStreak": 0, "repeatedQuestionCount": 0},
            "weaknessStrategy": {
                "enabled": True,
                "primaryWeakTag": "rag_quality",
                "primaryWeakLabel": "RAG 质量评估",
                "modePolicy": "coach_remediation",
                "recommendedAction": "practice_weakness",
                "recommendedDifficulty": "basic",
                "reason": "候选人画像显示 RAG 质量评估是高频薄弱点。",
                "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
                "guardrailApplied": False,
            },
        }
    )

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["difficulty"] == "basic"
    assert decision["focus"] == "RAG 质量评估"
    assert decision["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert "weakness_strategy" in decision["triggerRules"]
    assert "候选人画像" in decision["reason"]


def test_build_fallback_decision_includes_training_template_hint_for_weakness_strategy() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "模糊",
            "remainingRounds": 5,
            "agentMode": "coach",
            "answerAnalysis": {"weakAnswerStreak": 0, "repeatedQuestionCount": 0},
            "weaknessStrategy": {
                "enabled": True,
                "primaryWeakTag": "rag_quality",
                "primaryWeakLabel": "RAG 质量评估",
                "modePolicy": "coach_remediation",
                "recommendedAction": "practice_weakness",
                "recommendedDifficulty": "basic",
                "reason": "候选人画像显示 RAG 质量评估是高频薄弱点。",
                "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
                "guardrailApplied": False,
            },
        }
    )

    hint = decision["trainingTemplateHint"]
    assert hint["enabled"] is True
    assert hint["weakTag"] == "rag_quality"
    assert hint["mode"] == "coach"
    assert hint["difficulty"] == "basic"
    assert "Hit@K" in hint["recommendedQuestion"]
    assert "训练模板" in decision["decisionSummary"]


def test_build_fallback_decision_switches_topic_when_weakness_strategy_deadlocks() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "技术追问",
            "answerStatus": "不会",
            "remainingRounds": 5,
            "agentMode": "interview",
            "answerAnalysis": {"weakAnswerStreak": 2, "repeatedQuestionCount": 0},
            "weaknessStrategy": {
                "enabled": True,
                "primaryWeakTag": "rag_quality",
                "primaryWeakLabel": "RAG 质量评估",
                "modePolicy": "avoid_weakness_deadlock",
                "recommendedAction": "switch_topic",
                "recommendedDifficulty": "basic",
                "reason": "连续在 RAG 质量评估上回答偏弱，触发防死磕策略。",
                "triggerRules": ["weakness_strategy", "weakness_deadlock_guardrail"],
                "guardrailApplied": True,
            },
        }
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["weaknessStrategy"]["guardrailApplied"] is True
    assert decision["guardrailApplied"] is True
    assert "weakness_deadlock_guardrail" in decision["triggerRules"]


def test_normalize_agent_decision_accepts_valid_model_decision() -> None:
    fallback = {
        "nextAction": "deep_follow_up",
        "stage": "技术追问",
        "difficulty": "medium",
        "focus": "RAG",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
        "triggerRules": ["fallback_rule"],
        "agentMode": "interview",
        "policy": {
            "recommendedAction": "deep_follow_up",
            "difficulty": "medium",
            "shouldExplainBeforeAsk": False,
            "shouldSwitchTopic": False,
            "shouldAskUserChoice": False,
            "requiresHumanReview": False,
            "policyReasons": ["fallback policy"],
            "triggerRules": ["fallback_policy"],
        },
    }
    decision = normalize_agent_decision(
        {
            "nextAction": "switch_topic",
            "stage": "项目经历",
            "difficulty": "basic",
            "focus": "FastAPI 模块化",
            "reason": "避免重复卡在 RAG 日志",
            "tools": ["retrieve_context", "generate_question", "bad_tool"],
            "shouldUpdateMemory": False,
            "triggerRules": ["repeat_guard"],
            "agentMode": "coach",
        },
        fallback,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["tools"] == ["retrieve_context", "generate_question"]
    assert decision["fallbackUsed"] is False
    assert decision["triggerRules"] == ["repeat_guard"]
    assert decision["agentMode"] == "coach"
    assert decision["policy"]["policyReasons"] == ["fallback policy"]
    assert decision["decisionSummary"]


def test_normalize_agent_decision_uses_fallback_for_invalid_action() -> None:
    fallback = {
        "nextAction": "lower_difficulty",
        "stage": "技术追问",
        "difficulty": "basic",
        "focus": "RAG",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
        "triggerRules": ["fallback_rule"],
        "agentMode": "interview",
        "policy": {
            "recommendedAction": "lower_difficulty",
            "difficulty": "basic",
            "shouldExplainBeforeAsk": False,
            "shouldSwitchTopic": False,
            "shouldAskUserChoice": False,
            "requiresHumanReview": False,
            "policyReasons": ["invalid action fallback"],
            "triggerRules": ["fallback_policy"],
        },
    }

    decision = normalize_agent_decision({"nextAction": "unknown"}, fallback)

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["fallbackUsed"] is True
    assert decision["triggerRules"] == ["fallback_rule"]
    assert decision["policy"]["policyReasons"] == ["invalid action fallback"]


def test_normalize_agent_decision_applies_policy_guardrail_for_topic_lock() -> None:
    state = {
        "nextStage": "技术追问",
        "answerStatus": "不会",
        "remainingRounds": 5,
        "agentMode": "coach",
        "answerAnalysis": {
            "weakAnswerStreak": 3,
            "repeatedQuestionCount": 2,
            "topicLock": {"locked": True, "topic": "RAG 日志 JSON", "count": 3},
        },
    }
    fallback = build_fallback_decision(state)

    decision = normalize_agent_decision(
        {
            "nextAction": "deep_follow_up",
            "stage": "技术追问",
            "difficulty": "hard",
            "focus": "RAG 日志 JSON",
            "reason": "继续追问同一个知识点。",
            "tools": ["retrieve_context", "generate_question"],
            "triggerRules": ["model_deep_follow_up"],
            "agentMode": "coach",
        },
        fallback,
        state=state,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["guardrailApplied"] is True
    assert decision["policy"]["requiresHumanReview"] is True
    assert "topic_lock_guardrail" in decision["policy"]["triggerRules"]


async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
    return {
        "nextAction": "lower_difficulty",
        "stage": "技术追问",
        "difficulty": "basic",
        "focus": "RAG 日志字段",
        "reason": "候选人回答不知道，需要先补基础概念。",
        "tools": ["retrieve_context", "generate_question"],
        "shouldUpdateMemory": True,
    }


def test_decide_next_action_uses_model_decision_when_valid() -> None:
    state = {"nextStage": "技术追问", "answerStatus": "不会", "remainingRounds": 5}

    decision = asyncio.run(decide_next_action(state, call_model_fn=fake_call_model))

    assert decision["nextAction"] == "lower_difficulty"
    assert decision["fallbackUsed"] is False


def test_build_agent_state_detects_topic_lock_from_recent_focuses() -> None:
    state = build_agent_state(
        profile={"targetRole": "AI application intern"},
        history=[
            {"question": "Explain query_text", "answer": "", "focus": "rag_log_json"},
            {"question": "Explain hit_count", "answer": "", "focus": "rag_log_json"},
            {"question": "Explain hits_json", "answer": "", "focus": "rag_log_json"},
        ],
        next_stage="technical_follow_up",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        agent_mode="coach",
    )

    topic_lock = state["answerAnalysis"]["topicLock"]
    assert topic_lock["locked"] is True
    assert topic_lock["topic"] == "rag_log_json"
    assert topic_lock["count"] == 3
    assert "topic_lock_guardrail" in state["answerAnalysis"]["triggerSignals"]


def test_normalize_agent_decision_applies_guardrail_when_model_raises_difficulty_during_topic_lock() -> None:
    fallback = {
        "nextAction": "switch_topic",
        "stage": "technical_follow_up",
        "difficulty": "basic",
        "focus": "rag_observability",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
        "triggerRules": ["topic_lock_guardrail"],
        "agentMode": "coach",
    }
    state = {
        "answerStatus": "不会",
        "answerAnalysis": {
            "weakAnswerStreak": 3,
            "repeatedQuestionCount": 0,
            "topicLock": {"locked": True, "topic": "rag_log_json", "count": 3},
            "triggerSignals": ["weak_answer_streak", "topic_lock_guardrail"],
        },
    }

    decision = normalize_agent_decision(
        {
            "nextAction": "raise_difficulty",
            "stage": "technical_follow_up",
            "difficulty": "hard",
            "focus": "rag_log_json",
            "reason": "continue deep follow-up",
            "tools": ["retrieve_context"],
            "shouldUpdateMemory": True,
        },
        fallback,
        state=state,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["guardrailApplied"] is True
    assert "topic_lock_guardrail" in decision["triggerRules"]


def test_build_fallback_decision_includes_guardrail_metadata() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "technical_follow_up",
            "answerStatus": "不会",
            "remainingRounds": 5,
            "agentMode": "coach",
            "answerAnalysis": {"weakAnswerStreak": 1, "repeatedQuestionCount": 0},
        }
    )

    assert decision["guardrailApplied"] is False
    assert "triggerRules" in decision
    assert decision["decisionSummary"]


def test_build_fallback_decision_switches_topic_after_two_weak_answers_in_interview_mode() -> None:
    decision = build_fallback_decision(
        {
            "nextStage": "technical_follow_up",
            "answerStatus": "不会",
            "remainingRounds": 5,
            "agentMode": "interview",
            "answerAnalysis": {
                "weakAnswerStreak": 2,
                "repeatedQuestionCount": 0,
                "topicLock": {"locked": False, "topic": "", "count": 0},
            },
        }
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["agentMode"] == "interview"
    assert "interview_weak_answer_limit" in decision["triggerRules"]
    assert "topic_shift" in decision["triggerRules"]


def test_normalize_agent_decision_applies_guardrail_when_model_deep_follows_after_two_weak_interview_answers() -> None:
    fallback = {
        "nextAction": "switch_topic",
        "stage": "technical_follow_up",
        "difficulty": "basic",
        "focus": "rag_basic",
        "reason": "fallback",
        "tools": ["retrieve_context"],
        "shouldUpdateMemory": True,
        "triggerRules": ["interview_weak_answer_limit"],
        "agentMode": "interview",
    }
    state = {
        "agentMode": "interview",
        "answerStatus": "不会",
        "answerAnalysis": {
            "weakAnswerStreak": 2,
            "repeatedQuestionCount": 0,
            "topicLock": {"locked": False, "topic": "", "count": 0},
            "triggerSignals": ["weak_answer_streak"],
        },
    }

    decision = normalize_agent_decision(
        {
            "nextAction": "deep_follow_up",
            "stage": "technical_follow_up",
            "difficulty": "hard",
            "focus": "rag_log_json",
            "reason": "continue pressure",
            "tools": ["retrieve_context"],
            "shouldUpdateMemory": True,
            "agentMode": "interview",
        },
        fallback,
        state=state,
    )

    assert decision["nextAction"] == "switch_topic"
    assert decision["difficulty"] == "basic"
    assert decision["guardrailApplied"] is True
    assert "interview_weak_answer_limit" in decision["triggerRules"]
    assert decision["topicShift"] == {"from": "rag_log_json", "to": "rag_basic"}
    assert decision["debugSignals"] == {
        "weakAnswerStreak": 2,
        "repeatedQuestionCount": 0,
        "topicLocked": False,
        "topicLockTopic": "",
        "guardrailApplied": True,
        "topicShifted": True,
        "triggerRules": decision["triggerRules"],
    }
