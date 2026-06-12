# Docker + Nginx + VPS 上线 V1 设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统的下一阶段开发：把项目从“本地可运行、功能较完整”推进到“具备云服务器上线展示能力”。

本阶段不追求一次性达到大型互联网公司的完整生产运维标准，而是优先建立一条清晰、可复现、可讲解、可排错的上线链路：

```text
GitHub 仓库
-> VPS 拉取代码
-> Docker 固化运行环境
-> Docker Compose 编排应用、数据库、Redis/Celery
-> Alembic 初始化数据库表结构
-> Nginx 作为公网统一入口
-> 域名和 HTTPS 对外访问
-> 日志、备份、回滚、验收文档闭环
```

面试表达目标：

```text
这个项目不仅实现了 AI 模拟面试的业务功能，也补齐了上线前的工程化链路。我使用 Docker 固化运行环境，用 Compose 编排 FastAPI、数据库、Redis 和 Celery worker，用 Alembic 管理表结构迁移，用 Nginx 做统一入口和反向代理，并通过环境变量、健康检查、日志、备份和回滚文档保证部署过程可复现、可排错。
```

## 2. 当前项目状态

以 `docs/roadmap/current-state.md` 和当前代码为准，项目已经具备：

- FastAPI 后端。
- 原生 HTML / CSS / JavaScript 前端。
- SQLite 本地开发数据库。
- SQLAlchemy ORM。
- Alembic 迁移脚本。
- 用户系统与 JWT 双 token 认证。
- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档管理、metadata、hybrid search、rerank、质量评估、命中日志。
- Interview Orchestrator Agent、Agent Policy、决策日志。
- LangGraph 旁路实验接口与 checkpoint 摘要。
- Redis / Celery 基础设施和异步 RAG evaluation task。
- 管理员后台 MVP。
- 后端 pytest 和前端 `.mjs` 测试。
- GitHub 仓库：`https://github.com/davidluulc/ai-interview.git`。

尚未完成：

- Dockerfile。
- `.dockerignore`。
- docker-compose 部署编排。
- Nginx 反向代理配置。
- VPS 部署手册。
- 域名 / HTTPS 配置手册。
- 部署环境变量模板。
- 数据备份和恢复说明。
- 部署故障排查手册。
- 上线验收清单。

## 3. 推荐上线策略

### 3.1 服务器与域名选择

本阶段推荐：

```text
Cloudflare 管理域名 DNS / SSL
+ 香港或海外 VPS
```

原因：

- 避免中国大陆服务器备案流程阻塞学习和项目展示。
- 香港或海外 VPS 对个人项目上线更轻量。
- Cloudflare 适合做 DNS、HTTPS、基础 CDN 和访问保护。
- 项目目标是实习展示和学习，不是马上做商业化运营。

暂不推荐：

```text
中国大陆 ECS + ICP 备案
```

原因：

- 备案流程会拉长周期。
- 对当前“尽快做出可展示上线版本”的目标收益不高。
- 后续如果项目面向国内用户长期运营，再迁移到大陆云厂商更合适。

### 3.2 本地数据库与上线数据库

本地开发继续默认：

```text
SQLite
```

上线 V1 推荐使用：

```text
PostgreSQL 容器
```

原因：

- SQLite 适合本地学习和单机开发，但不适合多人访问、备份恢复和长期生产运行。
- PostgreSQL 更接近真实后端生产环境。
- 后续可以自然扩展到 pgvector 或独立向量数据库。
- 当前项目已经通过 `DATABASE_URL` 预留数据库切换能力。

阶段边界：

- 不要求用户本机安装 PostgreSQL。
- Docker Compose 中提供 PostgreSQL 服务。
- 本地开发不删除 SQLite 路线。
- 如果 Docker 不可用，仍可用 SQLite 跑完整测试。

## 4. 目标架构

### 4.1 请求链路

```text
用户浏览器
-> 域名
-> Cloudflare DNS / SSL
-> VPS 80/443 端口
-> Nginx
-> FastAPI / Uvicorn
-> PostgreSQL
-> Redis
-> Celery worker
-> DashScope / Qwen API
```

### 4.2 服务职责

