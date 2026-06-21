# 部署总入口

本文是部署文档短入口。详细部署材料位于 [docs/deployment/](deployment/)。

## 部署形态

当前公网演示环境使用：

```text
Nginx -> FastAPI app -> PostgreSQL
                  -> Redis
                  -> Celery worker
```

Nginx 负责：

- 服务 Vue3 构建产物 `/vue/`
- 代理 `/api/`
- 代理 `/docs`
- 代理 `/openapi.json`

## 本地开发

后端：

```powershell
.\start-backend.cmd
```

前端：

```powershell
.\start-vue-frontend.cmd
```

测试：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

## VPS 部署

推荐阅读：

1. [VPS 部署 runbook](deployment/vps-deploy-v1.md)
2. [部署故障排查](deployment/troubleshooting.md)
3. [备份与回滚](deployment/backup-and-rollback.md)
4. [Nginx / Cloudflare / HTTPS](deployment/nginx-cloudflare-https.md)

常规更新流程：

```bash
cd /home/ubuntu/ai-interview
git fetch --prune origin main
git pull --ff-only origin main
sudo docker run --rm -v "$PWD/frontend":/app -w /app node:20-alpine sh -c "npm ci && npm run build"
sudo docker compose --env-file .env.production up -d --build app worker nginx
sudo docker compose --env-file .env.production ps
curl -s http://127.0.0.1:8080/api/health
```

## 环境变量

- `.env.example`：本地开发样例，可以提交。
- `.env.production.example`：生产样例，只放占位符，可以提交。
- `.env`：本地真实配置，不提交。
- `.env.production`：服务器真实配置，不提交。

真实 API key、数据库密码、服务器密码和个人隐私资料不能写入公开仓库。

## 部署检查

```powershell
docker compose --env-file .env.production.example config --quiet
```

如果改动了 Docker Compose、Nginx、环境变量样例或启动脚本，需要至少跑一次配置检查。
