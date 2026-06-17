from backend_python.langgraph_agent.replay import build_runtime_replay


def test_replay_returns_empty_state_for_missing_checkpoint() -> None:
    replay = build_runtime_replay({"exists": False, "threadId": "missing-thread"})

    assert replay["exists"] is False
    assert replay["threadId"] == "missing-thread"
    assert replay["timeline"] == []
    assert replay["risks"] == []
    assert replay["nextActions"] == []
    assert replay["summary"] == "未找到 LangGraph 运行记录。"


def test_replay_builds_timeline_for_interrupted_human_review() -> None:
    replay = build_runtime_replay(
        {
            "exists": True,
            "threadId": "thread-a",
            "status": "interrupted",
            "currentNode": "human_review",
            "nodeTrace": [{"node": "observe_state"}, {"node": "human_review"}],
            "interrupt": {
                "reason": "连续弱回答，需要人工选择下一步。",
                "options": ["switch_to_coach", "continue_interview"],
            },
            "requiresHumanReview": True,
        }
    )

    assert replay["exists"] is True
    assert replay["status"] == "interrupted"
    assert replay["summary"] == "本轮 LangGraph 在 human_review 节点暂停：连续弱回答，需要人工选择下一步。"
    assert replay["timeline"][0]["node"] == "observe_state"
    assert replay["timeline"][1]["node"] == "human_review"
    assert "requires_human_review" in replay["risks"]
    assert replay["nextActions"] == ["resume", "fallback_classic"]
    assert replay["nodeValidation"]["valid"] is True


def test_replay_marks_fallback_and_quality_gate_risks() -> None:
    replay = build_runtime_replay(
        {
            "exists": True,
            "threadId": "thread-b",
            "status": "completed",
            "currentNode": "generate_question",
            "nodeTrace": [{"node": "generate_question"}, {"node": "unknown_node"}],
            "runtimeAudit": {
                "fallbackUsed": True,
                "qualityGateReasons": ["问题与最近问题重复"],
            },
            "qualityGate": {
                "passed": False,
                "reasons": ["缺少 checkpoint"],
            },
        }
    )

    assert replay["summary"] == "本轮 LangGraph 已回退到 classic Agent，可查看质量门禁原因。"
    assert "fallback_used" in replay["risks"]
    assert "问题与最近问题重复" in replay["risks"]
    assert "缺少 checkpoint" in replay["risks"]
    assert replay["nextActions"] == ["inspect_quality_gate", "fallback_classic"]
    assert replay["nodeValidation"]["valid"] is False
    assert replay["nodeValidation"]["unknownNodes"] == ["unknown_node"]
