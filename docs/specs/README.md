# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
docs/specs/active/backend-production-infrastructure-v1-design.md
```

最近完成并归档的 spec：

```text
docs/specs/completed/project-closure-audit-v1-design.md
```

最近完成阶段主题：

```text
Project Closure Audit V1：统一 README、启动入口、测试命令、文档状态、Vue3 主入口、旧兼容入口说明和后续开发基线。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
