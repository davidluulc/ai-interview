# RAG RetrievalService V2 设计说明

## 背景

当前系统已经具备三个 RAG 来源：

- 岗位知识库 RAG：为面试官提供岗位能力点、评分点和风险信号。
- 题库 RAG：为面试官提供参考题目、参考答案和答题要点。
- 候选人画像 RAG：为面试官提供当前用户历史回答、薄弱点和训练建议。

现有岗位知识库和题库已经支持数据库文档与 chunk，并且在没有数据库命中时回退到 JSON 种子数据。但当前检索逻辑分散在 `rag.py`、`question_rag.py` 和 `rag_store.py` 中，存在以下问题：

- 岗位知识库和题库各自维护一套相似的关键词打分逻辑。
- 检索模式只有自定义关键词打分，严格来说不是 BM25。
- RAG 日志中的 `retrieval_mode` 仍主要是 `keyword`，无法区分后续检索策略。
- 后续接入 embedding、hybrid search 和 rerank 时，如果不先抽象统一检索入口，会导致重复代码继续扩大。

本版本目标是先完成 **统一检索服务 + BM25 检索**，为后续 embedding、hybrid search 和 rerank 做结构准备。

## 目标

RAG RetrievalService V2-1 要实现以下目标：

- 新增统一 `RetrievalService`，作为岗位知识库和题库的共同检索入口。
- 支持对数据库 chunk 执行 BM25 检索。
- 岗位知识库 RAG 和题库 RAG 优先通过 `RetrievalService` 检索数据库 chunk。
- 数据库 BM25 没有命中时，继续回退到现有 JSON 种子数据检索。
- 检索结果保留 `score`、`matchedTokens`、`metadata`、`chunkId`、`documentId` 等可解释字段。
- RAG 日志能记录 `retrieval_mode="bm25"`，方便后续观察不同检索策略。
- 候选人画像 RAG 暂时不接入 BM25，继续保留当前按用户和投递档案召回的业务逻辑。

## 非目标

本阶段不实现以下能力：

- 不接入 embedding 模型。
- 不接入向量数据库。
- 不实现 hybrid search。
- 不调用 `qwen3-rerank`。
- 不做大模型语义 chunk 切分。
- 不重构候选人画像 RAG。
- 不改前端页面主体验。

这些能力会作为 V2-2、V2-3、V2-4 继续推进。

## 设计原则

### 先统一入口，再增强能力

检索能力升级的第一步不是直接堆模型，而是先抽象稳定边界。后续无论是 BM25、向量检索、混合召回还是 rerank，都应该挂在统一入口下。

### 岗位知识库和题库复用引擎

岗位知识库和题库的底层检索对象都是 `RagChunk`，区别主要在 `knowledge_base` 和 metadata。它们不应该各写一套检索引擎。

### 候选人画像先不向量化

候选人画像更强调用户隔离、投递档案优先级、历史时间顺序和训练弱点聚合。当前阶段保留现有业务召回更稳，不强行接入 BM25 或向量检索。

### 可解释优先

BM25 检索结果需要返回命中词、分数和来源信息，方便调试“为什么召回这条 chunk”。

## 核心模块设计

新增模块：

```text
backend_python/retrieval_service.py
```

职责：

- 将 query 分词。
- 从数据库读取当前用户、指定知识库下的 chunk。
- 使用 BM25 对 chunk 打分。
- 返回统一结构的检索结果。
- 提供 `retrieval_mode` 标识。

建议核心函数：

```python
def retrieve_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int = 3,
    mode: str = "bm25",
) -> list[dict[str, Any]]:
    ...
```

返回结构：

```json
{
  "source": "database",
  "retrievalMode": "bm25",
  "chunkId": 1,
  "documentId": 1,
  "knowledgeBase": "role_knowledge",
  "title": "FastAPI RAG 工程化",
  "content": "chunk 正文",
  "score": 3.42,
  "matchedTokens": ["FastAPI", "RAG"],
  "metadata": {
    "positionTag": "ai_app_intern",
    "category": "technical"
  }
}
```

## BM25 策略

V2-1 使用本地轻量 BM25，不新增第三方依赖。

核心公式：

```text
score = idf(term) * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len)))
```

默认参数：

