# AI 模拟面试系统

## 项目简介

这是一个面向大学生、应届生和社会求职者的 AI 模拟面试训练系统。

当前项目主线是 Python FastAPI 后端 + Vue3 前端 + RAG + Agent + LangGraph 旁路工作流。系统支持用户维护求职档案、进行模拟面试、查看历史复盘、生成专项训练任务，并通过管理员后台查看 RAG、Agent 和 LangGraph 相关可观测信息。

## 当前主前端

当前主前端位于：

```text
frontend/
```

本地开发时请打开：

```text
http://127.0.0.1:5173/vue/app/interview
```

注意：`http://localhost:8000/` 当前仍可能显示旧版原生前端或后端根入口，不是当前主页面。

## 本地启动

### 1. 启动后端

双击：

```text
start-backend.cmd
```

后端 API 文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

### 2. 启动 Vue3 前端

双击：

```text
start-vue-frontend.cmd
```

Vue3 前端：

```text
http://127.0.0.1:5173/vue/app/interview
```

### 3. 快速说明

也可以双击：

```text
start-dev.cmd
```

这个脚本不会替你同时启动两个服务，它会提示你分别打开后端和 Vue3 前端两个窗口。这样比隐藏启动两个后台进程更直观，也更适合本地学习和调试。

## 旧版原生前端

根目录下的 `index.html`、`styles.css`、`app.js` 是旧版原生前端。

它们暂时保留用于兼容历史测试、历史文档和旧入口，不再作为当前主开发入口。

后续如果要进一步整理目录，可以在单独阶段把旧版原生前端迁移到 `legacy_frontend/`，并同步修改仍引用旧文件的 `.mjs` 测试和文档。

## 目录结构

```text
backend_python/        FastAPI 后端、RAG、Agent、LangGraph 旁路接口
frontend/              Vue3 + Vite + TypeScript 当前主前端
tests/                 后端 pytest 测试和旧前端 .mjs 测试
docs/                  spec、plan、学习文档和部署文档
scripts/               本地维护脚本
data/                  本地 SQLite 数据和 seed 数据
logs/                  本地日志
deploy/                Nginx 等部署配置
alembic/               数据库迁移脚本
```

## 常用命令

后端测试：

```powershell
python -m pytest -q
```

前端测试：

```powershell
cd frontend
npm.cmd run test
```

前端构建：

```powershell
cd frontend
npm.cmd run build
```

## 当前学习重点

这个项目当前适合重点学习：

- FastAPI 路由拆分、Pydantic schema、SQLAlchemy ORM 和 Alembic 迁移。
- JWT 登录、refresh token、用户数据隔离和管理员权限。
- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档管理、metadata filter、hybrid search、rerank 和 evaluation。
- Interview Orchestrator Agent、Agent State、Tool Calls、Decision、fallback 和日志。
- LangGraph 旁路工作流、checkpoint、interrupt / resume 和 runtime governance。
- Vue3 + Vite + TypeScript + Pinia 的前后端分离开发。
- Docker、Nginx、Redis、Celery、PostgreSQL 的生产化预备能力。
