import os
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException

from .config import DASHSCOPE_API_KEY, DASHSCOPE_EMBEDDING_MODEL, LLM_TIMEOUT_SECONDS
from .security import redact_error_detail


DASHSCOPE_EMBEDDING_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ZHIPU_EMBEDDING_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    api_key: str
    model: str
    base_url: str
    url: str
    dimensions: int | None = None
    require_model_match: bool = True


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def parse_optional_int(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def build_embedding_url(base_url: str) -> str:
    normalized = str(base_url or "").rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized
    return f"{normalized}/embeddings"


def resolve_embedding_settings(env: dict[str, str] | None = None) -> EmbeddingSettings:
    source = env if env is not None else os.environ
    provider = str(source.get("EMBEDDING_PROVIDER") or "dashscope").strip().lower()

    if provider == "zhipu":
        base_url = str(source.get("EMBEDDING_BASE_URL") or ZHIPU_EMBEDDING_BASE_URL).strip()
        model = str(source.get("EMBEDDING_MODEL") or "embedding-3").strip()
        api_key = str(source.get("EMBEDDING_API_KEY") or source.get("ZHIPU_API_KEY") or "").strip()
    elif provider in {"openai_compatible", "freellmapi"}:
        provider = "openai_compatible"
        base_url = str(source.get("EMBEDDING_BASE_URL") or "").strip()
        model = str(source.get("EMBEDDING_MODEL") or "auto").strip()
        api_key = str(source.get("EMBEDDING_API_KEY") or "").strip()
    else:
        provider = "dashscope"
        base_url = str(source.get("EMBEDDING_BASE_URL") or DASHSCOPE_EMBEDDING_BASE_URL).strip()
        model = str(source.get("EMBEDDING_MODEL") or source.get("DASHSCOPE_EMBEDDING_MODEL") or DASHSCOPE_EMBEDDING_MODEL).strip()
        api_key = str(source.get("EMBEDDING_API_KEY") or source.get("DASHSCOPE_API_KEY") or DASHSCOPE_API_KEY).strip()

    return EmbeddingSettings(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        url=build_embedding_url(base_url),
        dimensions=parse_optional_int(source.get("EMBEDDING_DIMENSIONS")),
        require_model_match=parse_bool(source.get("EMBEDDING_REQUIRE_MODEL_MATCH"), default=True),
    )


def current_embedding_model() -> str:
    return resolve_embedding_settings().model


def embedding_provider_summary() -> dict[str, Any]:
    settings = resolve_embedding_settings()
    return {
        "provider": settings.provider,
        "model": settings.model,
        "baseUrl": settings.base_url,
        "dimensions": settings.dimensions,
        "requireModelMatch": settings.require_model_match,
        "apiKeyConfigured": bool(settings.api_key),
    }


def build_embedding_payload(model_name: str, text: str, dimensions: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "input": [text],
    }
    if dimensions is not None:
        payload["dimensions"] = dimensions
    return payload


def extract_embedding(data: dict[str, Any]) -> list[float]:
    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise ValueError("Embedding response has no embedding data.")
    embedding = items[0].get("embedding") if isinstance(items[0], dict) else None
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("Embedding response has no embedding vector.")
    return [float(value) for value in embedding]


async def embed_text(text: str, model_name: str | None = None) -> list[float]:
    settings = resolve_embedding_settings()
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="Missing embedding API key in .env.")
    if not settings.base_url:
        raise HTTPException(status_code=500, detail="Missing EMBEDDING_BASE_URL in .env.")
    if not str(text or "").strip():
        return []

    active_model = model_name or settings.model
    payload = build_embedding_payload(active_model, text, dimensions=settings.dimensions)
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.url,
                headers={
                    "Authorization": f"Bearer {settings.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
        )
        if response.status_code >= 400:
            _safe_body = redact_error_detail(response.text.replace(settings.api_key, mask_secret(settings.api_key)))
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
