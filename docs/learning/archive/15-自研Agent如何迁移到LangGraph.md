# 15 自研 Agent 如何迁移到 LangGraph

## 1. 为什么本阶段不直接引入 LangGraph

当前项目已经有自研的 Interview Orchestrator Agent。

它已经包含：

```text
Agent State
ToolCalls
Agent Decision
fallback
normalize
guardrail
nodeTrace
coach / interview 模式
训练任务信号
RAG 命中质量摘要
```

这说明项目已经不是简单的 LLM 调用。

但本阶段不直接引入 LangGraph，原因是：

- 当前训练任务系统刚接入 Agent，还在稳定字段。
- 管理员后台刚完成 MVP，还没有复杂人工审核流。
- 直接上框架会扩大改动面，影响 `/api/interview/next-question` 兼容性。
- 你现在最需要先讲清 Agent 底层逻辑，而不是只会说“用了 LangGraph”。

更合理的路线是：

```text
先稳定自研 Agent 的状态、节点、日志和测试。
再把这些稳定概念迁移成 LangGraph 的 StateGraph。
```

## 2. 当前自研 Agent 已经有哪些 LangGraph 雏形

当前自研 Agent 的流程已经接近状态图：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_weakness_strategy
-> select_training_template
-> select_action
-> generate_question
-> update_memory
```

这些节点现在还不是 LangGraph node，但已经被 `nodeTrace` 显式记录。

这很重要，因为迁移框架前，先把“节点边界”想清楚，后面才不会把所有逻辑塞进一个巨大 node。

## 3. 当前模块到 LangGraph 概念的映射

| 当前自研模块 | LangGraph 迁移概念 | 说明 |
| --- | --- | --- |
| `agent_state` 字典 | Graph State | 保存 profile、history、RAG hits、answerAnalysis、trainingTasks、decision |
| `observe_state` | node | 观察当前轮次、历史问答、剩余轮数 |
| `analyze_answer` | node | 判断上一轮回答质量、连续弱回答、重复问题 |
| `retrieve_context` | tool node | 调用岗位知识库、题库、候选人画像三类 RAG |
| `select_weakness_strategy` | node | 根据 weakTags 和候选人画像选择训练策略 |
| `select_training_template` | node | 根据薄弱点匹配训练模板 |
| `select_action` | decision node | 决定 deepen、lower_difficulty、switch_topic、finish 等动作 |
| `generate_question` | node | 生成下一道面试题 |
| `update_memory` | node | 更新长期画像或训练记忆 |
| `nextAction` | conditional edge | 根据动作决定下一条边 |
| `AgentDecisionLog` | checkpoint/trace 过渡形态 | 当前先用数据库日志记录状态与决策 |
| `nodeTrace` | execution trace | 记录每个节点输入摘要、输出摘要和兜底情况 |

## 4. LangGraph checkpoint 对咱们有什么价值

根据 LangGraph 官方 persistence 文档，LangGraph 的持久化层会把 graph state 保存为 checkpoints；checkpoint 能支持 human-in-the-loop、memory、time travel debugging 和 fault-tolerant execution。

迁移到本项目里，对应价值是：

```text
多轮面试状态恢复：
  用户刷新页面或服务重启后，可以从某个 thread_id 恢复面试状态。

Agent 决策路径调试：
  可以查看每一步 graph state，排查为什么选择降难度、深挖或切换话题。

失败恢复：
  如果 RAG 检索或问题生成节点失败，可以从上一个 checkpoint 恢复，不必重跑全部流程。

时间旅行调试：
  可以回到某一轮面试状态，尝试不同 nextAction 或不同提示词。
```

当前项目里的 `AgentDecisionLog` 只能算 checkpoint 的过渡形态。

它能记录：

```text
state_json
decision_json
nodeTrace
fallbackUsed
guardrailApplied
```

但它不能真正恢复 graph execution。

## 5. Human-in-the-loop 可以怎么接入

根据 LangGraph interrupts 文档，interrupt 可以让 graph 在某个节点暂停，保存当前状态，等待外部输入后再恢复。

咱们项目里后续可以这样用：

```text
场景 1：管理员审核高风险面试报告
generate_report -> interrupt(review_report) -> admin_approve_or_edit -> save_report

场景 2：管理员审核新增知识库文档
parse_document -> split_chunks -> interrupt(review_chunks) -> embed_and_index

场景 3：面试官人工接管
select_action -> interrupt(review_next_action) -> generate_question
```

这类能力现在不做，是因为当前项目还没有人工审核产品入口。

但是文档上先把迁移点设计出来，后续加管理员审核功能时就不会乱。

## 6. 最小 LangGraph POC 范围

后续第一版 LangGraph POC 不应该迁移整个项目。

建议只迁移下一题 Agent 的核心链路：

```text
START
-> observe_state
-> retrieve_context
-> analyze_answer
-> select_action
-> generate_question
-> END
```

先不迁移：

```text
报告生成
训练任务完成
管理员后台
知识库文档入库
复杂 human-in-the-loop
```

原因是：

```text
POC 的目的不是一次性替换整个系统，而是验证自研 Agent 节点能否稳定映射成 LangGraph nodes。
```

## 7. 未来迁移步骤

建议分四步：

```text
第一步：定义 Graph State 类型
```

字段包括：

```text
profile
history
nextStage
agentMode
roleHits
questionHits
memoryHits
candidateTrainingTasks
answerAnalysis
decision
nodeTrace
```

```text
第二步：把当前函数拆成 LangGraph nodes
```

例如：

```text
observe_state_node
retrieve_context_node
analyze_answer_node
select_action_node
generate_question_node
```

```text
第三步：把 nextAction 变成 conditional edge
```

例如：

```text
deepen -> generate_question
lower_difficulty -> generate_question
switch_topic -> generate_question
finish -> END
```

```text
第四步：接入 checkpointer
```

本地 POC 可以先用内存或 SQLite。

产品化时可以考虑 Postgres 或 Redis 相关持久化方案，但这属于部署和生产化阶段，不在本轮实现。

## 8. 面试时怎么讲

可以这样表达：

```text
这个项目当前没有直接引入 LangGraph，而是先实现了自研轻量 Orchestrator。它已经具备 Agent State、ToolCalls、Agent Decision、fallback、guardrail、nodeTrace 和训练任务信号。我的设计思路是先把 Agent 的节点边界和日志可观测性做稳定，再把 observe_state、retrieve_context、analyze_answer、select_action、generate_question 这些节点迁移成 LangGraph StateGraph nodes。后续可以把 nextAction 映射为 conditional edge，用 checkpoint 支持多轮面试状态恢复和故障恢复，用 interrupt 支持管理员审核或人工接管。
```

如果面试官问“为什么不用 LangGraph”，可以回答：

```text
我不是不用，而是当前阶段先保证底层状态、工具调用和决策链路可控。直接引入框架会让项目看起来高级，但如果讲不清 state、node、edge、checkpoint，反而容易被深挖露怯。所以我先做自研 V1，再预留 LangGraph 迁移路径。
```

## 9. 当前边界

当前没有安装：

```text
LangGraph
LangChain
```

当前没有真实实现：

```text
checkpoint
thread_id
interrupt
human-in-the-loop
graph resume
time travel debugging
```

它们属于后续 POC 或上线后工程化阶段。

## 10. 参考资料

- LangGraph Persistence 官方文档：`https://docs.langchain.com/oss/python/langgraph/persistence`
- LangGraph Interrupts 官方文档：`https://docs.langchain.com/oss/python/langgraph/human-in-the-loop`
