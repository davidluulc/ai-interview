from backend_python.training_tags import infer_weak_tags


def test_infer_weak_tags_maps_common_ai_interview_topics() -> None:
    tags = infer_weak_tags(
        focus="RAG 召回链路",
        text="候选人说不清 Hit@K、MRR、关键词覆盖率和知识库命中日志。",
    )

    assert "rag_retrieval" in tags
    assert "rag_quality" in tags


def test_infer_weak_tags_maps_backend_and_agent_topics() -> None:
    tags = infer_weak_tags(
        focus="后端模块设计",
        text="FastAPI router、schema、SQLAlchemy model 职责不清楚，也没讲清 Agent State。",
    )

    assert "backend_fastapi" in tags
    assert "database_modeling" in tags
    assert "agent_state" in tags


def test_infer_weak_tags_returns_general_expression_when_no_specific_match() -> None:
    assert infer_weak_tags(focus="综合表达", text="回答比较短") == ["communication_expression"]