| 组件 | 责任 |
| --- | --- |
| GitHub | 保存代码、版本历史、部署时拉取代码 |
| VPS | 运行 Linux、Docker、Nginx、应用容器 |
| Dockerfile | 固化 FastAPI 应用运行环境 |
| docker-compose.yml | 编排 app、db、redis、worker、nginx |
| FastAPI | 提供页面、API、认证、RAG、Agent、报告等业务能力 |
| PostgreSQL | 存储用户、投递档案、面试记录、RAG 文档、日志等结构化数据 |
| Redis | Celery broker / result backend，后续可扩展缓存、限流、token 黑名单 |
| Celery worker | 执行异步任务，例如 RAG evaluation |
| Nginx | 统一公网入口、反向代理、静态资源和 API 转发、后续 HTTPS 终止 |
| Cloudflare | DNS、HTTPS、基础安全防护 |

### 4.3 为什么需要 Nginx

FastAPI/Uvicorn 可以直接启动服务，但不建议直接裸露在公网。

Nginx 的作用：

- 接收公网请求。
- 把 `/api/` 转发给 FastAPI。
- 把页面请求转发给 FastAPI 静态页面或静态目录。
- 统一处理 80/443 端口。
- 后续配置 HTTPS 证书。
- 记录 access log 和 error log。
- 隔离公网入口和内部应用端口。

面试表达：

```text
我把 Nginx 放在应用前面作为反向代理。用户访问域名时，请求先到 Nginx，Nginx 根据路径把请求转发给后端容器。这样后端服务不用直接暴露公网端口，也便于后续统一配置 HTTPS、日志、超时和静态资源。
```

## 5. 本阶段做什么

### 5.1 部署配置基线

新增或整理：

- `.env.production.example`
- `.dockerignore`
- `Dockerfile`
- `docker-compose.yml`
- `deploy/nginx/ai-interview.conf`
- `deploy/README.md`

要求：

- 不写真实 API Key。
- 不写真实数据库密码。
- 不提交 `.env`。
- 本地 SQLite 配置不被破坏。
- 生产配置示例清楚展示数据库、Redis、Celery、JWT、模型配置。

### 5.2 Dockerfile

目标：

```text
让 FastAPI 应用可以在容器中启动。
```

要求：

- 使用 Python 官方镜像。
- 安装 `requirements.txt`。
- 设置工作目录。
- 复制项目文件。
- 暴露 `8000`。
- 默认启动 `backend_python.main:app`。
- 避免复制 `.env`、数据库、缓存、IDE 配置。

### 5.3 Docker Compose

目标：

```text
一条命令启动 app、PostgreSQL、Redis、Celery worker、Nginx。
```

服务建议：

- `app`
- `db`
- `redis`
- `worker`
- `nginx`

阶段边界：

- `worker` 可先只运行已有 Celery worker。
- 不做复杂 task queue 监控面板。
- 不引入 Flower，避免范围膨胀。
- 不引入 Kubernetes。

### 5.4 数据库迁移

目标：

```text
上线环境可通过 Alembic 初始化和升级数据库表结构。
```

要求：

- 文档说明 `alembic upgrade head`。
- 说明如何检查当前迁移版本。
- 说明迁移失败如何查看日志。
- 如果 compose 启动不自动迁移，也必须提供手动命令。
- 不使用 `Base.metadata.create_all()` 作为上线主流程。

### 5.5 Nginx 反向代理

目标：

```text
提供一份可放到 VPS 上使用的 Nginx 配置。
```

要求：

- `/` 能访问前端页面。
- `/api/` 能转发到 FastAPI。
- `/docs` 能访问 FastAPI Swagger。
- 保留 WebSocket/SSE 升级头的可扩展配置。
- 设置基础 proxy headers。
- 设置合理超时。
- 日志路径清晰。

### 5.6 VPS 部署文档

新增文档建议：

```text
docs/deployment/README.md
docs/deployment/vps-deploy-v1.md
docs/deployment/nginx-cloudflare-https.md
docs/deployment/troubleshooting.md
docs/deployment/backup-and-rollback.md
```

文档必须覆盖：

- 购买 VPS 后最小初始化。
- 安装 Git、Docker、Docker Compose。
- 克隆 GitHub 仓库。
- 准备 `.env.production`。
- 启动 compose。
- 执行 Alembic 迁移。
- 配置 Nginx。
- 配置 Cloudflare DNS。
- 配置 HTTPS 的两种路线：
  - Cloudflare 代理模式。
  - Let's Encrypt / Certbot。
- 查看日志。
- 常见错误排查。
- 数据库备份。
- 代码回滚。

