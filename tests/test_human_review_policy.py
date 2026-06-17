from backend_python.human_review_policy import evaluate_human_review


def test_requires_human_review_when_agent_policy_requests_it() -> None:
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": True, "recommendedAction": "lower_difficulty"},
        answer_analysis={"weakAnswerStreak": 1},
        history=[],
    )

    assert result["shouldInterrupt"] is True
    assert result["reason"]
    assert "continue_interview" in result["options"]
    assert "policy_requires_human_review" in result["triggerRules"]


def test_requires_human_review_after_three_weak_answers() -> None:
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": False},
        answer_analysis={"weakAnswerStreak": 3},
        history=[{"answer": "不会"}, {"answer": "不知道"}, {"answer": "还是不会"}],
    )

    assert result["shouldInterrupt"] is True
    assert "switch_to_coach" in result["options"]
    assert "weak_answer_streak" in result["triggerRules"]


def test_does_not_interrupt_normal_answer_flow() -> None:
    result = evaluate_human_review(
        agent_policy={"requiresHumanReview": False, "recommendedAction": "deep_follow_up"},
        answer_analysis={"weakAnswerStreak": 0},
        history=[{"answer": "我会从 checkpoint 和 thread_id 两层解释"}],
    )

    assert result["shouldInterrupt"] is False
    assert result["reason"] == ""
    assert result["options"] == []
    assert result["triggerRules"] == []
