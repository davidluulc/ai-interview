# Project Directory Cleanup V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让项目本地启动入口和目录边界更清晰，避免用户双击后端脚本后误以为 `localhost:8000` 是当前 Vue3 主前端。

**Architecture:** 本阶段不迁移旧前端文件，不删除 `index.html` / `styles.css` / `app.js`。通过新增清晰的 Windows 启动脚本、改造旧脚本为兼容入口、重写 README 和补充轻量测试来降低误用风险。

**Tech Stack:** Windows CMD, Python pathlib pytest, FastAPI, Vue3 Vite, Markdown documentation.

---

## File Map

- Create: `tests/test_project_entrypoints.py`
  - 验证本地入口脚本、README 说明和 legacy 旧前端边界。
- Create: `start-backend.cmd`
  - 当前推荐的 FastAPI 后端启动脚本。
- Create: `start-vue-frontend.cmd`
  - 当前推荐的 Vue3 前端启动脚本。
- Create: `start-dev.cmd`
  - 引导用户分别启动后端和 Vue3 前端。
- Modify: `start-python-server.cmd`
  - 保留旧文件名，但改成兼容入口，内部调用 `start-backend.cmd`。
- Modify: `README.md`
  - 重写成本项目当前状态说明，明确 8000 和 5173 的区别。
- Modify: `docs/plans/README.md`
  - 指向当前 active plan。
- Modify: `docs/roadmap/current-state.md`
  - 指向当前 active plan。

---

## Task 1: Entrypoint Tests

**Files:**

- Create: `tests/test_project_entrypoints.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_project_entrypoints.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_local_startup_scripts_are_explicit() -> None:
    backend = read_text("start-backend.cmd")
    frontend = read_text("start-vue-frontend.cmd")
    dev = read_text("start-dev.cmd")
    legacy = read_text("start-python-server.cmd")

    assert "backend_python.main:app" in backend
    assert "--port 8000" in backend
    assert "127.0.0.1:8000/docs" in backend
    assert "127.0.0.1:5173/vue/app/interview" in backend

    assert "cd /d \"%~dp0frontend\"" in frontend
    assert "npm.cmd run dev" in frontend
    assert "127.0.0.1:5173/vue/app/interview" in frontend

    assert "start-backend.cmd" in dev
    assert "start-vue-frontend.cmd" in dev

    assert "legacy script name" in legacy.lower()
    assert "call \"%~dp0start-backend.cmd\"" in legacy


def test_readme_explains_backend_and_vue_frontend_ports() -> None:
    readme = read_text("README.md")

    assert "当前主前端" in readme
    assert "frontend/" in readme
    assert "http://127.0.0.1:8000/docs" in readme
    assert "http://127.0.0.1:8000/api/health" in readme
    assert "http://127.0.0.1:5173/vue/app/interview" in readme
    assert "localhost:8000" in readme
    assert "旧版原生前端" in readme


def test_legacy_frontend_files_are_still_present_for_compatibility() -> None:
    assert (ROOT / "index.html").exists()
    assert (ROOT / "styles.css").exists()
    assert (ROOT / "app.js").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_project_entrypoints.py -q
```

Expected:

```text
FAIL because start-backend.cmd, start-vue-frontend.cmd, and start-dev.cmd do not exist yet.
```

---

## Task 2: Startup Scripts

**Files:**

- Create: `start-backend.cmd`
- Create: `start-vue-frontend.cmd`
- Create: `start-dev.cmd`
- Modify: `start-python-server.cmd`
- Test: `tests/test_project_entrypoints.py`

- [ ] **Step 1: Add backend startup script**

Create `start-backend.cmd`:

```cmd
@echo off
cd /d "%~dp0"

echo Starting AI Interview FastAPI backend...
echo.
echo Backend API docs:
echo http://127.0.0.1:8000/docs
echo.
echo Health check:
echo http://127.0.0.1:8000/api/health
echo.
echo Vue3 frontend is not served from this backend dev port.
echo To open the current main frontend, run start-vue-frontend.cmd
echo then visit:
echo http://127.0.0.1:5173/vue/app/interview
echo.

python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Backend server stopped. Press any key to close this window.
pause >nul
```

- [ ] **Step 2: Add Vue3 startup script**

Create `start-vue-frontend.cmd`:

