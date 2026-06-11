# RAG Rerank V2-4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Hybrid Search 后接入百炼 `qwen3-rerank`，对候选 chunk 做相关性重排，并支持失败降级和日志可观测。

**Architecture:** 新增独立 `rerank_client.py` 封装百炼 rerank API；在 `retrieval_service.py` 中新增 hit 文本化、重排结果应用、`hybrid_rerank` 检索模式；在 RAG 日志摘要中保留 rerank 调试字段。Rerank 是增强链路，失败时回退 Hybrid 原排序。

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite, httpx, pytest, Alibaba Cloud Model Studio DashScope `qwen3-rerank`.

---

## File Structure

- Modify: `backend_python/config.py`
  - 增加 `DASHSCOPE_RERANK_MODEL`
- Create: `backend_python/rerank_client.py`
  - 封装 payload 构造、响应解析、异步 API 调用
- Modify: `backend_python/retrieval_service.py`
  - 增加 `hit_to_rerank_document`
  - 增加 `apply_rerank_results`
  - 增加 `run_rerank_documents`
  - 增加 `retrieve_hybrid_rerank_chunks`
  - `retrieve_chunks` 支持 `mode="hybrid_rerank"`
- Modify: `backend_python/rag_logging.py`
  - `summarize_hit` 保留 rerank 调试字段
- Add: `tests/test_rerank_client.py`
  - 覆盖 payload、响应解析、错误处理
- Add: `tests/test_rag_rerank_retrieval.py`
  - 覆盖 hit 文本化、重排应用、hybrid_rerank、失败降级
- Modify: `tests/test_rag_retrieval_logs.py`
  - 覆盖 rerank 日志字段

## Task 1: Config and Rerank Client Payload

**Files:**
- Modify: `backend_python/config.py`
- Create: `backend_python/rerank_client.py`
- Add: `tests/test_rerank_client.py`

- [ ] Write the failing tests for config and payload.

```python
from backend_python.config import DASHSCOPE_RERANK_MODEL
from backend_python.rerank_client import build_rerank_payload


def test_default_rerank_model_is_qwen3_rerank() -> None:
    assert DASHSCOPE_RERANK_MODEL == "qwen3-rerank"


def test_build_rerank_payload_uses_qwen3_flat_request_shape() -> None:
    payload = build_rerank_payload(
        model_name="qwen3-rerank",
        query="什么是 RAG 重排？",
        documents=["文档 A", "文档 B"],
        top_n=2,
        instruct="根据 query 判断文档相关性。",
    )

    assert payload == {
        "model": "qwen3-rerank",
        "query": "什么是 RAG 重排？",
        "documents": ["文档 A", "文档 B"],
        "top_n": 2,
        "instruct": "根据 query 判断文档相关性。",
    }
    assert "input" not in payload
    assert "parameters" not in payload
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rerank_client.py::test_default_rerank_model_is_qwen3_rerank tests/test_rerank_client.py::test_build_rerank_payload_uses_qwen3_flat_request_shape -q
```

Expected: missing `DASHSCOPE_RERANK_MODEL` or missing `rerank_client`.

- [ ] Implement config and payload builder.

```python
# backend_python/config.py
DASHSCOPE_RERANK_MODEL = os.getenv("DASHSCOPE_RERANK_MODEL", "qwen3-rerank")
```

```python
# backend_python/rerank_client.py
from typing import Any

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
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rerank_client.py -q
```

Expected: config and payload tests pass.

## Task 2: Rerank Response Parsing

**Files:**
- Modify: `backend_python/rerank_client.py`
- Modify: `tests/test_rerank_client.py`

- [ ] Write the failing tests for response parsing.

