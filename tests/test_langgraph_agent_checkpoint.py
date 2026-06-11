from backend_python.langgraph_agent.checkpoint import (
    build_graph_config,
    record_checkpoint_summary,
    summarize_checkpoint,
)


def test_build_graph_config_uses_thread_id():
    config = build_graph_config("interview-demo-001")

    assert config == {"configurable": {"thread_id": "interview-demo-001"}}


def test_checkpoint_summary_is_recorded_by_thread_id():
    record_checkpoint_summary(
        thread_id="interview-demo-001",
        state={
            "roundCount": 2,
            "decision": {"nextAction": "lower_difficulty"},
            "policy": {
                "recommendedAction": "switch_topic",
                "shouldAskUserChoice": True,
                "requiresHumanReview": True,
                "policyReasons": ["连续弱回答，建议用户选择继续面试或先学习。"],
                "triggerRules": ["weak_answer_streak", "human_review_precheck"],
            },
            "nextQuestion": {"prompt": "你能先解释 RAG 的基本流程吗？"},
            "nodeTrace": [{"nodeName": "observe_state"}, {"nodeName": "select_action"}],
        },
    )

    summary = summarize_checkpoint("interview-demo-001")

    assert summary["exists"] is True
    assert summary["threadId"] == "interview-demo-001"
    assert summary["roundCount"] == 2
    assert summary["lastAction"] == "lower_difficulty"
    assert summary["lastQuestion"] == "你能先解释 RAG 的基本流程吗？"
    assert summary["nodeTraceCount"] == 2
    assert summary["policyRecommendedAction"] == "switch_topic"
    assert summary["shouldAskUserChoice"] is True
    assert summary["requiresHumanReview"] is True
    assert summary["policyReasons"] == ["连续弱回答，建议用户选择继续面试或先学习。"]
    assert summary["policyTriggerRules"] == ["weak_answer_streak", "human_review_precheck"]


def test_missing_checkpoint_summary_returns_exists_false():
    summary = summarize_checkpoint("missing-thread")

    assert summary["exists"] is False
    assert summary["threadId"] == "missing-thread"
    assert summary["policyRecommendedAction"] == ""
    assert summary["shouldAskUserChoice"] is False
    assert summary["requiresHumanReview"] is False
