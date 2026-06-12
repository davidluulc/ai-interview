# Docker + Nginx + VPS Deployment V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible deployment baseline for the AI interview system using Docker, Docker Compose, Nginx, production environment templates, deployment docs, and verification tests.

**Architecture:** Keep local development on SQLite, while adding a Docker Compose deployment path with FastAPI app, PostgreSQL, Redis, Celery worker, and Nginx. Treat deployment config as first-class code by testing required files and documenting VPS operations, logs, backup, rollback, and Cloudflare/HTTPS setup.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Docker, Docker Compose, Nginx, pytest, vanilla frontend tests.

---

## File Structure

- Create `.env.production.example`: production-safe environment template with placeholder values only.
- Create `.dockerignore`: keep local secrets, SQLite database, caches, IDE files, and logs out of Docker build context.
- Create `Dockerfile`: build the FastAPI application image.
- Create `docker-compose.yml`: compose app, db, redis, worker, and nginx services.
- Create `deploy/README.md`: deployment directory overview.
- Create `deploy/nginx/ai-interview.conf`: Nginx reverse proxy config.
- Create `docs/deployment/README.md`: deployment docs entrypoint.
- Create `docs/deployment/vps-deploy-v1.md`: step-by-step VPS deployment guide.
- Create `docs/deployment/nginx-cloudflare-https.md`: domain, DNS, Nginx, and HTTPS guide.
- Create `docs/deployment/troubleshooting.md`: common deployment failures and diagnosis.
- Create `docs/deployment/backup-and-rollback.md`: database backup and code rollback guide.
- Create `docs/learning/12-Docker-Nginx-VPS上线链路怎么理解.md`: learning note for deployment concepts and interview explanation.
- Create `tests/test_deployment_config.py`: automated checks for deployment config files.
- Modify `docs/roadmap/current-state.md`: mark deployment V1 progress.
- Modify `docs/roadmap/project-progress.md`: record implementation and verification.
- Modify `docs/specs/README.md` and `docs/plans/README.md`: keep active spec/plan state accurate.

## Task 1: Deployment Config Tests

**Files:**
- Create: `tests/test_deployment_config.py`

- [ ] **Step 1: Write tests for required deployment artifacts**

Add tests that assert:

- `.env.production.example` exists and does not contain real-looking API keys.
- `.dockerignore` excludes `.env`, local SQLite database, caches, logs, and IDE files.
- `Dockerfile` uses Python, installs requirements, exposes 8000, and starts Uvicorn.
- `docker-compose.yml` defines `app`, `db`, `redis`, `worker`, and `nginx`.
- Nginx config proxies `/api/` and `/docs` to the app service.

- [ ] **Step 2: Run tests and confirm failure before implementation**

Run:

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected before implementation: failures because deployment files do not exist yet.

## Task 2: Production Environment Template and Docker Context

**Files:**
- Create: `.env.production.example`
- Create: `.dockerignore`

- [ ] **Step 1: Implement `.env.production.example`**

Include placeholders for:

- DashScope/Qwen model settings.
- JWT settings.
- PostgreSQL `DATABASE_URL`.
- Redis URL.
- Celery broker/result backend.
- Production mode flags.

Use placeholder values like `replace_with_dashscope_api_key` and `replace_with_long_random_secret`.

- [ ] **Step 2: Implement `.dockerignore`**

Exclude:

- `.env`
- `.env.*` except templates are still available in Git
- `data/*.db`
- Python caches
- pytest caches
- IDE folders
- logs
- node/build outputs

- [ ] **Step 3: Run deployment config tests**

Run:

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: remaining failures for Dockerfile, compose, and Nginx files only.

## Task 3: Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Implement application Dockerfile**

Use Python official slim image, install requirements, copy project, expose 8000, and start:

