# AI 模拟面试系统

面向大学生、应届毕业生和社会求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 LangGraph Agent 工作流，生成贴合岗位和个人经历的面试问题；面试结束后生成复盘报告和训练任务。管理员后台提供 RAG 命中、Agent 决策、LangGraph runtime、checkpoint、fallback 和 quality gate 等可观测信息，减少 AI 黑箱问题。

## 当前状态

项目已经完成第一版公网部署：

- 公网演示入口：`http://124.221.230.218:8080/vue/auth/login`
- 公网健康检查：`http://124.221.230.218:8080/api/health`
- 本地 Vue3 前端：`http://127.0.0.1:5173/vue/app/interview`
- 本地管理员后台：`http://127.0.0.1:5173/vue/app/admin`
- 本地健康检查：`http://127.0.0.1:8000/api/health`
- 本地后端接口文档：`http://127.0.0.1:8000/docs`

公网部署使用 Docker Compose 编排 FastAPI、PostgreSQL、Redis、Celery worker 和 Nginx。当前仍是 IP + 8080 端口演示，尚未接入域名和 HTTPS。

当前主前端是 `frontend/` 下的 Vue3 应用，旧版原生前端位于根目录 `index.html`、`app.js`、`styles.css`，仅作为兼容入口保留。
`http://localhost:8000/` 或 `http://127.0.0.1:8000/` 可能显示旧版入口或后端根入口，不代表当前 Vue3 主页面。

## 核心能力

- 用户注册、登录、退出登录和管理员角色。
- 投递档案管理：简历、岗位 JD、公司信息和目标岗位。
- 面试主链路：`POST /api/interview/next-question`。
- 默认 Agent runtime：`langgraph_mainline`。
- 兼容兜底 runtime：`classic`。
- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档管理：手动录入、文件上传、chunk 生成、去重、可见性和生命周期状态。
- RAG 检索增强：BM25、向量检索、hybrid search、rerank、query rewrite 和 evaluation case。
- Agent 工程化：Agent State、Tool Calls、Agent Decision、policy、guardrail、fallback、nodeTrace。
- LangGraph：主链路工作流、checkpoint summary、runtime audit、quality gate 和 fallback 对比。
- 训练闭环：weakTags、训练任务、专项练习、掌握度更新和报告回跳。
- 管理员后台：用户概览、RAG 质量诊断、RAG 摄取任务、Agent 决策日志、AI Debug 和基础设施状态。
- 部署工程化：Alembic migration、PostgreSQL、Redis、Celery、Nginx、Docker Compose、部署排错文档。

## 本地启动

分别启动后端和 Vue3 前端：

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

也可以先查看启动说明：

```powershell
.\start-dev.cmd
```

## 测试和构建

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

部署配置检查：

```powershell
docker compose --env-file .env.production.example config
```

## 部署说明

生产演示环境需要先构建 Vue3 前端：

```powershell
cd frontend
npm.cmd run build
```

然后由 Nginx 服务 `/vue/` 静态资源，并把 `/api/`、`/docs`、`/openapi.json` 代理给 FastAPI。Compose 中的 Nginx 会挂载：

```text
./frontend/dist:/usr/share/nginx/html/vue:ro
```

真实生产配置从 `.env.production.example` 复制为 `.env.production` 后填写。`.env.production` 只能放在服务器本地，不能提交到 GitHub。

当前已知部署边界：

- 已完成公网 IP 演示。
- 已完成 PostgreSQL / Redis / Celery worker / Nginx 容器编排。
- 已完成生产库 Alembic 迁移修复。
- 尚未接入域名和 HTTPS。
- 尚未做对象存储、日志轮转、完整监控告警和数据库定时备份自动化。

## 文档入口

- 当前项目状态：`docs/roadmap/current-state.md`
- 开发基线：`docs/project-baseline.md`
- 文档总入口：`docs/README.md`
- 部署文档：`docs/deployment/`
- 演示资料：`docs/demo/public-demo-materials.md`
- 项目讲解材料：`docs/project-explanation/`
- 学习材料：`docs/learning/`
- 历史 spec：`docs/specs/completed/`
- 历史 plan：`docs/plans/completed/`

如果要继续开发，优先看 `docs/roadmap/current-state.md`，不要直接拿 `docs/specs/completed/` 里的旧 spec 重复执行。
