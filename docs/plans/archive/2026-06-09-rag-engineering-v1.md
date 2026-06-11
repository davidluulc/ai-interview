# RAG Engineering V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the AI interview system RAG layer into a metadata-consistent, explainable, measurable retrieval subsystem without changing deployment or adding new vector database dependencies.

**Architecture:** Add small focused modules around the existing RAG implementation instead of rewriting retrieval. `rag_metadata.py` standardizes chunk metadata, `rag_explain.py` turns hits into user/developer explanations, existing `rag_evaluation.py` and `rag_evaluation_seed.py` become the measurable quality baseline, and existing RAG logs/frontend panels are enhanced to expose the new summaries.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, pytest, plain JavaScript `.mjs` tests; no LangGraph, no LangChain, no Docker/Nginx/cloud deployment, no new vector database.

---

## File Structure

- Create `backend_python/rag_metadata.py`
  - Normalizes hit metadata into a stable camelCase summary.
  - Provides `normalize_rag_hit_metadata(...)`, `normalize_rag_hit(...)`, and metadata matching helpers.

- Create `backend_python/rag_explain.py`
  - Builds ordinary user-facing question rationale.
  - Builds developer-facing hit debug summaries.

- Modify `backend_python/rag_logging.py`
  - Uses normalized metadata in `summarize_hit(...)`.
  - Keeps existing fields compatible for frontend and tests.

- Modify `backend_python/rag_evaluation_seed.py`
  - Ensures at least 12 fixed cases, four per RAG family.

- Modify `backend_python/rag_evaluation.py`
  - Extends evaluation output with metadata match rate and empty recall detection if missing.

- Modify frontend tests and minimal rendering:
  - `tests/frontend_rag_logs.test.mjs`
  - `tests/frontend_rag_quality.test.mjs`
  - `app.js` only where existing debug panels need extra fields.

---

### Task 1: RAG Metadata Standardization

**Files:**
- Create: `backend_python/rag_metadata.py`
- Create: `tests/test_rag_metadata.py`
- Modify: `backend_python/rag_logging.py`

- [x] **Step 1: Write failing metadata tests**

Create `tests/test_rag_metadata.py` with tests for:

```python
from backend_python.rag_metadata import normalize_rag_hit, normalize_rag_hit_metadata, metadata_matches


def test_normalize_rag_hit_metadata_prefers_camel_case_and_existing_metadata():
    metadata = normalize_rag_hit_metadata(
        {
            "metadata": {"position_tag": "ai_app_intern", "interview_stage": "技术追问", "tags": ["RAG"]},
            "knowledgeBase": "role_knowledge",
            "documentId": 12,
            "chunkId": 81,
            "source": "database",
        },
        retriever_name="role_knowledge",
    )

    assert metadata["knowledgeBase"] == "role_knowledge"
    assert metadata["positionTag"] == "ai_app_intern"
    assert metadata["interviewStage"] == "技术追问"
    assert metadata["tags"] == ["RAG"]
    assert metadata["documentId"] == 12
    assert metadata["chunkId"] == 81
    assert metadata["source"] == "database"


def test_normalize_rag_hit_keeps_score_title_tokens_and_metadata():
    hit = normalize_rag_hit(
        {
            "score": 0.91,
            "title": "RAG 召回链路",
            "matchedTokens": ["rag", "召回"],
            "metadata": {"positionTag": "ai_app_intern"},
        },
        retriever_name="role_knowledge",
    )

    assert hit["score"] == 0.91
    assert hit["title"] == "RAG 召回链路"
    assert hit["matchedTokens"] == ["rag", "召回"]
    assert hit["metadata"]["knowledgeBase"] == "role_knowledge"
    assert hit["metadata"]["positionTag"] == "ai_app_intern"


def test_metadata_matches_checks_expected_filters():
    metadata = {"knowledgeBase": "question_bank", "positionTag": "ai_app_intern", "interviewStage": "技术追问"}

    assert metadata_matches(metadata, expected_knowledge_base="question_bank", expected_position_tag="ai_app_intern")
    assert not metadata_matches(metadata, expected_stage="项目背景")
```

