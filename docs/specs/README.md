# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
docs/specs/active/production-rag-v3-ingestion-quality-design.md
```

当前阶段状态：

```text
Production RAG V3 已进入 active spec：摄取任务持久化、失败重试与质量监控增强。本阶段聚焦 RAG 文档入口工程化，不重复 lifecycle、metadata、hybrid、rerank、evaluation 等已完成能力。
```

最近完成并归档的 spec：

```text
docs/specs/completed/langgraph-agent-workflow-v6-design.md
```

阶段主题：

```text
Production RAG V3：将文件导入任务从内存态升级为数据库持久化任务，并补齐失败原因、重试入口、用户侧任务历史和管理员摄取质量监控。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
