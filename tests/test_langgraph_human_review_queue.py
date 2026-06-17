import pytest

from backend_python.langgraph_agent.review_queue import build_review_queue, validate_review_decision


def test_review_queue_includes_interrupted_checkpoints() -> None:
    queue = build_review_queue(
        [
            {
                "threadId": "thread-a",
                "status": "interrupted",
                "currentNode": "human_review",
                "interrupt": {"reason": "连续弱回答", "options": ["switch_to_coach"]},
                "lastQuestion": "请解释 checkpoint。",
                "createdAt": "2026-06-17T10:00:00",
            }
        ]
    )

    assert len(queue) == 1
    assert queue[0]["threadId"] == "thread-a"
    assert queue[0]["reason"] == "连续弱回答"
    assert queue[0]["options"] == ["switch_to_coach"]
    assert queue[0]["lastQuestion"] == "请解释 checkpoint。"


def test_review_queue_includes_requires_human_review_checkpoints() -> None:
    queue = build_review_queue(
        [
            {
                "threadId": "thread-b",
                "status": "completed",
                "currentNode": "apply_policy",
                "requiresHumanReview": True,
                "interrupt": {},
            }
        ]
    )

    assert len(queue) == 1
    assert queue[0]["threadId"] == "thread-b"
    assert queue[0]["reason"] == "Agent policy 标记需要人工复核。"
    assert "continue_interview" in queue[0]["options"]


def test_review_queue_excludes_completed_checkpoints_without_review_need() -> None:
    queue = build_review_queue(
        [
            {
                "threadId": "thread-c",
                "status": "completed",
                "requiresHumanReview": False,
            }
        ]
    )

    assert queue == []


def test_validate_review_decision_allows_only_supported_decisions() -> None:
    assert validate_review_decision(" switch_to_coach ") == "switch_to_coach"

    with pytest.raises(ValueError, match="Unsupported human review decision"):
        validate_review_decision("delete_everything")
