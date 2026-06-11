from backend_python.agent_policy import apply_agent_policy


def _state(
    *,
    agent_mode: str = "coach",
    weak_streak: int = 0,
    repeated_count: int = 0,
    topic_locked: bool = False,
    topic_count: int = 0,
) -> dict:
    return {
        "agentMode": agent_mode,
        "answerAnalysis": {
            "answerStatus": "不会" if weak_streak else "模糊",
            "weakAnswerStreak": weak_streak,
            "repeatedQuestionCount": repeated_count,
            "topicLock": {
                "locked": topic_locked,
                "topic": "RAG 日志 JSON",
                "count": topic_count,
            },
        },
        "retrievalQuality": {
            "roleKnowledge": {"level": "good", "hitCount": 3},
            "questionBank": {"level": "weak", "hitCount": 1},
            "candidateMemory": {"level": "good", "hitCount": 2},
        },
        "weaknessStrategy": {},
        "candidateTrainingTasks": [],
        "history": [],
    }


def test_coach_weak_streak_one_lowers_difficulty() -> None:
    policy = apply_agent_policy(_state(agent_mode="coach", weak_streak=1))

    assert policy["recommendedAction"] == "lower_difficulty"
    assert policy["difficulty"] == "basic"
    assert policy["shouldExplainBeforeAsk"] is False
    assert policy["shouldSwitchTopic"] is False
    assert policy["policyReasons"]
    assert "weak_answer" in policy["triggerRules"]


def test_coach_weak_streak_two_explains_and_asks_user_choice() -> None:
    policy = apply_agent_policy(_state(agent_mode="coach", weak_streak=2))

    assert policy["recommendedAction"] == "lower_difficulty"
    assert policy["difficulty"] == "basic"
    assert policy["shouldExplainBeforeAsk"] is True
    assert policy["shouldAskUserChoice"] is True
    assert policy["shouldSwitchTopic"] is False
    assert "coach_explain_before_ask" in policy["triggerRules"]


def test_coach_weak_streak_three_switches_topic() -> None:
    policy = apply_agent_policy(_state(agent_mode="coach", weak_streak=3))

    assert policy["recommendedAction"] == "switch_topic"
    assert policy["difficulty"] == "basic"
    assert policy["shouldExplainBeforeAsk"] is True
    assert policy["shouldSwitchTopic"] is True
    assert "topic_shift" in policy["triggerRules"]


def test_interview_mode_switches_topic_without_feeding_answer() -> None:
    policy = apply_agent_policy(_state(agent_mode="interview", weak_streak=2))

    assert policy["recommendedAction"] == "switch_topic"
    assert policy["difficulty"] == "basic"
    assert policy["shouldExplainBeforeAsk"] is False
    assert policy["shouldAskUserChoice"] is False
    assert policy["shouldSwitchTopic"] is True
    assert "interview_weak_answer_limit" in policy["triggerRules"]


def test_topic_lock_requires_switch_and_human_review_precheck() -> None:
    policy = apply_agent_policy(
        _state(
            agent_mode="coach",
            weak_streak=3,
            repeated_count=2,
            topic_locked=True,
            topic_count=3,
        )
    )

    assert policy["recommendedAction"] == "switch_topic"
    assert policy["shouldSwitchTopic"] is True
    assert policy["requiresHumanReview"] is True
    assert "topic_lock_guardrail" in policy["triggerRules"]
    assert "repeat_guard" in policy["triggerRules"]


def test_policy_is_json_serializable_shape() -> None:
    policy = apply_agent_policy(_state(agent_mode="bad-mode", weak_streak=0))

    assert policy == {
        "recommendedAction": "deep_follow_up",
        "difficulty": "medium",
        "shouldExplainBeforeAsk": False,
        "shouldSwitchTopic": False,
        "shouldAskUserChoice": False,
        "requiresHumanReview": False,
        "policyReasons": ["回答不算完全不会，默认继续中等难度追问。"],
        "triggerRules": ["normal_follow_up"],
    }
