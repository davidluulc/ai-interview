# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
docs/specs/active/interview-training-loop-v3-design.md
```

当前阶段状态：

```text
当前 active 阶段为面试训练闭环增强 V3。目标是让训练任务从列表状态升级为可作答、可反馈、可更新掌握度的专项练习体验。
```

最近完成并归档的 spec：

```text
docs/specs/completed/langgraph-mainline-canary-v5-design.md
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
