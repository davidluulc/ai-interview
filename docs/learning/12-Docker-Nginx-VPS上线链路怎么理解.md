# Docker、Nginx、VPS 上线链路怎么理解

## 1. 先用一句话理解

```text
VPS 是一台公网 Linux 电脑，Docker 负责把项目运行环境打包，Compose 负责同时启动多个服务，Nginx 负责接公网请求并转发给后端，Cloudflare 负责域名解析和 HTTPS 入口。
```

## 2. VPS 和 Uvicorn 的区别

VPS 是服务器机器。

Uvicorn 是 Python ASGI 应用服务器，用来运行 FastAPI。

关系是：

```text
VPS 上运行 Docker
Docker 容器里运行 Uvicorn
Uvicorn 运行 FastAPI 应用
```

所以不能说“Uvicorn 是云服务器”。更准确的说法是：

```text
Uvicorn 是运行 FastAPI 的应用服务器进程。
```

## 3. Docker 是什么

Docker 解决的是“我的项目在你电脑上跑不起来”的问题。

它把运行环境写成镜像：

- Python 版本。
- 依赖包。
- 项目代码。
- 启动命令。

这样到 VPS 上不需要手工一点点配置 Python 环境。

## 4. Docker Compose 是什么

一个真实后端项目通常不只有一个进程：

- FastAPI app。
- PostgreSQL 数据库。
- Redis。
- Celery worker。
- Nginx。

Compose 用一个 `docker-compose.yml` 描述这些服务怎么启动、互相怎么连接、端口怎么暴露、数据卷怎么挂载。

## 5. Nginx 反向代理是什么

用户不直接访问 FastAPI 容器，而是访问 Nginx。

```text
用户浏览器 -> Nginx -> FastAPI
```

Nginx 替后端服务接收公网请求，所以叫反向代理。

它的价值：

- 统一入口。
- 配置 HTTPS。
- 转发 API。
- 记录访问日志。
- 隐藏内部服务端口。

## 6. Cloudflare、域名、DNS、HTTPS 分别是什么

域名是用户记得住的名字，例如：

```text
interview.example.com
```

DNS 是把域名解析到服务器 IP 的系统。

Cloudflare 可以管理 DNS，也可以给域名提供 HTTPS 入口和基础防护。

HTTPS 是加密访问协议，避免用户请求和响应在网络中明文传输。

## 7. SQLite 和 PostgreSQL 的区别

SQLite 是一个本地文件数据库，适合学习、本地开发和轻量 demo。

PostgreSQL 是独立数据库服务，更适合上线：

- 支持更强并发。
- 权限管理更完善。
- 备份恢复更规范。
- 更接近企业后端环境。

本项目保留：

```text
本地开发：SQLite
上线 V1：PostgreSQL 容器
```

## 8. 为什么 `.env` 不能提交 GitHub

`.env` 里通常有：

- API Key。
- 数据库密码。
- JWT SECRET。
- Redis 地址。

这些泄露后，别人可能盗刷模型额度、登录数据库或伪造 token。

正确做法：

- 提交 `.env.example` 和 `.env.production.example`。
- 真实 `.env` 只放本机或服务器。
- `.gitignore` 排除真实环境变量文件。

## 9. 为什么生产环境不自动建表

本地开发为了方便，可以让 FastAPI 启动时自动创建 SQLite 表。

但上线环境更推荐：

```text
AUTO_INIT_DB=false
alembic upgrade head
```

原因：

- Alembic 能记录数据库表结构版本。
- 团队协作时知道每次表结构变化来自哪次迁移。
- 避免应用启动时绕过迁移脚本直接建表，导致迁移版本和真实表结构不一致。

## 10. 面试时怎么讲

可以这样讲：

```text
我把项目上线链路拆成了四层。第一层是代码层，代码托管在 GitHub。第二层是运行环境层，用 Dockerfile 固化 Python 和依赖。第三层是服务编排层，用 Docker Compose 同时启动 FastAPI、PostgreSQL、Redis、Celery worker 和 Nginx。第四层是公网入口层，用户访问域名后请求先到 Cloudflare 和 Nginx，再由 Nginx 反向代理到 FastAPI。数据库表结构通过 Alembic 迁移，故障排查主要看 app、db、redis、nginx 的容器日志。
```

如果面试官追问“你为什么不直接用 Uvicorn 暴露公网”，可以回答：

```text
Uvicorn 更适合做应用服务器，不适合直接承担公网入口职责。Nginx 可以统一处理 80/443、HTTPS、反向代理、日志和超时配置，也能把内部 app 端口藏起来。
```
