# LangGraph 从旁路到候选主链路如何灰度迁移

## 1. 这一阶段解决什么问题

项目里已经有 classic Agent，也已经有 LangGraph 旁路 runtime。V4 不是重新接入 LangGraph，而是解决一个更工程化的问题：

```text
一个新 runtime 要怎样证明自己足够稳定，才能慢慢进入主链路？
```

答案是三件事：

- shadow compare：先后台对比，不直接影响用户。
- runtime quality gate：质量门禁不过就不展示。
- fallback classic：新链路异常时退回旧链路。

## 2. 为什么不直接替换主链路

面试主链路不只负责生成一句问题，还串着 RAG 检索、Agent 决策、历史记录、报告、训练任务、前端展示和后台日志。

直接替换的风险是：LangGraph 某一轮输出异常，就可能影响真实用户的完整面试体验。

所以更稳的路线是：

```text
classic Agent 继续服务用户
LangGraph 在 shadow 模式运行
系统记录两边差异
质量稳定后再考虑灰度迁移
```

## 3. shadow compare 是什么

shadow compare 的意思是：同一份 Agent State 同时给 classic Agent 和 LangGraph runtime 使用。

用户看到 classic Agent 的问题，后台记录 LangGraph 生成的问题和决策。

系统会比较：

- nextAction 是否一致。
- difficulty 是否一致。
- question 是否接近。
- LangGraph 是否触发 human review。
- LangGraph 是否缺少 checkpoint。
- LangGraph 是否需要 fallback。

## 4. runtime quality gate 是什么

quality gate 是一道门禁。LangGraph 结果想进入用户可见链路，必须先通过检查。

典型检查包括：

- 问题不能为空。
- 问题不能和最近几轮高度重复。
- nextAction 必须合法。
- difficulty 必须合法。
- checkpoint summary 必须存在。
- requiresHumanReview=true 时不能直接展示。

## 5. checkpoint summary 和完整 graph state 的区别

checkpoint summary 是项目侧用于观察和调试的摘要。

它记录：

- threadId。
- runtime。
- status。
- currentNode。
- lastAction。
- lastQuestion。
- qualityGate。
- comparisonSummary。

完整 graph state 是 LangGraph 内部用于恢复执行状态的数据。V4 先做 summary 持久化，不承诺完整 graph state 生产级恢复。

## 6. 面试时怎么讲

可以这样表达：

```text
我的项目没有为了写 LangGraph 而强行替换原有 Agent 主链路。我采用了渐进迁移：classic Agent 保持稳定可见链路，LangGraph 先作为 shadow runtime 跑同一份状态。

系统会比较两条链路的 action、difficulty、question 和 checkpoint，并用 quality gate 判断 LangGraph 输出是否可见。如果 LangGraph 输出为空、重复、非法或需要人工复核，就 fallback classic。

这种设计体现的是 Agent 工程化治理能力，而不是简单框架接入。
```
