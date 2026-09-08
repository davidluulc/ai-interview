from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .config import DASHSCOPE_API_KEY, LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS, QWEN_MODEL
from .llm_client import extract_json, post_chat_completion

logger = logging.getLogger(__name__)

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


def message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content") or "")


def parse_tool_arguments(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    tool_calls = choices[0].get("message", {}).get("tool_calls") if choices else None
    if not isinstance(tool_calls, list) or not tool_calls:
        raise LLMFormatError("Response has no tool_calls.")
    tool_call = tool_calls[0]
    if not isinstance(tool_call, dict):
        raise LLMFormatError("Tool call entry must be an object.")
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise LLMFormatError("Tool call function must be an object.")
    arguments = function.get("arguments")
    if not isinstance(arguments, str) or not arguments:
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
            try:
                return response.json()
            except Exception as exc:
                raise LLMFormatError(f"invalid provider response body: {exc}") from exc
        except LLMFormatError:
            raise
        except (LLMTransportError, httpx.TransportError) as exc:
            last_error = exc
            if attempt < LLM_MAX_RETRIES:
                await asyncio.sleep(0.3 * (attempt + 1))
                continue
    raise LLMTransportError(f"transport failed after retries: {last_error}")


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

    logger.warning("structured chain exhausted stages=%s", chain)
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
        _record(
            chain,
            "free_json_retry",
            "transport_error" if isinstance(exc, LLMTransportError) else "format_error",
            exc,
        )
        return None
    _record(chain, "free_json_retry", "ok")
    return validated


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
