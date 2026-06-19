# 当前项目状态与下一阶段路线

更新时间：2026-06-19

本文件是当前项目路线的唯一可信入口。判断下一步开发方向时，以本文件为准；旧 spec、旧 plan 和历史学习材料只作为背景资料。

## 1. 当前结论

项目已经从本地开发推进到第一版公网部署：

- GitHub 仓库：`https://github.com/davidluulc/ai-interview`
- 公网入口：`http://124.221.230.218:8080/vue/auth/login`
- 健康检查：`http://124.221.230.218:8080/api/health`
- 部署形态：Docker Compose + Nginx + FastAPI + PostgreSQL + Redis + Celery worker
- 默认 Agent runtime：`langgraph_mainline`
- 兼容 fallback runtime：`classic`

当前不再处于“继续无限加功能”的阶段，而是进入“公网演示稳定化、安全收尾、项目讲解和简历包装”阶段。

## 2. Active 状态

当前 active spec：

```text
docs/specs/active/public-demo-stabilization-rag-seed-v1-design.md
```

当前 active plan：

```text
docs/plans/active/public-demo-stabilization-rag-seed-v1.md
```

当前阶段进入 Public Demo Stabilization + Production RAG Seed V1。优先修复公网演示闭环：生产 RAG seed、面试启动状态、结束并复盘保存历史、训练任务生成、面试官思考 loading、知识库用户页简化、档案归档和 RAG 空召回提示。

## 3. 已真实落地的核心能力

### 3.1 用户和权限

- 用户注册、登录、退出登录。
- access token 和 refresh token。
- token blacklist。
- 管理员角色字段和管理员权限依赖。
- 管理员后台只允许管理员访问。

### 3.2 投递档案和面试

- 用户创建投递档案，录入简历、岗位 JD、公司信息和岗位标签。
- 面试页基于当前档案进入模拟面试。
- 面试接口为 `POST /api/interview/next-question`。
- 支持 coach / interview 模式。
- 面试结束后生成复盘报告和 weakTags。

### 3.3 RAG 工程化

- 岗位知识库 RAG。
- 题库 RAG。
- 候选人画像 RAG。
- RAG 文档管理。
- RAG 文档生命周期：enabled / disabled / archived。
- 文档可见性：private / public。
- metadata 存储和过滤。
- 文档 hash、chunk hash 和去重统计。
- BM25、向量检索、hybrid search、rerank、query rewrite。
- RAG 命中日志、RAG debug、RAG 质量诊断和 evaluation case。
- RAG 文件上传和数据库持久化摄取任务。
- Celery worker 处理 RAG ingestion task。

### 3.4 Agent 和 LangGraph

- Agent State。
- Tool Calls。
- Agent Decision。
- fallback decision。
- normalize / guardrail。
- policy layer。
- nodeTrace。
- RAG tools 被 LangGraph `retrieve_context` 节点复用。
- `langgraph_mainline` 已作为默认主链路。
- `classic` 保留为 fallback/debug 链路。
- checkpoint summary、runtime audit、quality gate 和 fallback summary 已接入观测。

### 3.5 训练闭环

- 面试报告生成 weakTags。
- weakTags 生成训练任务。
- 训练任务支持开始、完成、归档。
- 专项练习面板展示练习题、答题要点、常见错误和一分钟表达模板。
- 提交练习后更新 masteryScore、attemptCount 和 lastPracticedAt。

### 3.6 Vue3 前端

- Vue3 + Vite + TypeScript 主前端。
- 登录 / 注册。
- 用户工作台。
- 档案页面。
- 面试页面。
- 知识库页面。
- 历史复盘和报告页面。
- 训练中心。
- 管理员后台。

### 3.7 管理员后台

- 平台概览。
- 账号管理。
- RAG 文档概览。
- RAG 质量诊断。
- RAG 摄取任务监控。
- Agent 决策日志。
- AI Debug / Agent 工作流观测。
- 基础设施状态：database、Redis、Celery。

### 3.8 部署工程化

