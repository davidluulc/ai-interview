# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：

```text
docs/plans/active/production-rag-v3-ingestion-quality.md
```

当前 active spec：

```text
docs/specs/active/production-rag-v3-ingestion-quality-design.md
```

当前阶段状态：

```text
Production RAG V3 已进入 active plan：摄取任务持久化、失败重试与质量监控增强。本阶段优先按 TDD 开发后端任务模型、任务接口、管理员监控接口和 Vue3 可读展示。
```

最近完成并归档的 plan：

```text
docs/plans/completed/langgraph-agent-workflow-v6.md
```

阶段主题：

```text
Production RAG V3：RAG 文件摄取任务持久化、失败重试、用户任务历史和管理员摄取质量监控。
```

## 追求目标模式建议

如果要使用 Codex 的“追求目标”模式，不要直接复制 `completed/` 或 `archive/` 中的旧 plan。

推荐流程：

```text
先确认 active spec
-> 再写 active plan
-> 按 plan 分阶段测试驱动开发
-> 完成后把 spec 和 plan 移到 completed
-> 更新 roadmap/current-state.md
```
