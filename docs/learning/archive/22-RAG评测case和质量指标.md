# 22. RAG 评测 case 和质量指标

## 1. 为什么要做 RAG evaluation

RAG 质量不能只靠主观感觉。

如果你只说：

```text
我感觉召回还可以
```

面试官可能会继续追问：

```text
你怎么证明召回质量好？
升级 query rewrite 之后有没有变好？
引入 metadata filter 之后有没有误伤？
```

所以生产级 RAG 需要 evaluation cases 和量化指标。

## 2. 什么是 evaluation case

一个 evaluation case 可以理解成一条测试样例：

```text
给定 query
指定知识库
指定期望命中的资料标题或关键词
运行检索
看前 K 条结果是否命中预期
```

示例结构：

```json
{
  "id": "rag-quality",
  "query": "RAG 质量怎么评估",
  "knowledgeBase": "role_knowledge",
  "expectedTitle": "RAG 质量评估",
  "expectedKeywords": ["Hit@K", "MRR", "keywordCoverage"],
  "expectedKnowledgeBase": "role_knowledge",
  "expectedPositionTag": "ai_app_intern"
}
```

## 3. 本项目的核心指标

### Hit@K

Hit@K 表示：

```text
前 K 条召回结果里，是否命中预期资料
```

如果 K=3，前三条里命中了预期资料，则：

```text
Hit@3 = 1
```

否则：

```text
Hit@3 = 0
```

### MRR

MRR 是 Mean Reciprocal Rank。

它关注正确资料排在第几位：

```text
第 1 位命中：1 / 1 = 1.0
第 2 位命中：1 / 2 = 0.5
第 3 位命中：1 / 3 = 0.3333
没命中：0
```

MRR 比 Hit@K 更关注排序质量。

### 关键词覆盖率

关键词覆盖率表示：

```text
召回结果覆盖了多少预期关键词
```

例如期望关键词：

```text
["Hit@K", "MRR", "rerank", "metadata"]
```

召回结果只包含前两个：

```text
keywordCoverage = 2 / 4 = 0.5
```

### metadataMatch

metadataMatch 判断命中的资料是否符合预期业务边界：

```text
知识库是否正确
岗位标签是否正确
面试阶段是否正确
```

### emptyRecall

emptyRecall 表示空召回。

这是高优先级问题，因为没有资料被召回时，后面的 rerank、prompt 组装都没有意义。

## 4. 本轮新增的 case 管理能力

本轮没有重写指标，而是在现有评估能力上补了管理层：

- `normalize_evaluation_case()`
  - 统一 case 字段；
  - 自动补齐 `expectedKnowledgeBase`；
  - 把单个关键词转成 list。
- `filter_evaluation_cases()`
  - 按 `knowledgeBase` 和 `expectedPositionTag` 筛选 case。
- `run_evaluation_suite()`
  - 运行多种检索模式；
  - 输出 summary；
  - 输出 metricDefinitions；
  - 给每个 case 生成 caseInsight。

## 5. case insight 是什么

case insight 是给人看的解释。

它会把一条 case 归纳成：

```text
level: good / weak / miss
summary: 当前问题总结
action: 建议怎么修
evidence: top hit 证据
metrics: 指标明细
```

这样后续做后台质量面板时，不只是显示一堆数字，还能告诉管理员：

```text
这个 case 是空召回
这个 case 是 metadata miss
这个 case 是关键词覆盖率低
```

## 6. 面试表达模板

你可以这样讲：

```text
我没有只凭主观体验判断 RAG 质量，而是维护了 evaluation cases。
每个 case 包含 query、知识库、期望标题、期望关键词和 metadata 预期。
系统会运行检索并计算 Hit@K、MRR、关键词覆盖率、metadataMatch 和 emptyRecall。
Hit@K 判断前 K 条有没有命中，MRR 关注正确资料排第几，关键词覆盖率判断内容覆盖是否充分。
我还给每个 case 生成 insight，用 good、weak、miss 解释召回质量，并给出修复建议。
这样后续升级 query rewrite、metadata filter、hybrid search、rerank 时，都可以用同一批 cases 做回归评估。
```

## 7. 本轮测试

新增测试：

```text
tests/test_rag_evaluation_management.py
```

覆盖：

- case 字段规范化；
- case 按知识库和岗位筛选；
- evaluation suite 返回 summary、metricDefinitions 和 caseInsights。

局部验证：

```text
python -m pytest tests/test_rag_evaluation_management.py tests/test_rag_evaluation.py tests/test_rag_evaluation_explanations.py tests/test_rag_evaluation_script.py tests/test_rag_evaluation_seed.py -q
```

结果：

```text
23 passed
```
