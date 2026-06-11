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
