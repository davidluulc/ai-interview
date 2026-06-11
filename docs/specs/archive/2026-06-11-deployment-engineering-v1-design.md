# 部署工程化 V1 Spec

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段开发：部署工程化 V1。

当前项目已经完成较多后端、RAG、Agent、训练闭环、管理员后台和前端产品化能力。下一阶段不再继续重复 RAG / Agent 的底层能力建设，而是把项目从“本地开发可运行”推进到“具备云服务器上线条件”的工程化状态。

本阶段目标不是追求一次性达到大型互联网生产系统标准，而是建立一条能讲清楚、能测试、能部署、能排错的上线链路：

```text
环境配置清晰
-> 容器能启动
-> 数据库能迁移
-> 静态页面能访问
-> API 能被反向代理
-> 日志能定位问题
-> 部署步骤可复现
```

## 2. 当前项目状态

当前真实状态以 `docs/roadmap/current-state.md` 为准。

已经阶段性完成：

- FastAPI 后端应用。
- 原生 HTML / CSS / JavaScript 前端。
- SQLite 本地开发数据库。
- SQLAlchemy ORM。
- Alembic 迁移脚本。
- `.env.example`。
- PostgreSQL 连接示例。
- 本地启动脚本。
- 请求日志、统一错误响应和健康检查。
- 用户认证、RAG、Agent、训练任务和管理员后台。
- 前端产品化 V2 已完成阶段性收口。

仍未落地：

- Dockerfile。
- docker-compose.yml。
- Nginx 反向代理配置。
- 生产数据库容器或真实数据库切换验证。
- 生产环境变量分层。
- 日志目录规范与日志轮转说明。
- 部署启动、迁移、回滚和排错文档。
- 云服务器上线验收清单。

## 3. 总目标

本阶段完成后，项目应具备以下能力：

```text
开发者可以在一台新机器或云服务器上，根据文档复制 .env，启动容器，执行数据库迁移，通过 Nginx 访问前端页面和后端 API，并能通过日志定位常见错误。
```

面试表达目标：

```text
我不仅做了 AI 应用的业务功能，也补齐了上线前的工程化链路。项目使用 Docker 固化运行环境，通过 compose 编排应用和数据库，通过 Alembic 管理表结构迁移，通过 Nginx 做统一入口和反向代理，并把环境变量、日志、健康检查、部署验收和回滚步骤文档化。
```

## 4. 非目标

本阶段明确不做：

- 不重构 RAG 检索链路。
- 不重构 Agent Orchestrator。
- 不引入 LangGraph / LangChain。
- 不引入 React / Vue / Next.js。
- 不做复杂 Kubernetes。
- 不做 CI/CD 平台集成。
- 不做 Redis token 黑名单和任务队列。
- 不做对象存储正式接入。
- 不做短信、邮箱验证码、支付等商业化功能。
- 不真实购买或操作云服务器，除非用户后续明确要求。
- 不把 SQLite 彻底删除；本地开发仍可继续使用 SQLite。

如果实现过程中遇到以上需求，只记录为后续阶段，不在本阶段强行落地。

## 5. 设计原则

### 5.1 本地开发和部署配置分离

本地开发继续允许：

```text
DATABASE_URL=sqlite:///data/app.db
```

部署环境优先使用：

```text
DATABASE_URL=postgresql+psycopg://ai_interview:password@db:5432/ai_interview
```

关键点：

- `.env.example` 只保存示例，不保存真实密钥。
- 新增部署示例文件时使用占位符。
- 不把用户真实 API Key 写入仓库。

### 5.2 容器负责环境一致性

Dockerfile 负责：

- 固定 Python 运行环境。
- 安装 requirements。
- 复制项目文件。
- 暴露 FastAPI 服务端口。
- 使用 uvicorn 启动应用。

compose 负责：

- 启动后端应用。
- 启动 PostgreSQL 数据库。
- 挂载数据卷。
- 注入环境变量。
- 暴露本机端口用于测试。

### 5.3 数据库迁移必须可重复执行

Alembic 负责：

- 初始化新数据库表结构。
- 让本地和部署环境表结构一致。
- 为后续表结构变更保留规范流程。

本阶段要求新增脚本或文档说明：

```text
容器启动前或启动后如何执行 alembic upgrade head
迁移失败时如何查看日志
如何确认当前数据库版本
```

### 5.4 Nginx 作为统一公网入口

Nginx 负责：

- 接收公网 HTTP 请求。
- 转发 `/api/` 到 FastAPI。
- 转发前端静态页面请求到 FastAPI 静态服务或静态目录。
- 配置基础超时。
- 保留后续 HTTPS 配置位置。

第一版只提供可运行配置，不强制申请 HTTPS 证书。

