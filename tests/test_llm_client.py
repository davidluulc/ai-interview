import pytest

from backend_python.llm_client import build_chat_payload, extract_json, usage_summary


def test_extract_json_from_plain_json() -> None:
    result = extract_json('{"score": 88}')

    assert result == {"score": 88}


def test_extract_json_from_markdown_block() -> None:
    result = extract_json('```json\n{"prompt":"请介绍项目"}\n```')

    assert result == {"prompt": "请介绍项目"}


def test_extract_json_rejects_invalid_text() -> None:
    with pytest.raises(ValueError):
        extract_json("这不是 JSON")


def test_build_chat_payload_uses_json_object_response_format() -> None:
    payload = build_chat_payload(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.2,
        model_name="qwen-plus",
    )

    assert payload["model"] == "qwen-plus"
    assert payload["temperature"] == 0.2
    assert payload["response_format"] == {"type": "json_object"}


def test_usage_summary_defaults_missing_values_to_zero() -> None:
    result = usage_summary({"usage": {"prompt_tokens": 3, "total_tokens": 5}})

    assert result == {
        "prompt_tokens": 3,
        "completion_tokens": 0,
        "total_tokens": 5,
    }
