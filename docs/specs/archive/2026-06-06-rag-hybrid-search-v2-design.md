# RAG Hybrid Search V2-3 设计说明

## 背景

当前项目的 RAG 检索链路已经完成两个基础阶段：

- V2-1：统一 `RetrievalService`，岗位知识库 RAG 和题库 RAG 复用 BM25 检索。
- V2-2：RAG 文档 chunk 支持 embedding 入库，`retrieve_chunks(mode="vector")` 支持向量检索。

BM25 的优势是关键词命中稳定、结果容易解释，适合技术名词、岗位标签、字段名、框架名等明确表达。向量检索的优势是可以召回语义相近但关键词不完全一致的内容，适合用户表达不标准、同义改写、自然语言描述较多的场景。

V2-3 的目标是实现 BM25 + Vector 的混合检索，让系统先同时走两路召回，再把结果合并、去重、归一化排序。该阶段不引入 rerank，也不引入 Qdrant、pgvector 等向量数据库。

## 目标

本阶段实现以下能力：

- `RetrievalService.retrieve_chunks` 支持 `mode="hybrid"`。
- Hybrid 模式同时调用 BM25 检索和 vector 检索。
- 对 BM25 分数和 vector 分数分别做 0 到 1 的归一化，避免直接相加造成分数失真。
- 按 `chunkId` 去重，同一个 chunk 被两路命中时只保留一条结果。
- 同时命中的 chunk 记录 `matchedRetrievalModes=["bm25", "vector"]`。
- Hybrid 命中结果返回 `retrievalMode="hybrid"`。
- 命中结果保留可解释字段：`bm25Score`、`vectorScore`、`hybridScore`、`matchedTokens`、`matchedKeywords`。
- vector 失败时，Hybrid 不整体失败，而是降级返回 BM25 结果。
- BM25 无结果但 vector 有结果时，Hybrid 可以返回 vector 结果。
- RAG 日志能够记录 `retrievalMode="hybrid"`，并在 hits 中保留混合检索的关键摘要。

## 非目标

本阶段不实现以下内容：

- 不接入 `qwen3-rerank`。
- 不做大模型语义段落切分。
- 不引入 Qdrant、Milvus、Chroma、pgvector。
- 不做异步任务队列和批量重建 embedding。
- 不改造候选人画像 RAG。
- 不把主面试流程默认切到 hybrid，除非测试和调试确认质量稳定。
- 不做复杂前端页面改版，仅保证后端返回字段可被后续前端使用。

## 设计原则

### 1. BM25 保底

Hybrid 的第一原则是“关键词召回不能丢”。如果 vector API 失败、超时、返回空向量，系统仍然应该返回 BM25 结果。这样可以避免外部模型服务波动影响面试主流程。

### 2. 分数归一化后再融合

BM25 分数和 cosine similarity 分数不是同一个量纲：

- BM25 分数可能大于 1，也可能受文档数量、词频影响。
- vector cosine similarity 通常在 0 到 1 附近。

因此 Hybrid 不能直接使用 `bm25_score + vector_score`。本阶段采用 min-max 归一化：

```text
normalized_score = (score - min_score) / (max_score - min_score)
```

如果同一路召回只有一个正分结果，则该结果归一化为 1.0。

### 3. 权重先保守

默认融合公式：

```text
hybrid_score = bm25_weight * normalized_bm25_score + vector_weight * normalized_vector_score
```

默认权重：

```text
bm25_weight = 0.6
vector_weight = 0.4
```

理由：当前项目面向 AI 模拟面试，很多问题依赖岗位名、技术栈、项目名、字段名等明确关键词。BM25 权重略高可以减少语义召回跑偏。

### 4. 去重以 chunk 为单位

同一个 chunk 可能同时被 BM25 和 vector 命中。Hybrid 结果以 `chunkId` 作为唯一键合并：

- 如果两路都命中，合并为一条结果。
- `matchedRetrievalModes` 同时包含 `bm25` 和 `vector`。
- 文本、标题、metadata 以已有 hit 中的信息为准。
- `bm25Score` 和 `vectorScore` 分别记录原始分。
- `hybridScore` 作为最终排序分。

### 5. 可观测优先

Hybrid 检索不是黑盒。每条命中结果至少需要暴露：

- `retrievalMode`
- `matchedRetrievalModes`
- `score`
- `hybridScore`
- `bm25Score`
- `vectorScore`
- `matchedTokens`
- `matchedKeywords`
- `chunkId`
- `documentId`

这样后续调试时可以看出：这条资料到底是关键词命中的，还是向量语义命中的，还是两路同时命中的。

