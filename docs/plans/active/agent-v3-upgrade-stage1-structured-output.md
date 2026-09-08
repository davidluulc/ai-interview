# Agent v3 Stage 1：结构化输出降级链 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 LLM 调用建立「json_schema → function calling → 自由 JSON 校正重试」三段结构化输出降级链，异常按传输/格式分层，接入 Agent 决策与出题两个调用点，legacy 通道原样保留可回滚。

**Architecture:** 新建 `backend_python/structured_output.py` 承载全部机制（Schema 构建、payload 构建、解析、异常分层、三段链），传输层复用 `llm_client.post_chat_completion`；既有 `call_model` 一行不改。调用点通过可选参数 opt-in（`structured_call_fn=None` 默认），既有测试零改动。配置开关 `LLM_STRUCTURED_OUTPUT=chain|legacy` 运行时动态读取。

**Tech Stack:** Python 3.11+（沿用既有类型语法）、pydantic v2（随 FastAPI 已有）、httpx、pytest。**不新增任何依赖。**

**上游 spec:** `docs/specs/active/agent-v3-upgrade-design.md` §4-S1、§0 Goal Card。

## Global Constraints

- 不新增第三方依赖；不修改 `backend_python/llm_client.py` 的既有函数行为。
- 既有测试文件零改动、全绿；新测试全部落在 `tests/test_structured_output.py`。
- pydantic v2 API（`model_validate` / `model_dump` / `model_json_schema`）。
- 异步函数在测试中用 `asyncio.run(...)` 包裹（仓库未用 pytest-asyncio）。
- 提交信息用 conventional commits（`feat:` / `test:` / `docs:` / `chore:`）。
- 分支：`feat/agent-v3-upgrade`，基于 `main`。
- 每个任务结束必须：`python -m pytest -q`（仓库根目录）全绿后再 commit。

---

## File Map

- Create: `backend_python/structured_output.py` — 异常类型、strict schema、payload builders、解析器、`_send` 传输层、`call_model_structured` 三段链、`AgentDecisionModel` / `QuestionDraftModel`。
- Create: `tests/test_structured_output.py` — 本阶段全部新测试。
- Modify: `backend_python/config.py` — 增加动态读取的 `structured_output_enabled()`。
- Modify: `backend_python/interview_agent.py:432` — `decide_next_action` 增加可选 `structured_call_fn` 参数。
- Modify: `backend_python/langgraph_agent/adapters.py:58-79` — `decide_real_action_for_graph` 按开关传入 `structured_call_fn`。
- Modify: `backend_python/routes/interview.py:471-475` — `safe_call_question_model` structured 先行、legacy 兜底。
- Modify: `.env.example` / `.env.production.example` — 增加 `LLM_STRUCTURED_OUTPUT=chain`。
- Modify: `docs/plans/README.md`、`docs/roadmap/current-state.md` — active 指针与阶段记录。

---

## Task 1: 分支与 Active Plan 指针

**Files:**
- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: 创建功能分支**

```bash
git checkout main && git pull
git checkout -b feat/agent-v3-upgrade
```

- [ ] **Step 2: 更新 active plan 指针**

在 `docs/plans/README.md` 将 active plan 指向本文件，active spec 指向 `docs/specs/active/agent-v3-upgrade-design.md`（旧 V3 指针移入 completed 段落，注明「主体完成，公网 smoke 未做，见 current-state 待办」）。

- [ ] **Step 3: current-state.md 记录新阶段**

在 `docs/roadmap/current-state.md` 的 Active 状态段落，将 active spec/plan 改为本阶段两个文件，并追加一句：

```text
Agent v3 升级包（S1 结构化输出 → S2 pgvector → S3 融合实验 → S4 真图化 → S5 MCP），预算与停止条件见 spec §0 Goal Card。
```

- [ ] **Step 4: 验证指针生效**

```bash
rg -n "agent-v3-upgrade" docs/plans/README.md docs/roadmap/current-state.md
```

Expected: 两个文件各命中。

- [ ] **Step 5: Commit**

```bash
git add docs/plans/README.md docs/roadmap/current-state.md docs/specs/active/agent-v3-upgrade-design.md docs/plans/active/agent-v3-upgrade-stage1-structured-output.md
git commit -m "docs: add agent v3 upgrade spec and stage1 plan"
```

---

## Task 2: 模块骨架 + 异常类型 + strict schema + payload builders