```text
uvicorn backend_python.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Run deployment config tests**

Run:

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: remaining failures for compose and Nginx files only.

## Task 4: Docker Compose

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Implement compose services**

Define:

- `app`: builds from Dockerfile, reads `.env.production`, depends on db and redis, exposes only internal app port.
- `db`: PostgreSQL 16 with persistent volume.
- `redis`: Redis 7 with persistent volume.
- `worker`: same image as app, runs Celery worker, depends on redis and db.
- `nginx`: official Nginx image, mounts `deploy/nginx/ai-interview.conf`, maps host port 8080 to container port 80 for local verification.

- [ ] **Step 2: Keep production settings explicit**

Set deployment `DATABASE_URL`, `REDIS_ENABLED`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `CELERY_TASK_ALWAYS_EAGER=false` through `.env.production` or Compose defaults.

- [ ] **Step 3: Run deployment config tests**

Run:

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: remaining failures for Nginx file only.

## Task 5: Nginx Reverse Proxy

**Files:**
- Create: `deploy/README.md`
- Create: `deploy/nginx/ai-interview.conf`

- [ ] **Step 1: Implement Nginx config**

Config requirements:

- upstream points to `app:8000`.
- `/api/` proxies to app.
- `/docs` proxies to app.
- `/openapi.json` proxies to app.
- `/` proxies to app so the existing FastAPI static page works.
- Set `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`.
- Include reasonable read/connect/send timeouts.

- [ ] **Step 2: Add deploy README**

Explain what lives under `deploy/` and when to use the Nginx config.

- [ ] **Step 3: Run deployment config tests**

Run:

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: pass.

## Task 6: Deployment Documentation

**Files:**
- Create: `docs/deployment/README.md`
- Create: `docs/deployment/vps-deploy-v1.md`
- Create: `docs/deployment/nginx-cloudflare-https.md`
- Create: `docs/deployment/troubleshooting.md`
- Create: `docs/deployment/backup-and-rollback.md`

- [ ] **Step 1: Write deployment entrypoint**

Explain:

- What this deployment path is for.
- Which docs to read first.
- What is intentionally out of scope.

- [ ] **Step 2: Write VPS deployment guide**

Cover:

- VPS selection: Hong Kong/overseas, Ubuntu LTS.
- Install Git, Docker, Docker Compose plugin.
- Clone GitHub repo.
- Create `.env.production`.
- Start services.
- Run Alembic migration.
- Verify `/`, `/api/health`, and `/docs`.

- [ ] **Step 3: Write Nginx/Cloudflare/HTTPS guide**

Cover:

- Domain DNS A record.
- Cloudflare proxied vs DNS-only.
- HTTP first, HTTPS later.
- Cloudflare SSL mode notes.
- Let's Encrypt / Certbot alternative.

- [ ] **Step 4: Write troubleshooting guide**

Cover:

- Nginx 502.
- app container not starting.
- database connection failed.
- Redis connection failed.
- API Key missing.
- Alembic migration failed.
- port conflict.

- [ ] **Step 5: Write backup and rollback guide**

Cover:

- PostgreSQL backup with `pg_dump`.
- PostgreSQL restore.
- Code rollback with Git.
- Container rollback/rebuild.
- `.env.production` backup caution.

## Task 7: Learning Document and Roadmap Updates

**Files:**
- Create: `docs/learning/12-Docker-Nginx-VPS上线链路怎么理解.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/roadmap/project-progress.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Write learning document**

Explain in Chinese:

- Docker vs VPS vs Uvicorn.
- Compose service orchestration.
- Nginx reverse proxy.
- Domain/DNS/Cloudflare/HTTPS.
- SQLite vs PostgreSQL.
- Why `.env` is never committed.
- Interview explanation template.

- [ ] **Step 2: Update roadmap and active plan state**

Record:

- What was implemented.
- What was verified.
- What remains for real VPS deployment.
- Whether Docker local verification passed or was blocked.

## Task 8: Full Verification

**Files:**
- No new files unless verification reveals a concrete gap.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: no failing output.

- [ ] **Step 3: Run Docker verification if Docker is available**

Run:

```powershell
docker --version
docker compose version
docker build -t ai-interview-app:local .
docker compose -p ai-interview --env-file .env.production.example config
```

If safe and available, run:

```powershell
docker compose -p ai-interview --env-file .env.production.example up -d --build
docker compose -p ai-interview ps
docker compose -p ai-interview logs app --tail=80
docker compose -p ai-interview down
```

Record exact result. If Docker is unavailable, record the blocker without claiming Docker verification passed.

- [ ] **Step 4: Sensitive file scan**

Run:

```powershell
rg -n --hidden --glob '!.git/**' --glob '!.env' --glob '!data/*.db' "(sk-[A-Za-z0-9_-]{10,}|DASHSCOPE_API_KEY\\s*=\\s*sk-|OPENAI_API_KEY\\s*=\\s*sk-|kwb1515yxq)" .
```

Expected: no real secrets.

- [ ] **Step 5: Commit**

Commit after verification:

```powershell
git add .env.production.example .dockerignore Dockerfile docker-compose.yml deploy docs tests
git commit -m "feat: add docker nginx deployment baseline"
```