- Dockerfile。
- docker-compose.yml。
- Nginx 反向代理和 Vue 静态资源服务。
- PostgreSQL 生产数据库。
- Redis。
- Celery worker。
- Alembic migration。
- `.env.production.example`。
- 部署、排错、备份回滚和 HTTPS 参考文档。
- 已处理生产 PostgreSQL schema 与本地 SQLite 不一致导致的线上 500 问题，并补充正式 Alembic 迁移。

## 4. 当前已知边界

已经完成：

- IP + 8080 端口公网演示。
- Vue3 前端公网访问。
- FastAPI API 公网访问。
- PostgreSQL / Redis / Celery / Nginx 容器化运行。
- 生产库迁移问题修复。

尚未完成：

- 域名。
- HTTPS。
- API Key 轮换。
- 管理员强密码策略。
- 注册弱密码限制。
- 自动备份。
- 日志轮转。
- 监控告警。
- 对象存储。
- CI/CD。
- Qdrant / pgvector。
- OCR、Word、Excel、网页解析。

## 5. 刚上线暴露过的问题

### 5.1 PostgreSQL schema 缺字段

表现：

```text
登录、知识库或管理员后台出现 Internal server error
```

根因：

本地 SQLite 有自动补表逻辑，但生产 PostgreSQL 依赖 Alembic migration。部分模型字段已经被代码使用，但旧迁移没有完整创建字段。

处理：

- 线上热修缺失字段。
- 补充 Alembic migration。
- 增加迁移防漏测试。

价值：

这是很典型的生产化问题，可以在面试中包装成“本地开发环境与生产数据库迁移差异导致的线上 500 排查和修复”。

### 5.2 Nginx / Vue 静态资源配置需要固化

表现：

服务器上 `/vue/` 需要服务 Vue3 build 产物，`/api/` 需要代理 FastAPI。

处理：

- Compose 挂载 `frontend/dist` 到 Nginx。
- Nginx 对 `/vue/` 使用 `try_files` fallback 到 `/vue/index.html`。
- 根路径 `/` 重定向到 `/vue/auth/login`。

价值：

这说明部署不是只启动后端，还要处理前端静态资源、SPA 路由和 API 代理。

## 6. 推荐下一阶段

### 推荐 A：Pre-Launch Stabilization V1

目标：

把项目从“能公网跑”整理成“可以稳定发给 HR 演示”。

范围：

- 使用 `docs/demo/public-demo-materials.md` 走完整链路 smoke test。
- 修复公网链路暴露的小 bug。
- 轮换暴露过的 DashScope API Key。
- 管理员账号改强密码。
- 注册弱密码限制。
- README、current-state 和部署文档继续校准。
- 准备一组演示数据。
- 记录部署故障复盘。

推荐优先级：最高。

### 可选 B：HTTPS 和域名

目标：

把 `http://IP:8080` 升级为更像正式项目的 HTTPS 访问。

范围：

- 购买域名。
- DNS 解析。
- Nginx 80/443。
- Certbot 或 Cloudflare HTTPS。
- 更新 CORS / 前端 API base URL。

推荐优先级：中高。适合在演示链路稳定后做。

### 可选 C：项目讲解和简历包装

目标：

把项目整理成面试能讲清楚的故事。

范围：

- 业务背景。
- 系统架构。
- 核心链路。
- RAG、Agent、LangGraph、部署和生产事故复盘。
- 简历 bullet。
- 面试深挖问答。

推荐优先级：高。可以和 A 并行，但不要替代 A。

### 暂缓 D：继续重功能开发

包括：

- Qdrant / pgvector。
- OCR / Word / Excel / 网页解析。
- 更复杂 RBAC。
- CI/CD。
- 更完整运营后台。

原因：

这些能力有价值，但在当前阶段继续堆功能的边际收益低于把公网演示、安全和项目讲解打稳。

## 7. 下一步建议

下一步建议先执行：

```text
Pre-Launch Stabilization V1：公网演示稳定化与安全收尾
```

最小可交付：

1. 用虚构演示资料完成一遍完整链路。
2. 修复链路中出现的公网 bug。
3. 轮换 API Key 和管理员密码。
4. 更新部署文档和项目状态。
5. 写一份“上线问题复盘 + 面试讲法”。

完成后，再进入：

```text
HTTPS / 域名
-> 项目讲解和简历包装
-> 继续开发下一轮增强功能
```
