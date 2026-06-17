# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
docs/specs/active/langgraph-mainline-consolidation-v7-design.md
```

当前阶段状态：

```text
LangGraph Mainline Consolidation V7 已进入 active spec：将 /api/interview/next-question 默认主链路从 classic Python Orchestrator 收敛到 LangGraph mainline，classic Agent 降级为 fallback/helper，并清理前后台双轨对比式产品表达。
```

最近完成并归档的 spec：

```text
docs/specs/completed/production-rag-v3-ingestion-quality-design.md
```

阶段主题：

```text
LangGraph Mainline Consolidation V7：Agent 主链路收敛、workflow state、checkpoint、fallback、quality gate、RAG 节点化接入和后台工作流观测。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
