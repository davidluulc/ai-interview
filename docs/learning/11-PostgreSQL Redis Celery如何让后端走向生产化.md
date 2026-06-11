# PostgreSQL Redis Celery 如何让后端走向生产化

## 1. 这一阶段解决什么问题

AI 模拟面试系统前面已经完成了 RAG、Agent、LangGraph、用户系统、训练闭环和管理员后台。那些能力解决的是“产品有没有核心功能”。

本阶段解决的是另一个问题：

```text
这个项目能不能从本地 MVP 逐步走向真实后端工程？
```

真实后端系统通常不会只关心接口能不能跑，还会关心：

- 数据库能不能从本地文件迁移到生产数据库。
- 缓存和状态能不能由 Redis 承接。
- 耗时任务能不能放到后台执行。
- 本地测试能不能不依赖一堆外部服务。
- 后续 Docker、Nginx、云服务器上线时有没有清晰接口。

## 2. SQLite、MySQL、PostgreSQL 的区别

### SQLite

SQLite 是文件型数据库。

优点：

- 不需要单独安装数据库服务。
- 本地启动简单。
- 测试速度快。
- 非常适合项目早期开发。

缺点：

- 不适合高并发写入。
- 不适合复杂生产运维。
- 多实例部署时不方便共享数据。

所以本项目本地继续默认 SQLite，这是为了让开发和测试稳定。

### MySQL

MySQL 是常见生产关系型数据库。

它非常适合学习后端基础：

- 索引。
- B+ 树。
- 事务。
- 隔离级别。
- 锁。
- 慢查询。

你本机已经安装 MySQL，所以 MySQL 很适合用来补后端八股文。

但本项目没有强制切 MySQL，因为当前 AI 应用生产化路线更推荐 PostgreSQL。

### PostgreSQL

PostgreSQL 也是生产级关系型数据库，在 Python / FastAPI / AI 应用项目里很常见。

它的优势是：

- SQLAlchemy / Alembic 支持成熟。
- JSON、全文检索、扩展能力强。
- 后续可以接 `pgvector`，为向量检索生产化留空间。
- 云服务商托管支持普遍。

所以项目路线是：

```text
本地默认 SQLite
生产推荐 PostgreSQL
MySQL 作为关系型数据库知识储备和可选适配方向
```

## 3. DATABASE_URL 是什么

`DATABASE_URL` 是数据库连接字符串。

它的意义是：代码不要写死连接哪个数据库，而是从环境变量读取。

例如本地：

```env
DATABASE_URL=sqlite:///data/app.db
```

生产可以换成：

```env
DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/ai_interview
```

这样代码仍然走同一套 SQLAlchemy 入口，但数据库可以根据环境变化。

本阶段新增的数据库配置 helper 做了两件事：

- SQLite 自动加 `check_same_thread=false`。
- 外部数据库启用 `pool_pre_ping`，减少连接池里拿到坏连接的概率。

## 4. Redis 在后端系统中的位置

Redis 是内存型数据服务，常用于：

- 缓存。
- token 黑名单。
- 短期验证码。
- 限流计数器。
- 分布式锁。
- Celery broker。
- Celery result backend。
- 异步任务状态。

本阶段没有把业务强行绑定到 Redis，而是先做了可选基础设施：

```text
REDIS_ENABLED=false 时：本地禁用，不影响开发。
REDIS_ENABLED=true 时：尝试连接 Redis，并在 health 中暴露状态。
```

这叫“优雅降级”。

优雅降级的意义是：本地没有 Redis，也不应该导致整个项目启动失败。

## 5. Celery 是什么

Celery 是 Python 里的异步任务队列框架。

它一般需要：

```text
FastAPI API 服务
Redis 或 RabbitMQ 作为 broker
Celery worker 执行任务
Redis 或数据库保存结果
```

用户请求进来后，API 不一定要同步做完所有事情，而是可以：

```text
用户提交任务
-> API 返回 taskId
-> Celery worker 后台执行
-> 用户轮询 taskId 查询状态
```

