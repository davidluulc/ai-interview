# Specs 说明

`active/` 只放当前准备执行、尚未完成的 spec。
`completed/` 放已经阶段性完成、仍有复盘价值的 spec。
`archive/` 放历史 spec，只作为背景资料，不建议直接拿来继续执行。

## 当前状态

当前 active spec：
```text
暂无。下一阶段开始前再新建 active spec。
```

最近完成并归档的 spec：
```text
docs/specs/completed/public-demo-stabilization-rag-seed-v1-design.md
```

最近完成阶段主题：
```text
Public Demo Stabilization + Production RAG Seed V1：已完成生产 RAG seed、面试启动入口修复、结束复盘闭环、面试官 thinking loading、知识库用户页简化、档案归档/恢复、RAG 空召回提示和公网部署验证。
```

推荐下一阶段：
```text
Pre-Launch Stabilization V1：安全收口、演示脚本、README/部署文档校准、密钥轮换、管理员账号加固、最终 HR 演示准备。
```

## 使用规则

判断下一步开发路线时，优先看：

```text
docs/roadmap/current-state.md
docs/specs/active/
docs/plans/active/
```

不要直接复制 `completed/` 或 `archive/` 中的旧 spec 继续执行。旧文档只用于校准背景，新的开发阶段必须有新的 active spec 和 active plan。
