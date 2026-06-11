# VPS 部署 V1 手册

## 1. 服务器选择

当前推荐：

```text
香港或海外 VPS + Ubuntu LTS
```

原因：

- 不需要大陆 ICP 备案。
- 适合个人项目展示。
- 部署链路更轻量。

## 2. 安装基础工具

在 VPS 上登录后执行：

```bash
sudo apt update
sudo apt install -y git ca-certificates curl gnupg
```

安装 Docker：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

验证：

```bash
docker --version
docker compose version
```

## 3. 拉取项目代码

```bash
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/davidluulc/ai-interview.git
cd ai-interview
```

如果仓库仍是 Private，需要先配置 GitHub 登录、SSH key 或使用有权限的 token。

## 4. 准备生产环境变量

```bash
cp .env.production.example .env.production
nano .env.production
```

必须替换：

```text
DASHSCOPE_API_KEY
SECRET_KEY
POSTGRES_PASSWORD
DATABASE_URL 中的数据库密码
```

注意：

- `POSTGRES_PASSWORD` 和 `DATABASE_URL` 中的密码要一致。
- `.env.production` 不要提交 Git。
- `SECRET_KEY` 应该是一段足够长的随机字符串。
- `AUTO_INIT_DB=false` 表示生产环境不让 FastAPI 自动建表，而是通过 Alembic 迁移管理表结构。

## 5. 启动服务

先检查 Compose 配置：

```bash
docker compose -p ai-interview --env-file .env.production config
```

启动。VPS/Linux 环境优先使用：

```bash
docker compose -p ai-interview --env-file .env.production up -d --build
```

如果是在 Windows 中文路径下做本地验证，`docker compose up --build` 可能触发 Docker Desktop / BuildKit 的路径兼容问题。可以先执行：

```bash
docker build -t ai-interview-app:local .
docker compose -p ai-interview --env-file .env.production up -d --no-build
```

这是本地验证兼容方案，不影响 VPS/Linux 使用 `up -d --build`。

查看服务：

```bash
docker compose -p ai-interview ps
```

查看日志：

```bash
docker compose -p ai-interview logs app --tail=100
docker compose -p ai-interview logs nginx --tail=100
docker compose -p ai-interview logs db --tail=100
```

## 6. 执行数据库迁移

上线环境建议使用 Alembic 管理表结构：

```bash
docker compose -p ai-interview --env-file .env.production exec app alembic upgrade head
```

检查当前版本：

```bash
docker compose -p ai-interview --env-file .env.production exec app alembic current
```

## 7. 验证访问

本地 compose 默认把 Nginx 暴露到宿主机 `8080`：

```text
http://服务器IP:8080/
http://服务器IP:8080/api/health
http://服务器IP:8080/docs
```

如果后续直接使用标准 HTTP 端口，可把 `docker-compose.yml` 中的：

```yaml
ports:
  - "8080:80"
```

改成：

```yaml
ports:
  - "80:80"
```

正式修改前要确认服务器安全组和防火墙放行了对应端口。

## 8. 更新代码

```bash
git pull
docker compose -p ai-interview --env-file .env.production up -d --build
docker compose -p ai-interview --env-file .env.production exec app alembic upgrade head
docker compose -p ai-interview ps
```

## 9. 面试表达

可以这样讲：

```text
我把项目部署链路拆成了应用镜像、服务编排、数据库迁移和反向代理四层。应用镜像由 Dockerfile 固化，docker compose 同时拉起 FastAPI、PostgreSQL、Redis、Celery worker 和 Nginx。数据库表结构通过 Alembic 迁移，公网请求先进入 Nginx，再转发到 FastAPI，这样部署过程可以复现，也方便排查日志和回滚。
```
