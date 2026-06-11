import asyncio
import json
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException

from .config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_CHAT_URL,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    QWEN_MODEL,
)

logger = logging.getLogger(__name__)


def extract_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("{"):
        return json.loads(clean)

    if "```" in clean:
        start = clean.find("```")
        body = clean[start + 3 :]
        if body.startswith("json"):
            body = body[4:]
        end = body.find("```")
        if end >= 0:
            return json.loads(body[:end].strip())

    raise ValueError("Model response is not valid JSON.")


def build_chat_payload(
    messages: list[dict[str, Any]],
    temperature: float,
    model_name: str,
) -> dict[str, Any]:
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }


def usage_summary(data: dict[str, Any]) -> dict[str, int]:
    usage = data.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


async def post_chat_completion(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> httpx.Response:
    return await client.post(
        DASHSCOPE_CHAT_URL,
        headers={
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
    )


async def call_model(
    messages: list[dict[str, Any]],
    temperature: float,
    model_name: str = QWEN_MODEL,
) -> dict[str, Any]:
    if not DASHSCOPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing DASHSCOPE_API_KEY in .env.")

    payload = build_chat_payload(messages, temperature, model_name)
    started_at = time.perf_counter()
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                response = await post_chat_completion(client, payload)
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

                if response.status_code >= 400:
                    logger.warning(
                        "LLM request failed model=%s status=%s attempt=%s duration_ms=%s body=%s",
                        model_name,
                        response.status_code,
                        attempt + 1,
                        duration_ms,
                        response.text[:500],
                    )
                    raise HTTPException(status_code=502, detail="LLM provider request failed.")

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    raise ValueError("Model response has no content.")

                parsed = extract_json(content)
                logger.info(
                    "LLM request ok model=%s attempt=%s duration_ms=%s usage=%s",
                    model_name,
                    attempt + 1,
                    duration_ms,
                    usage_summary(data),
                )
                return parsed
            except HTTPException:
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                logger.warning(
                    "LLM request transport error model=%s attempt=%s error=%s",
                    model_name,
                    attempt + 1,
                    exc,
                )
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "LLM response parse error model=%s attempt=%s error=%s",
                    model_name,
                    attempt + 1,
                    exc,
                )
                raise HTTPException(status_code=502, detail=str(exc)) from exc

    raise HTTPException(status_code=504, detail=f"LLM request timed out or failed: {last_error}")
