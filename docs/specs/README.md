# Specs 说明

`active/` 只放“尚未执行、当前准备执行”的 spec。

如果一个 spec 已经按阶段执行完，即使它还有学习和复盘价值，也不要继续放在 `active/`，避免误判为下一步任务。

`completed/` 放已经执行完、但仍有复盘价值的 spec。

`archive/` 放历史 spec，保留上下文，不建议日常翻阅。

## 当前状态

当前 `active/` 有一个准备执行的 spec：

```text
docs/specs/active/vue3-frontend-rebuild-v1-design.md
```

主题：

```text
Vue3 前端重构 V1：在保留旧原生页面作为兜底入口的前提下，新建 Vue3 + Vite + TypeScript 前端工程，优先完成产品壳、登录态、投递档案和面试训练主流程，并采用极简、克制、接近苹果式审美的产品视觉。
```

上一阶段 Docker + Nginx + VPS 上线 V1 spec 已完成并移动到：

```text
docs/specs/completed/docker-nginx-vps-deployment-v1-design.md
```

上一阶段后端生产化 V1 spec 已完成并移动到：

```text
docs/specs/completed/backend-production-v1-postgres-redis-celery-design.md
```

上一阶段面试体验增强 V3 + LangGraph 深化 spec 已完成并移动到：

```text
docs/specs/completed/interview-experience-v3-langgraph-deepening-design.md
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

- `docker-nginx-vps-deployment-v1-design.md`
- `backend-production-v1-postgres-redis-celery-design.md`
- `interview-experience-v3-langgraph-deepening-design.md`
- `langgraph-agent-v2-real-rag-checkpoint-design.md`
- `langgraph-agent-poc-design.md`
- `frontend-productization-v2-design.md`
- `production-rag-engineering-design.md`
- `agent-engineering-v3-design.md`
- `pre-deployment-engineering-roadmap-design.md`

## 下一步怎么看

如果要判断下一阶段做什么，先看：

```text
docs/roadmap/current-state.md
```

再看 `docs/roadmap/project-progress.md` 的最新执行记录。
