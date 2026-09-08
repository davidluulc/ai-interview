from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from .config import QWEN_MODEL
from .llm_client import extract_json

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
