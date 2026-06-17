# Project Closure Audit V1 审计记录

更新时间：2026-06-17

## 1. 审计结论

本轮审计目标是建立后续 RAG 生产化、Redis、Celery、PostgreSQL 开发前的项目基线。本轮不新增业务功能，不做主链路重构，不删除无法确认安全性的历史文件。

初步只读扫描显示：当前项目已经具备 FastAPI 后端、Vue3 主前端、用户系统、三类 RAG、Agent/LangGraph 主链路、管理员后台观测和测试体系。当前最需要统一的是入口说明、文档状态、旧入口边界和下一阶段开发边界。

## 2. 已检查项

- [x] Git 工作区状态：开始审计时 `git status --short` 无输出。
- [x] 根目录文件结构：已确认 `backend_python/`、`frontend/`、`docs/`、`scripts/`、`tests/`、`data/`、`logs/`、`deploy/`、启动脚本和旧原生前端文件存在。
- [x] README 项目入口：已检查并在本轮更新。
- [x] docs roadmap / specs / plans 状态：已检查 active spec 和 active plan。
- [x] 后端启动脚本：`start-backend.cmd` 指向 `backend_python.main:app`，端口 `8000`。
- [x] Vue3 前端启动脚本：`start-vue-frontend.cmd` 指向 `frontend` 下的 Vite dev server，端口 `5173`。
- [x] 旧原生前端兼容入口：根目录 `index.html`、`app.js`、`styles.css` 保留。
- [x] `/api/interview/next-question` 主链路说明：当前基线记录为 `langgraph_mainline` 主链路，`classic` 为 fallback/helper。
- [x] RAG / Agent / LangGraph 当前能力索引：已写入 `docs/project-baseline.md`。
- [x] 后端测试命令。
- [x] 前端测试命令。
- [x] 前端构建命令。
- [x] 浏览器桌面端验证。
- [x] 浏览器移动端验证。

## 3. 保留但不作为当前主线的内容

- `index.html`、`app.js`、`styles.css`：旧原生前端兼容入口，当前主前端是 `frontend/` 下的 Vue3。
- `start-python-server.cmd`：旧兼容启动入口，当前建议优先使用 `start-backend.cmd` 和 `start-vue-frontend.cmd`。
- `deploy/`、`Dockerfile`、`docker-compose.yml`：部署相关历史或候选资料，本阶段不执行上线。

这些内容本轮不删除，原因是它们可能仍被历史测试、文档或兼容入口引用。后续如果要清理，应单独开“目录瘦身与 legacy 迁移”阶段。

## 4. 本轮不处理的遗留项

- Redis token blacklist、缓存、限流。
- Celery 异步任务。
- PostgreSQL 正式切换。
- Docker/Nginx/VPS/HTTPS 上线。
- RAG 主链路重构。
- Agent/LangGraph 主链路重构。
- Vue3 整站 UI 重构。
- 旧原生前端迁移到 `legacy_frontend/`。

## 5. 忽略和生成文件检查

`git status --ignored --short` 显示当前被忽略的主要类别包括：

- 本地环境：`.env`。
- IDE 和工具缓存：`.idea/`、`.pytest_cache/`、`.superpowers/`。
- Python 缓存：`backend_python/**/__pycache__/`、`scripts/__pycache__/`、`tests/__pycache__/`。
- 本地数据库和备份：`data/app.db`、`data/backups/`。
- 前端依赖和构建产物：`frontend/node_modules/`、`frontend/dist/`。
- 本地日志：`logs/`。

`.gitignore` 已覆盖上述主要生成物，本轮暂不追加忽略规则。

## 6. 验证记录

- 后端测试：`python -m pytest -q`，结果：`369 passed, 1 warning`。其中 warning 为 LangGraph/LangChain 依赖的弃用提示，不影响本轮审计。
- 前端测试：`cd frontend; npm.cmd run test`，结果：`30 passed` test files，`122 passed` tests。
- 前端构建：`cd frontend; npm.cmd run build`，结果：`vue-tsc --noEmit && vite build` 成功。
- 桌面端页面：`/vue/app/interview`、`/vue/app/admin` 已验证，页面可打开，无可见 `undefined`，无横向溢出。面试页在无已选档案时展示创建档案引导，属于预期状态。
- 移动端页面：390px 宽度下 `/vue/app/interview` 已验证，375px 宽度下 `/vue/app/admin` 已验证，无可见 `undefined`，无横向溢出。

## 7. 后续建议

下一阶段优先讨论 Backend Production Infrastructure V1。建议保留 SQLite 本地默认开发，同时增加 PostgreSQL 配置兼容，再引入 Redis 健康检查和 Celery 异步任务，最后让管理员后台展示异步任务状态、失败原因、重试次数和耗时。
