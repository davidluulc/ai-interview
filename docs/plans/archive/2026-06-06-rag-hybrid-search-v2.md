# RAG Hybrid Search V2-3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `RetrievalService` 增加 BM25 + Vector 混合检索模式，并保证失败降级、去重融合和日志可观测。

**Architecture:** 在现有 `retrieve_chunks` 接口中新增 `mode="hybrid"`，内部复用已有 BM25 和 vector 检索能力。新增独立的分数归一化与融合函数，按 `chunkId` 合并结果，并将 Hybrid 相关字段写入返回 hit 与 RAG 日志摘要。

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite, pytest, vanilla JS smoke tests.

---

## File Structure

- Modify: `backend_python/retrieval_service.py`
  - 新增 `normalize_scores`
  - 新增 `merge_hybrid_hits`
  - 新增 `retrieve_hybrid_chunks`
  - `retrieve_chunks` 支持 `mode="hybrid"`
- Modify: `backend_python/rag_logging.py`
  - `summarize_hit` 保留 `matchedRetrievalModes`、`bm25Score`、`vectorScore`、`hybridScore`
- Add: `tests/test_rag_hybrid_retrieval.py`
  - 覆盖分数归一化、去重融合、失败降级、vector-only 召回
- Modify: `tests/test_rag_retrieval_logs.py`
  - 覆盖 hybrid hits 的日志摘要

## Task 1: Hybrid Score Normalization

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Add: `tests/test_rag_hybrid_retrieval.py`

- [ ] Write the failing test for score normalization.

```python
from backend_python.retrieval_service import normalize_scores


def test_normalize_scores_maps_values_to_zero_one_range() -> None:
    assert normalize_scores([2.0, 4.0, 6.0]) == [0.0, 0.5, 1.0]


def test_normalize_scores_gives_single_positive_score_full_weight() -> None:
    assert normalize_scores([3.5]) == [1.0]


def test_normalize_scores_handles_empty_and_flat_scores() -> None:
    assert normalize_scores([]) == []
    assert normalize_scores([0.0, 0.0]) == [0.0, 0.0]
    assert normalize_scores([2.0, 2.0]) == [1.0, 1.0]
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py::test_normalize_scores_maps_values_to_zero_one_range tests/test_rag_hybrid_retrieval.py::test_normalize_scores_gives_single_positive_score_full_weight tests/test_rag_hybrid_retrieval.py::test_normalize_scores_handles_empty_and_flat_scores -q
```

Expected: import error or missing `normalize_scores`.

- [ ] Implement minimal normalization.

```python
def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    if all(score <= 0 for score in scores):
        return [0.0 for _ in scores]
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0 if score > 0 else 0.0 for score in scores]
    return [round((score - min_score) / (max_score - min_score), 4) for score in scores]
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py -q
```

Expected: normalization tests pass.

## Task 2: Hybrid Hit Merge

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Modify: `tests/test_rag_hybrid_retrieval.py`

- [ ] Write the failing test for deduplication and score fusion.

```python
from backend_python.retrieval_service import merge_hybrid_hits


def test_merge_hybrid_hits_deduplicates_by_chunk_id_and_records_modes() -> None:
    bm25_hits = [
        {
            "retrievalMode": "bm25",
            "chunkId": 1,
            "documentId": 10,
            "title": "RAG 日志",
            "content": "记录 query_text 和 hit_count",
            "score": 3.0,
            "matchedTokens": ["rag"],
            "matchedKeywords": ["RAG"],
            "metadata": {"category": "technical"},
        }
    ]
    vector_hits = [
        {
            "retrievalMode": "vector",
            "chunkId": 1,
            "documentId": 10,
            "title": "RAG 日志",
            "content": "记录 query_text 和 hit_count",
            "score": 0.8,
            "matchedTokens": [],
            "matchedKeywords": [],
            "metadata": {"category": "technical"},
            "embeddingStatus": "ready",
        }
    ]

    merged = merge_hybrid_hits(bm25_hits, vector_hits, limit=3)

    assert len(merged) == 1
    assert merged[0]["retrievalMode"] == "hybrid"
    assert merged[0]["matchedRetrievalModes"] == ["bm25", "vector"]
    assert merged[0]["bm25Score"] == 3.0
    assert merged[0]["vectorScore"] == 0.8
    assert merged[0]["score"] == merged[0]["hybridScore"]
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py::test_merge_hybrid_hits_deduplicates_by_chunk_id_and_records_modes -q
```

