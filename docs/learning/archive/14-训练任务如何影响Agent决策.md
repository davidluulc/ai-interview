# 14 训练任务如何影响 Agent 决策

## 1. 为什么要让 Agent 读取训练任务

前面训练中心已经把报告里的 `weakTags` 变成了 `TrainingTask`。

但如果训练任务只停留在页面上，Agent 仍然不知道用户长期薄弱点。

所以阶段 5 做的是：

```text
TrainingTask -> candidateTrainingTasks -> Agent State -> Agent Decision -> 下一题生成
```

这让系统从“单轮面试”继续升级为“带长期训练记忆的面试训练系统”。

## 2. 训练任务不是替代 RAG

当前系统已经有三类 RAG：

```text
岗位知识库 RAG
题库 RAG
候选人画像 RAG
```

训练任务进入 Agent 后，不是第四个 RAG，也不是替代 RAG。

它的定位是：

```text
个性化训练信号。
```

也就是说：

- RAG 负责提供外部资料和上下文。
- 历史问答负责提供当前对话状态。
- Agent State 负责打包当前局面。
- TrainingTask 负责告诉 Agent 用户长期薄弱点和掌握度。

## 3. candidateTrainingTasks 是什么

`candidateTrainingTasks` 是给 Agent 看的候选训练任务列表。

当前筛选规则是：

```text
只取当前用户自己的任务。
只取 todo / in_progress 状态。
优先 high priority。
优先 masteryScore 更低的任务。
最多取 3 条。
如果传入 applicationProfileId，则优先当前档案或全局任务。
```

这样可以避免把所有训练任务都塞给模型，导致 prompt 过长或重点不清楚。

## 4. selectedTrainingTask 是什么

`selectedTrainingTask` 是当前轮 Agent 选中的一个训练任务。

当前规则是：

```text
coach 模式：
  high 优先级，并且 masteryScore < 60，则优先作为拆小训练信号。

interview 模式：
  masteryScore < 80，则作为真实面试追问参考。
```

这体现了两个模式的差异：

```text
coach：更像老师，优先补薄弱点。
interview：更像面试官，保持压力，但会参考未稳定掌握的内容。
```

## 5. 代码位置

训练任务筛选逻辑：

```text
backend_python/training_tasks.py
```

关键函数：

```text
list_candidate_training_tasks
select_agent_training_task
```

面试下一题接入位置：

```text
backend_python/routes/interview.py
```

关键逻辑：

```text
读取候选训练任务
选择一个当前轮参考任务
写入 agent_state["candidateTrainingTasks"]
写入 agent_decision["selectedTrainingTask"]
把 candidateTrainingTasks 传给下一题生成模型
```

## 6. 为什么不直接让模型自己选任务

可以让模型选，但第一版没有这么做。

原因是：

- 规则更稳定。
- 测试更容易写。
- 选择逻辑可解释。
- 不会因为模型波动导致每次选择不同任务。
- 面试时更容易讲清楚。

当前做法是：

```text
后端规则先选出候选任务和推荐任务。
LLM 在生成下一题时参考这些信号。
```

这是一种工程上更稳的做法。

## 7. 日志里能看到什么

Agent 决策日志现在能看到：

```json
{
  "candidateTrainingTasks": [
    {
      "weakTag": "rag_quality",
      "title": "RAG 质量评估专项训练",
      "priority": "high",
      "masteryScore": 45
    }
  ]
}
```

以及：

```json
{
  "selectedTrainingTask": {
    "weakTag": "rag_quality",
    "priority": "high",
    "masteryScore": 45,
    "reason": "训练任务显示该薄弱点优先级高且掌握度偏低，coach 模式先拆小训练。"
  }
}
```

这能帮助排查：

```text
Agent 为什么又问 RAG 质量评估？
为什么这一轮降低难度？
为什么 coach 模式会围绕某个薄弱点继续训练？
```

## 8. 面试时怎么讲

可以这样表达：

```text
我把训练中心里的 TrainingTask 接入到了下一题 Agent 流程中。后端会从当前用户的 todo 和 in_progress 任务里筛选高优先级、低掌握度任务，写入 Agent State 的 candidateTrainingTasks。同时根据 coach/interview 模式选择一个 selectedTrainingTask，作为下一轮提问的个性化决策信号。这样 Agent 不只看当前回答和 RAG 命中，还能参考用户长期薄弱点。但它只是辅助信号，不会替代岗位知识库 RAG、题库 RAG 和候选人画像 RAG。
```

如果面试官问“这算不算 Agent”，可以回答：

```text
它不是简单 LLM 一问一答。系统会先观察当前状态，包括历史问答、RAG 命中、回答质量、训练任务，再通过规则和模型共同生成 Agent Decision，最后由问题生成模型生成下一题。训练任务的接入增强了 Agent 的长期状态感知和个性化决策能力。
```
