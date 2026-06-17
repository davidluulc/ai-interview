# Project Closure Audit V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成项目阶段性收口审计，统一 README、启动入口、文档状态、测试命令、主链路说明和后续生产化开发基线。

**Architecture:** 本阶段不新增业务功能，不重构 RAG/Agent/Vue3，不引入 Redis/Celery/PostgreSQL。先做只读扫描，再生成 `docs/project-baseline.md` 和审计清单，随后以最小改动更新 README、docs 入口和 roadmap，最后用测试、构建和浏览器验证当前基线。

**Tech Stack:** Markdown, PowerShell, FastAPI, Vue3, Pytest, Vitest, Vite, Git.

---

## File Structure

- Read: `README.md`
  - 项目主入口文档，执行时需要检查并更新为短而准的快速启动说明。
- Create: `docs/project-baseline.md`
  - 项目当前开发基线：目录结构、主入口、启动方式、测试方式、兼容入口、后续开发边界。
- Create: `docs/audits/project-closure-audit-v1.md`
  - 本轮审计清单：已检查项、保留项、未处理遗留项、下一阶段注意事项。
- Modify: `docs/roadmap/current-state.md`
  - 当前 active 阶段、当前实现进度、下一阶段建议。
- Modify: `docs/specs/README.md`
  - active spec / completed spec 状态。
- Modify: `docs/plans/README.md`
  - active plan / completed plan 状态。
- Move after completion:
  - `docs/specs/active/project-closure-audit-v1-design.md` -> `docs/specs/completed/project-closure-audit-v1-design.md`
  - `docs/plans/active/project-closure-audit-v1.md` -> `docs/plans/completed/project-closure-audit-v1.md`
- Verify only, do not modify unless clearly necessary:
  - `start-dev.cmd`
  - `start-backend.cmd`
  - `start-vue-frontend.cmd`
  - `start-python-server.cmd`
  - `index.html`
  - `app.js`
  - `styles.css`
  - `backend_python/`
  - `frontend/`
  - `scripts/`

---

### Task 1: Read-Only Baseline Scan

**Files:**
- Read: `README.md`
- Read: `docs/roadmap/current-state.md`
- Read: `docs/specs/README.md`
- Read: `docs/plans/README.md`
- Read: root startup scripts
- No writes in this task.

- [ ] **Step 1: Confirm git status is clean or understand existing changes**

Run:

```powershell
git status --short
```

Expected:

```text
No unrelated source-code changes should be present before starting the audit.
```

If there are unrelated user changes, do not revert them. Record them in `docs/audits/project-closure-audit-v1.md` under “审计时发现的外部改动”.

- [ ] **Step 2: Inventory root-level project files**

Run:

```powershell
Get-ChildItem -Force | Select-Object Name,Mode,Length | Sort-Object Name
```

Record important findings:

```text
README.md
backend_python/
frontend/
docs/
scripts/
start-dev.cmd
start-backend.cmd
start-vue-frontend.cmd
start-python-server.cmd
index.html / app.js / styles.css
data/
logs/
deploy/
Dockerfile / docker-compose.yml
```

Do not delete anything in this step.

- [ ] **Step 3: Inventory active and completed docs**

Run:

```powershell
Get-ChildItem docs\specs\active,docs\plans\active,docs\specs\completed,docs\plans\completed -Force |
  Select-Object FullName,Name,LastWriteTime |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 80
```

Expected:

```text
active spec contains project-closure-audit-v1-design.md.
active plan contains project-closure-audit-v1.md.
completed contains recent LangGraph / RAG / Vue3 phases.
```

- [ ] **Step 4: Locate startup and route entry evidence**

Run:

```powershell
rg -n "5173|8000|uvicorn|vite|/vue/app|next-question|langgraph_mainline|classic" README.md start-*.cmd backend_python frontend docs -g "!frontend/node_modules/**"
```

Record:

```text
Which files mention old/native frontend.
Which files mention Vue3 frontend.
Which files mention backend API port.
Which files mention LangGraph mainline.
```

- [ ] **Step 5: Inspect git ignored/generated areas before considering cleanup**

