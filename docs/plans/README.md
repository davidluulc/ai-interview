# Plans 说明

`active/` 只放当前准备执行、尚未完成的 implementation plan。
`completed/` 放已经阶段性完成、仍有复盘价值的 implementation plan。
`archive/` 放历史 plan，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active plan：
```text
docs/plans/active/admin-observability-ux-v3.md
```

当前 active spec：
```text
docs/specs/active/admin-observability-ux-v3-design.md
```

最近完成并归档的 plan：
```text
docs/plans/completed/admin-report-productization-v2.md
docs/plans/completed/production-ux-auth-hardening-v1.md
docs/plans/completed/public-demo-stabilization-rag-seed-v1.md
```

最近完成阶段主题：
```text
Admin & Report Productization V2：已完成强制下线闭环产品化、AI 调试控制台真 tabs、RAG/Agent 后台 dashboard、报告页出题依据人话化。
```

当前准备执行阶段：
```text
Admin Observability UX V3：把 RAG、Agent、AI 请求和面试报告按用户、档案、面试记录、问题轮次组织成诊断工作台，减少后台日志墙。
```

当前进度：
```text
V3 产品可见部分已完成：按钮可见性 bug、面试诊断聚合 API、前端诊断工作台入口、逐题链路详情、知识库健康 tab、Agent 行为 tab、AI 请求 tab 已落地；旧长日志默认收进开发排查。V3 仍保持 active，用于后续公网 smoke，底层 trace id/字段补强可进入 V3.1/V4。
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
