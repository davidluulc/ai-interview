import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from backend_python import structured_output as so


class SampleModel(BaseModel):
    nextAction: str
    difficulty: str


def run(coro):
    return asyncio.run(coro)


def test_strict_schema_strips_title_and_forces_required():
    schema = so.strict_schema(SampleModel)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"nextAction", "difficulty"}
    assert "title" not in schema
    assert "title" not in schema["properties"]["nextAction"]


def test_build_json_schema_payload_shape():
    messages = [{"role": "user", "content": "hi"}]
    payload = so.build_json_schema_payload(
        messages=messages, schema_model=SampleModel, temperature=0.2, model_name="qwen-test"
    )
    fmt = payload["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "SampleModel"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["required"] == ["nextAction", "difficulty"]
    assert payload["model"] == "qwen-test"
    assert payload["messages"] == messages
    assert payload["temperature"] == 0.2


def test_build_tool_call_payload_shape():
    messages = [{"role": "user", "content": "hi"}]
    payload = so.build_tool_call_payload(
        messages=messages, schema_model=SampleModel, temperature=0.2, model_name="qwen-test"
    )
    tool = payload["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "SampleModel"
    assert "nextAction" in tool["function"]["parameters"]["properties"]
    assert payload["tool_choice"] == {"type": "function", "function": {"name": "SampleModel"}}


def _resp(content=None, tool_arguments=None):
    message: dict[str, Any] = {}
    if content is not None:
        message["content"] = content
    if tool_arguments is not None:
        message["tool_calls"] = [
            {"function": {"name": "SampleModel", "arguments": tool_arguments}}
        ]
    return {"choices": [{"message": message}]}


def test_message_content_extracts_text():
    assert so.message_content(_resp(content='{"a": 1}')) == '{"a": 1}'
    assert so.message_content({"choices": []}) == ""


def test_parse_tool_arguments_decodes_json_string():
    raw = so.parse_tool_arguments(_resp(tool_arguments='{"nextAction": "ask", "difficulty": "medium"}'))
    assert raw == {"nextAction": "ask", "difficulty": "medium"}


def test_parse_tool_arguments_raises_format_error_when_missing():
    with pytest.raises(so.LLMFormatError):
        so.parse_tool_arguments(_resp(content="no tool calls here"))


def test_parse_content_json_supports_plain_and_fenced():
    assert so.parse_content_json('{"a": 1}') == {"a": 1}
    fenced = '说明文字\n```json\n{"a": 2}\n```'
    assert so.parse_content_json(fenced) == {"a": 2}


def test_parse_content_json_raises_format_error_on_garbage():
    with pytest.raises(so.LLMFormatError):
        so.parse_content_json("这不是 JSON")
