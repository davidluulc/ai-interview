# Backend Production Infrastructure V1：PostgreSQL 兼容、Redis 健康检查与 Celery 异步任务底座

更新时间：2026-06-17

## 1. 背景

AI 模拟面试系统已经完成 Project Closure Audit V1，当前主链路包括 FastAPI 后端、Vue3 前端、三类 RAG、Agent/LangGraph 主链路、RAG 文档管理、RAG ingestion task 持久化和管理员后台观测。

下一阶段不适合继续堆业务页面，而应该补齐后端生产化底座。当前项目已经有一部分基础设施脚手架：

- `.env.example` 已包含 `DATABASE_URL`、`REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`。
- `requirements.txt` 已包含 `redis` 和 `celery`。
- `backend_python/redis_client.py` 已有 Redis 客户端和健康检查雏形。
- `backend_python/celery_app.py` 已有 Celery app 配置。
- `backend_python/tasks/` 已有任务示例。
- `RagIngestionTask` 已在数据库中持久化 RAG 摄取任务状态。
- `docker-compose.yml` 已有 PostgreSQL、Redis、Celery worker 的候选编排。

但这些能力仍然偏脚手架，尚未形成稳定、可讲清、可测试、可逐步迁移的后端生产化架构。本阶段目标是把 PostgreSQL、Redis、Celery 的职责边界和最小可用链路整理清楚，并落地一组不破坏本地开发体验的基础能力。

## 2. 阶段目标

本阶段目标是建立后端生产化底座 V1：

1. 保留 SQLite 作为本地默认开发数据库。
2. 明确 PostgreSQL 作为生产环境主数据库的配置兼容路径。
3. 明确 Redis 作为短期状态、缓存、限流、token blacklist 和 Celery broker 的基础设施入口。
4. 明确 Celery 作为耗时任务异步执行框架的基础设施入口。
5. 为后续 Async RAG Ingestion V2 预留稳定任务接口。
6. 让管理员后台或健康检查接口能观察数据库、Redis、Celery 基础状态。
7. 保证测试环境不强依赖真实 Redis、Celery worker 或 PostgreSQL 服务。

本阶段不是为了“堆技术栈”，而是为了让 RAG 文件摄取、RAG evaluation、报告生成等耗时任务可以逐步从 HTTP 同步请求中拆出。

## 3. 三个组件的职责边界

### 3.1 PostgreSQL

PostgreSQL 负责长期可信业务数据：

- 用户、角色、refresh token。
- 投递档案、面试记录、报告、训练任务。
- RAG 文档、chunk、metadata、命中日志、质量评估数据。
- RAG ingestion task 状态、失败原因、重试次数、结果摘要。
- Agent 决策日志、runtime audit、LangGraph 观测数据。

本阶段不要求本地强制切换 PostgreSQL。本地默认仍然使用 SQLite，生产或集成环境通过 `DATABASE_URL` 切换 PostgreSQL。

### 3.2 Redis

Redis 负责短期、高频、可丢失或可重建的状态：

- Celery broker。
- Celery result backend。
- 健康检查。
- 后续 token blacklist。
- 后续接口限流。
- 后续短期缓存。
- 后续分布式锁或幂等 key。

Redis 不存核心业务数据，不替代 PostgreSQL。Redis 不可用时，系统应能在本地开发模式下降级，而不是直接阻断所有后端启动。

### 3.3 Celery

Celery 负责耗时任务异步化：

- RAG 文件解析、文本清洗、chunk 切分、入库。
- RAG evaluation 批量评估。
- 未来 embedding 批量生成。
- 未来面试报告生成。
- 未来定时清理或定时统计任务。

Celery 不直接对外提供 HTTP API。FastAPI 负责创建任务、鉴权、写入数据库状态、返回 taskId；Celery worker 负责后台执行并回写任务状态。

## 4. 推荐架构

```text
Vue3 前端
  -> FastAPI API
    -> PostgreSQL / SQLite 写入任务记录
    -> Celery 投递异步任务
      -> Redis broker / result backend
      -> Celery worker 执行耗时逻辑
      -> PostgreSQL / SQLite 更新任务状态、进度、失败原因和结果摘要
  -> Vue3 前端或管理员后台轮询任务状态
```

