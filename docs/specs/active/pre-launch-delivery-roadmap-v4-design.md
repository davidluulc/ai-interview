# Pre-Launch Delivery Roadmap V4：生产化收口、上线交付、项目讲解与简历材料

更新时间：2026-06-18

## 1. 背景

当前 AI 模拟面试系统已经完成了比较完整的产品和工程主链路：

- Vue3 前端、FastAPI 后端、用户系统、管理员后台。
- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档管理、摄取任务、质量评估、命中日志和调试面板。
- Agent / LangGraph 面试编排链路、runtime audit、workflow trace。
- 面试历史、报告、weakTag、训练任务和训练闭环。
- 基础生产化能力：PostgreSQL 配置兼容、Redis/Celery 基础设施入口、token blacklist、限流、错误脱敏、幂等、retry 并发保护。
- Dockerfile、docker-compose、Nginx 配置和部署文档已有基础版本。

但项目还没有真正完成“可投简历、可上线展示、可讲清楚”的最终交付闭环。下一阶段不能继续无边界堆功能，也不能只做学习文档。需要围绕上线和面试竞争力做生产化收口。

## 2. 本阶段总目标

本阶段目标不是把项目无限做复杂，而是把现有系统整理成一个能上线、能演示、能讲、能写进简历的作品。

完成后应达到：

- 本地开发仍可快速启动，不因为 PostgreSQL / Redis / Celery 增加日常开发负担。
- 生产化路径清楚：FastAPI、Vue3、PostgreSQL、Redis、Celery worker、Nginx 能通过 Docker Compose 或等价方式串起来。
- RAG 文档摄取的异步任务链路能解释清楚：HTTP 快速返回 taskId，后台 worker 处理，任务状态可见，失败可重试。
- 上线前关键风险有检查清单：环境变量、密钥、数据库、迁移、CORS、HTTPS、Nginx、日志、备份、回滚。
- 项目讲解材料完整：业务背景、系统架构、核心链路、RAG、Agent/LangGraph、生产化、可观测性、技术取舍。
- 简历材料完整：项目名称、项目描述、技术栈、职责、亮点、难点、量化表达、面试追问准备。

## 3. 执行原则

### 3.1 不以复杂度为目标

项目竞争力来自“真实问题 + 合理设计 + 可验证落地 + 能讲清取舍”，不是技术栈越多越好。

本阶段新增能力必须回答三个问题：

```text
它解决了什么真实痛点？
不用它会有什么问题？
做完后我能在面试里怎样讲？
```

如果无法回答，就不进入本阶段。

### 3.2 本地轻量，生产兼容

本地默认仍保留 SQLite 快速开发路径。PostgreSQL、Redis、Celery worker、Nginx 等生产组件优先通过配置和 Docker Compose 串起来，不强制每次开发都依赖全部服务。

### 3.3 先收口，再上线，再讲解

推荐顺序：

```text
Async Worker Readiness V4
-> PostgreSQL Compatibility V4
-> Deployment Integration V4
-> Project Explanation & Resume Pack V1
```

不要跳过生产化收口直接上线，也不要在上线前继续大规模重构 RAG、Agent 或前端。

### 3.4 测试优先

每个开发阶段都应优先补测试或验收脚本，再实现代码：

- 后端：`python -m pytest -q`
- 前端：`cd frontend && npm.cmd run test && npm.cmd run build`
- 部署配置：使用专门的配置测试、启动脚本检查或 Docker Compose 配置校验。
- 浏览器：上线前验证核心页面桌面端和移动端无明显布局错误。

## 4. 阶段 A：Async Worker Readiness V4

### 4.1 目标

让 RAG 文档摄取从“具备 Celery 基础”走向“异步任务生产就绪”。

核心价值：

```text
RAG 文档上传、解析、清洗、切 chunk 和入库属于慢任务，不应该长期阻塞 HTTP 请求。
Celery 的价值是把慢任务从请求链路拆出去，上传接口快速返回 taskId，worker 在后台处理，前端和管理员后台查看状态。
```

### 4.2 建议范围

