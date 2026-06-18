from typing import Any

import httpx
from fastapi import HTTPException

from .config import DASHSCOPE_API_KEY, DASHSCOPE_EMBEDDING_MODEL, LLM_TIMEOUT_SECONDS
from .security import redact_error_detail


EMBEDDING_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def build_embedding_payload(model_name: str, text: str) -> dict[str, Any]:
    return {
        "model": model_name,
        "input": [text],
    }


def extract_embedding(data: dict[str, Any]) -> list[float]:
    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise ValueError("Embedding response has no embedding data.")
    embedding = items[0].get("embedding") if isinstance(items[0], dict) else None
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("Embedding response has no embedding vector.")
    return [float(value) for value in embedding]


async def embed_text(text: str, model_name: str = DASHSCOPE_EMBEDDING_MODEL) -> list[float]:
    if not DASHSCOPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing DASHSCOPE_API_KEY in .env.")
    if not str(text or "").strip():
        return []

    payload = build_embedding_payload(model_name, text)
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                EMBEDDING_URL,
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
        )
        if response.status_code >= 400:
            _safe_body = redact_error_detail(response.text.replace(DASHSCOPE_API_KEY, mask_secret(DASHSCOPE_API_KEY)))
            raise HTTPException(status_code=502, detail="Embedding provider request failed.")
        return extract_embedding(response.json())
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="External provider request timed out.") from exc
    except httpx.HTTPError as exc:
        _ = redact_error_detail(str(exc))
        raise HTTPException(status_code=502, detail="Embedding provider request failed.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
