# RAG RetrievalService V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified RetrievalService with BM25 retrieval for database chunks used by role knowledge RAG and question bank RAG.

**Architecture:** Create `backend_python/retrieval_service.py` as the shared retrieval engine. Keep `backend_python/rag.py` and `backend_python/question_rag.py` responsible for domain-specific conversion and JSON seed fallback. Update RAG logging to infer `bm25` from database BM25 hits while leaving candidate memory unchanged.

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite, pytest.

---

## Why BM25 First

BM25 is the right first stage because it improves retrieval quality while staying local, deterministic, cheap, and testable. If BM25, embedding, hybrid search, and rerank are implemented at the same time, any behavior change becomes hard to diagnose: a bad result could come from tokenization, vector quality, fusion weights, rerank prompt/model behavior, metadata filtering, or prompt usage. Building one layer at a time creates a measurable baseline.

This is also how real engineering teams reduce risk: land a small reversible change, verify it, then build the next layer on top. BM25 gives us a stable `RetrievalService` interface; embedding and rerank can later plug into the same interface without rewriting business code.

## File Structure

- Create `backend_python/retrieval_service.py`: tokenization, BM25 scoring, database chunk retrieval.
- Modify `backend_python/rag.py`: replace direct `retrieve_database_chunks` use with `retrieve_chunks`.
- Modify `backend_python/question_rag.py`: replace direct `retrieve_database_chunks` use with `retrieve_chunks`.
- Modify `backend_python/rag_logging.py`: infer retrieval mode from hit-level `retrievalMode`.
- Modify `backend_python/routes/interview.py`: pass inferred retrieval mode to RAG logs.
- Add `tests/test_retrieval_service.py`: unit tests for BM25 and retrieval result shape.
- Modify `tests/test_rag_database_retrieval.py`: assert role/question database hits are BM25 hits.
- Modify `tests/test_rag_retrieval_logs.py`: assert logs record `bm25` when database chunks are hit.

## Task 1: RetrievalService BM25

**Files:**
- Create: `backend_python/retrieval_service.py`
- Test: `tests/test_retrieval_service.py`

- [ ] **Step 1: Write failing BM25 service tests**

Create `tests/test_retrieval_service.py`:

```python
from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import bm25_score, retrieve_chunks, tokenize


def create_user(db, prefix: str = "retrieval_service") -> User:
    suffix = uuid4().hex
    user = User(email=f"{prefix}-{suffix}@example.com", username=f"{prefix}_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_chunk(
    db,
    *,
    user_id: int,
    knowledge_base: str,
    title: str,
    content: str,
    keywords_json: str = "[]",
    metadata_json: str = "{}",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
        source_type="manual",
        content=content,
        metadata_json=metadata_json,
        chunk_count=1,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    chunk = RagChunk(
        user_id=user_id,
        document_id=document.id,
        knowledge_base=knowledge_base,
        title=title,
        content=content,
        chunk_index=0,
        keywords_json=keywords_json,
        metadata_json=metadata_json,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_tokenize_keeps_chinese_terms_and_technical_words() -> None:
    assert tokenize("FastAPI RAG 命中日志 qwen3-rerank") == ["fastapi", "rag", "命中日志", "qwen3-rerank"]


def test_bm25_score_prefers_matching_document() -> None:
    query_tokens = tokenize("RAG 命中日志")
    documents = [
        tokenize("RAG 命中日志 召回质量"),
        tokenize("FastAPI 路由 SQLAlchemy"),
    ]

    matching_score = bm25_score(query_tokens, documents[0], documents)
    unrelated_score = bm25_score(query_tokens, documents[1], documents)

    assert matching_score > unrelated_score
    assert matching_score > 0


def test_retrieve_chunks_returns_bm25_database_hits() -> None:
    with SessionLocal() as db:
        user = create_user(db)
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="RAG 日志工程化",
            content="RAG 命中日志需要记录 query、retriever、hit_count 和 quality。",
            keywords_json='["RAG", "命中日志", "quality"]',
        )
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="FastAPI 路由拆分",
            content="FastAPI 项目可以用 APIRouter 拆分路由。",
            keywords_json='["FastAPI", "APIRouter"]',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="请追问 RAG 命中日志 quality 字段",
            limit=2,
        )

    assert hits
    assert hits[0]["retrievalMode"] == "bm25"
    assert hits[0]["source"] == "database"
    assert "RAG" in hits[0]["matchedTokens"] or "命中日志" in hits[0]["matchedTokens"]
    assert hits[0]["score"] > 0
    assert hits[0]["title"] == "RAG 日志工程化"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_retrieval_service.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend_python.retrieval_service'`.