Run:

```powershell
git status --ignored --short
```

Do not delete ignored files unless the plan later identifies a safe cleanup. For this phase, prefer recording generated folders such as `.pytest_cache`, frontend build output, logs, and local database files.

---

### Task 2: Create Project Baseline Document

**Files:**
- Create: `docs/project-baseline.md`

- [ ] **Step 1: Create `docs/project-baseline.md`**

Create a Markdown document with this structure:

```markdown
# AI 模拟面试系统开发基线

更新时间：2026-06-17

## 1. 当前项目定位

本项目是面向大学生和求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 工作流生成面试问题，并在面试结束后生成复盘报告和训练任务。

## 2. 当前主入口

- 后端 API：`http://127.0.0.1:8000`
- Vue3 主前端：`http://127.0.0.1:5173/vue/app/interview`
- Vue3 管理员后台：`http://127.0.0.1:5173/vue/app/admin`
- 旧原生前端：保留为兼容入口，不作为当前主前端继续开发。

## 3. 本地启动

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

如果需要同时启动，可以使用：

```powershell
.\start-dev.cmd
```

## 4. 测试和构建

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

## 5. 当前主链路

- `/api/interview/next-question` 默认内部运行时：`langgraph_mainline`
- fallback/helper：`classic`
- RAG 接入方式：作为 LangGraph `retrieve_context` 节点复用现有三类 RAG。
- 后台观测：Agent 工作流观测、RAG 摘要、checkpoint、fallback、quality gate、runtime audit。

## 6. 目录结构基线

- `backend_python/`：FastAPI 后端。
- `frontend/`：Vue3 当前主前端。
- `docs/`：spec、plan、roadmap、基线文档和审计记录。
- `scripts/`：本地开发和维护脚本。
- `tests/`：后端测试。
- `data/`：本地 SQLite 数据和开发数据，不作为生产数据源。
- `logs/`：本地日志。
- `deploy/`、`Dockerfile`、`docker-compose.yml`：部署相关历史/候选资料，当前阶段不作为主线执行。

## 7. 本地演示账号

开发环境建议使用：

- 普通演示账号：`d77013643@gmail.com / 123456`
- 管理员演示账号：`1011569954@qq.com / 123456`

如果账号不存在，可以通过注册接口创建，再在本地数据库中提升管理员角色。

## 8. 当前不做的事情

- 不在本阶段引入 Redis。
- 不在本阶段引入 Celery。
- 不在本阶段切换 PostgreSQL。
- 不在本阶段做 Docker/Nginx/VPS/HTTPS 上线。
- 不在本阶段重构 RAG、Agent、LangGraph 或 Vue3 主链路。

## 9. 下一阶段候选方向

下一阶段可以讨论：

- Backend Production Infrastructure V1：PostgreSQL + Redis + Celery 后端生产化底座。
- RAG 异步入库和任务化升级。
- 管理员后台异步任务观测。
```

- [ ] **Step 2: Check baseline document for accidental over-claiming**

Run:

```powershell
rg -n "已经上线|生产可用|必须使用 PostgreSQL|必须启动 Redis|必须启动 Celery|TODO|TBD" docs\project-baseline.md
```

Expected:

```text
No matches.
```

If matches appear, revise wording to keep the document factual.

---

### Task 3: Create Audit Checklist Document

**Files:**
- Create: `docs/audits/project-closure-audit-v1.md`

- [ ] **Step 1: Ensure audit directory exists**

Run:

```powershell
if (!(Test-Path docs\audits)) { New-Item -ItemType Directory docs\audits }
```

- [ ] **Step 2: Create audit checklist**

Create `docs/audits/project-closure-audit-v1.md` with:

```markdown
# Project Closure Audit V1 审计记录

更新时间：2026-06-17

## 1. 审计结论

本轮审计目标是建立后续 RAG 生产化、Redis、Celery、PostgreSQL 开发前的项目基线。本轮不新增业务功能，不做主链路重构。

## 2. 已检查项