### 5.5 日志优先解决排错

本阶段日志目标：

- 明确容器日志怎么看。
- 明确应用日志目录。
- 明确 Nginx access/error log 位置。
- 明确常见问题排查路径。

暂不做复杂监控告警。

## 6. 阶段拆分

### 阶段 1：部署配置基线

目标：

```text
让环境变量、启动命令、健康检查和部署边界清晰。
```

计划内容：

- 整理 `.env.example`。
- 新增 `.env.production.example`。
- 确认 `backend_python/config.py` 能读取生产配置。
- 确认 `/health` 或已有健康检查接口可用于部署验收。
- 新增部署学习文档：环境变量、uvicorn、生产配置的关系。

验收标准：

- 不泄露真实 API Key。
- 本地 SQLite 配置仍可使用。
- 生产数据库 URL 示例清晰。
- pytest 全量通过。

### 阶段 2：Dockerfile

目标：

```text
让后端应用可以在容器内启动。
```

计划内容：

- 新增 `Dockerfile`。
- 使用 Python 官方基础镜像。
- 安装 `requirements.txt`。
- 复制项目文件。
- 设置工作目录。
- 暴露 `8000`。
- 使用 uvicorn 启动 `backend_python.main:app`。
- 新增 `.dockerignore`，避免复制缓存、数据库、日志和 IDE 文件。

验收标准：

- `docker build` 成功。
- 容器启动后可以访问健康检查。
- 容器日志能看到启动信息。

### 阶段 3：docker-compose 本地部署编排

目标：

```text
用 compose 一次性启动 app 和 PostgreSQL。
```

计划内容：

- 新增 `docker-compose.yml`。
- 新增 `db` 服务，使用 PostgreSQL。
- 新增 `app` 服务，依赖 `db`。
- 配置数据库数据卷。
- 配置环境变量读取。
- 保留模型 API Key 的注入方式。
- 文档说明首次启动和重复启动流程。

验收标准：

- `docker compose up -d --build` 能启动服务。
- `docker compose ps` 能看到 app 和 db。
- app 可以连接 PostgreSQL。
- 本机可访问 `http://127.0.0.1:8000/`。

### 阶段 4：Alembic 迁移和数据库验收

目标：

```text
让新数据库可以通过迁移脚本生成完整表结构。
```

计划内容：

- 新增或整理迁移执行脚本。
- 文档化 `alembic upgrade head`。
- 验证 PostgreSQL 环境下迁移可执行。
- 增加部署前数据库检查说明。

验收标准：

- 新数据库执行迁移成功。
- 用户表、RAG 表、Agent 日志表、训练任务相关表可用。
- 后端测试仍通过。

### 阶段 5：Nginx 反向代理配置

目标：

```text
让 Nginx 成为统一入口，为真实云服务器上线做准备。
```

计划内容：

- 新增 `deploy/nginx/ai-interview.conf`。
- 配置 `/` 访问前端页面。
- 配置 `/api/` 转发到后端。
- 配置合理的 proxy headers。
- 配置基础超时。
- 文档解释正向代理、反向代理和本项目 Nginx 的作用。

验收标准：

- 配置文件语法清晰。
- 路由规则不和 FastAPI 现有路径冲突。
- 文档能讲清楚公网请求如何进入后端。

### 阶段 6：日志、备份和排错手册

目标：

```text
让部署后出现问题时有明确排查路径。
```

计划内容：

- 新增 `docs/deployment/` 目录。
- 新增部署运行手册。
- 新增常见错误排查：
  - 容器启动失败。
  - 数据库连接失败。
  - Alembic 迁移失败。
  - Nginx 502。
  - API Key 未配置。
  - 前端能打开但 API 调用失败。
- 新增数据库备份和恢复基础命令说明。
- 新增日志查看命令说明。

验收标准：

- 用户能按文档完成本地 compose 部署。
- 用户能按文档定位常见错误。
- 不需要阅读源码也能理解部署链路。

### 阶段 7：部署验收与学习文档

目标：

```text
形成可复盘、可写进简历、可面试讲解的部署工程化闭环。
```

计划内容：

- 更新 `docs/roadmap/project-progress.md`。
- 新增学习文档：`docs/learning/07-Docker-Nginx-数据库如何串起后端项目.md`。
- 新增部署验收清单。
- 运行后端 pytest。
- 运行前端 `.mjs` 测试。
- 如果本地 Docker 可用，执行 compose 验证。
- 如果 Docker 不可用，记录阻塞原因和替代验证。

验收标准：

- 文档、配置、测试结果都有记录。
- 明确哪些能力已落地，哪些只是后续预留。
- 能讲清楚部署链路。

## 7. 文件规划

预期新增：

