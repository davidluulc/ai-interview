# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：

```text
docs/specs/active/pre-launch-delivery-roadmap-v4-design.md
```

最近完成并归档的 spec：

```text
docs/specs/completed/production-hardening-v3-2-v3-3-design.md
```

最近完成阶段主题：

```text
Production Hardening V3.2 + V3.3：已完成 token blacklist、基础限流、provider 错误脱敏、RAG upload 幂等、retry 并发保护、管理员安全摘要和 ingestion 异常聚合。SQLite 仍为本地默认数据库，Redis 保持 disabled / memory fallback 测试路径。
```

当前准备执行阶段：

```text
Pre-Launch Delivery Roadmap V4：Async Worker Readiness V4 已完成，下一步执行 PostgreSQL Compatibility V4。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
