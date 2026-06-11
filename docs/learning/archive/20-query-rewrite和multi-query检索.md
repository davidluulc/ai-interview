# 20. query rewrite 和 multi-query 检索

## 1. query rewrite 是什么

query rewrite 的意思是：

```text
不要只用用户原始输入去检索
而是结合岗位、阶段、简历、JD、薄弱点等上下文
扩展出多条更适合检索的 query
```

例如用户原始 query 是：

```text
日志怎么设计
```

系统可以扩展成：

```text
日志怎么设计 AI 应用开发岗 RAG 命中日志 质量评估
日志怎么设计 技术追问 RAG retrieval evaluation
日志怎么设计 ai_app_intern rag_quality
```

这样能提高召回覆盖率。

## 2. 本项目为什么先做规则版 query rewrite

query rewrite 可以用大模型做，也可以先用规则做。

本阶段选择规则版，原因是：

- 不增加模型调用成本；
- 输出更稳定，方便测试；
- 便于你面试时讲清楚；
- 后续可以替换成 LLM rewrite 或 LangGraph node。

当前项目的路线是：

```text
先做可测试的规则版
再预留 LLM rewrite 升级空间
```

## 3. 本轮支持的 query variant

当前 `build_query_variants()` 会生成：

```text
base     : 原始 query
role     : 原始 query + targetRole + positionTag + JD
stage    : 原始 query + targetRole + positionTag + 当前面试阶段
weakness : 原始 query + positionTag + weakTags
```

返回结构类似：

```json
[
  {"name": "base", "query": "RAG log quality"},
  {"name": "role", "query": "RAG log quality AI application intern ai_app_intern ..."},
  {"name": "stage", "query": "RAG log quality AI application intern ai_app_intern technical"},
  {"name": "weakness", "query": "RAG log quality ai_app_intern rag_quality"}
]
```

## 4. multi-query 检索怎么合并结果

本轮新增 `retrieve_multi_query_chunks()`：

```text
1. 生成 queryVariants
2. 每条 query variant 单独调用 retrieve_chunks()
3. 按 chunkId 合并命中结果
4. 同一个 chunk 被多条 query 命中时，保留分数更高的那次
5. 在 hit 中记录 matchedQueryVariant 和 queryVariants
```

这样日志里可以看到：

```text
这条资料到底是 base query 命中的
还是 role query / stage query / weakness query 命中的
```

## 5. 它和 metadata filter 的关系

metadata filter 是业务过滤：

```text
先限制候选范围
```

query rewrite 是召回增强：

```text
在候选范围内尝试多种 query 表达
```

所以完整顺序可以理解为：

```text
文档生命周期过滤
权限过滤
metadata filter
query rewrite / multi-query
BM25 / vector / hybrid / rerank
```

## 6. 本轮代码位置

新增：

- `backend_python/query_rewrite.py`
  - `build_query_variants()`

修改：

- `backend_python/retrieval_service.py`
  - `retrieve_multi_query_chunks()`
- `backend_python/rag.py`
  - 岗位知识库 RAG 接入 multi-query。
- `backend_python/question_rag.py`
  - 题库 RAG 接入 multi-query。

## 7. 面试表达模板

你可以这样讲：

```text
我在 RAG 召回阶段做了 query rewrite 和 multi-query 检索。
系统不会只用用户原始 query，而是结合岗位、positionTag、JD、面试阶段和薄弱点生成 base、role、stage、weakness 多条 query variant。
每条 query 会分别召回候选 chunk，然后按 chunkId 合并，保留分数更高的结果。
同时我会在 hit 里记录 matchedQueryVariant 和 queryVariants，
这样后续排查 RAG 命中质量时可以知道某条资料到底是被哪条 query 召回的。
当前版本是规则版 rewrite，优点是稳定、可测试、成本低；后续可以升级为 LLM rewrite 或 LangGraph 的独立节点。
```

## 8. 本轮测试

新增测试：

```text
tests/test_rag_query_rewrite.py
```

覆盖：

- `build_query_variants()` 能生成 base / role / stage / weakness；
- query variant 会去重；
- multi-query 检索能合并命中；
- hit 会记录 `matchedQueryVariant` 和 `queryVariants`；
- 岗位 RAG 上层能返回 query variant 信息。

局部验证：

```text
python -m pytest tests/test_rag_query_rewrite.py tests/test_rag_database_retrieval.py tests/test_rag_metadata_filter.py tests/test_rag_retrieval_logs.py tests/test_interview_agent_route.py -q
```

结果：

```text
28 passed
```
