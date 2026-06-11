from backend_python.weakness_training_templates import (
    CORE_WEAK_TAGS,
    get_training_template,
    select_training_template_hint,
)


def test_core_templates_cover_required_weak_tags() -> None:
    assert CORE_WEAK_TAGS == [
        "rag_quality",
        "rag_retrieval",
        "agent_state",
        "backend_fastapi",
        "database_modeling",
        "project_storytelling",
    ]
    for weak_tag in CORE_WEAK_TAGS:
        template = get_training_template(weak_tag)
        assert template["weakTag"] == weak_tag
        assert template["label"]
        assert len(template["coachQuestions"]) >= 2
        assert len(template["interviewQuestions"]) >= 2
        assert set(template["difficultyLadder"]) >= {"basic", "medium", "hard"}
        assert template["answerKeyPoints"]
        assert template["commonMistakes"]
        assert template["oneMinuteTemplate"]


def test_unknown_weak_tag_returns_generic_template() -> None:
    template = get_training_template("unknown_tag")

    assert template["weakTag"] == "communication_expression"
    assert template["fallbackUsed"] is True
    assert "表达" in template["label"]


def test_select_training_template_hint_prefers_coach_basic_question() -> None:
    hint = select_training_template_hint(
        weakness_strategy={
            "enabled": True,
            "primaryWeakTag": "rag_quality",
            "primaryWeakLabel": "RAG 质量评估",
        },
        agent_mode="coach",
        difficulty="basic",
    )

    assert hint["enabled"] is True
    assert hint["weakTag"] == "rag_quality"
    assert hint["mode"] == "coach"
    assert hint["difficulty"] == "basic"
    assert "Hit@K" in hint["recommendedQuestion"]
    assert any("MRR" in point for point in hint["answerKeyPoints"])
    assert hint["fallbackUsed"] is False


def test_select_training_template_hint_prefers_interview_question() -> None:
    hint = select_training_template_hint(
        weakness_strategy={
            "enabled": True,
            "primaryWeakTag": "agent_state",
            "primaryWeakLabel": "Agent State",
        },
        agent_mode="interview",
        difficulty="medium",
    )

    assert hint["enabled"] is True
    assert hint["weakTag"] == "agent_state"
    assert hint["mode"] == "interview"
    assert "Agent State" in hint["recommendedQuestion"]
    assert any("ToolCalls" in point or "Agent Decision" in point for point in hint["answerKeyPoints"])


def test_select_training_template_hint_returns_disabled_without_strategy() -> None:
    hint = select_training_template_hint(
        weakness_strategy={"enabled": False},
        agent_mode="coach",
        difficulty="basic",
    )

    assert hint["enabled"] is False
    assert hint["weakTag"] == ""
    assert hint["recommendedQuestion"] == ""
