# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：

```text
暂无。
```

当前 active spec：

```text
暂无。
```

当前阶段状态：

```text
LangGraph Mainline Consolidation V7 已完成并归档。当前没有 active plan，下一阶段需要先讨论方向，再写新的 active plan。
```

最近完成并归档的 plan：

```text
docs/plans/completed/langgraph-mainline-consolidation-v7.md
```

阶段主题：

```text
LangGraph Mainline Consolidation V7：Agent 主链路收敛、classic fallback、RAG 节点化接入、runtime audit、checkpoint、quality gate 和 Vue3 工作流观测。
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
