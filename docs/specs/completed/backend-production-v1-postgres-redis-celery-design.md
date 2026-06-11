# 后端生产化 V1：数据库适配 + Redis + Celery 设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统的下一阶段后端生产化开发。

上一阶段已经完成：

```text
RAG 工程化阶段性版本
Interview Orchestrator Agent
Agent Policy
LangGraph 旁路 V2/V3
训练闭环
管理员后台 MVP
```

当前项目已经具备“AI 应用核心能力”，下一步需要补强后端工程化能力，让项目从本地 MVP 更接近真实公司后端系统。

本阶段重点不是立刻上线，也不是堆中间件，而是建立：

```text
可切换数据库配置
Redis 基础设施层
Celery 异步任务框架
AI/RAG 耗时任务异步化预留
生产化学习文档和面试表达
```

## 2. 本阶段总目标

本阶段名称：

```text
PostgreSQL + Redis + Celery 后端生产化 V1
```

但落地时要注意：

```text
本地开发阶段继续默认使用 SQLite。
不要求当前电脑立刻安装 PostgreSQL。
生产数据库方向预留 PostgreSQL，同时保留 MySQL 可选理解。
Redis 和 Celery 先做基础设施和最小业务闭环。
```

最终效果：

- 本地开发仍然简单，默认 SQLite 可跑。
- 项目支持通过 `DATABASE_URL` 切换数据库。
- 文档中说明生产推荐 PostgreSQL 的原因。
- Redis client 有统一封装和健康检查。
- Celery app 能以 Redis 作为 broker/backend。
- 至少有一个可测试异步任务。
- 至少有一个 AI/RAG 业务任务被设计为异步任务入口或预留接口。
- 后续 Docker/Nginx/云服务器上线时可以直接承接这些基础设施。

## 3. 为什么当前更适合做后端生产化

当前项目的核心 AI 能力已经具备阶段性成品：

- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档管理、metadata、hybrid search、rerank、query rewrite、质量评估和命中日志。
- 自研 Agent：state、tool calls、decision、fallback、normalize、guardrail、nodeTrace。
- Agent Policy：弱回答、重复追问、话题切换、coach/interview 差异。
- LangGraph 旁路：StateGraph 节点、真实/fake adapter、checkpoint summary。

这些能力已经可以作为项目核心竞争力。继续做 Vue3 前端重构当然有价值，但用户目标更偏 Python 后端岗 / AI 应用开发岗，因此下一步先补：

```text
数据库生产化
缓存与状态基础设施
异步任务队列
耗时 AI 任务后台化
```

这更贴近后端岗位面试会追问的工程能力。

## 4. 数据库选型边界

### 4.1 本地开发默认 SQLite

本地开发继续使用 SQLite，原因：

- 启动简单。
- 不依赖外部数据库服务。
- 测试速度快。
- 适合 Codex 持续开发。

当前阶段不能因为引入生产化设计而破坏本地体验。

### 4.2 生产推荐 PostgreSQL

生产环境推荐 PostgreSQL，原因：

- Python / FastAPI 生态常见。
- 和 SQLAlchemy / Alembic 配合成熟。
- 后续可以接 `pgvector`，为向量检索生产化留空间。
- 云服务商托管 PostgreSQL 支持普遍。

但本阶段不要求用户现在手动安装 PostgreSQL。

### 4.3 MySQL 的位置

用户本机已经安装 MySQL。MySQL 仍然有学习和面试价值，尤其是索引、事务、锁、慢查询、B+ 树等八股文。

但本项目的生产化路线不强制切 MySQL。推荐表达是：

```text
本地默认 SQLite。
生产推荐 PostgreSQL。
MySQL 作为关系型数据库知识储备和可选适配方向。
```

## 5. 本阶段要做

### 5.1 阶段 1：数据库配置生产化

目标：让项目数据库连接从“写死本地 SQLite”升级为“通过环境变量配置”。

要做：

- 检查现有 `backend_python/database.py`。
- 保留 SQLite 默认行为。
- 明确 `DATABASE_URL` 的优先级。
- 整理 `.env.example` 中的数据库配置说明。
- 检查 SQLAlchemy 和 Alembic 是否依赖 SQLite 特有语法。
- 增加数据库 URL 解析和配置测试。

验收：

- 不配置 `DATABASE_URL` 时仍使用本地 SQLite。
- 配置 PostgreSQL 风格 URL 时能正确构造 engine 配置。
- 测试不要求真实 PostgreSQL 服务。
- Alembic 文档说明如何面向 PostgreSQL 运行迁移。

### 5.2 阶段 2：Redis 基础设施层

目标：先接入 Redis client，不急着把所有功能改成 Redis。

要做：

- 新增 Redis 配置项：
  - `REDIS_URL`
  - `REDIS_ENABLED`
- 新增 Redis client 封装。
- 支持 Redis 未开启时优雅降级。
- 新增 Redis health check。
- 新增简单 cache service：
  - `get`
  - `set`
  - `delete`
  - `exists`
- 写测试覆盖 enabled/disabled 两种状态。

本阶段 Redis 可以先服务于：

- 任务状态缓存预留。
- token 黑名单预留。
- 限流预留。
- RAG query 缓存预留。

验收：

- 没有 Redis 服务时，本地测试仍能通过。
- Redis disabled 时接口不报错。
- Redis enabled 但连接失败时日志清晰。
- 有一个健康检查能返回 Redis 状态。

### 5.3 阶段 3：Celery 异步任务框架

目标：建立异步任务队列骨架。

要做：

- 新增 Celery 配置项：
  - `CELERY_BROKER_URL`
  - `CELERY_RESULT_BACKEND`
  - `CELERY_TASK_ALWAYS_EAGER`
