import pytest

from backend_python.embedding_client import build_embedding_payload, extract_embedding, mask_secret


def test_build_embedding_payload_uses_single_text_input() -> None:
    payload = build_embedding_payload("text-embedding-v4", "RAG 检索测试")

    assert payload == {
        "model": "text-embedding-v4",
        "input": ["RAG 检索测试"],
    }


def test_extract_embedding_from_compatible_response() -> None:
    data = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    assert extract_embedding(data) == [0.1, 0.2, 0.3]


def test_extract_embedding_rejects_empty_response() -> None:
    with pytest.raises(ValueError, match="embedding"):
        extract_embedding({"data": []})


def test_mask_secret_does_not_leak_key() -> None:
    key = "sk-1234567890abcdef"

    masked = mask_secret(key)

    assert key not in masked
    assert masked.startswith("sk-1")
    assert masked.endswith("cdef")