这对 AI 应用尤其重要，因为很多任务比较耗时：

- PDF / 图片简历解析。
- 文档入库。
- embedding 生成。
- RAG 批量评测。
- 面试报告生成。
- 大模型批量调用。

## 6. 为什么测试环境用 eager 模式

本阶段使用：

```env
CELERY_TASK_ALWAYS_EAGER=true
```

意思是：测试里调用 `.delay()` 时，不真的丢给 worker，而是在当前进程同步执行。

这样做的好处：

- 单元测试不需要启动 Redis。
- 单元测试不需要启动 Celery worker。
- 仍然能验证任务函数、taskId、status、result 这些业务逻辑。

生产环境再设置：

```env
CELERY_TASK_ALWAYS_EAGER=false
```

然后启动 worker。

## 7. 同步接口和异步任务的区别

同步接口：

```text
前端请求
-> 后端立即处理
-> 后端立即返回结果
```

适合快任务，例如：

- 登录。
- 查询列表。
- 获取面试历史。

异步任务：

```text
前端提交任务
-> 后端立即返回 taskId
-> worker 后台执行
-> 前端查询任务状态
```

适合慢任务，例如：

- RAG evaluation。
- 文档批量入库。
- embedding 批量生成。
- 复杂报告生成。

本阶段先给 RAG evaluation 做异步任务入口，是因为它低风险，不影响主面试流程。

## 8. 本阶段代码怎么串起来

核心文件：

```text
backend_python/database.py
backend_python/redis_client.py
backend_python/celery_app.py
backend_python/task_status.py
backend_python/tasks/health.py
backend_python/tasks/rag_evaluation.py
backend_python/routes/rag.py
```

链路可以理解成：

```text
DATABASE_URL
-> database.py 构造 SQLAlchemy engine

REDIS_ENABLED / REDIS_URL
-> redis_client.py 构造 Redis health 和可选 cache

CELERY_BROKER_URL / CELERY_RESULT_BACKEND
-> celery_app.py 构造 Celery app

POST /api/rag/evaluation/tasks
-> 创建 task status
-> 调用 run_rag_evaluation_task.delay()
-> eager 模式下立即执行
-> 查询 task status
```

## 9. 后续上线时怎么串

后续进入 Docker / Nginx / 云服务器阶段时，可以演进成：

```text
Nginx
-> FastAPI API 服务
-> PostgreSQL 保存业务数据
-> Redis 作为缓存和 Celery broker
-> Celery worker 执行耗时 AI/RAG 任务
```

Docker Compose 里通常会有：

```text
api
worker
postgres
redis
nginx
```

本阶段先不做 Docker/Nginx，是为了避免工程复杂度太早膨胀。

## 10. 面试时怎么讲

可以这样表达：

```text
项目早期为了降低本地开发成本，默认使用 SQLite。后续我通过 DATABASE_URL 抽象数据库连接，让 SQLAlchemy engine 可以根据环境切换数据库。本地仍然用 SQLite，生产方向推荐 PostgreSQL，并为后续 pgvector 留空间。

在缓存和任务队列方面，我先引入 Redis 的可选基础设施。REDIS_ENABLED=false 时系统可以优雅降级，本地没有 Redis 也能正常开发和测试；上线后可以把 Redis 用于 token 黑名单、缓存、限流和 Celery broker。

对于 RAG evaluation 这类耗时任务，我引入 Celery 任务框架，并在测试环境使用 eager 模式，让任务可以同步执行，避免测试依赖真实 Redis 和 worker。业务上通过 taskId、status、progress、result、error 建立异步任务模型，后续可以迁移到真正的 worker 后台执行。
```

如果面试官问为什么不一开始就上 PostgreSQL 和 Redis：

```text
我把本地开发体验和生产化能力分开处理。本地默认 SQLite 可以保证开发简单、测试稳定；生产化能力通过 DATABASE_URL、Redis 可选开关和 Celery eager 模式逐步引入。这样不是逃避生产化，而是避免在项目还在快速迭代时把本地环境复杂化。
```
