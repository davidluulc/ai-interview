import asyncio

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
