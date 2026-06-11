# Agent 调试面板 UI V1 设计

## 1. 文档目的

本文档用于约束 AI 模拟面试系统下一阶段的前端体验增强：在面试训练工作台中增加 Agent 调试面板。

上一阶段已经完成 Agent Quality Control V2，后端已经能够输出：

- `triggerRules`
- `guardrailApplied`
- `topicShift`
- `debugSignals`
- `decisionSummary`
- `nodeTrace`
- `toolCalls`

这些字段说明 Agent 为什么降难度、为什么切换话题、是否触发保护规则、是否发生话题迁移。但当前页面主要还是把这些信息以“决策解释条”或“日志列表”的形式展示，用户和开发者不能一眼看出本轮 Agent 的关键判断。

本阶段目标是把后端可观测性能力转成前端可读的调试面板，让系统更像一个可解释、可复盘、可展示的 AI 应用工程化项目。

## 2. 当前基础

当前前端已有能力：

- 面试训练工作台。
- 聊天流式面试体验。
- `agentDecisionPanel` 展示本轮 Agent 决策摘要。
- “查看 Agent 决策日志”按钮。
- `renderAgentNodeTrace(decision)` 展示节点链路。
- `renderAgentToolCalls(decision)` 展示工具调用。
- `/api/agent/logs/recent` 最近 Agent 日志接口。

当前后端日志接口已经将以下字段提到顶层：

```json
{
  "debugSignals": {},
  "guardrailApplied": true,
  "topicShift": {
    "from": "rag_log_json",
    "to": "rag_basic"
  }
}
```

因此本阶段不需要改后端 API，重点是前端如何组织和展示这些信息。

## 3. 本阶段目标

本阶段目标：

```text
在不打断面试主流程的前提下，让用户和开发者能看懂 Agent 本轮为什么这么问。
```

具体目标：

- 在面试工作台中增加 Agent 调试面板。
- 展示当前轮 Agent 动作、难度、考察点、触发规则。
- 展示 `debugSignals` 摘要。
- 展示 `guardrailApplied` 是否触发。
- 展示 `topicShift.from` 和 `topicShift.to`。
- 保留当前 `agentDecisionPanel` 的轻量解释能力。
- 保留最近 Agent 日志列表能力。
- 不修改后端 API。
- 不引入 React、Vue、Next.js。

## 4. 非目标

本阶段明确不做：

- 不改后端 Agent 决策逻辑。
- 不改 `/api/interview/next-question` 的字段语义。
- 不新增数据库表。
- 不引入 LangGraph。
- 不安装 LangChain。
- 不做 Docker、Nginx、云服务器上线。
- 不做全站视觉重构。
- 不做管理员后台。
- 不把调试面板做成复杂可视化图编辑器。

## 5. 用户角色

### 5.1 普通练习用户

关注点：

- 为什么这一题这样问？
- 我是不是连续答不上来了？
- 系统是不是给我降难度了？
- 系统有没有换话题？

普通用户不需要理解所有原始 JSON。

### 5.2 学习者 / 开发者

关注点：

- `nextAction` 是什么？
- `triggerRules` 触发了哪些规则？
- `guardrailApplied` 是否为 true？
- `topicShift` 从哪切到哪？
- `debugSignals.weakAnswerStreak` 是多少？
- 节点链路和工具调用是否正常？

学习者需要看到工程字段，但不应该被大段 JSON 淹没。

## 6. 页面位置设计

推荐采用“伴随式调试面板”。

位置：

```text
面试工作台右侧或当前 Agent Insight Bar 下方
```

在当前纯 HTML/CSS/JS 结构中，建议先放在 `agentDecisionPanel` 附近，形成：

```text
Agent Insight Bar
Agent Debug Panel
Answer Composer
```

桌面端：

- 默认展开轻量摘要。
- 详细链路可以折叠。
- 不挤压聊天流主区域。

移动端：

- 默认折叠。
- 点击按钮展开。
- 不使用悬浮大弹窗作为核心交互。

## 7. 面板结构

### 7.1 顶部摘要

显示：

```text
Agent 动作：switch_topic
难度：basic
考察点：RAG 基础链路
保护规则：已介入 / 未介入
```

数据来源：

- `agentDecision.nextAction`
- `agentDecision.difficulty`
- `agentDecision.focus`
- `agentDecision.guardrailApplied`

显示原则：

- 用短标签展示。
- `guardrailApplied=true` 时用明显但不刺眼的状态样式。
- 不显示大段解释文字。

### 7.2 Debug Signals

显示字段：

```text
连续弱回答：2
重复问题次数：0
话题锁定：否
保护规则介入：是
发生话题切换：是
```

数据来源：

- `agentDecision.debugSignals.weakAnswerStreak`
- `agentDecision.debugSignals.repeatedQuestionCount`
- `agentDecision.debugSignals.topicLocked`
- `agentDecision.debugSignals.guardrailApplied`
- `agentDecision.debugSignals.topicShifted`

字段缺失时：

- 数字字段显示 `0`。
- 布尔字段显示 `否`。
- 不报错，不显示 `undefined`。

### 7.3 Topic Shift

当存在 `topicShift` 时展示：

```text
话题迁移：RAG 日志 JSON -> RAG 基础链路
```

数据来源：

- `agentDecision.topicShift.from`
- `agentDecision.topicShift.to`

如果没有发生话题切换：

```text
话题迁移：未发生
```

### 7.4 Trigger Rules

