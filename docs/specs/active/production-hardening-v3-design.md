# Production Hardening V3：后端可靠性与安全加固

更新时间：2026-06-17

## 1. 背景

当前项目已经完成两个生产化前置阶段：

- Backend Production Infrastructure V1：补齐 PostgreSQL 配置兼容、Redis 健康检查、Celery eager/health task 和管理员后台基础设施观测。
- Async RAG Ingestion V2：RAG 文档上传和 retry 已通过 `taskId` 派发 Celery ingestion task，任务状态、进度、失败原因和 `documentId` 会写回数据库。

这说明项目已经不再只是“能跑的 AI 应用 MVP”，而是进入后端生产化加固阶段。下一步不应重复做基础设施配置，也不应直接跳到 Docker/Nginx/VPS 上线，而应先把异步任务、安全边界、限流、幂等和可观测性继续补强。

## 2. 本阶段定位

Production Hardening V3 是上线部署前的后端可靠性增强阶段。它不追求一次性把所有生产问题解决完，而是围绕当前项目已经出现的真实痛点分三步推进：

```text
V3.1 Celery worker 真实运行与任务可靠性
-> V3.2 安全与流量保护
-> V3.3 缓存、幂等和可观测性增强
```

本 spec 是 V3 总设计文档。追求目标执行时应先创建 plan，并从 V3.1 开始实现。V3.2 和 V3.3 可以写入 plan 的后续任务池，但如果一次执行压力过大，可以在完成 V3.1 后归档为阶段性成果，再新开 V3.2 spec。

## 3. 已有能力与不重复内容

本阶段不重复开发：

- PostgreSQL 配置兼容摘要。
- Redis disabled / ok / error 健康检查。
- Celery app 基础配置、health task、eager mode 测试。
- RAG 上传任务持久化表。
- RAG upload / retry 的 Celery taskId 派发。
- Vue3 管理员后台基础设施状态展示。
- Vue3 知识库页和管理员页的 `queued` 状态兼容。
- LangGraph / Agent 主链路。
- RAG retrieval、rerank、evaluation 算法。

本阶段只在这些能力之上继续加固。

## 4. V3.1：Celery Worker 真实运行与任务可靠性

### 4.1 目标

当前 Celery 主要通过 eager mode 保证本地测试便利。V3.1 要让项目具备“真实 worker 模式可运行、可验证、可诊断”的能力，同时保持 SQLite 本地默认开发路径不被破坏。

完成后应能讲清：

```text
本地测试使用 Celery eager mode，保证不启动 Redis/worker 也能跑完整测试；
真实异步演练时可以关闭 eager mode，使用 Redis broker 启动 Celery worker，由 worker 根据 taskId 执行 RAG 入库。
```

### 4.2 功能范围

V3.1 应包含：

- 增加 Celery worker 启动脚本或文档化命令。
- 明确 eager mode 与 worker mode 的环境变量切换方式。
- 增加 worker mode 配置摘要，管理员后台能看出当前是 eager 还是 configured/worker-ready。
- RAG ingestion task 在非 eager 模式下返回 `queued`，不假装已经完成。
- `dispatch_rag_ingestion_task()` 需要更清楚地区分：
  - 派发成功但未完成。
  - eager mode 下已同步完成。
  - broker/dispatch 失败。
- 任务执行函数需要记录更稳定的耗时、开始时间、结束时间或可推导字段。
- 失败任务要保留可重试快照，不吞掉关键错误。
- 测试要覆盖 eager mode 和模拟非 eager dispatch。

### 4.3 不做内容

V3.1 不做：

- 不强制安装真实 Redis。
- 不要求本地必须启动 Celery worker 才能跑测试。
- 不迁移 PostgreSQL。
- 不做 Docker Compose 联调。
- 不做 token blacklist、限流、缓存。
- 不做 OCR、Word/Excel/网页解析。

## 5. V3.2：安全与流量保护

### 5.1 目标

V3.2 用来补齐后端常见安全边界，重点不是“企业级安全体系”，而是让项目具备实习面试可讲的基础防护。

建议能力：

- refresh token 退出增强。
- token blacklist 设计与最小实现。
- 登录接口、上传接口、AI 生成接口的基础限流。
- 对敏感配置、外部服务 URL、错误响应继续脱敏。
- 管理员接口保持后端强鉴权，不依赖前端隐藏入口。

### 5.2 边界

V3.2 不做复杂 RBAC 权限矩阵，不做短信/邮箱验证码，不做商业化账号系统。

## 6. V3.3：缓存、幂等和可观测性增强

### 6.1 目标

V3.3 处理生产环境里常见的“重复请求、重复任务、排查困难”问题。

建议能力：