- 梳理当前 `RagIngestionTask`、Celery dispatch、eager/test mode、worker mode 的真实链路。
- 明确三种运行模式：
  - local/eager：本地和测试快速运行。
  - fallback：Redis/Celery 不可用时系统仍能给出可解释状态。
  - worker：真实 Redis broker + Celery worker 执行任务。
- 补齐 worker 状态摘要：
  - broker 配置是否存在。
  - worker mode 是否开启。
  - 最近任务派发状态。
  - 最近失败原因。
- 强化任务状态一致性：
  - pending。
  - running。
  - succeeded。
  - failed。
  - retryable。
  - retry_count。
  - started_at / finished_at / duration。
- 管理员后台展示异步任务健康信息，但不做复杂监控系统。
- 增加 `scripts/start-celery-worker.cmd` 或完善已有脚本说明，确保 Windows 本地可理解如何启动 worker。

### 4.3 不做内容

- 不做分布式 worker 集群。
- 不做 Flower / Prometheus / Grafana。
- 不做对象存储。
- 不重写 RAG 检索算法。
- 不强制把本地数据库切换到 PostgreSQL。

### 4.4 验收标准

- 测试能证明 eager/fallback 不依赖真实 Redis 也可运行。
- 文档能说明真实 Redis/Celery worker 如何启动。
- 管理员后台能看到 worker / ingestion 任务健康摘要。
- RAG 上传任务失败、重试、成功路径状态可解释。

## 5. 阶段 B：PostgreSQL Compatibility V4

### 5.1 目标

在不破坏 SQLite 本地开发体验的前提下，让项目具备 PostgreSQL 生产兼容能力。

PostgreSQL 的价值：

- 更接近真实生产环境。
- 更适合多人系统和并发读写。
- 事务、索引、JSONB、复杂查询能力更强。
- 后续如果接 pgvector，路线更自然。

### 5.2 引入代价

- 本地环境复杂：安装服务、建库、建用户、配置密码和端口。
- 测试复杂：SQLite 通过不代表 PostgreSQL 一定通过。
- 迁移要求更高：Alembic 脚本、字段默认值、JSON 类型、时间类型都需要更谨慎。
- 排错成本上升：Windows 上可能遇到服务、权限、编码、端口占用和连接串问题。
- 启动链路变长：后端服务依赖数据库服务可用。

### 5.3 推荐策略

```text
本地默认 SQLite
生产配置支持 PostgreSQL
测试覆盖 DATABASE_URL 识别、URL 脱敏、engine 配置、Alembic 路径
可选使用 Docker PostgreSQL 做真实连接验证
部署阶段再正式切 PostgreSQL
```

### 5.4 建议范围

- 审计 SQLAlchemy 模型中 SQLite/PostgreSQL 兼容风险。
- 审计 Alembic 迁移脚本是否存在 SQLite-only 假设。
- 增加 PostgreSQL URL 配置示例。
- 增加生产环境 `.env.production.example` 说明。
- 可选增加 Docker Compose profile：启用 PostgreSQL 服务。
- 写一份 PostgreSQL 本地安装或 Docker 启动说明。

### 5.5 不做内容

- 不把 SQLite 删除。
- 不要求每个测试都跑 PostgreSQL。
- 不做真实数据迁移服务。
- 不做 pgvector。
- 不做复杂数据库性能优化。

## 6. 阶段 C：Deployment Integration V4

### 6.1 目标

把系统从“本地开发可运行”推进到“可部署演示”。

目标架构：

```text
Browser
-> Nginx
-> Vue3 static assets
-> FastAPI
-> PostgreSQL
-> Redis
-> Celery worker
```

### 6.2 建议范围

- 校准 Dockerfile、docker-compose、Nginx 配置。
- 确认前端构建产物如何被 Nginx 托管。
- 确认 `/api/*` 如何反向代理到 FastAPI。
- 确认 FastAPI 如何连接 PostgreSQL、Redis。
- 确认 Celery worker 使用同一份代码和环境变量。
- 补部署前检查脚本或清单：
  - 必填环境变量。
  - SECRET_KEY。
  - API key 不提交。
  - CORS。
  - 数据库迁移。
  - Redis broker。
  - 日志目录。
  - 端口映射。
