import asyncio

from backend_python.langgraph_agent.graph import run_interview_graph_v2


def test_run_interview_graph_v2_returns_checkpoint_summary():
    async def fake_decide(**kwargs):
        return {
            "decision": {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 基础",
                "reason": "候选人答不上来，先降低难度。",
                "tools": ["retrieve_context", "analyze_answer"],
                "fallbackUsed": False,
                "decisionSummary": "学习辅导模式：lower_difficulty。候选人答不上来，先降低难度。",
            },
            "agentState": {"answerStatus": "不会"},
        }

    def fake_retrieve(profile, next_stage):
        return {
            "roleHits": [{"id": "role-1", "content": "RAG"}],
            "questionHits": [],
            "memoryHits": [],
            "toolCalls": [{"toolName": "retrieve_role_knowledge", "success": True}],
            "retrievalQuality": {
                "roleKnowledge": {"hitCount": 1},
                "questionBank": {"hitCount": 0},
                "candidateMemory": {"hitCount": 0},
            },
        }

    result = asyncio.run(
        run_interview_graph_v2(
            thread_id="thread-v2-001",
            profile={"targetRole": "AI 应用开发实习生"},
            history=[
                {"question": "讲讲 RAG。", "answer": "不知道"},
                {"question": "那先说检索是什么？", "answer": "不会"},
            ],
            next_stage="技术追问",
            agent_mode="coach",
            draft_question={
                "stage": "技术追问",
                "stability": "动态追问",
                "focus": "RAG 真实追问",
                "prompt": "请结合你的项目说明 RAG 命中日志怎么定位召回质量问题。",
            },
            retrieve_context_fn=fake_retrieve,
            decide_action_fn=fake_decide,
        )
    )

    assert result["threadId"] == "thread-v2-001"
    assert result["checkpointSummary"]["exists"] is True
    assert result["decision"]["nextAction"] == "lower_difficulty"
    assert result["policy"]["recommendedAction"] == "lower_difficulty"
    assert result["decision"]["policy"]["shouldExplainBeforeAsk"] is True
    assert result["checkpointSummary"]["policyRecommendedAction"] == "lower_difficulty"
    assert result["nextQuestion"]["prompt"] == "请结合你的项目说明 RAG 命中日志怎么定位召回质量问题。"
    assert result["nextQuestion"]["focus"] == "RAG 真实追问"
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "apply_policy",
        "select_action",
        "generate_question",
        "update_memory",
    ]
