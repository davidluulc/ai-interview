import asyncio
import json
from typing import Any

import httpx
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


def test_parse_tool_arguments_raises_format_error_on_malformed_structure():
    malformed = {"choices": [{"message": {"tool_calls": [{"function": None}]}}]}
    with pytest.raises(so.LLMFormatError):
        so.parse_tool_arguments(malformed)


def test_parse_content_json_supports_plain_and_fenced():
    assert so.parse_content_json('{"a": 1}') == {"a": 1}
    fenced = '说明文字\n```json\n{"a": 2}\n```'
    assert so.parse_content_json(fenced) == {"a": 2}


def test_parse_content_json_raises_format_error_on_garbage():
    with pytest.raises(so.LLMFormatError):
        so.parse_content_json("这不是 JSON")


class _FakeTransport:
    """按脚本顺序返回 httpx.Response，记录调用次数。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __call__(self, client, payload):
        self.calls.append(payload)
        status, body = self.responses.pop(0)
        return httpx.Response(
            status,
            json=body,
            request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
        )


def test_send_returns_json_on_success(monkeypatch):
    transport = _FakeTransport([(200, {"choices": [{"message": {"content": "{}"}}]})])
    monkeypatch.setattr(so, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(so, "post_chat_completion", transport)
    data = run(so._send({"model": "m"}))
    assert data["choices"][0]["message"]["content"] == "{}"


def test_send_retries_transport_error_then_raises(monkeypatch):
    transport = _FakeTransport([(429, {"error": "rate"}) for _ in range(5)])
    monkeypatch.setattr(so, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(so, "post_chat_completion", transport)
    monkeypatch.setattr(so.asyncio, "sleep", _no_sleep)
    with pytest.raises(so.LLMTransportError):
        run(so._send({"model": "m"}))
    assert len(transport.calls) == so.LLM_MAX_RETRIES + 1


async def _no_sleep(_seconds):
    return None


def test_send_raises_format_error_immediately_on_4xx(monkeypatch):
    transport = _FakeTransport([(400, {"error": "response_format not supported"})])
    monkeypatch.setattr(so, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(so, "post_chat_completion", transport)
    with pytest.raises(so.LLMFormatError):
        run(so._send({"model": "m"}))
    assert len(transport.calls) == 1


def _ok_content(extra=None):
    payload = {"nextAction": "deep_follow_up", "difficulty": "medium"}
    if extra:
        payload.update(extra)
    return _resp(content=json.dumps(payload, ensure_ascii=False))


def _tool_ok():
    return _resp(tool_arguments='{"nextAction": "switch_topic", "difficulty": "basic"}')


def test_chain_succeeds_on_first_stage(monkeypatch):
    async def fake_send(payload):
        assert payload["response_format"]["type"] == "json_schema"
        return _ok_content()

    monkeypatch.setattr(so, "_send", fake_send)
    model, meta = run(so.call_model_structured(
        messages=[{"role": "user", "content": "go"}],
        schema_model=SampleModel,
        temperature=0.2,
    ))
    assert model.nextAction == "deep_follow_up"
    assert meta["finalStage"] == "json_schema"
    assert meta["stages"][-1]["status"] == "ok"


def test_chain_falls_to_tool_call_on_schema_error(monkeypatch):
    # 段①内容合法但缺字段 → ValidationError → 段② tool_call 成功
    bad = _resp(content=json.dumps({"nextAction": "deep_follow_up"}))
    calls = {"n": 0}

    async def fake_send(payload):
        calls["n"] += 1
        return bad if calls["n"] == 1 else _tool_ok()

    monkeypatch.setattr(so, "_send", fake_send)
    model, meta = run(so.call_model_structured(
        messages=[{"role": "user", "content": "go"}],
        schema_model=SampleModel,
        temperature=0.2,
    ))
    assert model.nextAction == "switch_topic"
    assert meta["finalStage"] == "tool_call"
    assert meta["stages"][0]["status"] == "format_error"


def test_chain_corrective_retry_in_free_json(monkeypatch):
    # 段①② provider 4xx（format）→ 段③首次缺字段 → 校正重试成功
    responses = [
        httpx.Response(400, json={"error": "x"}, request=httpx.Request("POST", "https://t")),
        httpx.Response(400, json={"error": "x"}, request=httpx.Request("POST", "https://t")),
        _resp(content=json.dumps({"difficulty": "medium"})),
        _ok_content(),
    ]
    calls = {"n": 0}

    async def fake_send(payload):
        item = responses[calls["n"]]
        calls["n"] += 1
        if isinstance(item, httpx.Response):
            if item.status_code >= 400:
                raise so.LLMFormatError(f"provider status {item.status_code}")
            return item.json()
        return item

    monkeypatch.setattr(so, "_send", fake_send)
    model, meta = run(so.call_model_structured(
        messages=[{"role": "user", "content": "go"}],
        schema_model=SampleModel,
        temperature=0.2,
    ))
    assert model.nextAction == "deep_follow_up"
    assert meta["finalStage"] == "free_json_retry"


def test_chain_raises_exhausted_when_all_stages_fail(monkeypatch):
    async def fake_send(payload):
        raise so.LLMTransportError("down")

    monkeypatch.setattr(so, "_send", fake_send)
    with pytest.raises(so.StructuredOutputExhausted) as exc_info:
        run(so.call_model_structured(
            messages=[{"role": "user", "content": "go"}],
            schema_model=SampleModel,
            temperature=0.2,
        ))
    assert len(exc_info.value.chain) >= 3


from backend_python.interview_agent import build_agent_state, decide_next_action
from backend_python import config as project_config


class _AgentDecisionStub(BaseModel):
    nextAction: str
    stage: str
    difficulty: str
    focus: str
    reason: str
    tools: list
    triggerRules: list
    agentMode: str
    shouldUpdateMemory: bool


def _agent_state():
    return build_agent_state(
        profile={"targetRole": "AI 应用开发"},
        history=[],
        next_stage="项目追问",
        role_hits=[],
        question_hits=[],
        memory_hits=[],
    )


def test_decide_next_action_uses_structured_fn_when_provided():
    async def fake_structured(**kwargs):
        return _AgentDecisionStub(
            nextAction="deep_follow_up",
            stage="项目追问",
            difficulty="hard",
            focus="RAG 检索链路",
            reason="上一轮回答覆盖不足",
            tools=[],
            triggerRules=[],
            agentMode="interview",
            shouldUpdateMemory=True,
        ), {"stages": [], "finalStage": "json_schema", "attemptCount": 1}

    async def legacy_should_not_run(**kwargs):
        raise AssertionError("legacy path must not run when structured fn succeeds")

    decision = run(decide_next_action(
        _agent_state(),
        call_model_fn=legacy_should_not_run,
        structured_call_fn=fake_structured,
    ))
    assert decision["nextAction"] == "deep_follow_up"
    assert decision["structuredChain"]["finalStage"] == "json_schema"


def test_decide_next_action_falls_back_when_structured_exhausted():
    async def fake_structured(**kwargs):
        raise so.StructuredOutputExhausted(chain=[{"stage": "json_schema", "status": "transport_error"}])

    async def legacy(**kwargs):
        return {"nextAction": "switch_topic", "stage": "换方向", "difficulty": "basic",
                "focus": "", "reason": "", "tools": [], "triggerRules": [],
                "agentMode": "interview", "shouldUpdateMemory": False}

    decision = run(decide_next_action(
        _agent_state(),
        call_model_fn=legacy,
        structured_call_fn=fake_structured,
    ))
    assert decision["nextAction"] == "switch_topic"


def test_config_flag_defaults_to_chain_and_respects_legacy(monkeypatch):
    monkeypatch.delenv("LLM_STRUCTURED_OUTPUT", raising=False)
    assert project_config.structured_output_enabled() is True
    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT", "legacy")
    assert project_config.structured_output_enabled() is False
