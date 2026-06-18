# Pre-Launch Deployment Runbook V4

## 目标架构

```text
Browser
-> Nginx
-> Vue3 static assets
-> FastAPI API
-> PostgreSQL
-> Redis
-> Celery worker
```

## 本地 Compose 验证

先确认配置能被 Docker Compose 正确解析：

```powershell
docker compose config
```

再按基础设施到应用的顺序启动：

```powershell
docker compose up -d db redis
docker compose up -d app worker nginx
```

查看状态：

```powershell
docker compose ps
docker compose logs app
docker compose logs worker
docker compose logs nginx
```

## VPS 部署步骤

1. 准备服务器，建议先使用 Linux VPS。
2. 安装 Docker 和 Docker Compose。
3. 从 GitHub 拉取项目代码。
4. 基于 `.env.production.example` 创建 `.env.production` 或部署环境变量。
5. 替换 `DASHSCOPE_API_KEY`、`SECRET_KEY`、`POSTGRES_PASSWORD` 等占位值。
6. 启动 PostgreSQL 和 Redis。
7. 启动 FastAPI app 和 Celery worker。
8. 启动 Nginx。
9. 配置域名解析到 VPS。
10. 通过 Cloudflare 或服务器证书方案配置 HTTPS。

## 必查环境变量

- `DASHSCOPE_API_KEY`
- `SECRET_KEY`
- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_TASK_ALWAYS_EAGER=false`

## 故障排查

### 后端启动失败

检查 `.env.production`、`DATABASE_URL`、模型 API key 和容器日志。

### 数据库连接失败

检查 `db` 容器是否 healthy，`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 是否和 `DATABASE_URL` 一致。

### Worker 不消费任务

检查 Redis 是否 healthy，`CELERY_BROKER_URL` 是否指向 `redis://redis:6379/1`，再看 `docker compose logs worker`。

### Nginx 502

检查 `app` 容器是否启动，Nginx upstream 是否指向 `app:8000`。

### HTTPS 失败

检查 DNS 是否生效、Cloudflare SSL 模式是否正确、证书是否覆盖当前域名。

## 面试表达

我把部署链路拆成 Nginx、FastAPI、PostgreSQL、Redis 和 Celery worker。Nginx 负责入口和反向代理，FastAPI 负责业务 API，PostgreSQL 存储结构化数据，Redis 作为缓存/限流/token blacklist/Celery broker，Celery worker 处理 RAG 文档摄取等慢任务。
