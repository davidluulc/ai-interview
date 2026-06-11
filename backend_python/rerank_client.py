from typing import Any

import httpx
from fastapi import HTTPException

from .config import DASHSCOPE_API_KEY, DASHSCOPE_RERANK_MODEL, LLM_TIMEOUT_SECONDS


DEFAULT_RERANK_INSTRUCT = "根据用户问题判断候选文档与 AI 模拟面试场景的相关性。"
RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"


def build_rerank_payload(
    *,
    model_name: str,
    query: str,
    documents: list[str],
    top_n: int,
    instruct: str = DEFAULT_RERANK_INSTRUCT,
) -> dict[str, Any]:
    return {
        "model": model_name,
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "instruct": instruct,
    }


def extract_rerank_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("Rerank response has no results.")

    parsed = []
    for item in results:
        if not isinstance(item, dict) or "index" not in item or "relevance_score" not in item:
            raise ValueError("Rerank result item is invalid.")
        try:
            parsed.append(
                {
                    "index": int(item["index"]),
                    "relevance_score": float(item["relevance_score"]),
                }
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Rerank result item is invalid.") from exc
    return parsed


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


async def rerank_documents(
    *,
    query: str,
    documents: list[str],
    top_n: int,
    instruct: str = DEFAULT_RERANK_INSTRUCT,
    model_name: str = DASHSCOPE_RERANK_MODEL,
) -> list[dict[str, Any]]:
    if not documents:
        return []
    if not DASHSCOPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing DASHSCOPE_API_KEY in .env.")

    payload = build_rerank_payload(
        model_name=model_name,
        query=query,
        documents=documents,
        top_n=min(top_n, len(documents)),
        instruct=instruct,
    )
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                RERANK_URL,
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code >= 400:
            safe_body = response.text[:500].replace(DASHSCOPE_API_KEY, mask_secret(DASHSCOPE_API_KEY))
            raise HTTPException(status_code=502, detail=f"Rerank provider request failed: {safe_body}")
        return extract_rerank_results(response.json())
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Rerank request timed out.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Rerank network error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