**Files:**
- Create: `backend_python/structured_output.py`
- Create: `tests/test_structured_output.py`

**Interfaces:**
- Produces: `LLMTransportError` / `LLMFormatError` / `StructuredOutputExhausted`；`strict_schema(schema_model: type[BaseModel]) -> dict`；`build_json_schema_payload(*, messages, schema_model, temperature, model_name) -> dict`；`build_tool_call_payload(...) -> dict`（后续任务的被测对象）。

- [ ] **Step 1: Write the failing tests**

`tests/test_structured_output.py`：

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend_python.structured_output'`（或 ImportError）。

- [ ] **Step 3: Write minimal implementation**

`backend_python/structured_output.py`：

```python
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .config import QWEN_MODEL

T = TypeVar("T", bound=BaseModel)


class LLMTransportError(Exception):
    """超时/限流/5xx 等基础设施错误：同段内重试，耗尽后上抛。"""


class LLMFormatError(Exception):
    """解析/校验失败等格式错误：触发降级到下一段。"""


class StructuredOutputExhausted(Exception):
    """三段降级链全部失败。chain 属性记录每段结果。"""

    def __init__(self, chain: list[dict[str, Any]]):
        super().__init__("structured output chain exhausted")
        self.chain = chain


def strict_schema(schema_model: type[BaseModel]) -> dict[str, Any]:
    schema = schema_model.model_json_schema()
    schema.pop("title", None)
    properties = schema.get("properties", {})
    for prop in properties.values():
        prop.pop("title", None)
    schema["additionalProperties"] = False
    schema["required"] = list(properties.keys())
    return schema


def build_json_schema_payload(
    *,
    messages: list[dict[str, Any]],
    schema_model: type[BaseModel],
    temperature: float,
    model_name: str = QWEN_MODEL,
) -> dict[str, Any]:
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_model.__name__,
                "schema": strict_schema(schema_model),
                "strict": True,
            },
        },
    }


def build_tool_call_payload(
    *,
    messages: list[dict[str, Any]],
    schema_model: type[BaseModel],
    temperature: float,
    model_name: str = QWEN_MODEL,
) -> dict[str, Any]:
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": schema_model.__name__,
                    "description": schema_model.__doc__ or "Return structured output.",
                    "parameters": strict_schema(schema_model),
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": schema_model.__name__}},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: PASS（3 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend_python/structured_output.py tests/test_structured_output.py
git commit -m "feat: add structured output module skeleton and payload builders"
```

---

## Task 3: 响应解析器（content JSON / tool arguments / 围栏兼容）

**Files:**
- Modify: `backend_python/structured_output.py`
- Modify: `tests/test_structured_output.py`

**Interfaces:**
- Consumes: `LLMFormatError`（Task 2）。
- Produces: `message_content(data: dict) -> str`；`parse_tool_arguments(data: dict) -> dict`；`parse_content_json(content: str) -> dict`（Task 5 使用）。

- [ ] **Step 1: Write the failing tests**

追加到 `tests/test_structured_output.py`：

```python
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
```

注意：文件顶部需补 `from typing import Any`（`_resp` 的类型标注用）。

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `AttributeError: module ... has no attribute 'message_content'`。

- [ ] **Step 3: Write minimal implementation**

追加到 `backend_python/structured_output.py`：

```python
import json

from .llm_client import extract_json


def message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content") or "")


def parse_tool_arguments(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    tool_calls = choices[0].get("message", {}).get("tool_calls") if choices else None
    if not tool_calls:
        raise LLMFormatError("Response has no tool_calls.")
    arguments = tool_calls[0].get("function", {}).get("arguments")
    if not arguments:
        raise LLMFormatError("Tool call has no arguments.")
    try:
        parsed = json.loads(arguments)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMFormatError(f"Tool arguments is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMFormatError("Tool arguments must be a JSON object.")
    return parsed


def parse_content_json(content: str) -> dict[str, Any]:
    try:
        parsed = extract_json(content)
    except (ValueError, json.JSONDecodeError) as exc:
        raise LLMFormatError(f"Content is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMFormatError("Content JSON must be an object.")
    return parsed
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: PASS（8 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend_python/structured_output.py tests/test_structured_output.py
git commit -m "feat: add structured output response parsers"
```

---

## Task 4: `_send` 传输层（异常分层 + 同段重试）

**Files:**
- Modify: `backend_python/structured_output.py`
- Modify: `tests/test_structured_output.py`