```python
import pytest

from backend_python.rerank_client import extract_rerank_results


def test_extract_rerank_results_reads_top_level_results() -> None:
    data = {
        "results": [
            {"index": 1, "relevance_score": 0.92},
            {"index": 0, "relevance_score": 0.71},
        ]
    }

    assert extract_rerank_results(data) == [
        {"index": 1, "relevance_score": 0.92},
        {"index": 0, "relevance_score": 0.71},
    ]


def test_extract_rerank_results_rejects_missing_results() -> None:
    with pytest.raises(ValueError, match="Rerank response has no results"):
        extract_rerank_results({})


def test_extract_rerank_results_rejects_invalid_item() -> None:
    with pytest.raises(ValueError, match="Rerank result item is invalid"):
        extract_rerank_results({"results": [{"index": "bad"}]})
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rerank_client.py::test_extract_rerank_results_reads_top_level_results tests/test_rerank_client.py::test_extract_rerank_results_rejects_missing_results tests/test_rerank_client.py::test_extract_rerank_results_rejects_invalid_item -q
```

Expected: missing `extract_rerank_results`.

- [ ] Implement response parsing.

```python
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
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rerank_client.py -q
```

Expected: rerank client parsing tests pass.

## Task 3: Rerank API Client Error Handling

**Files:**
- Modify: `backend_python/rerank_client.py`
- Modify: `tests/test_rerank_client.py`

- [ ] Write failing tests for safe API behavior.

```python
import pytest
from fastapi import HTTPException

from backend_python.rerank_client import mask_secret, rerank_documents


def test_mask_secret_hides_api_key() -> None:
    assert mask_secret("sk-1234567890abcdef").startswith("sk-1")
    assert "4567890abc" not in mask_secret("sk-1234567890abcdef")


@pytest.mark.asyncio
async def test_rerank_documents_returns_empty_for_empty_documents() -> None:
    assert await rerank_documents(query="RAG", documents=[], top_n=3) == []


@pytest.mark.asyncio
async def test_rerank_documents_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.rerank_client.DASHSCOPE_API_KEY", "")

    with pytest.raises(HTTPException) as exc_info:
        await rerank_documents(query="RAG", documents=["doc"], top_n=1)

    assert exc_info.value.status_code == 500
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rerank_client.py::test_mask_secret_hides_api_key tests/test_rerank_client.py::test_rerank_documents_returns_empty_for_empty_documents tests/test_rerank_client.py::test_rerank_documents_requires_api_key -q
```

Expected: missing `rerank_documents` or `mask_secret`.

- [ ] Implement async API client.

```python
import httpx
from fastapi import HTTPException

from .config import DASHSCOPE_API_KEY, DASHSCOPE_RERANK_MODEL, LLM_TIMEOUT_SECONDS


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
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rerank_client.py -q
```

Expected: rerank client tests pass.

## Task 4: Apply Rerank Results to Hits

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Add: `tests/test_rag_rerank_retrieval.py`

- [ ] Write failing tests for hit formatting and rerank application.

```python
from backend_python.retrieval_service import apply_rerank_results, hit_to_rerank_document


def test_hit_to_rerank_document_includes_title_content_and_metadata() -> None:
    text = hit_to_rerank_document(
        {
            "title": "RAG 日志工程化",
            "content": "记录 query_text 和 hit_count。",
            "metadata": {"category": "technical"},
        }
    )

    assert "标题：RAG 日志工程化" in text
    assert "内容：记录 query_text 和 hit_count。" in text
    assert "technical" in text


def test_apply_rerank_results_reorders_hits_and_records_debug_fields() -> None:
    hits = [
        {"chunkId": 1, "title": "A", "score": 0.5, "matchedRetrievalModes": ["bm25"], "hybridScore": 0.5},
        {"chunkId": 2, "title": "B", "score": 0.7, "matchedRetrievalModes": ["vector"], "hybridScore": 0.7},
    ]
    reranked = apply_rerank_results(
        hits,
        [
            {"index": 1, "relevance_score": 0.93},
            {"index": 0, "relevance_score": 0.61},
        ],
        limit=2,
    )

    assert [hit["chunkId"] for hit in reranked] == [2, 1]
    assert reranked[0]["retrievalMode"] == "hybrid_rerank"
    assert reranked[0]["score"] == 0.93
    assert reranked[0]["rerankScore"] == 0.93
    assert reranked[0]["rerankIndex"] == 1
    assert reranked[0]["preRerankRank"] == 2
    assert "rerank" in reranked[0]["matchedRetrievalModes"]
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_rerank_retrieval.py::test_hit_to_rerank_document_includes_title_content_and_metadata tests/test_rag_rerank_retrieval.py::test_apply_rerank_results_reorders_hits_and_records_debug_fields -q
```

