import pytest

from scripts.check_dashscope_models import (
    ModelCheck,
    build_chat_payload,
    build_embedding_payload,
    build_rerank_payload,
    mask_secret,
    summarize_checks,
)


def test_builds_expected_payloads() -> None:
    assert build_chat_payload("qwen-plus")["model"] == "qwen-plus"
    assert build_chat_payload("qwen-plus")["messages"][0]["role"] == "user"

    embedding_payload = build_embedding_payload("text-embedding-v4")
    assert embedding_payload == {"model": "text-embedding-v4", "input": ["RAG 检索测试"]}

    rerank_payload = build_rerank_payload("qwen3-rerank")
    assert rerank_payload["model"] == "qwen3-rerank"
    assert rerank_payload["input"]["query"] == "RAG 检索测试"
    assert len(rerank_payload["input"]["documents"]) == 2
    assert rerank_payload["parameters"]["top_n"] == 2


def test_masks_api_key_in_summary() -> None:
    secret = "sk-1234567890abcdef"
    checks = [
        ModelCheck(name="chat", model="qwen-plus", ok=True, detail=f"ok {secret}"),
        ModelCheck(name="embedding", model="text-embedding-v4", ok=False, detail=f"failed {secret}"),
    ]

    summary = summarize_checks(checks, api_key=secret)

    assert secret not in summary
    assert mask_secret(secret) in summary
    assert "chat" in summary
    assert "embedding" in summary


@pytest.mark.parametrize(
    ("value", "prefix", "suffix"),
    [
        ("", "", ""),
        ("abcd", "", ""),
        ("sk-1234567890abcdef", "sk-1", "cdef"),
    ],
)
def test_mask_secret(value: str, prefix: str, suffix: str) -> None:
    masked = mask_secret(value)
    if not value:
        assert masked == ""
        return
    if len(value) <= 8:
        assert masked == "****"
        return
    assert value not in masked
    assert masked.startswith(prefix)
    assert masked.endswith(suffix)