- [ ] Git 工作区状态
- [ ] README 项目入口
- [ ] docs roadmap / specs / plans 状态
- [ ] 后端启动脚本
- [ ] Vue3 前端启动脚本
- [ ] 旧原生前端兼容入口
- [ ] `/api/interview/next-question` 主链路说明
- [ ] RAG / Agent / LangGraph 当前能力索引
- [ ] 后端测试命令
- [ ] 前端测试命令
- [ ] 前端构建命令
- [ ] 浏览器桌面端验证
- [ ] 浏览器移动端验证

## 3. 保留但不作为当前主线的内容

- `index.html`、`app.js`、`styles.css`：旧原生前端兼容入口，当前主前端是 `frontend/` 下的 Vue3。
- `start-python-server.cmd`：旧兼容启动入口，如仍可用则保留说明。
- `deploy/`、`Dockerfile`、`docker-compose.yml`：部署相关候选资料，本阶段不执行上线。

## 4. 本轮不处理的遗留项

- Redis token blacklist、限流、缓存。
- Celery 异步任务。
- PostgreSQL 正式切换。
- Docker/Nginx/VPS/HTTPS 上线。
- RAG 主链路重构。
- Agent/LangGraph 主链路重构。

## 5. 后续建议

下一阶段优先讨论 Backend Production Infrastructure V1。建议先保留 SQLite 本地默认开发，同时增强 PostgreSQL 配置兼容，再引入 Redis 健康检查和 Celery 异步任务。
```

- [ ] **Step 3: Update checklist while executing later tasks**

As tasks complete, mark only verified items as checked. Do not mark browser checks complete until actual browser verification is done.

---

### Task 4: Update README As Current Entry Point

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README and identify stale claims**

Run:

```powershell
Get-Content README.md
rg -n "8000|5173|Vue3|旧|原生|LangGraph|Redis|Celery|PostgreSQL|Docker|Nginx|VPS|pytest|npm" README.md
```

Record stale or ambiguous parts in `docs/audits/project-closure-audit-v1.md`.

- [ ] **Step 2: Rewrite README with concise current structure**

Update README to include these sections:

```markdown
# AI 模拟面试系统

面向大学生和求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 工作流生成面试问题，面试结束后生成复盘报告和训练任务。管理员后台提供 RAG 命中、Agent 决策、LangGraph checkpoint、fallback 和 quality gate 观测。

## 当前主入口

- 后端 API / 旧兼容入口：`http://127.0.0.1:8000`
- Vue3 主前端：`http://127.0.0.1:5173/vue/app/interview`
- Vue3 管理员后台：`http://127.0.0.1:5173/vue/app/admin`

## 本地启动

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

也可以使用：

```powershell
.\start-dev.cmd
```

## 测试和构建

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

## 当前主链路

- 面试接口：`POST /api/interview/next-question`
- 默认 Agent runtime：`langgraph_mainline`
- 兜底链路：`classic`
- RAG 接入：岗位知识库、题库、候选人画像三类 RAG 作为 `retrieve_context` 节点复用。
- 可观测性：RAG 日志、Agent 决策日志、runtime audit、checkpoint summary、quality gate。

## 文档入口

- 当前路线：`docs/roadmap/current-state.md`
- 开发基线：`docs/project-baseline.md`
- 当前 spec：`docs/specs/active/`
- 当前 plan：`docs/plans/active/`
- 审计记录：`docs/audits/project-closure-audit-v1.md`

## 当前阶段边界

