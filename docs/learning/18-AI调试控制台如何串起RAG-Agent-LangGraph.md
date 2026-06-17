# AI 调试控制台如何串起 RAG、Agent 和 LangGraph

## 1. 为什么 AI 应用需要可观测性

普通后端接口如果出错，通常可以看请求参数、数据库记录、异常堆栈。

AI 应用更复杂，因为一次输出往往由多段链路共同决定：

```text
用户输入
-> RAG 检索资料
-> Agent 判断当前状态
-> 大模型生成决策或问题
-> 兜底规则修正不稳定输出
-> 前端展示给用户
```

如果只看最终问题，就很难判断问题出在哪里。

AI Debug Console 的作用是把这条链路拆开，让开发者能看到：

- RAG 有没有找到资料。
- Agent 为什么选择深挖、降难度、切话题或结束。
- fallback 是否触发。
- LangGraph 旁路有没有 checkpoint。
- 如果结果不好，应该补知识库、改策略，还是检查模型输出格式。

## 2. 一次面试问题生成链路

在当前项目里，一次面试提问大致可以理解成：

```text
候选人档案 + 岗位 JD + 历史问答
-> 三类 RAG 召回
-> RAG 质量摘要
-> Agent State
-> Agent Policy
-> Agent Decision
-> 问题生成
-> Agent / RAG / LangGraph 调试信息
```

管理员后台的 AI 调试控制台就是把这些信息聚合到一个页面。

它不是为了给普通用户看热闹，而是给开发者和管理员排查问题。

## 3. RAG 调试看什么

RAG 调试重点不是“有没有用了向量数据库”，而是看召回是否真的有效。

常见字段：

- `retrieverName`：是哪类知识库，比如岗位知识库、题库、候选人画像。
- `queryText`：本次检索用了什么问题。
- `hitCount`：命中了几条资料。
- `qualityLevel`：召回质量大致是 good、weak 还是 miss。
- `topHits`：前几条命中的资料摘要。

如果岗位知识库为空召回，说明系统没有找到岗位相关资料。

如果题库弱召回，说明系统可能需要补充题库样例、优化 chunk 标题，或者调整 query rewrite。

## 4. Agent 调试看什么

Agent 调试重点是看“它为什么这样决策”。

当前系统关注：

- `nextAction`：下一步动作。
- `difficulty`：下一题难度。
- `focus`：下一题关注点。
- `reason`：决策原因。
- `fallbackUsed`：是否启用了兜底规则。
- `policyReasons`：策略层判断原因。
- `triggerRules`：触发了哪些规则。

举例：

```text
如果用户连续答不上来，Agent 不应该一直死磕同一个问题。
更合理的策略是先降低难度，再切换到基础解释或新话题。
```

这就是 Agent 和普通 LLM 调用的区别：

```text
普通 LLM 更像一次性回答。
Agent 会观察状态、读取工具结果、应用策略，再决定下一步动作。
```

## 5. LangGraph checkpoint 看什么

当前项目里，LangGraph 仍然是旁路验证链路，不是主面试流程。

这点很重要。

AI Debug Console 会展示：

- `threadId`：同一条图工作流的线程标识。
- `exists`：是否存在 checkpoint。
- `roundCount`：图状态里记录的轮次。
- `lastAction`：上一次动作。
- `nodeTraceCount`：节点轨迹数量。
- `explanation`：当前请求是否启用了 LangGraph 旁路。

如果没有 checkpoint，不代表系统坏了。

它只说明：

```text
本次请求可能仍由 classic Agent 主流程处理，没有走 LangGraph 旁路。
```

## 6. 面试时怎么讲

可以这样说：

```text
我在项目里做了 AI Debug Console，用来解决 AI 应用黑箱问题。一次面试问题生成不是只看最终模型输出，而是把三类 RAG 召回、RAG 质量摘要、Agent State、Agent Policy、Agent Decision、fallback 状态、LangGraph nodeTrace 和 checkpoint 摘要串起来展示。
```

继续展开：

```text
如果系统问得不好，我可以通过后台判断是 RAG 没召回、召回质量弱、Agent 策略误判、模型 decision JSON 不稳定，还是 LangGraph 旁路没有 checkpoint。这样项目就不只是一个 demo，而是具备可观测性和调试闭环的 AI 应用工程。
```

如果面试官问为什么不直接把主流程切成 LangGraph：

```text
我没有直接替换主流程，因为主流程已经承载真实面试、历史记录、训练任务和报告生成。直接替换风险太高。所以我先把 LangGraph 做成旁路工作流，接真实 RAG、真实 Agent Decision 和 checkpoint，验证稳定后再考虑 agentRuntime=classic/langgraph 的灰度切换。
```
