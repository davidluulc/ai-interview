# 02 RAG 质量评估指标：Hit@K、MRR、关键词覆盖率

## 1. 为什么 RAG 需要质量评估

RAG 的核心问题不是“有没有搜到东西”，而是“搜到的东西是否真的有用”。

如果没有评估指标，开发者只能凭感觉判断：

```text
这次好像搜得还行。
```

这在真实项目里是不够的。工程化 RAG 需要固定 evaluation case 和稳定指标，让每次改 query、chunk、metadata、BM25、向量检索或 rerank 后，都能知道召回质量有没有变好。

## 2. Hit@K

Hit@K 表示：

```text
前 K 条召回结果里，是否命中了预期资料。
```

如果 K=5，前 5 条里出现了预期资料，Hit@K 就是 1；否则是 0。

它回答的问题是：

```text
检索有没有找对方向？
```

在 AI 模拟面试系统里，如果用户问 RAG 质量评估，但前几条都没有命中 RAG 指标相关资料，说明面试官后续提问可能没有依据。

## 3. MRR

MRR 是 Mean Reciprocal Rank，关注正确资料排在第几位。

如果第一条就是正确资料：

```text
reciprocal rank = 1 / 1 = 1.0
```

如果第三条才是正确资料：

```text
reciprocal rank = 1 / 3 = 0.3333
```

它回答的问题是：

```text
正确资料排得够不够靠前？
```

RAG 不只是要命中，还要让最相关资料排在前面。否则 prompt 可能塞进太多弱相关内容，影响模型生成。

## 4. 关键词覆盖率

关键词覆盖率表示：

```text
召回结果覆盖了多少预期关键词。
```

比如 expectedKeywords 是：

```text
Hit@K、MRR、关键词覆盖率、调试面板
```

如果召回内容只覆盖了 Hit@K 和 MRR，那么关键词覆盖率就是：

```text
2 / 4 = 0.5
```

它回答的问题是：

```text
命中的资料是否覆盖了这个问题真正想考的点？
```

关键词覆盖率不能单独代表最终回答质量，但它很适合排查 RAG 召回是否覆盖核心评分点。

## 5. metadataMatch

metadataMatch 判断命中资料的 metadata 是否符合预期，比如：

- 是否来自正确知识库。
- 是否匹配岗位标签。
- 是否匹配面试阶段。
- 是否属于当前用户可访问的资料。

它回答的问题是：

```text
资料来源和使用场景是否正确？
```

这对三类 RAG 很重要。岗位知识库、题库 RAG、候选人画像 RAG 不能混用，否则系统可能把历史弱点当成岗位标准，或者把题库参考答案当成候选人真实经历。

## 6. emptyRecall

emptyRecall 表示完全没有召回资料。

它通常说明：

- query 构造太差。
- 知识库数据缺失。
- metadata filter 太严格。
- 检索器配置有问题。

它是 RAG 链路里需要优先处理的问题，因为没有召回时，大模型只能依赖通用能力和用户输入，提问容易变泛。

## 7. 本阶段新增了什么

本阶段在 `backend_python/rag_evaluation.py` 中新增了两个解释函数：

- `explain_evaluation_metrics()`：用中文解释 Hit@K、MRR、关键词覆盖率、metadataMatch 和 emptyRecall。
- `build_case_insight()`：把单条 evaluation case 的指标转成 good、weak、miss 级别，并给出 summary、evidence 和 action。

这一步让 RAG 评估从“只有数字”升级为：

```text
有指标；
有解释；
有证据；
有下一步行动建议。
```

## 8. 面试时怎么讲

可以这样讲：

```text
我给 RAG 做了固定评估集，每条 case 有 query、预期标题、预期关键词和 metadata 约束。

评估时用 Hit@K 看前 K 条是否命中预期资料，用 MRR 看正确资料排得靠不靠前，用关键词覆盖率看命中内容是否覆盖核心评分点。

同时我还记录 metadataMatch 和 emptyRecall，用来判断资料来源是否正确、是否出现空召回。

为了让评估结果更容易排查，我把单条 case 的指标转成 good、weak、miss 三类诊断，并给出证据和下一步优化建议。
```
