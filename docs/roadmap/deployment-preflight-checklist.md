# AI 模拟面试系统上线前检查清单

## 1. 当前结论

当前项目适合继续做“上线前工程化补强”，还不建议立刻真实上线。

原因：

- 核心业务链路已经较完整。
- RAG、Agent、训练闭环已有工程化基础。
- 用户、历史、日志、测试已经具备。
- 但生产部署、HTTPS、数据库切换、备份、日志轮转、Nginx 配置还没实际落地。

## 2. 当前已具备

### 2.1 后端

- FastAPI 应用入口：`backend_python/main.py`
- 模块化路由：`backend_python/routes/`
- Pydantic schema：`backend_python/schemas.py`
- SQLAlchemy models：`backend_python/db_models.py`
- SQLite 本地数据库：`data/app.db`
- Alembic 迁移目录：`alembic/`
- 健康检查：`GET /api/health`

### 2.2 用户和数据

- 用户注册、登录、刷新、退出。
- JWT access token。
- 数据库 refresh token。
- 面试历史记录。
- 投递档案。
- RAG 文档管理。

### 2.3 AI 应用工程化

- Qwen / DashScope 模型调用。
- LLM 超时和重试。
- 简历解析。
- 三类 RAG。
- RAG 质量评估。
- RAG 命中解释。
- Agent 决策日志。
- Agent nodeTrace / toolCalls。
- 训练闭环 weakTags。

### 2.4 测试

- 后端 pytest 全量通过。
- 前端 `.mjs` 测试通过。
- 本地浏览器验证通过。

## 3. 上线前必须补齐

### 3.1 环境变量

检查：

- [ ] `.env.example` 包含所有必要变量。
- [ ] `.env` 不进入 Git。
- [ ] 生产 `SECRET_KEY` 使用强随机值。
- [ ] `DASHSCOPE_API_KEY` 不写入代码。
- [ ] `DATABASE_URL` 可切换生产数据库。
- [ ] CORS 允许域名有明确白名单。

关键变量：

```text
DASHSCOPE_API_KEY=
QWEN_MODEL=
QWEN_VISION_MODEL=
SECRET_KEY=
DATABASE_URL=
ACCESS_TOKEN_EXPIRE_MINUTES=
REFRESH_TOKEN_EXPIRE_DAYS=
LLM_TIMEOUT_SECONDS=
LLM_MAX_RETRIES=
```

### 3.2 数据库

检查：

- [ ] 本地 SQLite 表结构正常。
- [ ] Alembic `upgrade head` 可执行。
- [ ] 生产数据库连接串准备好。
- [ ] 用户表、refresh token 表、历史记录表、RAG 文档表都能迁移。
- [ ] 有备份策略。
- [ ] 有回滚策略。

上线建议：

```text
开发：SQLite
生产：PostgreSQL 或 MySQL
```

### 3.3 启动方式

开发命令：

```text
python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload
```

生产命令不应使用 `--reload`。

生产可选：

```text
python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000
```

后续再考虑：

```text
systemd
supervisor
Docker Compose
```

### 3.4 Nginx

上线前要准备：

- [ ] 反向代理到 `127.0.0.1:8000`。
- [ ] 配置 HTTPS。
- [ ] 配置上传大小限制。
- [ ] 配置 LLM 接口超时。
- [ ] 配置访问日志和错误日志。
- [ ] 配置静态文件缓存策略。

概念链路：

```text
用户 -> Nginx -> Uvicorn -> FastAPI
```

### 3.5 日志

已具备：

- 请求日志。
- 统一错误响应。
- RAG 命中日志。
- Agent 决策日志。
- LLM 调用工程化基础。

上线前补齐：

- [ ] 日志文件轮转。
- [ ] 慢接口日志。
- [ ] 未捕获异常日志。
- [ ] 日志中隐藏 token、密码、API key。
- [ ] 关键错误告警。

### 3.6 安全

检查：

- [ ] 密码只保存 hash。
- [ ] refresh token 只保存 hash。
- [ ] 退出登录能撤销 refresh token。
- [ ] `.env` 不提交。
- [ ] 上传文件类型有限制。
- [ ] 上传文件大小有限制。
- [ ] 接口错误不暴露敏感栈信息。
- [ ] CORS 不无脑允许所有域名。

后续可增强：

- Redis token 黑名单。
- 登录失败次数限制。
- IP 限流。
- 管理后台权限。

### 3.7 文件上传

当前：

- 支持 PDF / 图片简历解析。
- 暂不强调保存原始简历文件。

上线前要决定：

- [ ] 是否保存原始简历。
- [ ] 是否使用对象存储。
- [ ] 是否定期清理临时文件。
- [ ] 是否记录文件解析失败原因。

推荐：

```text
原始 PDF / 图片不要长期放服务器本地，后续使用 OSS / S3 类对象存储。
```

### 3.8 监控与健康检查

当前：

- 已有 `/api/health`。

上线前可补：

- [ ] 数据库连接健康检查。
- [ ] 模型 API 配置检查。
- [ ] 磁盘空间检查。
- [ ] 服务进程存活检查。
- [ ] Nginx 访问日志检查。

## 4. 当前明确不做

本阶段不做：

- 不购买云服务器。
- 不真实配置 Nginx。
- 不真实配置 HTTPS。
- 不启动 Docker Compose。
- 不迁移到 PostgreSQL / MySQL。
- 不做管理员后台。
- 不引入 LangGraph / LangChain。
- 不迁移 React / Vue / Next.js。

## 5. 真正上线推荐顺序

推荐顺序：

1. 本地全量测试通过。
2. 确认 `.env.example` 完整。
3. 确认 Alembic migration 可用。
4. 准备生产数据库。
5. 准备服务器 Python 环境。
6. 用 Uvicorn 跑通后端。
7. 用 Nginx 反向代理。
8. 配置域名和 HTTPS。
9. 配置日志轮转。
10. 配置备份。
11. 做一次完整真实用户流程验证。

## 6. 面试表达

可以这样讲：

> 我目前没有直接把项目部署到云服务器，而是先做了上线前工程化检查。项目已经具备 FastAPI 后端、SQLAlchemy 数据库、Alembic 迁移、用户认证、RAG 日志、Agent 日志和全量测试。真正上线时会采用 Nginx 作为公网入口，反向代理到 Uvicorn 运行的 FastAPI 服务，数据库从 SQLite 切换到 PostgreSQL 或 MySQL，并通过环境变量管理密钥和数据库连接。上线前还要补日志轮转、备份、HTTPS、CORS 白名单和上传文件限制。

如果面试官问“你离上线还差什么”，可以答：

> 主要差真实生产环境配置，包括云服务器、Nginx、HTTPS、生产数据库、备份、日志轮转和监控。目前代码侧已经在向上线前工程化靠拢，但我没有为了展示而仓促上线。
