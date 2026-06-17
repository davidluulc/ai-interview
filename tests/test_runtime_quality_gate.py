from backend_python.runtime_quality_gate import evaluate_runtime_quality


def test_quality_gate_passes_safe_langgraph_output() -> None:
    result = {
        "status": "completed",
        "nextQuestion": {"content": "请解释 LangGraph checkpoint 的作用。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True, "threadId": "runtime-a"},
    }

    gate = evaluate_runtime_quality(result, recent_questions=["什么是 RAG？"])

    assert gate["passed"] is True
    assert gate["fallbackToClassic"] is False
    assert gate["riskLevel"] == "low"
    assert gate["checks"]["nonEmptyQuestion"] is True
    assert gate["checks"]["validDecision"] is True
    assert gate["checks"]["validDifficulty"] is True
    assert gate["checks"]["notRepeated"] is True
    assert gate["checks"]["checkpointAvailable"] is True
    assert gate["checks"]["humanReviewBlocked"] is False


def test_quality_gate_blocks_empty_question() -> None:
    result = {
        "status": "completed",
        "nextQuestion": {"content": "   "},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["fallbackToClassic"] is True
    assert gate["riskLevel"] == "high"
    assert gate["checks"]["nonEmptyQuestion"] is False
    assert "LangGraph 没有生成可展示的问题" in gate["reasons"]


def test_quality_gate_blocks_invalid_action_and_difficulty() -> None:
    result = {
        "question": {"content": "请继续说明项目。"},
        "decision": {"nextAction": "random_action", "difficulty": "impossible"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["checks"]["validDecision"] is False
    assert gate["checks"]["validDifficulty"] is False
    assert "LangGraph 决策动作不合法：random_action" in gate["reasons"]
    assert "LangGraph 难度等级不合法：impossible" in gate["reasons"]


def test_quality_gate_blocks_repeated_question() -> None:
    result = {
        "nextQuestion": {"content": "请解释 Agent State 的作用。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        "checkpointSummary": {"exists": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=["请解释 Agent State 的作用。"])

    assert gate["passed"] is False
    assert gate["checks"]["notRepeated"] is False
    assert "LangGraph 问题与最近问题重复度过高" in gate["reasons"]


def test_quality_gate_blocks_human_review_required() -> None:
    result = {
        "nextQuestion": {"content": "请继续回答。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        "checkpointSummary": {"exists": True, "requiresHumanReview": True},
    }

    gate = evaluate_runtime_quality(result, recent_questions=[])

    assert gate["passed"] is False
    assert gate["checks"]["humanReviewBlocked"] is True
    assert "LangGraph 标记需要人工复核" in gate["reasons"]
