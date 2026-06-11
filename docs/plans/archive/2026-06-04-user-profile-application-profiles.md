# User Center And Application Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a logged-in user center and reusable application profiles so users can save resume/JD/company context and start interviews from a saved profile.

**Architecture:** Keep the MVP simple: one SQLAlchemy model for application profiles, one FastAPI router under `/api/application-profiles`, and front-end integration in the existing single-page app. User ownership is enforced through `get_current_user`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, vanilla HTML/CSS/JS.

---

### Task 1: Backend Application Profiles

**Files:**
- Modify: `backend_python/db_models.py`
- Create: `backend_python/routes/application_profiles.py`
- Modify: `backend_python/main.py`
- Create: `alembic/versions/20260604_0003_add_application_profiles.py`
- Test: `tests/test_application_profiles.py`

- [ ] Write failing tests for create/list/get/delete and user isolation.
- [ ] Run `python -m pytest tests/test_application_profiles.py -q` and verify route/model failures.
- [ ] Add `ApplicationProfile` model with `user_id`, `title`, `target_role`, `application_type`, `resume`, `jd`, `company`, `position_tag`, timestamps.
- [ ] Add authenticated CRUD endpoints.
- [ ] Add Alembic migration and SQLite compatibility helper.
- [ ] Run targeted and full backend tests.

### Task 2: Frontend User Center

**Files:**
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `app.js`
- Test: `node --check app.js`

- [ ] Add a user center section with account summary, training stats, and saved profile list.
- [ ] Add profile save/load/delete buttons.
- [ ] Use `authFetch` for profile endpoints so token refresh works automatically.
- [ ] Start interview from selected profile by filling the existing form fields.
- [ ] Verify in browser at `http://localhost:8000/`.

### Task 3: Final Verification

**Commands:**
- `python -m pytest -q`
- `node tests/frontend_auth_refresh.test.mjs`
- `node --check app.js`

**Browser checks:**
- Logged-in account card is visible.
- User center renders.
- Saving a profile creates an item.
- Selecting a profile fills the interview setup form.
