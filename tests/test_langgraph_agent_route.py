from fastapi.testclient import TestClient

from backend_python.main import app
from backend_python.routes import langgraph_agent


client = TestClient(app)


def test_langgraph_agent_poc_route_returns_graph_result():
    response = client.post(
        "/api/langgraph-agent/next-question-poc",
        json={
            "profile": {"candidateName": "David", "targetRole": "AI 应用开发实习生"},
            "history": [{"question": "讲讲 RAG。", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["nextAction"] == "lower_difficulty"
    assert payload["nextQuestion"]["prompt"]
    assert payload["memoryUpdate"]["status"] == "deferred"
    assert payload["graphState"]["agentMode"] == "coach"
    assert [item["nodeName"] for item in payload["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "apply_policy",
        "select_action",
        "generate_question",
        "update_memory",
    ]
    assert payload["graphState"]["policy"]["recommendedAction"] == "lower_difficulty"


def test_existing_next_question_route_still_exists():
    response = client.post(
        "/api/interview/next-question",
        json={
            "profile": {"candidateName": "David", "targetRole": "AI 应用开发实习生"},
            "history": [],
            "nextStage": "自我介绍",
            "agentMode": "coach",
        },
    )

    assert response.status_code in {200, 401, 500}
    assert response.status_code != 404


def test_langgraph_agent_v2_route_returns_thread_and_checkpoint():
    response = client.post(
        "/api/langgraph-agent/next-question-v2",
        json={
            "threadId": "route-thread-001",
            "profile": {"targetRole": "AI 应用开发实习生"},
            "history": [{"question": "讲讲 RAG。", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "useRealRag": False,
            "useRealDecision": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threadId"] == "route-thread-001"
    assert payload["checkpointSummary"]["exists"] is True
    assert payload["decision"]["nextAction"]
    assert payload["nextQuestion"]["prompt"]


def test_langgraph_checkpoint_route_returns_summary():
    client.post(
        "/api/langgraph-agent/next-question-v2",
        json={
            "threadId": "route-thread-002",
            "profile": {},
            "history": [],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "useRealRag": False,
            "useRealDecision": False,
        },
    )

    response = client.get("/api/langgraph-agent/checkpoint/route-thread-002")

    assert response.status_code == 200
    payload = response.json()
    assert payload["exists"] is True
    assert payload["threadId"] == "route-thread-002"


def test_langgraph_agent_v2_route_can_select_real_adapters(monkeypatch):
    called = {"rag": False, "decision": False}

    def fake_real_retrieve(profile, next_stage):
        called["rag"] = True
        return {
            "roleHits": [{"id": "real-role"}],
            "questionHits": [],
            "memoryHits": [],
            "toolCalls": [{"toolName": "retrieve_role_knowledge", "success": True}],
            "retrievalQuality": {
                "roleKnowledge": {"hitCount": 1},
                "questionBank": {"hitCount": 0},
                "candidateMemory": {"hitCount": 0},
            },
        }

    async def fake_real_decide(**kwargs):
        called["decision"] = True
        return {
            "decision": {
                "nextAction": "deep_follow_up",
                "stage": "技术追问",
                "difficulty": "medium",
                "focus": "真实 adapter 分支",
                "reason": "测试 true 分支会选择真实 adapter。",
                "tools": ["retrieve_context"],
                "fallbackUsed": False,
                "decisionSummary": "真实 adapter 分支已调用。",
            },
            "agentState": {"answerStatus": "完整"},
        }

    monkeypatch.setattr(langgraph_agent, "_real_retrieve_context", fake_real_retrieve)
    monkeypatch.setattr(langgraph_agent, "_real_decide_action", fake_real_decide)

    response = client.post(
        "/api/langgraph-agent/next-question-v2",
        json={
            "threadId": "route-thread-real-001",
            "profile": {"targetRole": "AI 应用开发实习生"},
            "history": [{"question": "讲讲 checkpoint。", "answer": "它保存 graph state。"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "useRealRag": True,
            "useRealDecision": True,
        },
    )

    assert response.status_code == 200
    assert called == {"rag": True, "decision": True}
    assert response.json()["decision"]["focus"] == "真实 adapter 分支"


def test_langgraph_runtime_replay_and_report_routes():
    thread_id = "route-runtime-v6-001"
    run_response = client.post(
        "/api/langgraph-agent/runtime/run",
        json={
            "threadId": thread_id,
            "agentRuntime": "langgraph",
            "agentMode": "coach",
            "history": [
                {"question": "什么是 checkpoint？", "answer": "不会"},
                {"question": "thread_id 有什么用？", "answer": "不知道"},
            ],
            "answer": "还是不会",
            "enableInterrupt": True,
        },
    )
    assert run_response.status_code == 200
    assert run_response.json()["status"] == "interrupted"

    replay_response = client.get(f"/api/langgraph-agent/runtime/replay/{thread_id}")
    assert replay_response.status_code == 200
    replay = replay_response.json()
    assert replay["threadId"] == thread_id
    assert replay["status"] == "interrupted"
    assert replay["timeline"]
    assert "requires_human_review" in replay["risks"]
    assert replay["nextActions"] == ["resume", "fallback_classic"]

    report_response = client.get(f"/api/langgraph-agent/runtime/report/{thread_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["threadId"] == thread_id
    assert report["totalRuns"] >= 1
    assert report["humanReviewCount"] >= 1


def test_langgraph_runtime_reviews_and_resolve_routes():
    thread_id = "route-runtime-review-v6-001"
    client.post(
        "/api/langgraph-agent/runtime/run",
        json={
            "threadId": thread_id,
            "agentRuntime": "langgraph",
            "history": [
                {"question": "什么是 Agent State？", "answer": "不会"},
                {"question": "为什么要 checkpoint？", "answer": "不知道"},
            ],
            "answer": "不会",
            "enableInterrupt": True,
        },
    )

    reviews_response = client.get("/api/langgraph-agent/runtime/reviews")
    assert reviews_response.status_code == 200
    reviews = reviews_response.json()["items"]
    assert any(item["threadId"] == thread_id for item in reviews)

    resolve_response = client.post(
        f"/api/langgraph-agent/runtime/reviews/{thread_id}/resolve",
        json={"decision": "switch_to_coach", "comment": "先切换到学习辅导。"},
    )
    assert resolve_response.status_code == 200
    payload = resolve_response.json()
    assert payload["threadId"] == thread_id
    assert payload["status"] == "resumed"
    assert payload["resumeDecision"] == "switch_to_coach"

    reviews_after_resolve = client.get("/api/langgraph-agent/runtime/reviews").json()["items"]
    assert not any(item["threadId"] == thread_id for item in reviews_after_resolve)
