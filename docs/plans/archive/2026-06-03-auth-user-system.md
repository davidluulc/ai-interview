# Auth User System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a formal JWT double-token user authentication MVP and isolate interview history by authenticated user.

**Architecture:** Add SQLAlchemy `User` and `RefreshToken` models plus an Alembic migration. Implement password hashing and JWT helpers in `backend_python/auth.py`, expose auth APIs under `backend_python/routes/auth.py`, and require `get_current_user` for history and candidate memory APIs.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PyJWT, bcrypt, pytest, browser localStorage for temporary frontend token storage.

---

## File Structure

- Modify `requirements.txt`: add `PyJWT` and `bcrypt`.
- Modify `backend_python/config.py`: add auth settings.
- Modify `backend_python/db_models.py`: add `User`, `RefreshToken`, and `InterviewRecord.user_id`.
- Create `backend_python/auth.py`: password hashing, token creation, token verification, refresh token hashing.
- Create `backend_python/routes/auth.py`: register, login, refresh, logout, me.
- Modify `backend_python/routes/history.py`: require current user and filter by `user_id`.
- Modify `backend_python/candidate_memory.py`: accept optional `user_id` and filter memory records.
- Modify `backend_python/routes/interview.py`, `memory.py`, `rag.py`: pass current user where user-specific memory is needed.
- Modify `backend_python/main.py`: include auth router.
- Create `alembic/versions/20260603_0002_add_users_and_refresh_tokens.py`.
- Create tests for auth and user history isolation.
- Modify frontend files with a minimal auth panel.
- Update README and `.env.example`.

---

## Implementation Tasks

1. Add failing auth helper tests.
2. Implement auth helpers and dependencies.
3. Add failing API flow tests.
4. Add database models and migration.
5. Implement auth routes.
6. Protect and filter history by user.
7. Connect candidate memory filtering to current user where appropriate.
8. Add minimal frontend auth panel and token-aware fetch helper.
9. Update docs.
10. Run dependency install, tests, Alembic history, temporary migration verification, and FastAPI import check.
