# Candidate Memory Profile Priority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make candidate memory RAG prioritize interview history from the selected application profile, then fall back to user-global history when profile history is sparse.

**Architecture:** Extend `retrieve_candidate_memory` with `application_profile_id` and `min_profile_records`. It first retrieves/scoring records for the current user and profile; if fewer than the threshold are available, it appends scored global user records excluding the current profile.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, existing SQLite models.

---

### Task 1: Tests First

**Files:**
- Modify: `tests/test_candidate_memory.py`
- Modify: `tests/test_rag_retrieval_logs.py`

- [ ] Add a test that profile-specific history is ranked before unrelated global history.
- [ ] Add a test that global history is included when profile-specific history is sparse.
- [ ] Add a test that next-question retrieval logs preserve `applicationProfileId`.

### Task 2: Retrieval Implementation

**Files:**
- Modify: `backend_python/candidate_memory.py`
- Modify: `backend_python/routes/interview.py`
- Modify: `backend_python/routes/rag.py`

- [ ] Add `application_profile_id` argument to candidate memory retrieval.
- [ ] Filter candidate memory by user before applying profile priority.
- [ ] Pass `payload.applicationProfileId` from question/report generation.
- [ ] Accept `applicationProfileId` in RAG debug query params.

### Task 3: Verification

**Commands:**
- `python -m pytest tests/test_candidate_memory.py tests/test_rag_retrieval_logs.py -q`
- `python -m pytest -q`
- `node --check app.js`
