# Repository Showcase Cleanup V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository into a polished public project page while keeping job-search packaging materials private outside the GitHub repo.

**Architecture:** Public repository documentation explains the product, architecture, data flow, deployment, status, and engineering troubleshooting. Private career documents live outside the repo and contain BOSS resume text, interview scripts, and role-specific positioning. Code directories and production deployment behavior are not changed.

**Tech Stack:** Markdown, Mermaid diagrams, existing Vue3/FastAPI/PostgreSQL/Redis/Celery/Docker documentation.

---

### Task 1: Rewrite Public README

**Files:**
- Modify: `README.md`

- [ ] Replace README with a GitHub-facing project homepage.
- [ ] Include a concise system data-flow Mermaid diagram.
- [ ] Include a compact architecture diagram.
- [ ] Link to project status, deployment, troubleshooting, data model, demo materials, and existing project explanation docs.
- [ ] Explain that `frontend/` is the current Vue3 frontend and root `index.html` / `app.js` / `styles.css` are legacy compatibility files.

### Task 2: Add Public Documentation Entrypoints

**Files:**
- Create: `docs/PROJECT_STATUS.md`
- Create: `docs/DEPLOYMENT.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/project-explanation/data-model.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/deployment/troubleshooting.md`

- [ ] Add short status, deployment, and troubleshooting entrypoints that link to detailed existing docs instead of duplicating them.
- [ ] Add data model doc with Mermaid ER diagram and relationship explanations.
- [ ] Update current-state with showcase-packaging phase.
- [ ] Update troubleshooting with engineering-level incidents only and consistent incident format.

### Task 3: Add Private Career Materials Outside Repo

**Files outside repo:**
- Create: `C:\Users\Sharknro\Documents\求职材料\AI模拟面试系统\boss-project-description.md`
- Create: `C:\Users\Sharknro\Documents\求职材料\AI模拟面试系统\resume-bullets.md`
- Create: `C:\Users\Sharknro\Documents\求职材料\AI模拟面试系统\interview-script.md`
- Create: `C:\Users\Sharknro\Documents\求职材料\AI模拟面试系统\interview-qa-private.md`
- Create: `C:\Users\Sharknro\Documents\求职材料\AI模拟面试系统\project-packaging-notes.md`

- [ ] Write BOSS project description in project description / responsibility / achievement format.
- [ ] Write resume bullets for Python backend, AI application, and full-stack positioning.
- [ ] Write 1-minute and 3-minute interview scripts.
- [ ] Write private interview Q&A preparation.
- [ ] Write packaging notes explaining public/private boundaries.

### Task 4: Safety Cleanup and Verification

**Files:**
- Modify only if needed: `.gitignore`

- [ ] Verify `.gitignore` covers env files, logs, cache, build artifacts, and private career material patterns if they could be accidentally placed inside the repo.
- [ ] Confirm `.env` remains ignored but note whether it is tracked.
- [ ] Run `git diff --check`.
- [ ] Run `git status --short` and verify private career files are absent.
- [ ] Do not run full app tests unless executable config or code changes were made.
