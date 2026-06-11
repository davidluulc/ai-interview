# Application Profile Interview Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link saved application profiles to interview records so the product has a clear profile → interview → report loop.

**Architecture:** Add a nullable `application_profile_id` on `InterviewRecord`, validate ownership when saving history, and include a compact `applicationProfile` summary in history responses. The frontend stores the selected profile id when a saved profile is used and submits it with interview/report payloads.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, vanilla HTML/CSS/JS.

---

### Task 1: Backend Link And Tests

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/routes/history.py`
- Create: `alembic/versions/20260604_0004_link_interviews_to_application_profiles.py`
- Modify: `backend_python/database.py`
- Test: `tests/test_history_application_profile_link.py`

- [ ] Write failing tests that saving history with `applicationProfileId` returns the profile summary.
- [ ] Write failing tests that a user cannot attach another user's profile.
- [ ] Add nullable foreign key and relationship.
- [ ] Validate profile ownership in `/api/history`.
- [ ] Serialize profile summary in history list/detail responses.
- [ ] Run targeted and full backend tests.

### Task 2: Frontend Selected Profile Flow

**Files:**
- Modify: `app.js`
- Modify: `styles.css`

- [ ] Track `session.selectedProfileId`.
- [ ] Set it when a user clicks “选用”.
- [ ] Include `applicationProfileId` in report save payloads and interview question profile payload.
- [ ] Show the source profile in history cards and review header.
- [ ] Run `node --check app.js` and browser verify.
