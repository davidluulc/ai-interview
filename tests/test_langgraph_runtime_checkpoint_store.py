from backend_python.langgraph_agent.checkpoint_store import (
    InMemoryCheckpointSummaryStore,
    build_checkpoint_summary,
)


def test_checkpoint_summary_store_saves_and_reads_latest_summary() -> None:
    store = InMemoryCheckpointSummaryStore()
    summary = build_checkpoint_summary(
        thread_id="thread-a",
        state={
            "nodeTrace": [{"node": "observe_state"}, {"node": "human_review"}],
            "decision": {"nextAction": "lower_difficulty"},
            "policy": {"requiresHumanReview": True, "triggerRules": ["weak_answer_streak"]},
            "runtime": "langgraph",
            "currentNode": "human_review",
        },
    )

    store.save_summary(summary)

    loaded = store.get_summary("thread-a")
    assert loaded["exists"] is True
    assert loaded["threadId"] == "thread-a"
    assert loaded["runtime"] == "langgraph"
    assert loaded["currentNode"] == "human_review"
    assert loaded["lastAction"] == "lower_difficulty"
    assert loaded["requiresHumanReview"] is True
    assert loaded["nodeTraceCount"] == 2
    assert loaded["policyTriggerRules"] == ["weak_answer_streak"]


def test_checkpoint_summary_store_marks_interrupted_and_resumed() -> None:
    store = InMemoryCheckpointSummaryStore()
    summary = build_checkpoint_summary(
        thread_id="thread-b",
        state={"nodeTrace": [], "runtime": "langgraph"},
    )
    store.save_summary(summary)

    store.mark_interrupted(
        "thread-b",
        interrupt={
            "reason": "需要人工选择下一步",
            "options": ["continue_interview", "switch_to_coach"],
        },
    )
    interrupted = store.get_summary("thread-b")
    assert interrupted["status"] == "interrupted"
    assert interrupted["interrupt"]["reason"] == "需要人工选择下一步"

    store.mark_resumed("thread-b", resume_decision="switch_to_coach")
    resumed = store.get_summary("thread-b")
    assert resumed["status"] == "resumed"
    assert resumed["resumeDecision"] == "switch_to_coach"
    assert resumed["interrupt"] is None


def test_checkpoint_summary_store_returns_empty_summary_for_missing_thread() -> None:
    store = InMemoryCheckpointSummaryStore()

    summary = store.get_summary("missing-thread")

    assert summary["exists"] is False
    assert summary["threadId"] == "missing-thread"
    assert summary["runtime"] == ""
    assert summary["status"] == "missing"
    assert summary["requiresHumanReview"] is False
