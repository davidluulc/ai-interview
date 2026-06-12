# Specs 说明

`active/` 只放“尚未执行、当前准备执行”的 spec。

如果一个 spec 已经按阶段执行完，即使它还有学习和复盘价值，也不要继续放在 `active/`，避免误判为下一步任务。

`completed/` 放已经执行完、但仍有复盘价值的 spec。

`archive/` 放历史 spec，保留上下文，不建议日常翻阅。

## 当前状态

当前 `active/` 有一个准备执行的 spec：

```text
docs/specs/active/docker-nginx-vps-deployment-v1-design.md
```

主题：

```text
Docker + Nginx + VPS 上线 V1：把当前 AI 模拟面试系统从本地可运行推进到具备云服务器上线展示能力，补齐 Dockerfile、docker-compose、Nginx、部署环境变量、VPS 部署手册、日志、备份、回滚和验收文档。
```

上一阶段后端生产化 V1 spec 已完成并移动到：

```text
docs/specs/completed/backend-production-v1-postgres-redis-celery-design.md
```

主题：

```text
后端生产化 V1：本地继续 SQLite，通过 DATABASE_URL 预留 PostgreSQL/MySQL 生产数据库方向，引入 Redis 基础设施和 Celery 异步任务框架。
```

上一阶段面试体验增强 V3 + LangGraph 深化 spec 已完成并移动到：

```text
docs/specs/completed/interview-experience-v3-langgraph-deepening-design.md
```

主题：

```text
面试体验增强 V3 + LangGraph 深化：通过 Agent Policy 连接 classic Agent 与 LangGraph 旁路工作流。
```

上一阶段 LangGraph Agent V2 已完成并移动到：

```text
docs/specs/completed/langgraph-agent-v2-real-rag-checkpoint-design.md
```

已执行完但仍有参考价值的主线 spec 在：

```text
docs/specs/completed/
```

其中包括：

- `pre-deployment-engineering-roadmap-design.md`
- `production-rag-engineering-design.md`
- `agent-engineering-v3-design.md`
- `frontend-productization-v2-design.md`
- `langgraph-agent-poc-design.md`
- `langgraph-agent-v2-real-rag-checkpoint-design.md`
- `interview-experience-v3-langgraph-deepening-design.md`
- `backend-production-v1-postgres-redis-celery-design.md`

历史暂缓执行的 spec 在：

```text
docs/specs/archive/2026-06-11-deployment-engineering-v1-design.md
```

原因：当时用户希望先继续打磨项目核心竞争力，暂不进入上线部署准备。当前路线已经重新进入上线展示 V1，因此以 `active/docker-nginx-vps-deployment-v1-design.md` 为准。

## 下一步怎么看

如果要判断下一阶段做什么，先看：

```text
docs/roadmap/current-state.md
```

再看 `docs/roadmap/project-progress.md` 的最新执行记录。
