# AI 模拟面试系统开发基线

更新时间：2026-06-17

## 1. 当前项目定位

本项目是面向大学生、应届生和社会求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 工作流生成面试问题，并在面试结束后生成复盘报告和训练任务。

当前阶段已经完成 Backend Production Infrastructure V1：在保留 SQLite 本地默认开发体验的前提下，补齐 PostgreSQL 配置兼容摘要、Redis 健康检查、Celery eager/health task 基础和管理员后台基础设施观测。

## 2. 当前主入口

- 后端 API：`http://127.0.0.1:8000`
- 后端接口文档：`http://127.0.0.1:8000/docs`
- Vue3 主前端：`http://127.0.0.1:5173/vue/app/interview`
- Vue3 管理员后台：`http://127.0.0.1:5173/vue/app/admin`
- 旧原生前端：根目录 `index.html`、`app.js`、`styles.css` 暂时保留为兼容入口，不作为当前主前端继续开发。

## 3. 本地启动

分别启动后端和 Vue3 前端：

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

也可以先打开启动说明：

```powershell
.\start-dev.cmd
```

`start-dev.cmd` 主要用于提示启动方式，不会替代开发者同时管理两个服务窗口。

## 4. 测试和构建

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

## 5. 当前主链路

- 面试核心接口：`POST /api/interview/next-question`
- 默认 Agent runtime：`langgraph_mainline`
- 兼容兜底链路：`classic`
- RAG 接入方式：岗位知识库、题库、候选人画像三类 RAG 作为 LangGraph `retrieve_context` 节点复用现有检索能力。
- 后台观测能力：RAG 命中摘要、Agent 决策日志、LangGraph runtime audit、checkpoint summary、fallback 信息和 quality gate 信息。
- 基础设施观测能力：`/api/health` 和管理员后台配置区可以查看 database、Redis、Celery 的基础状态，并对外部服务 URL 做脱敏。

这条链路的表达重点是：系统不是简单调用一次 LLM，而是先组织候选人档案、历史回答、RAG 检索结果和 Agent 状态，再通过工作流节点生成、约束、记录和审计下一轮问题。

## 6. 目录结构基线

- `backend_python/`：FastAPI 后端、认证、数据库模型、RAG、Agent、LangGraph runtime 和管理后台接口。
- `frontend/`：Vue3 + Vite + TypeScript 当前主前端。
- `tests/`：后端 pytest 测试和旧原生前端相关 `.mjs` 测试。
- `docs/`：spec、plan、roadmap、学习资料、审计记录和开发基线文档。
- `scripts/`：本地维护脚本和数据辅助脚本。
- `alembic/`：数据库迁移脚本。
- `data/`：本地 SQLite 数据和开发数据，不作为生产数据源。
- `logs/`：本地日志输出。
- `deploy/`、`Dockerfile`、`docker-compose.yml`：部署相关历史或候选资料，当前阶段不作为主线执行对象。

## 7. 本地演示账号

开发环境建议使用：

- 普通演示账号：`d77013643@gmail.com / 123456`
- 管理员演示账号：`1011569954@qq.com / 123456`

如果账号不存在，可以通过注册接口创建，再在本地数据库中提升管理员角色。账号只作为本地开发和演示约定，不代表生产环境账号策略。

## 8. 当前生产化底座

已落地：

- SQLite 仍是本地默认数据库。
- PostgreSQL 作为生产候选数据库具备 `DATABASE_URL` 配置兼容、数据库类型摘要和 Alembic 迁移路径说明。
- Redis 具备 `disabled` / `ok` / `error` 三态健康检查，当前只作为后续 broker、缓存、限流和 token blacklist 的入口预留。
- Celery 具备 app 配置、health task、eager mode 测试和基础状态摘要；RAG 文档上传和 retry 已通过 taskId 派发 Celery ingestion task，并把 queued/running/succeeded/failed 状态写回数据库。
- 管理员后台展示基础设施状态，避免把数据库、Redis、Celery 的运行状态藏在后端内部。

仍未做：

- 不做真实 VPS/生产库迁移。
- 不做 Docker/Nginx/VPS/HTTPS 上线。
- 不引入 Qdrant、pgvector 或对象存储。
- 不重构 RAG、Agent、LangGraph 或 Vue3 主链路。

## 9. 下一阶段候选方向

建议下一阶段进入：

- Redis/Celery worker 真实运行演练：在不改变 SQLite 默认开发路径的前提下，验证非 eager worker 处理 RAG ingestion task。
- PostgreSQL 集成演练：在本机或容器环境验证 Alembic 迁移和 PostgreSQL 连接，不影响 SQLite 默认开发路径。
- RAG 摄取能力扩展：后续再讨论 OCR、Word/Excel/网页解析、对象存储或向量数据库，不与本轮 Celery 化混做。

## 10. 2026-06-17 补充：Async RAG Ingestion V2 已完成

本阶段已把 RAG 文档上传和 retry 从“接口内同步创建文档”升级为“接口创建/更新 `RagIngestionTask`，保存文本快照，然后通过 Celery taskId 派发后台入库任务”。Celery task 会重新打开数据库 session，根据 `taskId` 读取 `input_json` 中的 `textSnapshot`、metadata、可见性和知识库类型，复用现有 `create_rag_document_with_embeddings()` 创建 `RagDocument` / `RagChunk`，并把 `document_id`、`result_json`、`status`、`progress` 和失败原因写回任务表。

本阶段保持明确边界：未引入 Qdrant/pgvector、对象存储、OCR、Word/Excel/网页解析，也未做 Docker/Nginx/VPS/HTTPS 上线。前端只做最小状态兼容，知识库页和管理员后台能识别 `queued` 并显示为“排队中”。
