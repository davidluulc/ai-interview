# 部署故障排查手册

本文记录适合公开沉淀的工程排障经验。只保留能体现系统性定位、生产化意识和可迁移经验的问题，不记录纯粘贴、路径记错、平台操作习惯这类低价值操作问题。

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

## 2. Nginx 502：代理找不到可用后端

问题现象：

```text
浏览器或 curl 返回 502 Bad Gateway，Nginx 日志中出现 connect() failed 或 upstream 连接失败。
```

影响范围：

```text
前端静态页面可能能打开，但所有 /api/ 请求失败。
```

定位过程：

- `app` 容器没启动。
- FastAPI 启动失败。
- Nginx 配置里的 upstream 服务名写错。
- app 端口不是 8000。

```bash
docker compose -p ai-interview ps
docker compose -p ai-interview logs app --tail=100
docker compose -p ai-interview logs nginx --tail=100
```

根因：

```text
Nginx 只是代理层，502 通常说明它无法连接上游 app，不等于前端代码坏了。
```

修复方式：

```text
先恢复 app 容器和 FastAPI 启动，再检查 Nginx upstream 服务名和端口。
```

沉淀经验：

```text
502 优先看容器状态和 Nginx upstream；不要先从 Vue 页面或浏览器缓存开始猜。
```

## 3. Nginx 504：后端或模型请求超过代理等待时间

问题现象：

```text
面试生成或复盘接口等待很久后返回 504 Gateway Time-out。
```

影响范围：

```text
登录、档案、知识库等普通接口正常，只有慢模型请求或复盘生成失败。
```

定位过程：

```bash
docker compose -p ai-interview logs app --tail=120
docker compose -p ai-interview logs nginx --tail=120
```

根因：

```text
LLM 请求耗时超过 Nginx proxy_read_timeout，或者后端等待模型响应时间过长。
```

修复方式：

```text
区分模型慢请求和后端崩溃；必要时提高 Nginx 代理超时，优化模型选择，或给报告生成增加结构化 fallback。
```

沉淀经验：

```text
504 是“上游太慢或无响应”，不是简单的前端 bug。AI 应用上线时必须考虑慢模型、重试和代理超时。
```

## 4. PostgreSQL 生产迁移字段缺失

问题现象：

```text
本地 SQLite 正常，生产 PostgreSQL 登录、后台或业务接口报 column/relation does not exist。
```

影响范围：

```text
依赖新字段或新表的接口失败，例如用户角色、报告、训练或后台管理功能。
```

定位过程：

```bash
docker compose -p ai-interview exec app alembic current
docker compose -p ai-interview exec app alembic upgrade head
docker compose -p ai-interview logs app --tail=120
```

根因：

```text
代码版本已经访问新字段，但生产数据库迁移没有同步执行，或者旧迁移没有覆盖当前代码需要的字段。
```

修复方式：

```text
补齐 Alembic migration，生产环境执行 upgrade head；必要时为已有表补字段并记录迁移原因。
```

沉淀经验：

```text
生产数据库结构必须和代码版本同步。不要用 create_all 代替上线迁移，也不要只在本地 SQLite 验证。
```

## 5. 数据库连接失败

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

## 7. 模型额度耗尽与 embedding provider 切换

问题现象：

```text
RAG 入库、面试生成或后台诊断出现模型服务错误；向量模型额度耗尽后，新文档无法生成 embedding。
```

影响范围：

```text
聊天模型和 embedding 模型可能分别受影响。embedding 失败会影响 RAG 召回，聊天模型失败会影响问题生成和复盘。
```

定位过程：

```bash
docker compose -p ai-interview logs app --tail=120
grep -E 'EMBEDDING_PROVIDER|EMBEDDING_MODEL|DASHSCOPE|ZHIPU' .env.production
```

根因：

```text
DashScope embedding 额度耗尽后，旧 provider 无法继续生成向量；切换到智谱 embedding-3 后，新旧向量模型需要隔离或重新入库。
```

修复方式：

```text
显式配置 EMBEDDING_PROVIDER、EMBEDDING_MODEL 和 EMBEDDING_DIMENSIONS；验证新 provider 可用后，重新 seed 或重新摄取知识库。
```

沉淀经验：

```text
RAG 系统不能只看 chat model token。embedding provider、向量维度、模型名和已有 chunk 状态都要纳入生产配置。
```

## 8. VPS GitHub 拉取 TLS 超时

问题现象：

```text
git clone/fetch/pull 出现 SSL connection timeout、GnuTLS recv error 或 non-properly terminated。
```

影响范围：

```text
代码无法增量更新，影响服务器部署，但不代表仓库不存在或权限一定错误。
```

定位过程：

```bash
git remote -v
git ls-remote origin main
git fetch -v origin main
git status --short --branch
```

根因：

```text
国内 VPS 到 GitHub 网络不稳定，TLS 连接容易中断。
```

修复方式：

```text
优先多次 fetch 后 fast-forward；必要时使用镜像源或本地打包上传。遇到 non-fast-forward 先检查本地是否有未提交变更，不要强行 reset。
```

沉淀经验：

```text
部署更新失败时要区分网络问题、Git 历史分叉和本地脏工作区。生产服务器上避免随意改代码，减少无法 fast-forward 的风险。
```

## 9. Docker daemon 权限问题

问题现象：

```text
普通 ubuntu 用户执行 docker compose 报 permission denied while trying to connect to the Docker daemon socket。
```

影响范围：

```text
无法查看容器、构建镜像或启动服务。
```

定位过程：

```bash
docker ps
groups
ls -l /var/run/docker.sock
```

根因：

```text
当前用户不在 docker 组，无法访问 /var/run/docker.sock。
```

修复方式：

```text
临时使用 sudo docker compose；长期可把用户加入 docker 组并重新登录。
```

沉淀经验：

```text
部署脚本要明确是否需要 sudo。权限问题和 compose 配置错误要分开排查。
```

## 10. Vue 新旧入口混淆

问题现象：

```text
访问根路径看到旧 HTML 页面，访问 /vue/auth/login 才看到 Vue3 登录页。
```

影响范围：

```text
容易误以为前端没有更新，或公网部署仍在使用旧页面。
```

定位过程：

```bash
docker compose -p ai-interview exec nginx ls -lah /usr/share/nginx/html/vue
grep -nE 'location = /|location /vue/' deploy/nginx/ai-interview.conf
```

根因：

```text
仓库保留了旧版根目录 HTML 兼容入口，当前主前端构建产物挂载在 /vue/。
```

修复方式：

```text
Nginx 根路径重定向到 /vue/auth/login；README 明确 frontend/ 是当前主前端，旧 HTML 仅兼容保留。
```

沉淀经验：

```text
多前端迁移阶段要明确入口、构建产物和 Nginx location，否则容易把缓存、路由和部署路径混为一谈。
```

## 11. 端口占用

如果启动时报 `port is already allocated`，说明宿主机端口被占用。

检查：

```bash
sudo lsof -i :8080
```

解决：

- 停掉占用端口的服务。
- 或修改 `docker-compose.yml` 里的宿主机端口，例如 `8081:80`。

## 12. 页面能打开但 API 失败

检查浏览器 Network：

- API 是否请求到正确域名。
- 是否是 401 鉴权问题。
- 是否是 502 Nginx 问题。
- 是否是后端 500。

后端日志：

```bash
docker compose -p ai-interview logs app --tail=100
```

## 13. Windows 中文路径下 Compose build 异常

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
