# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
暂无。
```

最近完成并归档的 spec：

```text
docs/specs/completed/async-rag-ingestion-v2-design.md
```

最近完成阶段主题：

```text
Async RAG Ingestion V2：RAG 文档上传和 retry 通过 taskId 派发 Celery ingestion task，任务状态、进度、失败原因和 documentId 写回数据库。
```

当前准备执行阶段：

```text
暂无。下一阶段需要先根据 roadmap/current-state.md 重新讨论并创建新的 active spec。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