展示触发规则：

```text
weak_answer_streak
interview_weak_answer_limit
topic_shift
```

数据来源：

- 优先使用 `agentDecision.debugSignals.triggerRules`
- 兜底使用 `agentDecision.triggerRules`

显示原则：

- 使用小标签。
- 规则为空时显示 `暂无触发规则`。
- 保留英文工程字段，方便面试讲项目。

### 7.5 节点链路和工具调用

复用现有能力：

- `renderAgentNodeTrace(decision)`
- `renderAgentToolCalls(decision)`

调整展示方式：

- 放到“高级调试详情”折叠区。
- 默认收起或弱化。
- 避免把主面试页面变成日志页。

## 8. 最近日志列表增强

当前已有“查看 Agent 决策日志”按钮。

本阶段增强最近日志卡片：

- 直接显示顶层 `debugSignals`。
- 直接显示顶层 `guardrailApplied`。
- 直接显示顶层 `topicShift`。
- 保留原来的 nodeTrace 和 toolCalls。

展示示例：

```text
动作：switch_topic
保护规则：已介入
连续弱回答：2
话题迁移：rag_log_json -> rag_basic
触发规则：interview_weak_answer_limit / topic_shift
```

## 9. 数据兼容策略

前端必须兼容旧数据。

兼容规则：

- `agentDecision.debugSignals` 不存在时，使用空对象。
- `debugSignals` 顶层不存在时，从 `decision.debugSignals` 兜底。
- `guardrailApplied` 顶层不存在时，从 `decision.guardrailApplied` 兜底。
- `topicShift` 顶层不存在时，从 `decision.topicShift` 兜底。
- 字段都不存在时，显示默认状态。

不允许：

- 页面出现 `undefined`。
- 因为某个字段缺失导致 JS 报错。
- 因为新字段缺失导致旧面试流程不可用。

## 10. 测试策略

本阶段遵循前端测试驱动。

优先测试：

### 10.1 当前轮 Agent 调试面板

可更新：

```text
tests/frontend_interview_flow.test.mjs
```

覆盖：

- `agentDecisionPanel` 能展示 `guardrailApplied`。
- 能展示 `debugSignals.weakAnswerStreak`。
- 能展示 `topicShift.from -> topicShift.to`。
- 缺失字段时不显示 `undefined`。

### 10.2 最近 Agent 日志列表

可更新：

```text
tests/frontend_agent_logs.test.mjs
```

覆盖：

- 日志卡片能展示顶层 `debugSignals`。
- 日志卡片能展示顶层 `guardrailApplied`。
- 日志卡片能展示顶层 `topicShift`。
- 旧日志没有这些字段时仍能正常渲染。

### 10.3 布局存在性

可更新：

```text
tests/frontend_workbench_layout.test.mjs
```

覆盖：

- Agent Debug Panel 容器存在。
- 面板不替代聊天流。
- 面板在移动端可以折叠或自然换行。

## 11. 推荐实现范围

本阶段优先修改：

```text
index.html
styles.css
app.js
tests/frontend_interview_flow.test.mjs
tests/frontend_agent_logs.test.mjs
tests/frontend_workbench_layout.test.mjs
```

不修改：

```text
backend_python/*
requirements.txt
数据库模型
Docker/Nginx/云服务器配置
```

## 12. 验收标准

完成后应满足：

- 当前轮面试问题下方能看到 Agent 调试摘要。
- 能看出是否触发 guardrail。
- 能看出连续弱回答次数。
- 能看出是否发生 topic shift。
- 能看出触发规则。
- 最近 Agent 日志卡片能展示相同的调试摘要。
- 缺失字段时页面不报错，不出现 `undefined`。
- 前端 `.mjs` 测试通过。
- 后端 `python -m pytest -q` 通过。
- 页面仍可打开 `http://localhost:8000/`。

## 13. 面试表达

可以这样讲：

```text
后端 Agent 已经能输出 triggerRules、guardrailApplied、topicShift 和 debugSignals。
为了避免这些能力只停留在日志 JSON 里，我在前端面试工作台增加了 Agent 调试面板。
它会把本轮 Agent 的动作、保护规则、连续弱回答次数、话题迁移和触发规则展示出来。
这样用户能理解为什么系统降难度或切换话题，开发者也能更快排查 Agent 决策是否符合预期。
这体现了 AI 应用工程化里的可观测性和可解释性。
```

## 14. 追求目标模式建议

如果要用 Codex 的追求目标模式执行本阶段，可以输入：

```text
根据 docs/superpowers/specs/2026-06-09-agent-debug-panel-ui-design.md，
持续推进 AI 模拟面试系统 Agent 调试面板 UI V1。

要求：
1. 每次开发前先用中文解释本轮要学的前端可观测性知识点。
2. 开发时优先测试驱动，先写或更新前端 .mjs 测试，再实现。
3. 当前阶段优先改 index.html、styles.css、app.js 和前端 .mjs 测试。
4. 不改后端 API，不改数据库。
5. 不引入 React、Vue、Next.js。
6. 不引入 LangGraph，不安装 LangChain。
7. 不做 Docker、Nginx、云服务器上线。
8. 每轮开发后总结改了哪些文件、为什么这么改、面试时应该怎么讲。
9. 完成后运行 python -m pytest -q 和所有前端 .mjs 测试。
10. 完成后使用内置浏览器验证 http://localhost:8000/ 的桌面端和移动端页面效果。
```

