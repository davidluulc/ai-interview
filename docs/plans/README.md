# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：
```text
暂无
```

当前 active spec：
```text
暂无
```

最近完成并归档的 plan：
```text
docs/plans/completed/production-ux-auth-hardening-v1.md
docs/plans/completed/public-demo-stabilization-rag-seed-v1.md
```

最近完成阶段主题：
```text
Production UX & Auth Hardening V1：已完成报告页出题依据、训练页薄弱点筛选、AI 调试台分类去重、Redis 会话控制和管理员强制下线。
```

当前准备执行阶段：
```text
暂无。建议下一轮先进入 Pre-Launch Stabilization V1：公网 smoke test、API Key 轮换、演示数据和 README/部署/讲解材料整理。
```

## 追求目标模式建议

如果要使用 Codex 的“追求目标”模式，不要直接复制 `completed/` 或 `archive/` 中的旧 plan。

推荐流程：

```text
先确认 active spec
-> 再写 active plan
-> 按 plan 分阶段测试驱动开发或审计
-> 完成后把 spec 和 plan 移到 completed
-> 更新 roadmap/current-state.md
```