- `k1 = 1.5`
- `b = 0.75`

文档字段组合：

```text
title + content + keywords + metadata values
```

query 字段来源仍沿用现有逻辑：

- 目标岗位。
- 岗位标签。
- 简历摘要。
- JD。
- 公司要求。
- 当前面试阶段。

命中规则：

- 如果 query token 在 chunk 文本中出现，参与 BM25 打分。
- 如果 chunk 关键词与 query 命中，可额外记录到 `matchedTokens`，但 V2-1 不做过重人工加权。
- 只返回 `score > 0` 的结果。
- 按 `score` 倒序返回 Top K。

## 与现有模块的关系

### 岗位知识库 RAG

`backend_python/rag.py` 保留岗位知识库特有的格式化逻辑和 JSON 种子兜底逻辑。

变化：

- 数据库 chunk 检索从 `retrieve_database_chunks` 改为调用 `RetrievalService`。
- 数据库命中后仍通过 `convert_database_role_hit` 转换成岗位知识库上下文结构。
- 没有数据库命中时继续使用 `role_knowledge_seed.json`。

### 题库 RAG

`backend_python/question_rag.py` 保留题库特有的格式化逻辑和 JSON 种子兜底逻辑。

变化：

- 数据库 chunk 检索改为调用同一个 `RetrievalService`。
- 数据库命中后仍通过 `convert_database_question_hit` 转换成题库上下文结构。
- 没有数据库命中时继续使用 `question_bank_seed.json`。

### RAG 日志

当前日志入口在 `routes/interview.py` 的 `log_retrievals` 中统一写入。

V2-1 要求：

- 如果命中结果中包含 `retrievalMode`，日志优先使用该值。
- 岗位知识库和题库数据库命中时记录 `bm25`。
- JSON 种子兜底结果仍记录 `keyword`。
- 候选人画像仍记录 `keyword` 或现有模式。

## 错误处理

- 数据库中没有 chunk：返回空数组，由上层回退到 JSON 种子数据。
- query 为空：返回空数组，不强行召回。
- knowledge_base 不合法：返回空数组或抛出明确错误，具体由实现计划决定。
- metadata JSON 解析失败：按空对象处理，不影响检索。
- BM25 全部得分为 0：返回空数组。

## 测试策略

后端测试覆盖：

- BM25 能让包含 query 关键词的 chunk 排在前面。
- 不相关 chunk 不返回或排在后面。
- `retrieve_chunks` 返回 `retrievalMode="bm25"`。
- 岗位知识库 RAG 能通过 `RetrievalService` 命中数据库 chunk。
- 题库 RAG 能通过 `RetrievalService` 命中数据库 chunk。
- 数据库无命中时，岗位知识库和题库仍能使用 JSON 种子兜底。
- RAG 日志在数据库 BM25 命中时记录 `retrievalMode="bm25"`。

## 验收标准

- 新增统一 `RetrievalService`。
- 岗位知识库和题库不再直接依赖旧的 `retrieve_database_chunks` 作为数据库检索入口。
- 数据库 chunk 检索采用 BM25 分数。
- RAG Debug 或日志能看到 `bm25` 检索模式。
- 原有面试生成、报告生成、RAG 文档管理测试仍然通过。
- 候选人画像 RAG 行为不被影响。

## 后续路线

V2-1 完成后，后续按以下顺序推进：

1. V2-2：Embedding 入库与向量检索。
2. V2-3：BM25 + Vector 的 hybrid search。
3. V2-4：接入 `qwen3-rerank` 对候选 chunk 重排。
4. V2-5：建立固定 RAG 评估集，对比 keyword、BM25、vector、hybrid、rerank 的命中效果。

## 面试表达建议

可以这样讲：

> 我没有给岗位知识库 RAG 和题库 RAG 分别写两套检索逻辑，而是抽象了统一 RetrievalService。第一阶段先把原来的关键词匹配升级成 BM25，让召回分数更接近真实信息检索逻辑，同时保留 JSON 种子数据作为兜底。候选人画像 RAG 没有盲目向量化，因为它更强调用户隔离、投递档案优先和历史弱点聚合。后续可以在统一检索服务下继续接 embedding、hybrid search 和 rerank，而不需要推翻业务层代码。
