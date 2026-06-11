# 部署故障排查手册

## 1. 总体排查顺序

遇到部署问题时按这个顺序看：

```text
容器是否启动
-> app 日志
-> db / redis 日志
-> Nginx 日志
-> 环境变量
-> 端口和防火墙
-> 数据库迁移
```

常用命令：

```bash
docker compose -p ai-interview ps
docker compose -p ai-interview logs app --tail=100
docker compose -p ai-interview logs nginx --tail=100
docker compose -p ai-interview logs db --tail=100
docker compose -p ai-interview logs redis --tail=100
```

## 2. Nginx 502

常见原因：

- `app` 容器没启动。
- FastAPI 启动失败。
- Nginx 配置里的 upstream 服务名写错。
- app 端口不是 8000。

检查：

```bash
docker compose -p ai-interview ps
docker compose -p ai-interview logs app --tail=100
docker compose -p ai-interview logs nginx --tail=100
```

## 3. 数据库连接失败

常见原因：

- `DATABASE_URL` 密码和 `POSTGRES_PASSWORD` 不一致。
- `DATABASE_URL` host 写成了 `localhost`，但在 compose 网络里应该写 `db`。
- db 容器还没启动完成。

正确示例：

```text
DATABASE_URL=postgresql+psycopg://ai_interview:replace_with_postgres_password@db:5432/ai_interview
```

检查：

```bash
docker compose -p ai-interview logs db --tail=100
docker compose -p ai-interview exec app alembic current
```

## 4. Redis 连接失败

常见原因：

- `REDIS_URL` 写成了 `localhost`。
- redis 容器未启动。

正确示例：

```text
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

检查：

```bash
docker compose -p ai-interview logs redis --tail=100
docker compose -p ai-interview logs worker --tail=100
```

## 5. API Key 缺失

现象：

- 面试题生成失败。
- embedding 或 rerank 调用失败。
- 日志出现 `Missing DASHSCOPE_API_KEY`。

检查：

```bash
docker compose -p ai-interview exec app printenv DASHSCOPE_API_KEY
```

如果为空，检查 `.env.production` 是否存在，以及启动时是否使用：

```bash
docker compose -p ai-interview --env-file .env.production up -d --build
```

## 6. Alembic 迁移失败

检查当前版本：

```bash
docker compose -p ai-interview exec app alembic current
```

执行迁移：

```bash
docker compose -p ai-interview exec app alembic upgrade head
```

如果失败：

- 先看报错信息。
- 确认数据库连接是否正常。
- 确认迁移脚本是否兼容 PostgreSQL。
- 不要直接跳过迁移，也不要用 `create_all()` 替代上线迁移。

如果迁移时报表已经存在，例如：

```text
relation "interview_records" already exists
```

优先检查生产环境是否错误设置了：

```text
AUTO_INIT_DB=true
```

上线环境应使用：

```text
AUTO_INIT_DB=false
```

否则 FastAPI 启动时可能先自动建表，随后 Alembic 迁移又尝试建同一张表。

## 7. 端口占用

如果启动时报 `port is already allocated`，说明宿主机端口被占用。

检查：

```bash
sudo lsof -i :8080
```

解决：

- 停掉占用端口的服务。
- 或修改 `docker-compose.yml` 里的宿主机端口，例如 `8081:80`。

## 8. 页面能打开但 API 失败

检查浏览器 Network：

- API 是否请求到正确域名。
- 是否是 401 鉴权问题。
- 是否是 502 Nginx 问题。
- 是否是后端 500。

后端日志：

```bash
docker compose -p ai-interview logs app --tail=100
```

## 9. Windows 中文路径下 Compose build 异常

现象可能类似：

```text
failed to dial gRPC
header key "x-docker-expose-session-sharedkey" contains value with non-printable ASCII characters
```

处理方式：

```bash
docker build -t ai-interview-app:local .
docker compose -p ai-interview --env-file .env.production up -d --no-build
```

原因：

```text
这是本地 Windows 路径和 Docker Desktop / BuildKit 的兼容问题，不代表 FastAPI 代码或 Dockerfile 一定有错。
```
