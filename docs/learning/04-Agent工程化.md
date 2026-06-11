# Agent 工程化

## Agent 和普通 LLM 调用的区别

普通 LLM 调用通常是：

```text
输入 prompt
-> 模型生成回答
```

Agent 多了一层状态观察和决策：

```text
观察当前状态
-> 调用工具
-> 分析用户回答
-> 选择下一步动作
-> 生成问题或建议
-> 更新记忆和日志
```

## 当前 Agent 节点

项目里已经拆出这些概念：

- `observe_state`
- `retrieve_context`
- `analyze_answer`
- `select_action`
- `generate_question`
- `update_memory`

虽然目前不是 LangGraph，但已经具备迁移到状态图的结构。

## Agent State

Agent State 里包含：

- profile；
- history；
- 当前轮次；
- 剩余轮次；
- 上一轮问答；
- 三个 RAG hits；
- retrievalQuality；
- answerAnalysis；
- weaknessStrategy；
- trainingTemplateHint。

它的作用是约束模型：

```text
不要凭空问
要根据当前状态和资料问
```

## Agent Decision

Agent Decision 决定下一步动作：

- deepen：继续深挖；
- simplify：降低难度；
- shift_topic：切换话题；
- coach_explain：学习辅导；
- finish：结束。

决策会被 normalize 和 fallback 兜底，避免模型输出非法 JSON 或不可用 action。

## 日志

Agent 日志记录：

- state_json；
- decision_json；
- next_action；
- stage；
- difficulty；
- focus；
- reason；
- fallback_used；
- nodeTrace；
- toolCalls。

这能解释：

```text
为什么下一题这么问
系统用了哪些资料
有没有触发兜底
```

## LangGraph 迁移方向

后续可以把当前自研 Agent 映射为 LangGraph nodes：

```text
observe_state -> retrieve_context -> analyze_answer -> select_action -> generate_question -> update_memory
```

LangGraph 的 checkpoint 可以用于：

- 多轮状态恢复；
- human-in-the-loop；
- 调试决策路径；
- 失败重试。

## 面试表达

```text
我的 Agent 不是简单套 prompt。
它会先构造 Agent State，把用户档案、历史问答、三个 RAG 命中、回答质量和薄弱点放进去。
然后 Agent Decision 决定下一步是深挖、降难度、切话题还是辅导解释。
决策结果会经过 normalize 和 fallback 兜底，并写入 Agent 日志。
这样系统既能动态追问，也能解释为什么这么问。
```