## 数据流

Hybrid 检索流程：

```text
用户 query
-> retrieve_chunks(mode="hybrid")
-> 执行 BM25 检索
-> 执行 vector 检索
-> 分别归一化分数
-> 按 chunkId 合并去重
-> 计算 hybridScore
-> 按 hybridScore 倒序返回 Top K
-> RAG 日志记录 retrievalMode="hybrid"
```

异常处理流程：

```text
vector 检索失败
-> 捕获异常或收到空结果
-> Hybrid 继续使用 BM25 结果
-> 命中结果 matchedRetrievalModes=["bm25"]
-> 不影响面试主流程
```

## 返回结构

Hybrid hit 示例：

```json
{
  "source": "database",
  "retrievalMode": "hybrid",
  "matchedRetrievalModes": ["bm25", "vector"],
  "chunkId": 12,
  "documentId": 3,
  "knowledgeBase": "role_knowledge",
  "title": "RAG 日志工程化",
  "content": "RAG 命中日志需要记录 query_text、retriever_name、hit_count、quality。",
  "score": 0.91,
  "hybridScore": 0.91,
  "bm25Score": 2.43,
  "vectorScore": 0.87,
  "matchedTokens": ["rag", "quality"],
  "matchedKeywords": ["RAG", "quality"],
  "metadata": {
    "category": "technical"
  }
}
```

其中：

- `score` 与 `hybridScore` 保持一致，兼容已有调用方。
- `bm25Score` 和 `vectorScore` 是原始分，便于调试。
- `matchedRetrievalModes` 用于判断该 chunk 来自哪一路召回。

## 与现有模块的关系

### `backend_python/retrieval_service.py`

本阶段主要修改该文件：

- 新增分数归一化函数。
- 新增 hybrid 结果合并函数。
- 新增 `retrieve_hybrid_chunks`。
- 在 `retrieve_chunks` 中支持 `mode="hybrid"`。

### `backend_python/rag_logging.py`

只做小幅增强：

- `summarize_hit` 保留 hybrid 相关字段。
- `infer_retrieval_mode` 可以识别 hybrid hit。

### `backend_python/rag.py` 和 `backend_python/question_rag.py`

本阶段默认不切换主流程检索模式。后续可以通过配置项控制：

```text
RAG_DEFAULT_RETRIEVAL_MODE=bm25
```

本阶段可以先不引入该配置项，避免范围扩张。

## 测试策略

新增或补充以下测试：

- `normalize_scores` 能把不同范围分数归一化到 0 到 1。
- 单个正分结果归一化为 1.0。
- Hybrid 能合并 BM25 和 vector 两路结果。
- 同一个 `chunkId` 被两路命中时只返回一条。
- 两路同时命中的结果优先级高于单路弱命中。
- vector 失败时 Hybrid 降级为 BM25。
- BM25 无结果时 Hybrid 可以返回 vector。
- BM25 默认行为不变。
- RAG 日志能记录 hybrid 命中摘要。

## 验收标准

- `retrieve_chunks(mode="bm25")` 原有测试全部通过。
- `retrieve_chunks(mode="vector")` 原有测试全部通过。
- `retrieve_chunks(mode="hybrid")` 有独立测试覆盖。
- Hybrid 命中结果包含 `retrievalMode="hybrid"`。
- Hybrid 命中结果包含 `matchedRetrievalModes`。
- 同一个 chunk 不重复返回。
- vector 失败不影响 BM25 返回。
- 全量后端测试通过。
- 前端 smoke 测试通过。

## 后续路线

V2-3 完成后，下一阶段建议：

1. V2-4：接入 `qwen3-rerank`，对 Hybrid Top K 做重排。
2. V2-5：设计 RAG 评估集，对比 BM25、Vector、Hybrid、Hybrid + Rerank。
3. V2-6：把 SQLite JSON 向量存储替换为 pgvector 或 Qdrant。
4. V2-7：将主面试流程从 BM25 默认切换为可配置的 Hybrid。

## 面试表达建议

可以这样讲：

> 我没有直接用向量检索替换 BM25，而是做了混合检索。原因是 BM25 对技术关键词、岗位标签、框架名这类精确表达更稳定，而向量检索更适合召回语义相近但关键词不完全一致的资料。我的 Hybrid Search 会分别执行 BM25 和 vector 检索，对两路分数做归一化，再按 chunkId 去重融合，并保留 bm25Score、vectorScore、matchedRetrievalModes 等可观测字段。这样既能提高召回覆盖面，也能在调试时解释每条资料为什么被召回。