- [ ] **Step 3: Implement RetrievalService**

Create `backend_python/retrieval_service.py`:

```python
import json
import math
import re
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import RagChunk
from .rag_store import VALID_KNOWLEDGE_BASES, parse_json


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", str(text or "").lower())
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        if token not in seen:
            result.append(token)
            seen.add(token)
    return result


def chunk_text(chunk: RagChunk) -> str:
    keywords = " ".join(str(item) for item in parse_json(chunk.keywords_json, []))
    metadata = " ".join(str(value) for value in parse_json(chunk.metadata_json, {}).values())
    return f"{chunk.title} {chunk.content} {keywords} {metadata}"


def bm25_score(
    query_tokens: list[str],
    document_tokens: list[str],
    corpus_tokens: list[list[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    if not query_tokens or not document_tokens or not corpus_tokens:
        return 0.0

    term_frequency = Counter(document_tokens)
    document_count = len(corpus_tokens)
    average_length = sum(len(tokens) for tokens in corpus_tokens) / max(document_count, 1)
    document_length = len(document_tokens)
    score = 0.0

    for token in query_tokens:
        frequency = term_frequency[token]
        if frequency <= 0:
            continue
        document_frequency = sum(1 for tokens in corpus_tokens if token in tokens)
        idf = math.log(1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5))
        denominator = frequency + k1 * (1 - b + b * document_length / max(average_length, 1))
        score += idf * ((frequency * (k1 + 1)) / denominator)

    return round(score, 4)


def matched_tokens(query_tokens: list[str], document_tokens: list[str]) -> list[str]:
    document_token_set = set(document_tokens)
    return [token for token in query_tokens if token in document_token_set][:8]


def retrieve_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int = 3,
    mode: str = "bm25",
) -> list[dict[str, Any]]:
    if mode != "bm25" or knowledge_base not in VALID_KNOWLEDGE_BASES or not str(query or "").strip():
        return []

    chunks = db.scalars(
        select(RagChunk)
        .where(RagChunk.user_id == user_id, RagChunk.knowledge_base == knowledge_base)
        .order_by(RagChunk.created_at.desc(), RagChunk.id.desc())
        .limit(120)
    ).all()
    if not chunks:
        return []

    query_tokens = tokenize(query)
    corpus_tokens = [tokenize(chunk_text(chunk)) for chunk in chunks]
    scored: list[dict[str, Any]] = []

    for chunk, document_tokens in zip(chunks, corpus_tokens, strict=False):
        score = bm25_score(query_tokens, document_tokens, corpus_tokens)
        if score <= 0:
            continue
        scored.append(
            {
                "source": "database",
                "retrievalMode": "bm25",
                "chunkId": chunk.id,
                "documentId": chunk.document_id,
                "knowledgeBase": chunk.knowledge_base,
                "title": chunk.title,
                "content": chunk.content,
                "score": score,
                "matchedTokens": matched_tokens(query_tokens, document_tokens),
                "matchedKeywords": matched_tokens(query_tokens, tokenize(" ".join(parse_json(chunk.keywords_json, [])))),
                "metadata": parse_json(chunk.metadata_json, {}),
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m pytest tests/test_retrieval_service.py -q`

Expected: PASS.

## Task 2: Wire RetrievalService Into Role and Question RAG

**Files:**
- Modify: `backend_python/rag.py`
- Modify: `backend_python/question_rag.py`
- Modify: `tests/test_rag_database_retrieval.py`

- [ ] **Step 1: Write failing integration expectations**

Modify `tests/test_rag_database_retrieval.py`:

```python
assert items[0]["retrievalMode"] == "bm25"
```

Add it after `assert items[0]["source"] == "database"` in `test_role_rag_retrieves_user_database_chunk_first`.

Add:

```python
assert questions[0]["retrievalMode"] == "bm25"
```

after `assert questions[0]["source"] == "database"` in `test_question_rag_retrieves_user_database_chunk_first`.

- [ ] **Step 2: Run integration tests to verify RED**

Run: `python -m pytest tests/test_rag_database_retrieval.py -q`

Expected: FAIL because converted role/question hits do not include `retrievalMode`.

- [ ] **Step 3: Wire service into `rag.py`**

Change import:

```python
from .retrieval_service import retrieve_chunks
```

Replace `retrieve_database_chunks(...)` call with:

