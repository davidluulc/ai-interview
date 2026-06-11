# 08 weakTag 训练模板如何让 Agent 更会训练

## 1. 本阶段解决什么问题

上一阶段系统已经能识别候选人的长期薄弱点。

例如用户多次在 RAG 质量评估相关问题上回答不好，历史报告会沉淀出：

```json
{
  "frequentWeakTags": ["rag_quality"]
}
```

Agent 也已经能把这个薄弱点转成 `weaknessStrategy`，决定本轮要不要围绕这个点训练。

但这还不够。

因为系统只知道：

```text
用户在 rag_quality 上薄弱。
```

还不等于系统知道：

```text
rag_quality 应该怎么练？
从什么难度开始？
coach 模式怎么问？
interview 模式怎么追问？
回答时应该覆盖哪些要点？
常见错误是什么？
```

本阶段新增的 `weakTag 训练模板系统` 就是为了解决这个问题。

## 2. 三个核心概念

### 2.1 weakTag

`weakTag` 回答的是：

```text
候选人哪里弱？
```

例如：

```text
rag_quality
rag_retrieval
agent_state
backend_fastapi
database_modeling
project_storytelling
```

它是一个稳定标签，便于系统统计、检索和策略判断。

### 2.2 weaknessStrategy

`weaknessStrategy` 回答的是：

```text
本轮要不要围绕这个弱点训练？
用 coach 方式补基础，还是用 interview 方式真实追问？
```

例如：

```json
{
  "enabled": true,
  "primaryWeakTag": "rag_quality",
  "primaryWeakLabel": "RAG 质量评估",
  "modePolicy": "coach_remediation",
  "recommendedDifficulty": "basic"
}
```

### 2.3 trainingTemplateHint

`trainingTemplateHint` 回答的是：

```text
这个弱点本轮具体怎么练？
```

例如：

```json
{
  "enabled": true,
  "weakTag": "rag_quality",
  "label": "RAG 质量评估",
  "mode": "coach",
  "difficulty": "basic",
  "recommendedQuestion": "Hit@K、MRR、关键词覆盖率分别解决什么问题？",
  "answerKeyPoints": ["Hit@K", "MRR", "关键词覆盖率", "空召回率", "metadata 匹配率"],
  "commonMistakes": ["只解释字段名，不解释指标用途"]
}
```

这三个概念的关系是：

```text
weakTag：哪里弱
-> weaknessStrategy：本轮是否围绕它训练，以及采取什么策略
-> trainingTemplateHint：具体问什么、看什么、避免什么
```

## 3. 为什么训练模板不是题库 RAG

训练模板和题库 RAG 容易混淆，但它们职责不同。

题库 RAG 解决的是：

```text
这个岗位、这个阶段，真实面试里可能会问哪些题？
```

训练模板解决的是：

```text
这个候选人的长期薄弱点应该怎么训练？
```

题库 RAG 更偏资料召回，训练模板更偏训练策略。

生成下一题时，两者应该同时存在：

```text
题库 RAG 保证问题像真实面试。
训练模板保证问题能补候选人的薄弱点。
```

所以训练模板不是第四个 RAG，也不是替代题库。

## 4. coach 和 interview 怎么使用模板

### 4.1 coach 模式

coach 模式是学习辅导。

当用户在 `rag_quality` 上薄弱时，系统会优先选择基础训练问题：

```text
Hit@K、MRR、关键词覆盖率分别解决什么问题？
```

目标不是压迫用户，而是帮用户拆小问题、补概念、建立回答框架。

### 4.2 interview 模式

interview 模式是真实面试。

同样是 `rag_quality`，问题会更像面试官追问：

```text
如果你说项目里做了 RAG 质量评估，请说清 Hit@K 和 MRR 分别怎么计算。
```

目标是验证候选人是不是真的理解项目，而不是只会背词。

## 5. 本阶段代码链路

本阶段新增了：

```text
backend_python/weakness_training_templates.py
```

它负责：

- 定义 6 个核心 weakTag 的训练模板。
- 提供 `get_training_template()`。
- 提供 `select_training_template_hint()`。

Agent 链路现在变成：

```text
candidateProfile.frequentWeakTags
-> weaknessStrategy
-> trainingTemplateHint
-> Agent Decision
-> questionStrategy
-> 下一题生成
```

`nodeTrace` 中新增：

```text
select_training_template
```

完整节点顺序变成：

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

这说明系统是先选择薄弱点，再选择训练方式，最后才生成下一题。

## 6. 为什么这能提升问题稳定性

没有训练模板时，大模型虽然知道 `rag_quality`，但可能每次自由发挥：

```text
请写一条 RAG JSON。
quality 怎么算？
Hit@K 是什么？
再写一条日志。
```

有模板后，系统会给模型更稳定的约束：

```text
本轮弱点是 RAG 质量评估。
当前模式是 coach。
当前难度是 basic。
推荐问题是 Hit@K、MRR、关键词覆盖率分别解决什么问题。
答题要点包括 Hit@K、MRR、关键词覆盖率、空召回率、metadata 匹配率。
常见错误是只解释字段名，不解释指标用途。
```

这样问题生成会更贴近训练目标。

## 7. 面试时怎么讲

可以这样讲：

> 我在训练闭环里不只做了 weakTags 识别，还做了 weakTag 到训练模板的映射。比如用户多次在 rag_quality 上薄弱，系统不会只记一个标签，而是会找到 RAG 质量评估模板。这个模板里包含 coach 模式的问题、interview 模式的问题、从基础到进阶的训练阶梯、答题要点和常见错误。下一轮 Agent 生成问题时，会先根据候选人画像选出 weaknessStrategy，再根据 weakTag 选择 trainingTemplateHint。这样问题生成不完全依赖模型自由发挥，而是被稳定的训练目标约束。同时模板摘要会写入 Agent Decision、questionStrategy 和 nodeTrace，方便解释为什么这一轮这样训练。

如果面试官问“这和题库 RAG 有什么区别”，可以这样答：

> 题库 RAG 解决的是岗位和面试阶段下应该参考哪些真实问题，weakTag 训练模板解决的是某个候选人的长期薄弱点应该如何训练。前者偏资料召回，后者偏训练策略。生成下一题时，我会同时参考题库 RAG 和训练模板：题库保证问题像真实面试，模板保证问题能补用户薄弱点。

如果面试官问“为什么不直接让大模型自己想怎么练”，可以这样答：

> 因为大模型自由生成不稳定，容易重复追问或偏离训练目标。我把常见 weakTag 抽象成训练模板，让关键训练目标、难度阶梯、答题要点和常见错误都结构化，再交给模型生成自然语言问题。这样既保留模型表达自然的优势，又让训练策略可控、可测、可观察。

## 8. 当前边界

本阶段没有做：

- 训练任务表。
- 掌握度评分。
- 前端专项训练页面。
- 模板后台管理。
- LangGraph 状态图迁移。
- Docker / Nginx / 云服务器上线。

这些可以作为后续扩展。

当前阶段的核心目标是：

```text
让 Agent 不只知道用户哪里弱，还知道这个弱点该怎么练。
```