本阶段不引入 Redis、Celery、PostgreSQL，不做 Docker/Nginx/VPS/HTTPS 上线，不重构 RAG/Agent/Vue3 主链路。下一阶段再讨论后端生产化底座。
```

Keep README concise. Put detailed explanation in `docs/project-baseline.md`.

- [ ] **Step 3: Verify README does not overstate deployment**

Run:

```powershell
rg -n "已上线|生产环境已部署|必须启动 Redis|必须启动 Celery|必须使用 PostgreSQL" README.md
```

Expected:

```text
No matches.
```

---

### Task 5: Update Documentation Indexes And Roadmap

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Confirm current active paths**

Run:

```powershell
Get-ChildItem docs\specs\active,docs\plans\active -Force | Select-Object FullName,Name
```

Expected:

```text
docs/specs/active/project-closure-audit-v1-design.md
docs/plans/active/project-closure-audit-v1.md
```

- [ ] **Step 2: Update roadmap current state**

Ensure the top section of `docs/roadmap/current-state.md` states:

```text
当前 active 开发阶段：Project Closure Audit V1：项目阶段性收口审计与开发基线整理
当前 active spec：docs/specs/active/project-closure-audit-v1-design.md
当前 active plan：docs/plans/active/project-closure-audit-v1.md
当前实现进度：LangGraph Mainline Consolidation V7 已完成...
本阶段目标：统一 README、启动入口、测试命令、文档状态、Vue3 主入口、旧兼容入口说明和后续开发基线。
```

- [ ] **Step 3: Update specs README**

Ensure `docs/specs/README.md` says:

```text
当前 active spec：docs/specs/active/project-closure-audit-v1-design.md
最近完成并归档的 spec：docs/specs/completed/langgraph-mainline-consolidation-v7-design.md
```

- [ ] **Step 4: Update plans README**

Ensure `docs/plans/README.md` says:

```text
当前 active plan：docs/plans/active/project-closure-audit-v1.md
当前 active spec：docs/specs/active/project-closure-audit-v1-design.md
最近完成并归档的 plan：docs/plans/completed/langgraph-mainline-consolidation-v7.md
```

- [ ] **Step 5: Check for contradictory active status**

Run:

```powershell
rg -n "当前 active spec：\\s*$|当前 active plan：\\s*$|当前没有 active|暂无。下一步需要先讨论方向|LangGraph Mainline Consolidation V7 已完成并归档。当前没有 active" docs\roadmap\current-state.md docs\specs\README.md docs\plans\README.md
```

Expected:

```text
No stale "no active" statements in these three current entry docs.
```

---

### Task 6: Conservative File Cleanup Review

**Files:**
- Modify only if safe:
  - `.gitignore`
  - docs audit file
- Do not delete uncertain source files.

- [ ] **Step 1: List ignored and untracked files**

Run:

```powershell
git status --short --ignored
```

Record categories in `docs/audits/project-closure-audit-v1.md`:

```text
ignored cache
ignored logs
local database
frontend build output
untracked files
```

- [ ] **Step 2: Check whether obvious generated folders are ignored**

Run:

```powershell
Get-Content .gitignore
```

Expected common ignored entries may include:

```text
.env
__pycache__/
.pytest_cache/
node_modules/
dist/
data/*.db
logs/
```

If a generated folder is not ignored, update `.gitignore` with the narrowest safe pattern. Do not ignore source directories.

- [ ] **Step 3: Do not delete legacy frontend files**

Verify these files still exist:

```powershell
Test-Path index.html
Test-Path app.js
Test-Path styles.css
```

Record them as old native frontend compatibility entry in the audit file. Do not delete them.

- [ ] **Step 4: Do not delete deployment files**

Verify these files/directories:

```powershell
Test-Path deploy
Test-Path Dockerfile
Test-Path docker-compose.yml
```

Record them as deployment candidates / historical deployment material. Do not execute deployment in this phase.

---

### Task 7: Verification Commands

**Files:**
- No source modifications expected.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All backend tests pass. A LangGraph/LangChain deprecation warning is acceptable if tests pass.
```

Record result in `docs/audits/project-closure-audit-v1.md`.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
npm.cmd run test
```

Workdir:

```text
frontend
```

Expected:

```text
All Vitest files pass.
```

Record result in `docs/audits/project-closure-audit-v1.md`.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
npm.cmd run build
```

Workdir:

```text
frontend
```

Expected:

```text
vue-tsc --noEmit and vite build pass.
```

Record result in `docs/audits/project-closure-audit-v1.md`.

- [ ] **Step 4: Check markdown for placeholders**

Run:

```powershell
rg -n "TBD|TODO|待定|待补|\\?\\?\\?" README.md docs\project-baseline.md docs\audits\project-closure-audit-v1.md docs\roadmap\current-state.md docs\specs\README.md docs\plans\README.md
```

Expected:

```text
No placeholder matches.
```

Then run this Python encoding-damage check:

```powershell
@'
from pathlib import Path

paths = [
    "README.md",
    "docs/project-baseline.md",
    "docs/audits/project-closure-audit-v1.md",
    "docs/roadmap/current-state.md",
    "docs/specs/README.md",
    "docs/plans/README.md",
]
for raw in paths:
    text = Path(raw).read_text(encoding="utf-8", errors="replace")
    if "\ufffd" in text:
        print(raw)
'@ | python -
```

Expected:

```text
No output.
```

---

### Task 8: Browser Verification

**Files:**
- No source modifications expected unless verification exposes a small documentation mismatch.

- [ ] **Step 1: Confirm local services are listening**

Run:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 5 LocalAddress,LocalPort,State,OwningProcess
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -First 5 LocalAddress,LocalPort,State,OwningProcess
```

If missing, start services using:

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

- [ ] **Step 2: Verify desktop Vue3 interview page**

Use the in-app browser to open:

```text
http://127.0.0.1:5173/vue/app/interview
```

Expected:

```text
Page loads without blank screen.
No "undefined" visible.
No horizontal overflow.
If no profile is selected, the create-profile guide is acceptable.
```

- [ ] **Step 3: Verify desktop admin page**

Use the in-app browser to open:

```text
http://127.0.0.1:5173/vue/app/admin
```

Expected:

```text
Admin page loads for admin account.
Agent workflow observation section is available when debug data exists.
No "undefined" visible.
No horizontal overflow.
```

If login is required, use local development admin account from `docs/project-baseline.md`.

- [ ] **Step 4: Verify mobile width pages**

Set viewport to roughly:

```text
390 x 844
```

Re-check:

```text
/vue/app/interview
/vue/app/admin
```

Expected:

```text
No horizontal overflow.
No "undefined" visible.
Navigation remains usable.
```

- [ ] **Step 5: Record browser verification**

Update `docs/audits/project-closure-audit-v1.md` with:

```markdown
## 6. 验证记录

- 后端测试：通过，记录命令和摘要。
- 前端测试：通过，记录命令和摘要。
- 前端构建：通过，记录命令和摘要。
- 桌面端页面：`/vue/app/interview`、`/vue/app/admin` 已验证。
- 移动端页面：390px 宽度已验证。
```

---

### Task 9: Archive Spec And Plan After Completion

**Files:**
- Move: `docs/specs/active/project-closure-audit-v1-design.md`
- Move: `docs/plans/active/project-closure-audit-v1.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Move active spec and plan to completed**

Use PowerShell:

```powershell
Move-Item -LiteralPath docs\specs\active\project-closure-audit-v1-design.md -Destination docs\specs\completed\project-closure-audit-v1-design.md
Move-Item -LiteralPath docs\plans\active\project-closure-audit-v1.md -Destination docs\plans\completed\project-closure-audit-v1.md
```

- [ ] **Step 2: Update specs README**

Set:

```text
当前 active spec：暂无。
最近完成并归档的 spec：docs/specs/completed/project-closure-audit-v1-design.md
```

- [ ] **Step 3: Update plans README**

Set:

```text
当前 active plan：暂无。
最近完成并归档的 plan：docs/plans/completed/project-closure-audit-v1.md
```

- [ ] **Step 4: Update roadmap**

Set current active section to:

```text
当前 active 开发阶段：暂无。
当前 active spec：暂无。
当前 active plan：暂无。
当前实现进度：Project Closure Audit V1 已完成...
```

Mention next candidate:

```text
Backend Production Infrastructure V1：PostgreSQL + Redis + Celery 后端生产化底座
```

- [ ] **Step 5: Final git and diff check**

Run:

```powershell
git status --short
git diff --check
```

Expected:

```text
Only intended docs / minimal ignore changes are present.
git diff --check reports no whitespace errors.
```

- [ ] **Step 6: Commit final audit work**

Run:

```powershell
git add README.md docs .gitignore
git commit -m "docs: complete project closure audit"
```

Do not push unless the user explicitly asks.
