# 21. hybrid 权重和 rerank 解释

## 1. hybrid search 是什么

hybrid search 是把多种召回方式合在一起。

本项目当前主要是：

```text
BM25 关键词检索
向量语义检索
```

BM25 适合精确关键词：

```text
FastAPI
JWT
RAG 命中日志
query_text
```

向量检索适合语义相近：

```text
用户说“资料召回质量”
系统也可能召回“RAG evaluation / hit rate / rerank”
```

hybrid 的价值是：

```text
既保留关键词稳定性
又补充语义泛化能力
```

## 2. 为什么权重不能写死

如果权重写死，例如：

```text
BM25 0.6
Vector 0.4
```

短期能用，但生产系统里不同场景可能需要不同权重：

- 技术八股题：关键词更重要；
- 开放式项目复盘：语义相似更重要；
- 日志排查：精确字段更重要；
- 简历深挖：语义泛化更重要。

所以本轮新增：

```text
normalize_hybrid_weights()
```

支持传入：

```json
{"bm25": 2, "vector": 1}
```

归一化后变成：

```json
{"bm25": 0.6667, "vector": 0.3333}
```

## 3. hybridWeights 为什么要写回 hit

命中结果里新增：

```text
hybridWeights
```

这样调试时可以知道：

```text
这次排序到底更偏向 BM25
还是更偏向向量检索
```

如果某次召回质量很差，我们可以根据日志判断是否需要调权重。

## 4. rerank 解释解决什么问题

rerank 的作用是：

```text
先召回一批候选文档
再让重排模型重新判断这些文档和 query 的相关性
```

但是只返回最终排序不够，因为我们不知道：

- 它原来排第几；
- rerank 后排第几；
- 是上升还是下降；
- rerank score 是多少。

所以本轮新增：

```text
preRerankRank
postRerankRank
rankChange
rerankExplanation
```

示例：

```text
preRank=2, postRank=1, moved up 1, rerankScore=0.95
```

这让 rerank 从黑箱排序变成可解释排序。

## 5. 本轮代码位置

主要修改：

- `backend_python/retrieval_service.py`
  - `normalize_hybrid_weights()`
  - `merge_hybrid_hits()` 返回 `hybridWeights`
  - `retrieve_hybrid_chunks()` 支持 `hybrid_weights`
  - `retrieve_hybrid_rerank_chunks()` 支持 `hybrid_weights`
  - `retrieve_chunks()` 透传 `hybrid_weights`
  - `retrieve_multi_query_chunks()` 透传 `hybrid_weights`
  - `apply_rerank_results()` 返回排名变化和解释字段

## 6. 面试表达模板

你可以这样讲：

```text
我的 RAG 不是只做单一路径召回，而是支持 hybrid search。
BM25 负责关键词稳定召回，向量检索负责语义泛化召回。
我把 bm25Weight 和 vectorWeight 做成可配置并归一化，命中结果里会记录 hybridWeights，方便后续调参和排查。
在 rerank 阶段，我不只返回重排后的结果，还记录 preRerankRank、postRerankRank、rankChange 和 rerankExplanation。
这样当某条资料被 rerank 提升或降低时，我们能解释它原来排第几、现在排第几、分数是多少，减少黑箱感。
```

## 7. 本轮测试

新增测试：

```text
tests/test_rag_hybrid_rerank_explain.py
```

覆盖：

- hybrid 权重归一化；
- hybrid hit 返回 `hybridWeights`；
- rerank hit 返回 `postRerankRank`、`rankChange` 和 `rerankExplanation`。

局部验证：

```text
python -m pytest tests/test_rag_hybrid_rerank_explain.py tests/test_rag_hybrid_retrieval.py tests/test_rag_rerank_retrieval.py tests/test_rag_query_rewrite.py tests/test_rag_retrieval_logs.py tests/test_interview_agent_route.py -q
```

结果：

```text
31 passed
```