```text
Dockerfile
.dockerignore
docker-compose.yml
.env.production.example
deploy/nginx/ai-interview.conf
docs/deployment/README.md
docs/deployment/local-compose-deploy.md
docs/deployment/nginx-reverse-proxy.md
docs/deployment/troubleshooting.md
docs/learning/07-Docker-Nginx-数据库如何串起后端项目.md
```

预期修改：

```text
.env.example
backend_python/config.py
docs/roadmap/current-state.md
docs/roadmap/project-progress.md
docs/specs/README.md
docs/plans/README.md
```

可能新增测试：

```text
tests/test_deployment_config.py
tests/test_healthcheck.py
```

是否需要修改 `backend_python/main.py` 取决于当前健康检查和静态文件挂载是否已经满足部署验收。

## 8. 测试策略

优先级从高到低：

1. 配置读取测试。
2. 健康检查测试。
3. 全量后端 pytest。
4. 全量前端 `.mjs` 测试。
5. Docker build。
6. docker compose 启动。
7. Nginx 配置语法和路径检查。

基础验证命令：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

如果 Docker 可用，再执行：

```powershell
docker build -t ai-interview-app:local .
docker compose up -d --build
docker compose ps
docker compose logs app --tail=80
```

如果 Docker 不可用，不能假装通过；必须在进度文档中记录真实阻塞。

## 9. 风险与控制

### 9.1 Windows 本地环境差异

风险：

```text
Windows 上 Docker Desktop、路径挂载、换行符和端口占用可能导致部署验证不稳定。
```

控制：

- 文档中区分 Windows 本地验证和 Linux 云服务器部署。
- 使用容器内路径，避免依赖本机绝对路径。
- 端口冲突时记录替代端口。

### 9.2 SQLite 到 PostgreSQL 差异

风险：

```text
SQLite 宽松，PostgreSQL 更严格，部分字段类型或默认值可能暴露问题。
```

控制：

- 保留 SQLite 本地开发。
- 用 PostgreSQL compose 做部署验证。
- 迁移失败必须修迁移或模型，不绕过。

### 9.3 密钥泄露

风险：

```text
真实模型 API Key 或 SECRET_KEY 被写入仓库。
```

控制：

- 只提交 `.env.example` 和 `.env.production.example`。
- `.env` 保持 gitignore。
- 文档反复强调真实密钥只存在服务器环境。

### 9.4 过早生产化

风险：

```text
一次性引入 Redis、Celery、对象存储、监控告警会让项目复杂度失控。
```

控制：

- V1 只做容器、数据库、Nginx、日志和文档。
- Redis、Celery、对象存储放到后续 V2。

## 10. 和后续 LangGraph 的关系

本阶段不引入 LangGraph。

原因：

```text
LangGraph 解决的是 Agent 工作流编排和状态持久化问题；部署工程化解决的是项目如何上线运行的问题。两者都重要，但不应该混在同一轮改动里。
```

推荐顺序：

```text
部署工程化 V1
-> 云服务器真实上线
-> LangGraph POC
-> 最终项目讲解和简历表达
```

## 11. 面试表达目标

完成本阶段后，可以这样讲：

```text
这个项目除了 AI 面试业务本身，我还做了上线前工程化。后端用 FastAPI，数据库用 SQLAlchemy 和 Alembic 管理迁移。本地开发可以用 SQLite，部署环境通过 DATABASE_URL 切到 PostgreSQL。Dockerfile 固化 Python 运行环境，docker-compose 编排 app 和 db，Nginx 作为公网统一入口，把 /api 请求反向代理到 FastAPI。部署文档里还整理了环境变量、数据库迁移、日志查看、备份恢复和常见故障排查，所以项目不是只能在我电脑上跑，而是具备迁移到云服务器的条件。
```

如果面试官追问 Nginx：

```text
Nginx 在这里不是业务服务器，而是入口网关。用户访问公网域名时，请求先到 Nginx，Nginx 根据路径把请求转发给后端服务。这样后端不需要直接暴露在公网，也方便后续统一加 HTTPS、超时、日志和静态资源策略。
```

如果面试官追问 Docker：

```text
Docker 的作用是把 Python 版本、依赖包、启动命令这些运行环境固化下来，减少“我电脑能跑，服务器不能跑”的问题。compose 则负责把应用容器和数据库容器一起编排起来。
```

## 12. 当前执行建议

第一轮建议只实现：

```text
阶段 1：部署配置基线
阶段 2：Dockerfile
阶段 3：docker-compose 本地部署编排
```

原因：

```text
先让容器化链路跑起来，再做 Nginx、日志、备份和完整上线手册，质量会更稳。
```

如果第一轮验证顺利，再继续阶段 4 到阶段 7。
