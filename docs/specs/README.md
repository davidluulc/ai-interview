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
面试训练闭环增强 V3 已完成并归档。下一阶段建议先讨论是否进入 LangGraph / Agent 工作流深化 B 阶段，再写新的 active spec。
```

最近完成并归档的 spec：

```text
docs/specs/completed/interview-training-loop-v3-design.md
```

阶段主题：

```text
面试训练闭环增强 V3：报告 weakTag -> 训练任务 -> 专项练习 -> 用户作答 -> 掌握度更新 -> 再面试。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