- 新增 `backend_python/celery_app.py`。
- 新增 `backend_python/tasks/` 目录。
- 新增 `ping_task` 或 `health_task`。
- 测试中使用 eager 模式，不要求启动真实 worker。
- 文档中说明真实运行 worker 的命令。

验收：

- 测试环境可以同步执行 Celery task。
- 不启动 Redis / worker 时测试仍能验证任务逻辑。
- 文档说明生产环境要启动：

```text
FastAPI API 服务
Celery worker
Redis broker/backend
```

### 5.4 阶段 4：AI/RAG 耗时任务异步化预留

目标：不一口气重构所有 RAG，而是先选低风险场景做异步入口或任务状态模型。

候选任务：

- RAG 文档入库任务。
- embedding 生成任务。
- RAG evaluation 批量评测任务。
- 简历解析任务。
- 面试报告生成任务。

推荐本阶段优先做：

```text
RAG evaluation 异步任务
```

原因：

- 业务风险低。
- 不影响主面试链路。
- 很适合展示“耗时任务后台化”。
- 可以和现有 RAG evaluation 测试结合。

要做：

- 设计 task id。
- 设计任务状态结构：
  - `pending`
  - `running`
  - `success`
  - `failed`
- 支持查询任务状态。
- 支持在 eager 测试模式下立即拿到结果。

验收：

- 提交异步任务后能拿到 `taskId`。
- 查询任务状态能返回 status。
- 失败时能记录错误。
- 不破坏现有同步 RAG evaluation。

### 5.5 阶段 5：文档、路线和面试表达

要做：

- 新增中文学习文档：

```text
docs/learning/11-PostgreSQL Redis Celery如何让后端走向生产化.md
```

- 更新：
  - `docs/roadmap/project-progress.md`
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`

学习文档必须讲清：

- SQLite、MySQL、PostgreSQL 的区别。
- 为什么本地继续 SQLite。
- Redis 在后端系统中的位置。
- Celery 为什么适合 AI/RAG 耗时任务。
- 同步接口和异步任务的区别。
- 后续 Docker/Nginx/云服务器部署时这些组件如何串起来。
- 面试时如何讲。

## 6. 本阶段不做

本阶段明确不做：

- 不做 Docker Compose。
- 不做 Nginx。
- 不做云服务器上线。
- 不做 Vue3 前端重构。
- 不强制安装 PostgreSQL。
- 不强制安装本机 Redis。
- 不把所有接口都改成 Celery。
- 不重构所有 RAG 底层算法。
- 不引入微服务架构。
- 不引入 Kubernetes。
- 不引入复杂监控告警平台。

这些后续可以进入：

```text
Docker + Nginx + 云服务器上线 V1
```

## 7. 数据结构草案

### 7.1 环境变量草案

```env
# 本地默认 SQLite；生产可切换 PostgreSQL
DATABASE_URL=sqlite:///./data/ai_interview.db

# Redis 基础设施
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_ALWAYS_EAGER=true
```

### 7.2 任务状态草案

```json
{
  "taskId": "rag-eval-20260611-001",
  "taskType": "rag_evaluation",
  "status": "success",
  "progress": 100,
  "message": "RAG evaluation finished.",
  "result": {
    "caseCount": 8,
    "averageHitRate": 0.75
  },
  "error": "",
  "createdAt": "2026-06-11T10:00:00",
  "updatedAt": "2026-06-11T10:00:05"
}
```

## 8. 推荐测试策略

必须继续 TDD。

重点测试：

- `tests/test_database_config.py`
  - 默认 SQLite。
  - `DATABASE_URL` 覆盖。
  - PostgreSQL URL 解析。

- `tests/test_redis_client.py`
  - disabled 状态。
  - fake client get/set/delete。
  - health check 输出。

- `tests/test_celery_app.py`
  - eager 模式执行 ping task。
  - task 返回 JSON 可序列化结果。

- `tests/test_async_tasks.py`
  - 创建任务状态。
  - 查询任务状态。
  - 失败状态记录错误。

- 现有回归：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 9. 面试表达目标

完成后可以这样讲：

```text
项目早期为了降低本地开发成本使用 SQLite。后续我通过 DATABASE_URL 抽象数据库连接，让 SQLAlchemy 和 Alembic 能支持生产数据库，生产方向推荐 PostgreSQL，也保留 MySQL 作为关系型数据库知识储备。

对于 AI 应用里的耗时任务，例如 RAG 文档入库、embedding 生成、简历解析和 RAG evaluation，我引入 Redis + Celery。Redis 承担 broker/backend、缓存和任务状态基础设施，Celery 把耗时任务从同步 HTTP 请求中拆出去，避免接口长时间阻塞。

当前阶段我没有一口气做 Docker/Nginx/云服务器上线，而是先把后端生产化底座打好，后续上线时可以用 Docker Compose 把 FastAPI、PostgreSQL、Redis、Celery worker、Nginx 串起来。
```

如果面试官问为什么本地还用 SQLite：

```text
因为本地开发阶段追求启动简单和测试稳定。生产化不是把开发环境搞复杂，而是让配置具备迁移能力。通过 DATABASE_URL 保持本地 SQLite 默认，同时预留 PostgreSQL 生产配置，这样开发体验和生产能力都能兼顾。
```

## 10. 下一步

下一步应先写 implementation plan：

```text
docs/plans/active/backend-production-v1-postgres-redis-celery.md
```

推荐执行顺序：

```text
数据库配置测试
-> 数据库配置实现
-> Redis client 测试
-> Redis client 实现
-> Celery app 测试
-> Celery app 实现
-> RAG evaluation 异步任务预留
-> 学习文档和路线文档
-> 全量测试
```
