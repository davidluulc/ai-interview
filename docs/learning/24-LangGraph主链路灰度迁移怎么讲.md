# LangGraph 主链路灰度迁移怎么讲

更新时间：2026-06-14

## 1. 这一阶段到底做了什么

这一阶段不是“又接了一次 LangGraph”，而是把 LangGraph 从旁路实验推进到可灰度的候选主链路。

项目里现在有三种链路：

```text
classic：稳定主链路，默认给所有用户使用。
shadow：用户仍然看到 classic，后台同时跑 LangGraph 做对比。
langgraph_canary：管理员或实验账号可以让 LangGraph 小范围成为可见链路。
```

重点是：LangGraph 即使进入 canary，也不是无条件接管。它必须先通过 quality gate。

## 2. 为什么不能直接全量切 LangGraph

面试系统的主链路不只是生成一句问题。

它还串着：

- 简历档案。
- 岗位 JD。
- 三类 RAG。
- Agent State。
- Agent Decision。
- 历史记录。
- 面试报告。
- 训练任务。
- 管理员后台日志。

如果直接全量替换，一旦 LangGraph 某一轮输出空问题、重复问题或非法决策，真实用户体验就会受影响。

所以更稳的生产路线是：

```text
默认 classic
-> shadow 后台对比
-> canary 小范围可见
-> quality gate 门禁
-> fallback classic 回退
-> runtime audit 审计
```

## 3. runtime policy 是什么

`runtime policy` 负责回答：

```text
这次请求有没有资格使用 LangGraph？
```

它会看：

- 用户请求的是 classic、shadow 还是 langgraph_canary。
- 当前用户是不是管理员。
- 当前是 coach 还是 interview 模式。
- runtime 名称是否合法。

普通用户请求 `langgraph_canary` 时，系统不会报错，而是降级成 classic，并记录原因：

```text
普通用户暂不开放 LangGraph 灰度链路。
```

管理员请求 `langgraph_canary` 时，系统允许进入 LangGraph 灰度链路。

## 4. quality gate 是什么

`quality gate` 是 LangGraph 输出进入用户可见链路前的门禁。

典型检查包括：

- 问题不能为空。
- 问题不能和最近几轮高度重复。
- `nextAction` 必须合法。
- `difficulty` 必须合法。
- checkpoint summary 必须存在。
- 如果需要人工复核，则不能直接展示给用户。

如果门禁不通过，本轮问题不会展示 LangGraph 结果，而是 fallback 到 classic。

## 5. runtime audit 是什么

`runtime audit` 是运行审计记录。

它记录：

```text
requestedRuntime：用户或前端请求的链路。
allowedRuntime：策略层允许的链路。
visibleRuntime：最终展示给用户的链路。
fallbackUsed：是否发生回退。
policyReasons：策略层为什么这样决定。
qualityGateReasons：质量门禁为什么拦截。
```

这样管理员后台就不再只能看一坨 JSON，而是可以直接看懂：

```text
这次本来想用 LangGraph。
系统允许了。
但质量门禁没过。
所以最终回退到了 classic。
```

## 6. 面试时怎么讲

可以这样说：

```text
我的项目里 classic Agent 是默认稳定主链路，LangGraph 不是一接入就全量替换，而是采用渐进式迁移。

第一步是 shadow compare，用户仍然看到 classic，后台同时跑 LangGraph 并比较 action、difficulty、question 和 checkpoint。

第二步是 canary 灰度，管理员或实验账号可以请求 langgraph_canary。系统会先根据 runtime policy 判断是否允许，再运行 LangGraph，并用 quality gate 检查输出质量。如果 LangGraph 输出为空、重复、非法或需要人工复核，就 fallback 到 classic。

同时系统会记录 runtime audit，包括请求链路、允许链路、最终可见链路、回退状态和原因。这样既能体现 LangGraph 的工作流能力，又能保证主面试体验稳定。
```

## 7. 面试官可能追问

### 为什么不用 LangGraph 直接重写所有 Agent？

可以回答：

```text
因为 LangGraph 是工作流编排框架，不是质量保证本身。核心业务链路迁移要考虑稳定性、回退、审计和用户体验。我先保留 classic 稳定主链路，再让 LangGraph 通过 shadow 和 canary 逐步验证，这更接近生产系统迁移方式。
```

### canary 和 shadow 有什么区别？

可以回答：

```text
shadow 不影响用户，用户看到的仍然是 classic，只在后台对比 LangGraph。
canary 是小范围可见，LangGraph 有机会生成用户看到的问题，但必须先通过 quality gate，失败就回退 classic。
```

### runtime audit 有什么价值？

可以回答：

```text
runtime audit 让 Agent 决策链路可观测。它能说明本轮请求的 runtime、策略允许的 runtime、最终展示的 runtime、是否 fallback，以及为什么 fallback。这样排查问题时不会只凭感觉。
```