```python
database_hits = retrieve_chunks(
    db,
    user_id=user_id,
    knowledge_base="role_knowledge",
    query=query,
    limit=limit,
)
```

In `convert_database_role_hit`, add:

```python
"retrievalMode": hit.get("retrievalMode") or "bm25",
```

- [ ] **Step 4: Wire service into `question_rag.py`**

Change import:

```python
from .retrieval_service import retrieve_chunks
```

Replace `retrieve_database_chunks(...)` call with:

```python
database_hits = retrieve_chunks(
    db,
    user_id=user_id,
    knowledge_base="question_bank",
    query=query,
    limit=limit,
)
```

In `convert_database_question_hit`, add:

```python
"retrievalMode": hit.get("retrievalMode") or "bm25",
```

- [ ] **Step 5: Run integration tests to verify GREEN**

Run: `python -m pytest tests/test_rag_database_retrieval.py -q`

Expected: PASS.

## Task 3: RAG Logs Record BM25 Mode

**Files:**
- Modify: `backend_python/rag_logging.py`
- Modify: `backend_python/routes/interview.py`
- Modify: `tests/test_rag_retrieval_logs.py`

- [ ] **Step 1: Write failing log mode test**

In `tests/test_rag_retrieval_logs.py`, add a test that creates an authenticated user, posts one role knowledge document, triggers next question, then asserts the role knowledge log uses BM25.

```python
def test_next_question_logs_bm25_for_database_rag_hits(monkeypatch) -> None:
    from backend_python.routes import interview

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"rag-bm25-log-{suffix}@example.com", f"rag_bm25_{suffix[:8]}")

    document_response = client.post(
        "/api/rag/documents",
        headers=auth_headers(tokens),
        json={
            "title": "RAG BM25 日志知识",
            "knowledgeBase": "role_knowledge",
            "sourceType": "manual",
            "content": "RAG 命中日志需要记录 query、retriever、hit_count、quality 和 used_in_prompt。",
            "metadata": {"category": "technical"},
        },
    )
    assert document_response.status_code == 200

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 RAG 命中日志",
                "jd": "要求理解 RAG 命中日志和 quality",
            },
            "history": [],
            "nextStage": "技术追问",
        },
    )
    assert response.status_code == 200

    logs = client.get("/api/rag/logs/recent", headers=auth_headers(tokens)).json()["items"]
    role_log = next(item for item in logs if item["retrieverName"] == "role_knowledge")
    assert role_log["retrievalMode"] == "bm25"
```

- [ ] **Step 2: Run log test to verify RED**

Run: `python -m pytest tests/test_rag_retrieval_logs.py::test_next_question_logs_bm25_for_database_rag_hits -q`

Expected: FAIL because `log_retrievals` currently passes `retrieval_mode="keyword"` for all retrievers.

- [ ] **Step 3: Add retrieval mode inference**

In `backend_python/rag_logging.py`, add:

```python
def infer_retrieval_mode(hits: list[dict[str, Any]], fallback: str = "keyword") -> str:
    for hit in hits:
        mode = hit.get("retrievalMode") or hit.get("retrieval_mode")
        if mode:
            return str(mode)
    return fallback
```

In `backend_python/routes/interview.py`, update import:

```python
from ..rag_logging import build_rag_query, create_rag_log, infer_retrieval_mode
```

In `log_retrievals`, change:

```python
retrieval_mode="keyword",
```

to:

```python
retrieval_mode=infer_retrieval_mode(hits),
```

- [ ] **Step 4: Run log test to verify GREEN**

Run: `python -m pytest tests/test_rag_retrieval_logs.py::test_next_question_logs_bm25_for_database_rag_hits -q`

Expected: PASS.

## Task 4: Full Verification

**Files:**
- No additional production files.

- [ ] **Step 1: Run focused backend verification**

Run:

```powershell
python -m pytest tests/test_retrieval_service.py tests/test_rag_database_retrieval.py tests/test_rag_retrieval_logs.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full backend regression**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend smoke regression**

Run:

```powershell
node tests/frontend_rag_logs.test.mjs
node tests/frontend_rag_quality.test.mjs
node --check app.js
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan covers RetrievalService, BM25 scoring, role RAG integration, question RAG integration, RAG log retrieval mode, tests, and regression verification.
- Placeholder scan: No implementation step depends on TBD behavior.
- Type consistency: The result field is consistently named `retrievalMode` in hit dictionaries and mapped to `retrieval_mode` in persisted logs.
