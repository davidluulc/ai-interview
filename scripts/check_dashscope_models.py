import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
EMBEDDING_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"


@dataclass
class ModelCheck:
    name: str
    model: str
    ok: bool
    detail: str


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def build_chat_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "请只回复 JSON：{\"ok\":true}",
            }
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def build_embedding_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": ["RAG 检索测试"],
    }


def build_rerank_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": {
            "query": "RAG 检索测试",
            "documents": [
                "RAG 系统会先检索相关 chunk，再把上下文放入 prompt。",
                "FastAPI 可以通过 APIRouter 拆分后端模块。",
            ],
        },
        "parameters": {
            "top_n": 2,
            "return_documents": False,
        },
    }


def summarize_response(data: dict[str, Any]) -> str:
    usage = data.get("usage") or {}
    if usage:
        return f"ok usage={usage}"
    if data.get("output") or data.get("results") or data.get("data"):
        return "ok"
    return "ok response received"


def summarize_error(response: httpx.Response, api_key: str) -> str:
    text = response.text[:500].replace(api_key, mask_secret(api_key))
    return f"status={response.status_code} body={text}"


async def post_json(
    client: httpx.AsyncClient,
    *,
    url: str,
    payload: dict[str, Any],
    api_key: str,
    dashscope_style: bool = False,
) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if dashscope_style:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return await client.post(url, headers=headers, json=payload)


async def run_single_check(
    client: httpx.AsyncClient,
    *,
    name: str,
    model: str,
    url: str,
    payload: dict[str, Any],
    api_key: str,
) -> ModelCheck:
    if not model:
        return ModelCheck(name=name, model="", ok=False, detail="model name is empty")
    try:
        response = await post_json(client, url=url, payload=payload, api_key=api_key)
        if response.status_code >= 400:
            return ModelCheck(name=name, model=model, ok=False, detail=summarize_error(response, api_key))
        return ModelCheck(name=name, model=model, ok=True, detail=summarize_response(response.json()))
    except httpx.TimeoutException:
        return ModelCheck(name=name, model=model, ok=False, detail="request timeout")
    except httpx.HTTPError as exc:
        return ModelCheck(name=name, model=model, ok=False, detail=f"network error: {exc}")
    except ValueError as exc:
        return ModelCheck(name=name, model=model, ok=False, detail=f"invalid json response: {exc}")


async def check_models(
    *,
    api_key: str,
    chat_model: str,
    embedding_model: str,
    rerank_model: str,
    timeout: float = 30,
) -> list[ModelCheck]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await asyncio.gather(
            run_single_check(
                client,
                name="chat",
                model=chat_model,
                url=CHAT_URL,
                payload=build_chat_payload(chat_model),
                api_key=api_key,
            ),
            run_single_check(
                client,
                name="embedding",
                model=embedding_model,
                url=EMBEDDING_URL,
                payload=build_embedding_payload(embedding_model),
                api_key=api_key,
            ),
            run_single_check(
                client,
                name="rerank",
                model=rerank_model,
                url=RERANK_URL,
                payload=build_rerank_payload(rerank_model),
                api_key=api_key,
            ),
        )


def summarize_checks(checks: list[ModelCheck], api_key: str) -> str:
    masked_key = mask_secret(api_key)
    lines = [f"DashScope model check, api_key={masked_key}"]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        detail = check.detail.replace(api_key, masked_key)
        lines.append(f"[{status}] {check.name}: model={check.model or '-'} detail={detail}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check DashScope/Bailian model availability without printing API keys.")
    parser.add_argument("--chat-model", default=os.getenv("QWEN_MODEL", "qwen-plus"))
    parser.add_argument("--embedding-model", default=os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4"))
    parser.add_argument("--rerank-model", default=os.getenv("DASHSCOPE_RERANK_MODEL", "qwen3-rerank"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")))
    return parser.parse_args()


async def async_main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    args = parse_args()
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("Missing DASHSCOPE_API_KEY in .env.")
        return 2
    checks = await check_models(
        api_key=api_key,
        chat_model=args.chat_model,
        embedding_model=args.embedding_model,
        rerank_model=args.rerank_model,
        timeout=args.timeout,
    )
    print(summarize_checks(checks, api_key))
    return 0 if all(check.ok for check in checks) else 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
