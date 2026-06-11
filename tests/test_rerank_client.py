import asyncio

import pytest
from fastapi import HTTPException

from backend_python.config import DASHSCOPE_RERANK_MODEL
from backend_python.rerank_client import build_rerank_payload, extract_rerank_results, mask_secret, rerank_documents


def test_default_rerank_model_is_qwen3_rerank() -> None:
    assert DASHSCOPE_RERANK_MODEL == "qwen3-rerank"


def test_build_rerank_payload_uses_qwen3_flat_request_shape() -> None:
    payload = build_rerank_payload(
        model_name="qwen3-rerank",
        query="什么是 RAG 重排？",
        documents=["文档 A", "文档 B"],
        top_n=2,
        instruct="根据 query 判断文档相关性。",
    )

    assert payload == {
        "model": "qwen3-rerank",
        "query": "什么是 RAG 重排？",
        "documents": ["文档 A", "文档 B"],
        "top_n": 2,
        "instruct": "根据 query 判断文档相关性。",
    }
    assert "input" not in payload
    assert "parameters" not in payload


def test_extract_rerank_results_reads_top_level_results() -> None:
    data = {
        "results": [
            {"index": 1, "relevance_score": 0.92},
            {"index": 0, "relevance_score": 0.71},
        ]
    }

    assert extract_rerank_results(data) == [
        {"index": 1, "relevance_score": 0.92},
        {"index": 0, "relevance_score": 0.71},
    ]


def test_extract_rerank_results_rejects_missing_results() -> None:
    with pytest.raises(ValueError, match="Rerank response has no results"):
        extract_rerank_results({})


def test_extract_rerank_results_rejects_invalid_item() -> None:
    with pytest.raises(ValueError, match="Rerank result item is invalid"):
        extract_rerank_results({"results": [{"index": "bad"}]})


def test_mask_secret_hides_api_key() -> None:
    assert mask_secret("sk-1234567890abcdef").startswith("sk-1")
    assert "4567890abc" not in mask_secret("sk-1234567890abcdef")


def test_rerank_documents_returns_empty_for_empty_documents() -> None:
    assert asyncio.run(rerank_documents(query="RAG", documents=[], top_n=3)) == []


def test_rerank_documents_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.rerank_client.DASHSCOPE_API_KEY", "")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(rerank_documents(query="RAG", documents=["doc"], top_n=1))

    assert exc_info.value.status_code == 500