**Interfaces:**
- Consumes: `LLMTransportError` / `LLMFormatError`（Task 2）、`llm_client.post_chat_completion`。
- Produces: `async def _send(payload: dict) -> dict[str, Any]`——成功返回响应 JSON；4xx 抛 `LLMFormatError`（不重试）；超时/429/5xx 同段重试后抛 `LLMTransportError`（Task 5 使用）。

- [ ] **Step 1: Write the failing tests**

追加（并补文件级 import：`import httpx`）：

```python
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
```

注意：`_no_sleep` 需定义在 `test_send_retries_transport_error_then_raises` 之前（或任意模块级位置），`so.asyncio` 可用要求 structured_output 顶部 `import asyncio`（本任务实现中加入）。

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `AttributeError: ... has no attribute '_send'`。

- [ ] **Step 3: Write minimal implementation**

文件顶部 import 区调整为：

```python
import asyncio
import json
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from .config import DASHSCOPE_API_KEY, DASHSCOPE_CHAT_URL, LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS, QWEN_MODEL
from .llm_client import extract_json, post_chat_completion
```

（`DASHSCOPE_CHAT_URL` 暂不直接使用可不导入；保留最小集合：`DASHSCOPE_API_KEY, LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS, QWEN_MODEL`。）

追加实现：

```python
async def _send(payload: dict[str, Any]) -> dict[str, Any]:
    if not DASHSCOPE_API_KEY:
        raise LLMTransportError("Missing DASHSCOPE_API_KEY in .env.")
    last_error: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                response = await post_chat_completion(client, payload)
            if response.status_code == 429 or response.status_code >= 500:
                raise LLMTransportError(f"provider status {response.status_code}")
            if response.status_code >= 400:
                raise LLMFormatError(f"provider status {response.status_code}: {response.text[:200]}")
            return response.json()
        except LLMFormatError:
            raise
        except (LLMTransportError, httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt < LLM_MAX_RETRIES:
                await asyncio.sleep(0.3 * (attempt + 1))
                continue
    raise LLMTransportError(f"transport failed after retries: {last_error}")
```

注意 `DASHSCOPE_API_KEY` 在测试中被 `monkeypatch.setattr(so, "DASHSCOPE_API_KEY", ...)` 覆盖，因此函数内直接引用模块全局名即可命中补丁。

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: PASS（11 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend_python/structured_output.py tests/test_structured_output.py
git commit -m "feat: add layered transport sender for structured output"
```

---

## Task 5: `call_model_structured` 三段链 + 校正重试

**Files:**
- Modify: `backend_python/structured_output.py`
- Modify: `tests/test_structured_output.py`

**Interfaces:**
- Consumes: Task 2-4 全部产物。
- Produces: `async def call_model_structured(*, messages, schema_model, temperature=0.2, model_name=QWEN_MODEL) -> tuple[BaseModel, dict]`；meta 结构 `{"stages": [...], "finalStage": str, "attemptCount": int}`；全失败抛 `StructuredOutputExhausted(chain)`（Task 6/7 使用）。

- [ ] **Step 1: Write the failing tests**

追加：

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `AttributeError: ... has no attribute 'call_model_structured'`。

- [ ] **Step 3: Write minimal implementation**

追加到 `backend_python/structured_output.py`：

```python
_STAGES = ("json_schema", "tool_call", "free_json")


def _record(chain: list[dict[str, Any]], stage: str, status: str, detail: Any = "") -> None:
    chain.append({"stage": stage, "status": status, "detail": str(detail)[:200]})


def _meta(chain: list[dict[str, Any]], *, final_stage: str) -> dict[str, Any]:
    return {"stages": chain, "finalStage": final_stage, "attemptCount": len(chain)}


def _payload_for(
    stage: str,
    *,
    messages: list[dict[str, Any]],
    schema_model: type[BaseModel],
    temperature: float,
    model_name: str,
) -> dict[str, Any]:
    if stage == "json_schema":
        return build_json_schema_payload(
            messages=messages, schema_model=schema_model, temperature=temperature, model_name=model_name
        )
    if stage == "tool_call":
        return build_tool_call_payload(
            messages=messages, schema_model=schema_model, temperature=temperature, model_name=model_name
        )
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }


async def call_model_structured(
    *,
    messages: list[dict[str, Any]],
    schema_model: type[BaseModel],
    temperature: float = 0.2,
    model_name: str = QWEN_MODEL,
) -> tuple[Any, dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    free_messages = list(messages)
    for stage in _STAGES:
        payload = _payload_for(
            stage,
            messages=free_messages if stage == "free_json" else messages,
            schema_model=schema_model,
            temperature=temperature,
            model_name=model_name,
        )
        try:
            data = await _send(payload)
        except (LLMTransportError, LLMFormatError) as exc:
            _record(chain, stage, "transport_error" if isinstance(exc, LLMTransportError) else "format_error", exc)
            continue

        raw: dict[str, Any] = {}
        try:
            raw = parse_tool_arguments(data) if stage == "tool_call" else parse_content_json(message_content(data))
            validated = schema_model.model_validate(raw)
        except (LLMFormatError, ValidationError) as exc:
            _record(chain, stage, "format_error", exc)
            if stage == "free_json":
                retry_ok = await _free_json_corrective(
                    free_messages=free_messages,
                    schema_model=schema_model,
                    temperature=temperature,
                    model_name=model_name,
                    chain=chain,
                )
                if retry_ok is not None:
                    return retry_ok, _meta(chain, final_stage="free_json_retry")
            continue

        _record(chain, stage, "ok")
        return validated, _meta(chain, final_stage=stage)

    raise StructuredOutputExhausted(chain)


async def _free_json_corrective(
    *,
    free_messages: list[dict[str, Any]],
    schema_model: type[BaseModel],
    temperature: float,
    model_name: str,
    chain: list[dict[str, Any]],
) -> Any | None:
    corrective_messages = [
        *free_messages,
        {"role": "assistant", "content": json.dumps({"output": "（上次输出不合规）"}, ensure_ascii=False)},
        {
            "role": "user",
            "content": (
                "上一次输出未通过 schema 校验。请严格按字段要求重新输出，"
                "只输出一个 JSON 对象，不要包含任何解释或代码围栏。"
            ),
        },
    ]
    payload = {
        "model": model_name,
        "messages": corrective_messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    try:
        data = await _send(payload)
        raw = parse_content_json(message_content(data))
        validated = schema_model.model_validate(raw)
    except (LLMTransportError, LLMFormatError, ValidationError) as exc:
        _record(chain, "free_json_retry", "format_error", exc)
        return None
    _record(chain, "free_json_retry", "ok")
    return validated
```

同时把顶部 pydantic 导入改为 `from pydantic import BaseModel, ValidationError`。

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: PASS（15 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend_python/structured_output.py tests/test_structured_output.py
git commit -m "feat: add three-stage structured output chain with corrective retry"
```

---

## Task 6: Schema 模型 + 开关 + Agent 决策接线（opt-in）

**Files:**
- Modify: `backend_python/structured_output.py`
- Modify: `backend_python/config.py`
- Modify: `backend_python/interview_agent.py:432`
- Modify: `backend_python/langgraph_agent/adapters.py:58-79`
- Modify: `tests/test_structured_output.py`

**Interfaces:**
- Consumes: `call_model_structured` / `StructuredOutputExhausted`（Task 5）；`decide_next_action` / `normalize_agent_decision` / `build_fallback_decision`（既有）。
- Produces: `AgentDecisionModel`、`QuestionDraftModel`（Task 7 使用）；`config.structured_output_enabled() -> bool`；`decide_next_action(state, *, call_model_fn, structured_call_fn=None)`。

- [ ] **Step 1: Write the failing tests**

追加：

```python
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
    return build_agent_state(profile={"targetRole": "AI 应用开发"}, history=[], next_stage="项目追问")


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `TypeError: decide_next_action() got an unexpected keyword argument 'structured_call_fn'`；及 `AttributeError: ... no attribute 'structured_output_enabled'`。

- [ ] **Step 3: Write minimal implementation**

1）`backend_python/config.py` 追加：

```python
def structured_output_enabled() -> bool:
    """LLM_STRUCTURED_OUTPUT=chain（默认）| legacy。运行时动态读取，便于灰度与回滚。"""
    value = os.getenv("LLM_STRUCTURED_OUTPUT", "chain").strip().lower()
    return value not in {"legacy", "off", "0", "false"}
```

（`config.py` 已有 `import os`；若实际文件用其他 env 读取方式，保持同风格即可，函数名不变。）

2）`backend_python/structured_output.py` 追加两个业务 Schema：

```python
class AgentDecisionModel(BaseModel):
    """面试 Agent 的下一步动作决策。"""

    nextAction: str
    stage: str
    difficulty: str
    focus: str
    reason: str
    tools: list[str]
    triggerRules: list[str]
    agentMode: str
    shouldUpdateMemory: bool


class QuestionDraftModel(BaseModel):
    """生成的下一道面试题草稿。extra=allow 保留模型附带字段，避免下游缺 key。"""

    model_config = {"extra": "allow"}

    stage: str
    stability: str
    focus: str
    prompt: str
```

3）`backend_python/interview_agent.py` 的 `decide_next_action`（当前 432-468 行）改为：

```python
async def decide_next_action(
    state: dict[str, Any],
    *,
    call_model_fn: Callable[..., Awaitable[dict[str, Any]]],
    structured_call_fn: Callable[..., Awaitable[tuple[Any, dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    fallback = build_fallback_decision(state)
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {"state": state, "fallbackDecision": fallback, "outputSchema": {...}},  # 保持既有内容不变
                ensure_ascii=False,
            ),
        },
    ]
    if structured_call_fn is not None:
        try:
            model, chain_meta = await structured_call_fn(
                messages=messages,
                schema_model=AgentDecisionModel,
                temperature=0.2,
            )
            decision = model.model_dump()
            decision["structuredChain"] = chain_meta
            return normalize_agent_decision(decision, fallback, state=state)
        except Exception:
            pass  # 落回 legacy 通道
    try:
        result = await call_model_fn(temperature=0.2, messages=messages)
        return normalize_agent_decision(result, fallback, state=state)
    except Exception:
        return {**fallback, "fallbackUsed": True}
```

（`messages` 与 `outputSchema` 内容**照抄当前实现原样**，只是提到 `if` 之前共用；顶部补 `from .structured_output import AgentDecisionModel`。）

4）`backend_python/langgraph_agent/adapters.py` 的 `decide_real_action_for_graph`（58-79 行）：

```python
from backend_python.config import structured_output_enabled
from backend_python.structured_output import call_model_structured

# 函数签名不变；第 78 行调用改为：
    structured_call_fn = call_model_structured if structured_output_enabled() else None
    decision = await decide_next_action(
        agent_state,
        call_model_fn=call_model_fn,
        structured_call_fn=structured_call_fn,
    )
```

- [ ] **Step 4: Run tests to verify they pass（含既有全量）**

```bash
python -m pytest tests/test_structured_output.py -q && python -m pytest -q
```

Expected: 新增 3 passed；全量无回归（既有文件零改动，`structured_call_fn` 缺省 None 走原路径）。

- [ ] **Step 5: Commit**

```bash
git add backend_python/structured_output.py backend_python/config.py backend_python/interview_agent.py backend_python/langgraph_agent/adapters.py tests/test_structured_output.py
git commit -m "feat: wire structured decision chain behind opt-in flag"
```

---

## Task 7: 出题调用点接线（structured 先行、legacy 兜底）

**Files:**
- Modify: `backend_python/routes/interview.py:471-475`
- Modify: `.env.example`、`.env.production.example`
- Modify: `tests/test_structured_output.py`

**Interfaces:**
- Consumes: `call_model_structured` / `QuestionDraftModel` / `LLMTransportError` / `StructuredOutputExhausted`（Task 5/6）；既有 `call_model` 与 `__provider_error__` 契约。
- Produces: `safe_call_question_model` 新行为——开关开启时 structured 先行，失败落回 legacy 原路径（下游契约不变），成功时附带 `structuredChain`。

- [ ] **Step 1: Write the failing tests**

追加：

```python
def test_safe_question_model_prefers_structured(monkeypatch):
    from backend_python.routes import interview as interview_routes

    class _QuestionStub(BaseModel):
        model_config = {"extra": "allow"}
        stage: str
        stability: str
        focus: str
        prompt: str

    async def fake_structured(**kwargs):
        return _QuestionStub(stage="项目追问", stability="稳定", focus="RAG", prompt="请讲讲..."), {
            "stages": [], "finalStage": "json_schema", "attemptCount": 1,
        }

    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT", "chain")
    monkeypatch.setattr(interview_routes, "call_model_structured", fake_structured)
    data = run(interview_routes.safe_call_question_model(
        messages=[{"role": "user", "content": "go"}], temperature=0.3,
    ))
    assert data["prompt"] == "请讲讲..."
    assert data["structuredChain"]["finalStage"] == "json_schema"


def test_safe_question_model_falls_back_to_legacy(monkeypatch):
    from backend_python.routes import interview as interview_routes

    async def broken_structured(**kwargs):
        raise so.StructuredOutputExhausted(chain=[])

    async def fake_legacy(**kwargs):
        return {"stage": "x", "stability": "y", "focus": "z", "prompt": "legacy 题"}

    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT", "chain")
    monkeypatch.setattr(interview_routes, "call_model_structured", broken_structured)
    monkeypatch.setattr(interview_routes, "call_model", fake_legacy)
    data = run(interview_routes.safe_call_question_model(
        messages=[{"role": "user", "content": "go"}], temperature=0.3,
    ))
    assert data["prompt"] == "legacy 题"
    assert data.get("structuredFallbackUsed") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_structured_output.py -q
```

Expected: FAIL — `AttributeError: module 'backend_python.routes.interview' has no attribute 'call_model_structured'`。

- [ ] **Step 3: Write minimal implementation**

`backend_python/routes/interview.py` 顶部补：

```python
from ..config import structured_output_enabled
from ..structured_output import (
    LLMTransportError,
    QuestionDraftModel,
    StructuredOutputExhausted,
    call_model_structured,
)
```

`safe_call_question_model`（当前 471-475 行）改为：

```python
async def safe_call_question_model(*, messages: list[dict[str, Any]], temperature: float) -> dict[str, Any]:
    if structured_output_enabled():
        try:
            model, chain_meta = await call_model_structured(
                messages=messages,
                schema_model=QuestionDraftModel,
                temperature=temperature,
            )
            data = model.model_dump()
            data["structuredChain"] = chain_meta
            return data
        except (StructuredOutputExhausted, LLMTransportError):
            pass  # 落回 legacy，保持既有契约
    try:
        data = await call_model(messages=messages, temperature=temperature)
        if structured_output_enabled():
            data["structuredFallbackUsed"] = True
        return data
    except HTTPException as exc:
        return {"__provider_error__": exc}
```

`.env.example` 与 `.env.production.example` 各追加一行：

```text
# 结构化输出通道：chain（默认，三段降级链）| legacy（仅旧 JSON 通道）
LLM_STRUCTURED_OUTPUT=chain
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_structured_output.py -q && python -m pytest -q
```

Expected: 新增 2 passed；全量无回归。

- [ ] **Step 5: Commit**

```bash
git add backend_python/routes/interview.py .env.example .env.production.example tests/test_structured_output.py
git commit -m "feat: route question generation through structured chain with legacy fallback"
```

---

## Task 8: 阶段收尾（全量验证 + 状态记录）

**Files:**
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: 全量测试与配置校验**

```bash
python -m pytest -q
docker compose --env-file .env.production.example config --quiet
```

Expected: 全绿（既有 440+ 与新增 ~20）；compose 配置无错。

- [ ] **Step 2: 记录阶段完成**

在 `docs/roadmap/current-state.md` Active 段落追加：

```text
S1 结构化输出降级链已完成：json_schema → tool_call → free_json(校正重试) 三段链，
异常按传输/格式分层，Agent 决策与出题两个调用点已接入，LLM_STRUCTURED_OUTPUT=legacy 可整体回滚。
报告生成与简历解析仍在 legacy 通道，留待后续机械迁移。
```

- [ ] **Step 3: Commit**

```bash
git add docs/roadmap/current-state.md
git commit -m "docs: record stage1 structured output completion"
```

- [ ] **Step 4: 公网部署窗口（另行安排，不阻塞本阶段关闭）**

S2 动数据库前再统一部署一次；此处仅在 current-state 待办记一笔「S1 待公网 smoke」。

---

## Self-Review（已执行）

- Spec 覆盖：spec §4-S1 的三段链 / 异常分层 / 两个调用点 / 回滚开关 / 测试要求均有对应 Task（2-7）；验收条款「每段有单测、行为不回退、可回滚」分别由 Task 3/5 测试、Task 6 Step 4 全量回归、`LLM_STRUCTURED_OUTPUT=legacy` 覆盖。
- 类型一致性：`call_model_structured` 返回 `(BaseModel, dict)` 与 Task 6/7 消费一致；`structured_call_fn` 签名与 `decide_next_action` 定义一致；`_send` / `_record` / `_meta` 命名在 Task 4/5 间一致。
- 无占位符：所有代码步骤含完整代码；`outputSchema` 一处标注「照抄当前实现」因其内容与被测行为无关且必须逐字保留。
