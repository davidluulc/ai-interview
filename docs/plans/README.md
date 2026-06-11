# Plans 说明

`active/` 只放“尚未执行、当前准备执行”的 implementation plan。

如果一个 plan 已经执行完，即使里面还有复盘价值，也不要继续放在 `active/`，避免误判为下一步任务。

`completed/` 放已经执行完、但仍有复盘价值的 implementation plan。

`archive/` 放历史计划，保留上下文，不建议日常翻阅。

## 当前状态

当前 `active/` 有一个准备执行的 implementation plan：

```text
docs/plans/active/docker-nginx-vps-deployment-v1.md
```

主题：

```text
Docker + Nginx + VPS 上线 V1：按部署配置测试、环境变量模板、Dockerfile、docker-compose、Nginx、部署文档、学习文档和全量验证的顺序推进。
```

上一阶段后端生产化 V1 plan 已完成并移动到：

```text
docs/plans/completed/backend-production-v1-postgres-redis-celery.md
```

主题：

```text
后端生产化 V1：数据库适配 + Redis + Celery。
```

上一阶段面试体验增强 V3 + LangGraph 深化 plan 已完成并移动到：

```text
docs/plans/completed/interview-experience-v3-langgraph-deepening.md
```

主题：

```text
面试体验增强 V3 + LangGraph 深化：新增 Agent Policy 层，并让 classic Agent 与 LangGraph 旁路复用同一套策略。
```

上一阶段 LangGraph Agent V2 plan 已完成并移动到：

```text
docs/plans/completed/langgraph-agent-v2-real-rag-checkpoint.md
```

下一步不要直接复制旧 plan 继续跑，应先根据 `docs/roadmap/current-state.md` 讨论新的主线，再写新的 active spec 和 active plan。

已执行完但仍有参考价值的主线 plan 在：

```text
docs/plans/completed/
```

其中包括：

- `pre-deployment-engineering-roadmap.md`
- `production-rag-engineering.md`
- `frontend-productization-v2.md`
- `langgraph-agent-poc.md`
- `langgraph-agent-v2-real-rag-checkpoint.md`
- `interview-experience-v3-langgraph-deepening.md`
- `backend-production-v1-postgres-redis-celery.md`

## 追求目标模式怎么用

如果要使用 Codex 的“追求目标”模式，不要直接复制 `completed/` 里的旧 plan。

推荐流程是：

1. 先看 `docs/roadmap/current-state.md`。
2. 再看 `docs/specs/active/` 是否只有一份明确的新阶段 spec。
3. 如果只有 spec、没有 plan，先写 plan。
4. plan 写完后再按 plan 执行。