Expected: missing functions.

- [ ] Implement hit formatting and result application.

```python
def hit_to_rerank_document(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata") or {}
    metadata_text = " ".join(str(value) for value in metadata.values())
    return "\n".join(
        [
            f"标题：{hit.get('title') or ''}",
            f"内容：{hit.get('content') or ''}",
            f"元数据：{metadata_text}",
        ]
    ).strip()


def apply_rerank_results(
    hits: list[dict[str, Any]],
    rerank_results: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    reranked = []
    for result in rerank_results:
        index = int(result["index"])
        if index < 0 or index >= len(hits):
            continue
        item = {**hits[index]}
        modes = list(item.get("matchedRetrievalModes") or [])
        if "rerank" not in modes:
            modes.append("rerank")
        item["retrievalMode"] = "hybrid_rerank"
        item["matchedRetrievalModes"] = modes
        item["rerankScore"] = float(result["relevance_score"])
        item["rerankIndex"] = index
        item["preRerankRank"] = index + 1
        item["score"] = item["rerankScore"]
        reranked.append(item)
    reranked.sort(key=lambda item: item["rerankScore"], reverse=True)
    return reranked[:limit]
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_rerank_retrieval.py -q
```

Expected: hit formatting and rerank application tests pass.

## Task 5: `retrieve_chunks(mode="hybrid_rerank")`

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Modify: `tests/test_rag_rerank_retrieval.py`

- [ ] Write failing tests for hybrid_rerank mode and fallback.

```python
from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import retrieve_chunks


def create_rerank_user(db) -> User:
    suffix = uuid4().hex
    user = User(email=f"rerank-{suffix}@example.com", username=f"rerank_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_rerank_chunk(db, *, user_id: int, title: str, content: str, keywords_json: str, embedding_json: str) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base="role_knowledge",
        source_type="manual",
        content=content,
        metadata_json='{"category":"technical"}',
        chunk_count=1,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    chunk = RagChunk(
        user_id=user_id,
        document_id=document.id,
        knowledge_base="role_knowledge",
        title=title,
        content=content,
        chunk_index=0,
        keywords_json=keywords_json,
        metadata_json=document.metadata_json,
        embedding_json=embedding_json,
        embedding_model="text-embedding-v4",
        embedding_status="ready",
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_retrieve_chunks_hybrid_rerank_reorders_hybrid_candidates(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def fake_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict]:
        return [
            {"index": 1, "relevance_score": 0.96},
            {"index": 0, "relevance_score": 0.63},
        ]

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)
    monkeypatch.setattr("backend_python.retrieval_service.rerank_documents", fake_rerank_documents)

    with SessionLocal() as db:
        user = create_rerank_user(db)
        create_rerank_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text 和 quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )
        create_rerank_chunk(
            db,
            user_id=user.id,
            title="面试追问策略",
            content="面试官应该围绕候选人回答继续追问。",
            keywords_json='["面试", "追问"]',
            embedding_json="[0.7, 0.2, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG 面试追问",
            limit=2,
            mode="hybrid_rerank",
        )

    assert hits[0]["retrievalMode"] == "hybrid_rerank"
    assert hits[0]["rerankScore"] == 0.96
    assert "rerank" in hits[0]["matchedRetrievalModes"]


def test_retrieve_chunks_hybrid_rerank_falls_back_to_hybrid_when_rerank_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def fake_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict]:
        raise RuntimeError("rerank provider failed")

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)
    monkeypatch.setattr("backend_python.retrieval_service.rerank_documents", fake_rerank_documents)

    with SessionLocal() as db:
        user = create_rerank_user(db)
        create_rerank_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text 和 quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG quality",
            limit=2,
            mode="hybrid_rerank",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert "rerankScore" not in hits[0]
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_rerank_retrieval.py::test_retrieve_chunks_hybrid_rerank_reorders_hybrid_candidates tests/test_rag_rerank_retrieval.py::test_retrieve_chunks_hybrid_rerank_falls_back_to_hybrid_when_rerank_fails -q
```

