# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：

```text
docs/plans/active/langgraph-agent-workflow-v6.md
```

当前 active spec：

```text
docs/specs/active/langgraph-agent-workflow-v6-design.md
```

当前阶段状态：

```text
正在准备执行 LangGraph / Agent 工作流深化 V6：围绕节点契约、执行回放、人工复核队列和 runtime report 深化 LangGraph 工作流治理。
```

最近完成并归档的 plan：

```text
docs/plans/completed/interview-training-loop-v3.md
```

阶段主题：

```text
面试训练闭环增强 V3：训练任务练习材料、用户作答、自评、掌握度更新和训练中心前端体验。
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