- RAG 上传防重复提交。
- ingestion task 幂等键设计。
- retry 防止重复并发触发。
- 任务耗时、失败类型、重试次数聚合。
- 管理员后台展示更清楚的任务状态、失败类型和最近异常。
- 为后续部署监控预留结构化日志字段。

### 6.2 边界

V3.3 不引入完整 APM，不做 Prometheus/Grafana，不做大型监控平台。

## 7. 接口与兼容性要求

必须保持兼容：

- `/api/rag/documents/upload`
- `/api/rag/documents/ingestion-tasks`
- `/api/rag/documents/ingestion-tasks/{task_id}`
- `/api/rag/documents/ingestion-tasks/{task_id}/retry`
- `/api/admin/config`
- `/api/admin/rag/ingestion-tasks`
- `/api/health`

现有前端调用不能被破坏。允许增加字段，但不删除已有字段。

## 8. 测试策略

每一轮实现必须测试驱动。

V3.1 后端测试建议：

- eager mode 下 upload 仍可最终返回 `succeeded`。
- 模拟非 eager mode 下 upload 返回 `queued`。
- Celery dispatch 失败时任务变为 `failed`，并保留 `canRetry` 和错误原因。
- retry 复用 dispatch，非 eager mode 下不在 HTTP 请求内直接完成入库。
- `/api/health` 和 `/api/admin/config` 能展示 Celery 当前模式。

V3.1 前端测试建议：

- 知识库页 `queued` 文案不误导用户。
- 管理员后台能区分 queued/running/succeeded/failed。
- 不做页面大重构。

回归验证：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

要求桌面端和移动端无 `undefined`、无横向溢出。

## 9. 文档与归档要求

实现完成后必须更新：

- `docs/project-baseline.md`
- `docs/roadmap/current-state.md`
- `docs/specs/README.md`
- `docs/plans/README.md`

如果只完成 V3.1，应在文档中明确：

```text
Production Hardening V3.1 已完成，V3.2/V3.3 尚未执行。
```

不能把整个 V3 都标记完成。

## 10. 面试表达种子

可以这样讲：

```text
我没有一开始就把所有生产化能力堆上去，而是按阶段推进。先做基础设施配置和健康检查，再把 RAG 文档入库迁移到 Celery taskId 异步任务模型。接下来我继续做 Production Hardening，把 Celery 从 eager 测试模式扩展到真实 worker 演练，同时补充任务失败恢复、重试、限流、token blacklist、幂等和可观测性。这样做的好处是每一阶段都有真实业务痛点和测试验证，而不是为了堆技术栈。
```

V3.1 完成后可以补充：

```text
RAG ingestion 在本地测试时可以使用 eager mode，保证开发环境简单；在真实异步演练时可以切换到 Redis broker 和 Celery worker，HTTP 接口只返回 queued，worker 后台执行入库并写回状态。这个设计兼顾了本地开发效率和生产环境可迁移性。
```

## 11. 追求目标建议文本

```text
根据 docs/specs/active/production-hardening-v3-design.md，持续推进 AI 模拟面试系统 Production Hardening V3。

要求：
1. 先根据 active spec 编写 docs/plans/active/production-hardening-v3.md，然后严格按 plan 执行。
2. 本阶段优先执行 V3.1：Celery worker 真实运行与任务可靠性。
3. 每轮开发前先用中文解释本轮要学的后端生产化 / 异步任务可靠性知识点。
4. 开发时优先测试驱动，先写或更新后端测试，再实现。
5. 保持 SQLite 作为本地默认开发数据库，不强制安装 PostgreSQL。
6. 保留 Celery eager mode 测试能力，不要求本地真实启动 Redis 或 Celery worker 才能跑测试。
7. 允许增加 worker mode 配置、启动脚本、健康检查摘要和任务可靠性字段，但不能破坏现有接口兼容。
8. 不做 Docker、Nginx、VPS、HTTPS 上线。
9. 不引入 Qdrant、pgvector、对象存储。
10. 不做 OCR、Word / Excel / 网页解析。
11. 不重构 RAG 检索、rerank、evaluation 算法。
12. 不重构 Agent、LangGraph 或 Vue3 主链路。
13. 前端只允许最小化更新知识库页和管理员后台的任务状态文案与展示兼容，不做页面大重构。
14. 完成后运行 python -m pytest -q、cd frontend && npm.cmd run test、cd frontend && npm.cmd run build。
15. 完成后使用内置浏览器验证 /vue/app/knowledge 和 /vue/app/admin 的桌面端与移动端，无 undefined、无横向溢出。
16. 完成后更新 docs/project-baseline.md、docs/roadmap/current-state.md、docs/specs/README.md、docs/plans/README.md。
17. 如果只完成 V3.1，只能标记 Production Hardening V3.1 完成，不能宣称整个 V3 完成。
```
