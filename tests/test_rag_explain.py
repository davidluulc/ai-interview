from backend_python.rag_explain import build_developer_rag_debug_summary, build_relevant_user_rag_reason, build_user_rag_reason


def test_build_user_rag_reason_uses_top_hit_and_matched_tokens():
    reason = build_user_rag_reason(
        retriever_name="role_knowledge",
        hits=[
            {
                "title": "RAG 召回链路追问",
                "score": 0.91,
                "matchedTokens": ["rag", "召回"],
                "metadata": {"interviewStage": "技术追问"},
            }
        ],
        focus="RAG 召回链路",
    )

    assert "RAG 召回链路" in reason
    assert "岗位知识库" in reason
    assert "RAG 召回链路追问" in reason
    assert "rag、召回" in reason


def test_build_user_rag_reason_handles_empty_recall():
    reason = build_user_rag_reason(retriever_name="candidate_memory", hits=[], focus="项目表达")

    assert "暂无候选人画像命中" in reason


def test_build_relevant_user_rag_reason_filters_unrelated_hits():
    reason = build_relevant_user_rag_reason(
        retriever_name="question_bank",
        hits=[
            {
                "title": "PostgreSQL、Redis、Celery 职责",
                "content": "本题讨论数据库、缓存和异步任务。",
                "matchedTokens": ["postgresql", "redis", "celery"],
            }
        ],
        focus="RAG 日志字段定位",
        prompt="在 RAG 命中日志中，你会查看哪个字段区分 BM25 还是向量召回？",
    )

    assert reason is None


def test_build_relevant_user_rag_reason_keeps_related_hits():
    reason = build_relevant_user_rag_reason(
        retriever_name="role_knowledge",
        hits=[
            {
                "title": "RAG 日志字段定位",
                "content": "matchedRetrievalModes 用于区分 BM25 与向量召回。",
                "matchedTokens": ["rag", "matchedRetrievalModes", "bm25", "vector"],
            }
        ],
        focus="RAG 日志字段定位",
        prompt="在 RAG 命中日志中，你会查看哪个字段区分 BM25 还是向量召回？",
    )

    assert reason is not None
    assert "RAG 日志字段定位" in reason
    assert "岗位知识库" in reason


def test_build_developer_rag_debug_summary_includes_metadata_and_prompt_usage():
    summary = build_developer_rag_debug_summary(
        query_text="AI 应用开发实习生 RAG 技术追问",
        retriever_name="question_bank",
        retrieval_mode="bm25",
        hits=[
            {
                "question": "请说明 RAG 的基本流程。",
                "score": 0.88,
                "matchedTags": ["RAG"],
                "metadata": {"positionTag": "ai_app_intern", "interviewStage": "技术追问"},
            }
        ],
        used_in_prompt=True,
    )

    assert summary["queryText"] == "AI 应用开发实习生 RAG 技术追问"
    assert summary["retrieverName"] == "question_bank"
    assert summary["retrievalMode"] == "bm25"
    assert summary["hitCount"] == 1
    assert summary["usedInPrompt"] is True
    assert summary["hits"][0]["score"] == 0.88
    assert summary["hits"][0]["metadata"]["positionTag"] == "ai_app_intern"