Expected: missing `merge_hybrid_hits`.

- [ ] Implement minimal merge logic.

```python
def merge_hybrid_hits(
    bm25_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    *,
    limit: int,
    bm25_weight: float = 0.6,
    vector_weight: float = 0.4,
) -> list[dict[str, Any]]:
    bm25_normalized = normalize_scores([float(hit.get("score") or 0) for hit in bm25_hits])
    vector_normalized = normalize_scores([float(hit.get("score") or 0) for hit in vector_hits])
    merged: dict[int, dict[str, Any]] = {}

    def ensure_item(hit: dict[str, Any]) -> dict[str, Any]:
        chunk_id = int(hit.get("chunkId") or 0)
        if chunk_id not in merged:
            merged[chunk_id] = {
                **hit,
                "retrievalMode": "hybrid",
                "matchedRetrievalModes": [],
                "bm25Score": 0.0,
                "vectorScore": 0.0,
                "hybridScore": 0.0,
            }
        return merged[chunk_id]

    for hit, normalized_score in zip(bm25_hits, bm25_normalized, strict=False):
        item = ensure_item(hit)
        item["bm25Score"] = hit.get("score") or 0.0
        item["hybridScore"] += bm25_weight * normalized_score
        item["matchedRetrievalModes"].append("bm25")

    for hit, normalized_score in zip(vector_hits, vector_normalized, strict=False):
        item = ensure_item(hit)
        item["vectorScore"] = hit.get("score") or 0.0
        item["hybridScore"] += vector_weight * normalized_score
        if "vector" not in item["matchedRetrievalModes"]:
            item["matchedRetrievalModes"].append("vector")

    results = []
    for item in merged.values():
        item["hybridScore"] = round(float(item["hybridScore"]), 4)
        item["score"] = item["hybridScore"]
        results.append(item)
    results.sort(key=lambda item: item["hybridScore"], reverse=True)
    return results[:limit]
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py -q
```

Expected: normalization and merge tests pass.

## Task 3: `retrieve_chunks(mode="hybrid")`

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Modify: `tests/test_rag_hybrid_retrieval.py`

- [ ] Write the failing test for real database hybrid retrieval.

```python
from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import retrieve_chunks


def create_hybrid_user(db) -> User:
    suffix = uuid4().hex
    user = User(email=f"hybrid-{suffix}@example.com", username=f"hybrid_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_hybrid_chunk(db, *, user_id: int, title: str, content: str, keywords_json: str, embedding_json: str) -> RagChunk:
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


def test_retrieve_chunks_hybrid_combines_bm25_and_vector(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_hybrid_user(db)
        create_hybrid_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text、retriever_name、hit_count、quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )
        create_hybrid_chunk(
            db,
            user_id=user.id,
            title="FastAPI 模块化",
            content="FastAPI 使用 APIRouter 拆分后端模块。",
            keywords_json='["FastAPI", "APIRouter"]',
            embedding_json="[0.1, 0.8, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG quality 命中日志",
            limit=3,
            mode="hybrid",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert "bm25" in hits[0]["matchedRetrievalModes"]
    assert "vector" in hits[0]["matchedRetrievalModes"]
    assert hits[0]["title"] == "RAG 日志工程化"
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py::test_retrieve_chunks_hybrid_combines_bm25_and_vector -q
```

Expected: `retrieve_chunks(mode="hybrid")` returns empty or missing hybrid fields.

- [ ] Implement `retrieve_hybrid_chunks` and route from `retrieve_chunks`.

```python
def retrieve_hybrid_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    bm25_hits = retrieve_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=max(limit * 2, 6),
        mode="bm25",
    )
    vector_hits = retrieve_vector_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=max(limit * 2, 6),
    )
    return merge_hybrid_hits(bm25_hits, vector_hits, limit=limit)
```