### 5.7 验收与学习文档

新增学习文档建议：

```text
docs/learning/12-Docker-Nginx-VPS上线链路怎么理解.md
```

内容要求：

- Docker 是什么。
- Compose 是什么。
- Nginx 反向代理是什么。
- VPS 和 Uvicorn 的区别。
- Cloudflare、域名、DNS、HTTPS 分别是什么。
- SQLite、本地 PostgreSQL、云上 PostgreSQL 的区别。
- 为什么 `.env` 不能提交 GitHub。
- 面试时如何讲上线链路。

## 6. 本阶段不做什么

明确不做：

- 不做 Vue3 前端重构。
- 不重构 RAG。
- 不重构 Agent。
- 不把 LangGraph 替换为主流程。
- 不做 Kubernetes。
- 不做复杂 CI/CD。
- 不做 Prometheus / Grafana 监控。
- 不做对象存储 OSS/S3 正式接入。
- 不做短信、邮箱验证码、支付。
- 不做大陆服务器备案流程。
- 不在文档中写真实 API Key、真实密码、真实服务器 IP。

## 7. 测试策略

### 7.1 本地代码测试

必须运行：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

### 7.2 Docker 测试

如果本机 Docker 可用，执行：

```powershell
docker build -t ai-interview-app:local .
docker compose up -d --build
docker compose ps
docker compose logs app --tail=80
```

验证：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

如果 Docker 不可用，不能假装通过，必须在最终说明中记录阻塞原因。

### 7.3 配置测试

建议新增测试：

- `.env.production.example` 不包含真实 key。
- `Dockerfile` 存在并包含应用启动命令。
- `docker-compose.yml` 包含 app、db、redis、worker、nginx。
- Nginx 配置包含 `/api/` 代理规则。
- `.dockerignore` 排除 `.env`、`data/*.db`、缓存目录。

## 8. 验收标准

本阶段完成时必须满足：

- GitHub 仓库已有最新代码。
- 本地测试全部通过。
- 前端 `.mjs` 测试全部通过。
- Dockerfile 可构建。
- Compose 配置结构完整。
- `.env.production.example` 清楚且不泄密。
- Nginx 配置路径清晰。
- 部署文档能指导用户从空 VPS 走到可访问页面。
- 故障排查文档覆盖 502、数据库连接失败、API Key 缺失、迁移失败、端口占用。
- 备份与回滚文档说明数据库和代码两个层面的恢复。
- `docs/roadmap/current-state.md` 更新当前阶段状态。
- `docs/roadmap/project-progress.md` 记录实施结果。

## 9. 风险与控制

### 9.1 服务器环境差异

风险：

```text
本地 Windows、Docker Desktop、Linux VPS 的路径、网络、端口、权限不同。
```

控制：

- 文档区分本地验证和 VPS 部署。
- 容器内统一使用 Linux 路径。
- 不依赖 Windows 本机绝对路径。

### 9.2 密钥泄露

风险：

```text
把 .env、API Key、数据库密码推到 GitHub。
```

控制：

- `.gitignore` 和 `.dockerignore` 排除敏感文件。
- spec 和文档只写占位符。
- 交付前执行敏感词扫描。

### 9.3 数据库迁移失败

风险：

```text
SQLite 可运行，但 PostgreSQL 下迁移或字段类型暴露问题。
```

控制：

- 使用 Alembic 作为上线迁移主流程。
- Compose 使用 PostgreSQL 验证。
- 失败时修迁移脚本，不绕过。

### 9.4 范围膨胀

风险：

```text
上线过程中顺手加入 Vue3、CI/CD、监控、对象存储，导致阶段失控。
```

控制：

- 本阶段只做上线展示 V1。
- 所有额外需求进入后续 backlog。

## 10. 后续方向

完成本阶段后，后续可以选择：

1. 真正购买 VPS 和域名，按文档实机上线。
2. 做 Vue3 前端重构。
3. 做 LangGraph checkpoint 持久化和 human-in-the-loop。
4. 做对象存储和简历文件生产级上传。
5. 做 CI/CD 自动部署。
6. 做项目讲解、简历包装和面试训练。

当前推荐完成顺序：

```text
Docker + Nginx + VPS 上线 V1
-> 实机上线一次
-> 项目讲解与简历表达
-> 再评估 Vue3 或 LangGraph 深化
```