Expected: `hybrid_rerank` mode missing or returns empty.

- [ ] Implement sync bridge and retrieval mode.

```python
from .rerank_client import rerank_documents


def run_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict[str, Any]]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(rerank_documents(query=query, documents=documents, top_n=top_n))
    return []


def retrieve_hybrid_rerank_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    candidates = retrieve_hybrid_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=max(limit * 3, 8),
    )
    if not candidates:
        return []
    documents = [hit_to_rerank_document(hit) for hit in candidates]
    try:
        results = run_rerank_documents(query, documents, limit)
    except Exception:
        return candidates[:limit]
    if not results:
        return candidates[:limit]
    return apply_rerank_results(candidates, results, limit=limit)
```

In `retrieve_chunks`, add:

```python
if mode == "hybrid_rerank":
    return retrieve_hybrid_rerank_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=limit,
    )
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_rerank_retrieval.py -q
```

Expected: rerank retrieval tests pass.

## Task 6: RAG Log Rerank Fields

**Files:**
- Modify: `backend_python/rag_logging.py`
- Modify: `tests/test_rag_retrieval_logs.py`

- [ ] Write the failing test for rerank log summary fields.

```python
from backend_python.rag_logging import serialize_hits


def test_serialize_hits_keeps_rerank_debug_fields() -> None:
    raw = serialize_hits(
        [
            {
                "retrievalMode": "hybrid_rerank",
                "matchedRetrievalModes": ["bm25", "vector", "rerank"],
                "chunkId": 1,
                "documentId": 2,
                "title": "RAG 日志",
                "score": 0.96,
                "hybridScore": 0.71,
                "bm25Score": 2.4,
                "vectorScore": 0.87,
                "rerankScore": 0.96,
                "rerankIndex": 1,
                "preRerankRank": 2,
            }
        ]
    )

    assert '"retrievalMode": "hybrid_rerank"' in raw
    assert '"rerankScore": 0.96' in raw
    assert '"rerankIndex": 1' in raw
    assert '"preRerankRank": 2' in raw
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_retrieval_logs.py::test_serialize_hits_keeps_rerank_debug_fields -q
```

Expected: rerank fields missing.

- [ ] Update `summarize_hit`.

```python
summary = {
    ...
    "rerankScore": hit.get("rerankScore"),
    "rerankIndex": hit.get("rerankIndex"),
    "preRerankRank": hit.get("preRerankRank"),
}
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_retrieval_logs.py -q
```

Expected: RAG log tests pass.

## Task 7: Verification

- [ ] Run focused tests.

```powershell
python -m pytest tests/test_rerank_client.py tests/test_rag_rerank_retrieval.py tests/test_rag_hybrid_retrieval.py tests/test_rag_vector_retrieval.py tests/test_retrieval_service.py tests/test_rag_retrieval_logs.py -q
```

Expected: all focused tests pass.

- [ ] Run full backend tests.

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] Run frontend smoke checks.

```powershell
node tests/frontend_rag_documents.test.mjs
node tests/frontend_rag_logs.test.mjs
node --check app.js
```

Expected: each command exits with code 0.

## Self-Review

- Spec coverage: Rerank client、payload、response parsing、hybrid_rerank retrieval、fallback、日志字段都已映射到任务。
- Scope check: 不引入多模态 rerank、不引入新框架、不切换主流程默认模式。
- Type consistency: 检索模式使用 `hybrid_rerank`；调试字段使用 camelCase：`rerankScore`、`rerankIndex`、`preRerankRank`。
- Testing discipline: 每个行为都先写失败测试，再写最小实现。

