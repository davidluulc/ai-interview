import json

from backend_python.rag_metadata import normalize_rag_hit, normalize_rag_hit_metadata, metadata_matches


def test_normalize_rag_hit_metadata_prefers_camel_case_and_existing_metadata():
    metadata = normalize_rag_hit_metadata(
        {
            "metadata": {"position_tag": "ai_app_intern", "interview_stage": "技术追问", "tags": ["RAG"]},
            "knowledgeBase": "role_knowledge",
            "documentId": 12,
            "chunkId": 81,
            "source": "database",
        },
        retriever_name="role_knowledge",
    )

    json.dumps(metadata, ensure_ascii=False)
    assert metadata["knowledgeBase"] == "role_knowledge"
    assert metadata["positionTag"] == "ai_app_intern"
    assert metadata["interviewStage"] == "技术追问"
    assert metadata["tags"] == ["RAG"]
    assert metadata["documentId"] == 12
    assert metadata["chunkId"] == 81
    assert metadata["source"] == "database"


def test_normalize_rag_hit_metadata_uses_defaults_for_missing_fields():
    metadata = normalize_rag_hit_metadata(
        {"question": "请解释 RAG 的基本流程。", "matchedTags": ["RAG", "检索"]},
        retriever_name="question_bank",
    )

    assert metadata["knowledgeBase"] == "question_bank"
    assert metadata["source"] == "seed_json"
    assert metadata["tags"] == ["RAG", "检索"]
    assert metadata["documentId"] is None
    assert metadata["chunkId"] is None


def test_normalize_rag_hit_keeps_score_title_tokens_and_metadata():
    hit = normalize_rag_hit(
        {
            "score": 0.91,
            "title": "RAG 召回链路",
            "matchedTokens": ["rag", "召回"],
            "metadata": {"positionTag": "ai_app_intern"},
        },
        retriever_name="role_knowledge",
    )

    assert hit["score"] == 0.91
    assert hit["title"] == "RAG 召回链路"
    assert hit["matchedTokens"] == ["rag", "召回"]
    assert hit["metadata"]["knowledgeBase"] == "role_knowledge"
    assert hit["metadata"]["positionTag"] == "ai_app_intern"


def test_normalize_rag_hit_uses_question_as_title_for_question_bank():
    hit = normalize_rag_hit(
        {
            "question": "FastAPI 的 Depends 是什么？",
            "position_tag": "python_backend",
            "difficulty": "basic",
        },
        retriever_name="question_bank",
    )

    assert hit["title"] == "FastAPI 的 Depends 是什么？"
    assert hit["metadata"]["positionTag"] == "python_backend"
    assert hit["metadata"]["difficulty"] == "basic"


def test_metadata_matches_checks_expected_filters():
    metadata = {
        "knowledgeBase": "question_bank",
        "positionTag": "ai_app_intern",
        "interviewStage": "技术追问",
    }

    assert metadata_matches(metadata, expected_knowledge_base="question_bank", expected_position_tag="ai_app_intern")
    assert not metadata_matches(metadata, expected_stage="项目背景")