开发环境默认：

```text
SQLite + Celery eager mode + Redis disabled 或 Redis optional
```

生产候选环境：

```text
PostgreSQL + Redis + Celery worker
```

测试环境默认：

```text
SQLite + Celery eager mode + Redis fake/disabled
```

## 5. 本阶段功能范围

### 5.1 配置层

需要统一整理并测试以下配置：

- `DATABASE_URL`
- `AUTO_INIT_DB`
- `REDIS_ENABLED`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_TASK_ALWAYS_EAGER`

要求：

- 默认本地启动不依赖 PostgreSQL 或 Redis。
- 配置摘要对外展示时必须脱敏。
- 测试环境可通过环境变量切换 eager mode。

### 5.2 数据库兼容层

需要确认：

- SQLite 本地默认仍可启动。
- 非 SQLite 数据库不走 SQLite 自动补表逻辑。
- Alembic 迁移仍是 PostgreSQL 生产路径的主入口。
- `/api/admin/config` 或健康检查接口展示数据库类型时不泄露完整密码。

本阶段不要求真实执行 PostgreSQL 集成测试，除非本地环境已经具备可用 PostgreSQL 服务。

### 5.3 Redis 健康检查

需要明确 Redis 状态：

- `disabled`：本地开发未启用 Redis。
- `ok`：Redis 启用且 ping 成功。
- `error`：Redis 启用但连接失败。

健康检查输出应能支持管理员判断：

```text
Redis 是没启用、启用了且正常，还是启用了但失败。
```

### 5.4 Celery 基础任务链路

本阶段优先保证 Celery 基础设施可测试：

- Celery app 配置清晰。
- 有最小 `ping_task` 或 health task。
- eager mode 下测试不需要真实 worker。
- 任务投递失败时 API 能给出可解释错误。
- 管理员后台或健康检查可以展示 Celery 基础配置状态。

本阶段不强制把 RAG 上传主链路完全迁移到 Celery；该迁移属于后续 Async RAG Ingestion V2。

### 5.5 RAG ingestion 异步化预留

本阶段需要为下一阶段预留清晰接口边界：

- `RagIngestionTask` 继续作为任务状态事实来源。
- 后续异步任务应读取 taskId，再从数据库读取任务输入快照。
- worker 执行时更新 `pending -> running -> succeeded/failed`。
- retry 不应重复创建不可控的重复文档。
- 后续需要考虑幂等 key、重复上传保护和失败恢复。

## 6. 非目标

本阶段明确不做：

- 不强制本地切换 PostgreSQL。
- 不要求用户手动安装 PostgreSQL。
- 不要求真实 VPS 部署。
- 不做 Docker/Nginx/VPS/HTTPS 上线。
- 不把全部 RAG ingestion 主链路一次性迁移到 Celery。
- 不引入 Qdrant、pgvector 或对象存储。
- 不重构 RAG 检索、rerank、evaluation 算法。
- 不重构 Agent/LangGraph 主链路。
- 不做完整 token blacklist、限流、缓存策略。
- 不做复杂运维监控系统。

## 7. 建议实施顺序

本阶段 implementation plan 建议按以下顺序写：

1. 只读扫描当前配置、Redis、Celery、数据库、RAG ingestion task 代码。
2. 补配置测试：验证默认 SQLite、Redis disabled、Celery eager mode。
3. 整理数据库配置摘要：区分 SQLite/PostgreSQL，脱敏 URL。
4. 强化 Redis 健康检查：disabled/ok/error 三态。
5. 强化 Celery health task：eager mode 可测，worker mode 可运行。
6. 增加后端健康检查或管理员配置摘要字段。
7. 如有必要，补 Vue3 管理员后台的基础设施状态展示。
8. 更新 docs/project-baseline.md 和 docs/roadmap/current-state.md。
9. 运行后端测试、前端测试、前端构建。
10. 使用浏览器验证管理员后台状态展示。
11. 归档 spec 和 plan。

## 7.1 追求目标执行约定

本阶段可以直接交给 Codex 追求目标模式执行。执行时不需要先由当前对话单独创建 active plan 文件，而是要求追求目标模式先根据本 spec 在 `docs/plans/active/` 下生成 implementation plan，再严格按 plan 执行。

执行时必须遵守以下约束：

- 先写或更新后端测试，再实现后端代码。
- PostgreSQL 只做配置兼容、URL 脱敏、数据库类型识别和 Alembic 路径说明，不要求本地真实切换。
- Redis 只做健康检查和基础入口，不接入业务缓存、限流或 token blacklist。
- Celery 只做 app 配置、health task、eager mode 和任务投递底座，不迁移完整 RAG ingestion 主链路。
- 如需前端改动，只做管理员后台基础设施状态的最小展示。
- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不重构 RAG、Agent、LangGraph 或 Vue3 主链路。
- 完成后更新 `docs/project-baseline.md`、`docs/roadmap/current-state.md`、`docs/specs/README.md` 和 `docs/plans/README.md`。
- 完成后将本 spec 和生成的 plan 从 `active/` 移动到 `completed/`。

## 8. 测试计划

后端测试：

- 默认配置下不依赖 Redis 和 PostgreSQL。
- `DATABASE_URL=sqlite:///...` 时识别为 local sqlite。
- PostgreSQL URL 配置时能识别为外部数据库，并脱敏密码。
- `REDIS_ENABLED=false` 时健康状态为 disabled。
- `REDIS_ENABLED=true` 且 fake client ping 成功时状态为 ok。
- `REDIS_ENABLED=true` 且 fake client ping 失败时状态为 error。
- Celery eager mode 下 health task 可执行。
- 管理员配置或健康检查接口能返回基础设施状态。

