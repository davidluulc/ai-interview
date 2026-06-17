# LangGraph 工作流治理如何理解 checkpoint、interrupt 和 runtime

## 1. 这阶段到底在做什么

本阶段不是重复接入 LangGraph，而是把 LangGraph 从旁路实验升级为可治理的 Agent Runtime。

以前我们已经证明：

```text
LangGraph 图能跑
节点能串起来
三类 RAG 能接入
Agent Policy 能复用
checkpoint 摘要能查询
```

但企业级 AI 应用不能只停留在“能跑”。它还需要回答：

```text
中途失败能不能恢复？
关键决策能不能暂停等待人工确认？
新 runtime 能不能灰度，不影响稳定主流程？
一次提问为什么这样走，后台能不能看清楚？
```

所以本阶段做的是 Agent 工作流治理。

## 2. thread_id 是什么

`thread_id` 是一场 LangGraph 工作流的会话编号。

你可以把它理解成：

```text
同一场实验面试的状态编号
同一次 Agent 调试运行的编号
同一条可恢复工作流的主键
```

如果没有 `thread_id`，系统就不知道当前 checkpoint 属于哪一场工作流。  
如果 resume 时换了 `thread_id`，系统也无法恢复到原来的状态。

面试时可以这样讲：

```text
thread_id 是 LangGraph 多轮状态恢复的关键标识。它让 checkpointer 知道应该保存和恢复哪一条 graph state。
```

## 3. checkpoint 和普通日志有什么区别

日志主要回答：

```text
发生了什么？
什么时候发生？
当时输入和输出是什么？
```

checkpoint 还要回答：

```text
当前图执行到哪里？
当前 graph state 是什么？
如果暂停了，后面能不能从这里继续？
```

所以日志偏可观测，checkpoint 偏状态恢复。

在本项目里：

```text
AgentDecisionLog：记录 Agent 为什么这样决策
RagRetrievalLog：记录 RAG 召回了什么
checkpointSummary：记录 LangGraph runtime 当前状态摘要
```

三者不是互相替代关系，而是一起构成 AI Debug Console 的调试链路。

## 4. interrupt / resume 为什么需要 checkpoint

interrupt 表示图执行到某个节点时暂停。

例如：

```text
候选人连续三轮回答“不会”
Agent Policy 判断继续深挖没有意义
Human Review Policy 建议暂停
系统返回 interrupted 状态，让管理员或后续流程选择下一步
```

如果没有 checkpoint，暂停之后系统就丢失了：

```text
暂停前执行到哪个节点
上一轮 Agent Decision 是什么
当前候选人状态是什么
下一步可选动作是什么
```

所以 resume 必须依赖同一个 `thread_id` 找回 checkpoint。  
这就是为什么 LangGraph 官方文档会把 persistence、checkpoint 和 human-in-the-loop 放在一起讲。

## 5. classic / langgraph / shadow 三种 runtime

本项目设计了三种 runtime：

```text
classic
继续使用当前稳定的自研 Agent 主流程。

langgraph
使用 LangGraph 实验工作流。

shadow
用户仍然看到 classic 结果，但后台同时跑 LangGraph，方便对比两条链路。
```

为什么不直接把主流程替换成 LangGraph？

因为当前 classic Agent 已经承担真实面试流程。直接替换会同时影响：

```text
提问质量
RAG 召回
历史记录
训练闭环
前端展示
用户体验
```

所以更稳妥的工程方案是：

```text
classic 保稳定
langgraph 做实验
shadow 做对比
AI Debug Console 做观察
```

## 6. Human Review Policy 是什么

Human Review Policy 是“什么时候需要人工介入”的规则层。

它不是让大模型自己决定是否暂停，而是用可测试规则判断，例如：

```text
Agent Policy 明确 requiresHumanReview=true
候选人连续三轮弱回答
候选人连续空回答
```

这样做的好处是：

```text
规则稳定
方便测试
方便解释
方便进入 AI Debug Console
```

面试时可以这样讲：

```text
我没有把是否人工介入完全交给大模型，而是抽出了 Human Review Policy，用规则判断 interrupt 条件，避免 Agent 决策变成黑箱。
```

## 7. AI Debug Console 在这里起什么作用

AI Debug Console 不是普通后台页面，它的作用是把一次 AI 提问拆成可观察链路：

```text
RAG 召回了什么
Agent 做了什么决策
LangGraph runtime 是 classic、langgraph 还是 shadow
当前状态是 completed 还是 interrupted
当前节点是不是 human_review
是否需要人工介入
resume 时选择了什么
```

这样当系统问得不好时，可以判断问题来自哪里：

```text
知识库没召回 -> 补 RAG 文档
Agent Policy 判断不合理 -> 改策略
LangGraph 状态没保存 -> 查 checkpoint
连续弱回答还在深挖 -> 查 Human Review Policy
```

## 8. 面试时怎么讲

可以这样讲：

```text
我在项目里没有直接把稳定的自研 Agent 主流程替换成 LangGraph，而是采用 runtime governance 的方式渐进接入。
classic Agent 继续承载稳定流程，LangGraph 先作为实验 runtime 和 shadow runtime。
我实现了 checkpoint summary、Human Review Policy、interrupt/resume 实验接口和 AI Debug Console 展示。
这样既保证主流程稳定，又能证明 Agent 工作流具备状态恢复、人工介入、灰度切换和可观测能力。
```

如果面试官追问“checkpoint 和日志有什么区别”，可以答：

```text
日志是事后观察，checkpoint 是状态恢复。日志能告诉我发生了什么，checkpoint 还能支持从某个 thread 的 graph state 继续执行。
```

如果面试官追问“为什么需要 shadow runtime”，可以答：

```text
因为不能直接把稳定主流程替换掉。shadow 模式让用户继续拿到 classic Agent 的稳定结果，同时后台跑 LangGraph 做对比，降低迁移风险。
```

