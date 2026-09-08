# Agent v3 升级流水线 · 总控文档（Goal 模式启动文本）

更新时间：2026-09-09

本文档是 S2-S5 四个阶段的执行总纲：阶段顺序、合并门、停止条件与启动文本。各阶段详细计划见 `docs/plans/active/agent-v3-upgrade-stage{2,3,4,5}-*.md`，总 spec 见 `docs/specs/active/agent-v3-upgrade-design.md`（§0 Goal Card 的预算/红线继续生效）。

## 阶段依赖与顺序

```text
S1 结构化输出（已完成，已合并 main）
S2 pgvector      ── 独立
S3 RRF 实验      ── 独立（数字完整性受益于 S2，公网复跑统一补）
S4 LangGraph v3  ── 依赖 S1（已完成），独立于 S2/S3
S5 MCP           ── 依赖 S4 的 graph_v3 tool_fns 注入点（S4 受阻时 S5 的
                    server 侧 Task 1-2 仍可做，client 侧 Task 3-4 挂起）
```

受阻跳过规则：某阶段按其 plan 的停止条件受阻时，记录后跳到下一个可独立推进的阶段；S4 受阻时 S5 只做 server 侧。

## 预先解决的阻塞点（2026-09-09 已验证）

1. `pgvector/pgvector:pg16` 镜像已拉取；docker 守护进程可用（29.3.1）。
2. langgraph 0.2.76 支持 `add_conditional_edges`（S4 无版本风险）。
3. mcp SDK 当前为 v2（2.2.0）：`FastMCP` 已更名 `MCPServer`（`from mcp.server.mcpserver import MCPServer`），装饰器 `@m.tool()` 可用——S5 计划按 v2 编写。

## 合并门（每阶段结束时由总控执行）

1. 阶段 plan 全部 Task 完成 + 全量 `pytest -q` 无新失败（基线 = 467 passed + 1 个 main 遗留 README 失败）。
2. 整分支终审（最强模型）clean 或修复波闭环。
3. 满足 1+2 → `git checkout main && git merge feat/agent-v3-s<N>-* && git branch -d`（本地合并，不 push）。
4. 不满足 → 分支保留，记录阻塞点，跳到下一独立阶段或停止。

## 流水线 Goal 启动文本（粘贴即启动）

```text
[Goal 模式启动] Agent v3 升级流水线 · S2→S3→S4→S5

目标：按 docs/plans/active/agent-v3-upgrade-pipeline.md 的顺序与合并门，
完成 S2-S5 四个阶段。每阶段：从 main 切分支 feat/agent-v3-s<N>-* →
按该阶段 plan 用子代理驱动执行（每 Task 实现+审查+修复环）→ 全量测试
无新失败 + 整分支终审 clean → 合并回 main → 删分支 → 下一阶段。

预算：本窗口 8 小时硬上限；单阶段超其 plan 预算 1.5 倍即停该阶段。

停止条件：
1. 阶段内 Task 重派 2 次不过 → 停该阶段，跳下一独立阶段（顺序见
   pipeline 文档「受阻跳过规则」）。
2. 合并门不满足 → 分支保留不合并，记录后跳下一阶段。
3. 数据破坏性风险（迁移在非测试库执行、删列删表）→ 全局停止。
4. 需要产品级决策 → 记录并跳过该决策点，能继续则继续。
5. 8 小时窗口耗尽 → commit 现状，输出晨报。

红线：不 push 远端；不动生产 VPS；不新增 mcp 之外的依赖；不升级
langgraph 版本；不修范围外问题（记 current-state 待办）；S2-S5 各 plan
的 Global Constraints 逐条生效。

预授权（无需人工确认）：本地合并回 main、跳过受阻阶段、对 plan 中
标注「执行时确认」的事实型占位按实际情况落值并记账、S3 默认融合
模式按实验数字切换（规则见其 plan Task 4）。

汇报节奏：每 Task 一行；每阶段结束一行「S<N> ✅ merged <hash> /
受阻跳过」；窗口结束输出晨报（各阶段状态、测试数、合并记录、
遗留清单、main 当前 HEAD）。

从 S2 开始。
```

## 晨报模板

```text
- S2 pgvector：完成/受阻/未开始 · 合并 hash · 新增测试 N
- S3 RRF：…（含四组数字表）
- S4 graph v3：…
- S5 MCP：…
- main HEAD：<hash>；远端未推送（待人工）
- 遗留：current-state.md 待办新增 X 条
```
