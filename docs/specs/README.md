# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
暂无
```

当前阶段状态：

```text
LangGraph / Agent 工作流深化 V6 已完成并归档。下一阶段建议先讨论是否继续扩大 LangGraph 主链路迁移，或进入生产级 RAG V3，再写新的 active spec。
```

最近完成并归档的 spec：

```text
docs/specs/completed/langgraph-agent-workflow-v6-design.md
```

阶段主题：

```text
LangGraph / Agent 工作流深化 V6：节点契约 -> 执行回放 -> 人工复核队列 -> runtime report -> 管理员后台可读诊断。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