```cmd
@echo off
cd /d "%~dp0frontend"

echo Starting AI Interview Vue3 frontend...
echo.
echo Vue3 frontend:
echo http://127.0.0.1:5173/vue/app/interview
echo.
echo Backend API should be running at:
echo http://127.0.0.1:8000
echo.
echo If dependencies are missing, run:
echo npm.cmd install
echo.

npm.cmd run dev

echo.
echo Vue3 frontend server stopped. Press any key to close this window.
pause >nul
```

- [ ] **Step 3: Add dev helper script**

Create `start-dev.cmd`:

```cmd
@echo off
cd /d "%~dp0"

echo AI Interview local development startup
echo.
echo Please start two windows:
echo.
echo 1. Backend:
echo    start-backend.cmd
echo.
echo 2. Vue3 frontend:
echo    start-vue-frontend.cmd
echo.
echo Current main frontend:
echo http://127.0.0.1:5173/vue/app/interview
echo.
echo Backend docs:
echo http://127.0.0.1:8000/docs
echo.

pause
```

- [ ] **Step 4: Convert old script to compatibility wrapper**

Replace `start-python-server.cmd` with:

```cmd
@echo off
echo This is a legacy script name. Prefer start-backend.cmd.
echo.
call "%~dp0start-backend.cmd"
```

- [ ] **Step 5: Run targeted test**

Run:

```powershell
python -m pytest tests/test_project_entrypoints.py -q
```

Expected:

```text
FAIL because README has not been updated yet.
```

---

## Task 3: README Refresh

**Files:**

- Modify: `README.md`
- Test: `tests/test_project_entrypoints.py`

- [ ] **Step 1: Rewrite README**

Replace `README.md` with a concise current-state README containing:

```markdown
# AI 模拟面试系统

## 项目简介

这是一个面向大学生、应届生和社会求职者的 AI 模拟面试训练系统。

当前项目主线是 Python FastAPI 后端 + Vue3 前端 + RAG + Agent + LangGraph 旁路工作流。

## 当前主前端

当前主前端位于：

`frontend/`

本地开发时请打开：

`http://127.0.0.1:5173/vue/app/interview`

注意：`http://localhost:8000/` 当前仍可能显示旧版原生前端或后端根入口，不是当前主页面。

## 本地启动

### 1. 启动后端

双击：

`start-backend.cmd`

后端 API 文档：

`http://127.0.0.1:8000/docs`

健康检查：

`http://127.0.0.1:8000/api/health`

### 2. 启动 Vue3 前端

双击：

`start-vue-frontend.cmd`

Vue3 前端：

`http://127.0.0.1:5173/vue/app/interview`

## 旧版原生前端

根目录下的 `index.html`、`styles.css`、`app.js` 是旧版原生前端。

它们暂时保留用于兼容历史测试、历史文档和旧入口，不再作为当前主开发入口。

## 常用命令

后端测试：

`python -m pytest -q`

前端测试：

`cd frontend`

`npm.cmd run test`

前端构建：

`cd frontend`

`npm.cmd run build`
```

- [ ] **Step 2: Run targeted test**

Run:

```powershell
python -m pytest tests/test_project_entrypoints.py -q
```

Expected:

```text
3 passed
```

---

## Task 4: Roadmap And Plan Index

**Files:**

- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Update plans README**

Set current active plan to:

```text
docs/plans/active/project-directory-cleanup-v1.md
```

Set current active spec to:

```text
docs/specs/active/project-directory-cleanup-v1-design.md
```

- [ ] **Step 2: Update roadmap current state**

Set current active plan to:

```text
docs/plans/active/project-directory-cleanup-v1.md
```

Keep current active spec as:

```text
docs/specs/active/project-directory-cleanup-v1-design.md
```

- [ ] **Step 3: Verify active docs**

Run:

```powershell
Test-Path 'docs\specs\active\project-directory-cleanup-v1-design.md'
Test-Path 'docs\plans\active\project-directory-cleanup-v1.md'
rg -n "project-directory-cleanup-v1" docs\specs\README.md docs\plans\README.md docs\roadmap\current-state.md
```

Expected:

```text
Both Test-Path commands print True.
rg finds the active spec and active plan references.
```

---

## Task 5: Final Verification

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/test_project_entrypoints.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 2: Run frontend build smoke check**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected:

```text
vue-tsc --noEmit and vite build complete successfully.
```

- [ ] **Step 3: Confirm no legacy frontend files were deleted**

Run:

```powershell
Test-Path .\index.html
Test-Path .\styles.css
Test-Path .\app.js
```

Expected:

```text
True
True
True
```