前端测试：

- 如果管理员后台新增基础设施状态展示，需要覆盖 Redis、Celery、database 三类状态。
- Redis disabled 不应显示为系统故障。
- 外部数据库 URL 不应泄露密码。

回归测试：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

- `/vue/app/admin` 桌面端可查看基础设施状态。
- `/vue/app/admin` 移动端无横向溢出。
- 页面无可见 `undefined`。

## 9. 验收标准

完成后必须满足：

- 本地默认启动仍不依赖 PostgreSQL 或 Redis。
- PostgreSQL 作为生产数据库的配置路径被明确支持和测试。
- Redis 健康状态具备 disabled/ok/error 三态。
- Celery 至少具备可测试的 health task 和 eager mode 测试。
- 管理员或健康检查接口能观察 database/redis/celery 基础状态。
- 没有把 Redis 当成长期业务数据库。
- 没有把 Celery worker 暴露成 HTTP 服务。
- 没有重构 RAG、Agent、LangGraph 或 Vue3 主链路。
- 后端测试、前端测试、前端构建通过。
- spec 和 plan 最终归档到 completed。

## 10. 面试表达种子

可以这样讲：

```text
项目进入生产化增强前，我没有直接把 Redis、Celery、PostgreSQL 一次性硬塞进业务主链路，而是先做了后端生产化底座设计。

PostgreSQL 负责长期可信业务数据，Redis 负责短期状态和任务队列基础设施，Celery 负责把 RAG 文件摄取、批量评估这类耗时任务从 HTTP 请求链路中拆出去。

本地开发仍保留 SQLite，避免环境复杂度影响迭代；生产环境通过 DATABASE_URL 切换 PostgreSQL。Redis 和 Celery 也采用可选启用和 eager mode 测试，保证没有外部服务时测试仍然稳定。这样后续再把 RAG ingestion 迁移成真正异步任务时，任务状态、失败原因、重试和管理员观测都有清晰的落点。
```

## 11. 下一阶段衔接

本阶段完成后，下一阶段建议进入：

```text
Async RAG Ingestion V2：将 RAG 文档上传、解析、清洗、chunk 入库从同步 HTTP 请求迁移到 Celery 异步任务。
```