- 输出 VPS / 域名 / Cloudflare / HTTPS 操作手册。

### 6.3 不做内容

- 不购买域名或 VPS，除非用户明确要求并确认预算。
- 不在文档中写入真实密钥。
- 不做 Kubernetes。
- 不做复杂 CI/CD。

### 6.4 验收标准

- Docker Compose 配置可以被校验。
- 文档能指导从空服务器部署到可访问页面。
- 上线前检查清单清楚。
- 关键故障有排查路径：
  - 后端启动失败。
  - 数据库连接失败。
  - Redis 连接失败。
  - worker 不消费任务。
  - Nginx 代理失败。
  - HTTPS 证书问题。

## 7. 阶段 D：Project Explanation & Resume Pack V1

### 7.1 目标

把项目从“功能很多”整理成“面试官能听懂、简历能表达、自己能讲清”的项目材料。

### 7.2 交付物

- 项目总讲解文档：
  - 业务背景。
  - 用户流程。
  - 系统架构。
  - 核心接口。
  - 三类 RAG 协作。
  - Agent / LangGraph 编排。
  - 训练闭环。
  - 管理员后台和可观测性。
  - 生产化设计。
  - 技术取舍。
- 面试深挖问答库：
  - 为什么拆三个 RAG？
  - 为什么用 Agent / LangGraph？
  - 为什么需要 RAG 日志和 Agent 日志？
  - 为什么 Celery 适合 RAG 文档入库？
  - 为什么本地 SQLite、生产 PostgreSQL？
  - Redis 在项目中承担什么职责？
  - 如果模型输出不稳定怎么办？
  - 如果 RAG 召回质量差怎么排查？
- 简历材料：
  - 一段项目简介。
  - 3 到 5 条项目职责。
  - 3 到 5 条技术亮点。
  - 可量化或可验证表达。
  - 针对 Python 后端岗版本。
  - 针对 AI 应用开发岗版本。

### 7.3 不做内容

- 不伪造工作经历。
- 不夸大为大规模线上生产系统。
- 不把没有真实落地的能力写成已上线能力。
- 不用听起来高级但自己讲不清的术语堆砌简历。

## 8. 推荐执行顺序

```text
1. 写 active plan：把本 spec 拆成可执行任务池。
2. 执行阶段 A：Async Worker Readiness V4。
3. 阶段 A 完成后运行后端、前端和必要浏览器验证。
4. 执行阶段 B：PostgreSQL Compatibility V4。
5. 阶段 B 完成后验证 SQLite 默认路径不受影响，并补 PostgreSQL 配置文档。
6. 执行阶段 C：Deployment Integration V4。
7. 阶段 C 完成后做本地 Docker Compose 或部署配置验证。
8. 执行阶段 D：Project Explanation & Resume Pack V1。
9. 更新 `docs/roadmap/current-state.md`、`docs/specs/README.md`、`docs/plans/README.md`。
10. 把完成的 spec / plan 从 active 移到 completed。
```

## 9. 追求目标模式注意事项

由于本 spec 覆盖多个阶段，追求目标模式执行时必须遵守：

- 先写 implementation plan，再改代码。
- 不要一次性改完所有模块。
- 每完成一个阶段都要运行测试并更新进度。
- 如果发现上一阶段未提交改动，不要回滚，先识别并继续工作。
- 不要重复执行已完成的 V3.2/V3.3。
- 不要为了消耗额度而无边界加功能。
- 每一轮开发都要输出：
  - 改了哪些文件。
  - 为什么这么改。
  - 怎么验证。
  - 面试时怎么讲。

## 10. 本阶段完成定义

本阶段完成不等于功能无限完善，而是达到以下状态：

- RAG 异步任务链路具备生产解释力。
- PostgreSQL 生产兼容路径清楚。
- Docker/Nginx/VPS/HTTPS 上线手册和配置能支撑一次真实部署。
- 项目可以被完整讲解。
- 简历材料可以直接进入投递前润色。
- 当前开发路线文档不再混乱，active/completed/archive 状态清楚。
