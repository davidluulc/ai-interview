# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：

```text
docs/plans/active/pre-launch-delivery-roadmap-v4.md
```

当前 active spec：

```text
docs/specs/active/pre-launch-delivery-roadmap-v4-design.md
```

最近完成并归档的 plan：

```text
docs/plans/completed/production-hardening-v3-2-v3-3.md
```

最近完成阶段主题：

```text
Pre-Launch Delivery Roadmap V4 / Deployment Integration V4：已完成 Docker Compose 结构化验证、稳定 project name、上线 runbook 和 pre-launch checklist。下一步继续执行 Project Explanation & Resume Pack V1。
```

## 追求目标模式建议

如果要使用 Codex 的“追求目标”模式，不要直接复制 `completed/` 或 `archive/` 中的旧 plan。

推荐流程：

```text
先确认 active spec：docs/specs/active/pre-launch-delivery-roadmap-v4-design.md
-> 再写 active plan
-> 按 plan 分阶段测试驱动开发或审计
-> 完成后把 spec 和 plan 移到 completed
-> 更新 roadmap/current-state.md
```
