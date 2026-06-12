# Plans 说明

`active/` 只放“尚未执行、当前准备执行”的 implementation plan。

如果一个 plan 已经执行完，即使里面还有复盘价值，也不要继续放在 `active/`，避免误判为下一步任务。

`completed/` 放已经执行完、但仍有复盘价值的 implementation plan。

`archive/` 放历史计划，保留上下文，不建议日常翻阅。

## 当前状态

当前 `active/` 暂时没有 implementation plan。

原因：

```text
Vue3 前端重构 V1 的 spec 已经写入 active，但还需要用户 review 并确认范围。确认后，再根据 spec 编写新的 implementation plan。
```

当前 active spec：

```text
docs/specs/active/vue3-frontend-rebuild-v1-design.md
```

上一阶段 Docker + Nginx + VPS 上线 V1 plan 已完成并移动到：

```text
docs/plans/completed/docker-nginx-vps-deployment-v1.md
```

上一阶段后端生产化 V1 plan 已完成并移动到：

```text
docs/plans/completed/backend-production-v1-postgres-redis-celery.md
```

上一阶段面试体验增强 V3 + LangGraph 深化 plan 已完成并移动到：

```text
docs/plans/completed/interview-experience-v3-langgraph-deepening.md
```

上一阶段 LangGraph Agent V2 plan 已完成并移动到：

```text
docs/plans/completed/langgraph-agent-v2-real-rag-checkpoint.md
```

已执行完但仍有参考价值的主线 plan 在：

```text
docs/plans/completed/
```

## 追求目标模式怎么用

如果要使用 Codex 的“追求目标”模式，不要直接复制 `completed/` 里的旧 plan。

推荐流程是：

1. 先看 `docs/roadmap/current-state.md`。
2. 再看 `docs/specs/active/` 是否只有一份明确的新阶段 spec。
3. 如果只有 spec、没有 plan，先写 plan。
4. plan 写完后再按 plan 执行。