- [x] **Step 2: Run metadata tests and verify red**

Run:

```powershell
python -m pytest tests/test_rag_metadata.py -q
```

Expected: fail because `backend_python.rag_metadata` does not exist yet.

- [x] **Step 3: Implement minimal metadata module**

Implement normalization with stable keys:

```text
knowledgeBase, documentId, chunkId, title, source, ownerUserId,
applicationProfileId, positionTag, interviewStage, difficulty,
tags, createdAt
```

- [x] **Step 4: Integrate metadata into RAG logs**

Modify `rag_logging.summarize_hit(...)` so each serialized hit includes `metadata` from `normalize_rag_hit(...)` while preserving existing debug fields like `retrievalMode`, `hybridScore`, and `rerankScore`.

- [x] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_rag_metadata.py tests/test_rag_retrieval_logs.py -q
```

Expected: pass.

---

### Task 2: RAG Hit Explanation

**Files:**
- Create: `backend_python/rag_explain.py`
- Create: `tests/test_rag_explain.py`
- Modify: `backend_python/rag_logging.py` if needed

- [x] **Step 1: Write failing explanation tests**

Tests must verify that:

- non-empty hits produce a user-facing reason with title, retriever, and matched tokens.
- empty hits produce a clear fallback explanation.
- developer summaries include score, metadata, retrieval mode, and used-in-prompt status.

- [x] **Step 2: Implement explanation helpers**

Add:

```text
build_user_rag_reason(...)
build_developer_rag_debug_summary(...)
```

- [x] **Step 3: Run tests**

Run:

```powershell
python -m pytest tests/test_rag_explain.py -q
```

Expected: pass.

---

### Task 3: RAG Evaluation Baseline

**Files:**
- Modify: `backend_python/rag_evaluation_seed.py`
- Modify: `backend_python/rag_evaluation.py`
- Modify/Create: `tests/test_rag_evaluation.py`

- [x] **Step 1: Expand fixed evaluation cases**

Ensure at least 12 cases:

- four `role_knowledge`
- four `question_bank`
- four `candidate_memory`

- [x] **Step 2: Add metadata-aware evaluation**

Extend evaluation to include:

```text
metadataMatch
emptyRecall
```

- [x] **Step 3: Run evaluation tests**

Run:

```powershell
python -m pytest tests/test_rag_evaluation.py tests/test_rag_evaluation_seed.py -q
```

Expected: pass.

---

### Task 4: Frontend RAG Debug Display Enhancement

**Files:**
- Modify: `tests/frontend_rag_logs.test.mjs`
- Modify: `tests/frontend_rag_quality.test.mjs`
- Modify: `app.js`

- [x] **Step 1: Update frontend tests first**

Add assertions that RAG logs or quality panels can show:

```text
queryText, retrieverName, retrievalMode, hitCount,
score, matchedTokens/matchedKeywords, metadata, usedInPrompt
```

- [x] **Step 2: Implement minimal rendering**

Keep ordinary UI compact and put detailed JSON-like metadata in existing collapsible debug panels.

- [x] **Step 3: Run frontend focused tests**

Run:

```powershell
node tests/frontend_rag_logs.test.mjs
node tests/frontend_rag_quality.test.mjs
```

Expected: pass.

---

### Task 5: Full Verification

**Files:**
- No new files expected.

- [x] **Step 1: Run all backend tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [x] **Step 2: Run all frontend `.mjs` tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend scripts pass.

---

## Self-Review

- Spec coverage: This plan covers metadata, hit explanations, evaluation baseline, RAG debug frontend display, compatibility, and full verification.
- Scope control: This plan does not introduce LangGraph, LangChain, Docker, Nginx, cloud deployment, or a new vector database.
- TDD: Each implementation task starts with failing tests.
- Compatibility: Existing `/api/interview/next-question` and `/api/interview/report` are protected by current backend tests and full verification.
