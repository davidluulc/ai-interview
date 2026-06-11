from backend_python.weakness_strategy import select_weakness_strategy


def test_select_weakness_strategy_returns_disabled_without_history() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": False, "frequentWeakTags": []},
        agent_mode="coach",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="技术追问",
        history=[],
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        answer_analysis={},
    )

    assert strategy["enabled"] is False
    assert strategy["matchedWeakTags"] == []
    assert strategy["primaryWeakTag"] == ""
    assert strategy["modePolicy"] == "none"


def test_select_weakness_strategy_prefers_related_tag_in_coach_mode() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["agent_state", "rag_quality"]},
        agent_mode="coach",
        profile={"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
        next_stage="技术追问",
        history=[{"question": "RAG 质量怎么评估？", "answer": "不知道", "focus": "RAG 质量评估"}],
        role_hits=[{"title": "RAG 质量评估与可观测面板", "content": "Hit@K、MRR、关键词覆盖率"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={"weakAnswerStreak": 1, "topicLock": {"locked": False}},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["modePolicy"] == "coach_remediation"
    assert strategy["recommendedDifficulty"] == "basic"
    assert strategy["recommendedAction"] == "practice_weakness"
    assert "rag_quality" in strategy["matchedWeakTags"]
    assert "学习辅导模式" in strategy["reason"]


def test_select_weakness_strategy_uses_interview_probe_policy() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["agent_state"]},
        agent_mode="interview",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="项目深挖",
        history=[],
        role_hits=[{"title": "Agent State 与 ToolCalls", "content": "Agent State 决策"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "agent_state"
    assert strategy["modePolicy"] == "interview_probe"
    assert strategy["recommendedDifficulty"] == "medium"
    assert strategy["recommendedAction"] == "deep_follow_up"
    assert "真实面试模式" in strategy["reason"]


def test_select_weakness_strategy_avoids_deadlock_after_repeated_weak_tag() -> None:
    strategy = select_weakness_strategy(
        candidate_profile={"hasHistory": True, "frequentWeakTags": ["rag_quality"]},
        agent_mode="interview",
        profile={"targetRole": "AI 应用开发实习生"},
        next_stage="技术追问",
        history=[
            {"question": "Hit@K 是什么？", "answer": "不知道", "focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
            {"question": "MRR 是什么？", "answer": "不会", "focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
        ],
        role_hits=[{"title": "RAG 质量评估", "content": "Hit@K MRR 关键词覆盖率"}],
        question_hits=[],
        memory_hits=[],
        answer_analysis={"weakAnswerStreak": 2, "topicLock": {"locked": True, "topic": "RAG 质量评估"}},
    )

    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["guardrailApplied"] is True
    assert strategy["modePolicy"] == "avoid_weakness_deadlock"
    assert strategy["recommendedAction"] == "switch_topic"
    assert "weakness_deadlock_guardrail" in strategy["triggerRules"]
