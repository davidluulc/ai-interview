import pytest

from backend_python.embedding_client import (
    build_embedding_payload,
    build_embedding_url,
    extract_embedding,
    mask_secret,
    resolve_embedding_settings,
)


def test_build_embedding_payload_uses_single_text_input() -> None:
    payload = build_embedding_payload("text-embedding-v4", "RAG 检索测试")

    assert payload == {
        "model": "text-embedding-v4",
        "input": ["RAG 检索测试"],
    }


def test_build_embedding_payload_includes_zhipu_dimensions_when_configured() -> None:
    payload = build_embedding_payload("embedding-3", "RAG search", dimensions=1024)

    assert payload == {
        "model": "embedding-3",
        "input": ["RAG search"],
        "dimensions": 1024,
    }


def test_resolve_embedding_settings_supports_zhipu_provider() -> None:
    settings = resolve_embedding_settings(
        {
            "EMBEDDING_PROVIDER": "zhipu",
            "EMBEDDING_API_KEY": "zhipu-secret",
            "EMBEDDING_MODEL": "embedding-3",
            "EMBEDDING_DIMENSIONS": "1024",
        }
    )

    assert settings.provider == "zhipu"
    assert settings.api_key == "zhipu-secret"
    assert settings.model == "embedding-3"
    assert settings.dimensions == 1024
    assert settings.url == "https://open.bigmodel.cn/api/paas/v4/embeddings"


def test_build_embedding_url_appends_embeddings_for_openai_compatible_base_url() -> None:
    assert build_embedding_url("http://freellmapi:3001/v1") == "http://freellmapi:3001/v1/embeddings"


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