In `retrieve_chunks`, add the hybrid branch before the unknown-mode guard:

```python
if mode == "hybrid":
    return retrieve_hybrid_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=limit,
    )
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py -q
```

Expected: hybrid retrieval tests pass.

## Task 4: Hybrid Fallback Behavior

**Files:**
- Modify: `tests/test_rag_hybrid_retrieval.py`
- Modify: `backend_python/retrieval_service.py`

- [ ] Write the failing test for vector failure fallback.

```python
def test_retrieve_chunks_hybrid_falls_back_to_bm25_when_vector_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        raise RuntimeError("embedding provider failed")

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_hybrid_user(db)
        create_hybrid_chunk(
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
            limit=3,
            mode="hybrid",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert hits[0]["matchedRetrievalModes"] == ["bm25"]
    assert hits[0]["vectorScore"] == 0.0
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py::test_retrieve_chunks_hybrid_falls_back_to_bm25_when_vector_fails -q
```

Expected: fallback fields missing or mode remains `bm25`.

- [ ] Adjust merge logic so BM25-only hits are still converted to hybrid hits.

No new public function is needed. Ensure `merge_hybrid_hits` always sets:

```python
item["retrievalMode"] = "hybrid"
item["matchedRetrievalModes"] = ["bm25"]
item["vectorScore"] = 0.0
item["score"] = item["hybridScore"]
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py -q
```

Expected: fallback test passes with all previous hybrid tests.

## Task 5: RAG Log Summary Fields

**Files:**
- Modify: `backend_python/rag_logging.py`
- Modify: `tests/test_rag_retrieval_logs.py`

- [ ] Write the failing test for hybrid log summaries.

```python
from backend_python.rag_logging import serialize_hits


def test_serialize_hits_keeps_hybrid_debug_fields() -> None:
    raw = serialize_hits(
        [
            {
                "retrievalMode": "hybrid",
                "matchedRetrievalModes": ["bm25", "vector"],
                "chunkId": 1,
                "documentId": 2,
                "title": "RAG 日志",
                "score": 0.91,
                "hybridScore": 0.91,
                "bm25Score": 2.4,
                "vectorScore": 0.87,
                "matchedTokens": ["rag"],
                "matchedKeywords": ["RAG"],
            }
        ]
    )

    assert '"matchedRetrievalModes": ["bm25", "vector"]' in raw
    assert '"hybridScore": 0.91' in raw
    assert '"bm25Score": 2.4' in raw
    assert '"vectorScore": 0.87' in raw
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_retrieval_logs.py::test_serialize_hits_keeps_hybrid_debug_fields -q
```

Expected: hybrid fields are missing from serialized summary.

- [ ] Update `summarize_hit`.

```python
summary = {
    ...
    "retrievalMode": hit.get("retrievalMode") or hit.get("retrieval_mode") or "",
    "matchedRetrievalModes": hit.get("matchedRetrievalModes") or [],
    "hybridScore": hit.get("hybridScore"),
    "bm25Score": hit.get("bm25Score"),
    "vectorScore": hit.get("vectorScore"),
}
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_retrieval_logs.py -q
```

Expected: RAG log tests pass.

## Task 6: Focused Regression

**Files:**
- No production edits unless a regression appears.

- [ ] Run focused backend tests.

```powershell
python -m pytest tests/test_rag_hybrid_retrieval.py tests/test_rag_vector_retrieval.py tests/test_retrieval_service.py tests/test_rag_retrieval_logs.py -q
```

Expected: all selected tests pass.

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

- Spec coverage: Hybrid mode, score normalization, result merge, deduplication, vector fallback, and log observability are all mapped to tasks.
- Scope check: Rerank, vector database, semantic chunking, async queue, and frontend redesign are excluded from this plan.
- Type consistency: Public retrieval mode values are `bm25`、`vector`、`hybrid`; API hit fields use camelCase where existing code already does.
- Testing discipline: Each behavior starts with a failing pytest case before implementation.

