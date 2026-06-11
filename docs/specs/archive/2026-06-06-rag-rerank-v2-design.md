# RAG Rerank V2-4 设计说明

## 背景

当前项目的 RAG 检索链路已经完成：

- V2-1：统一 `RetrievalService`，岗位知识库 RAG 和题库 RAG 复用 BM25 检索。
- V2-2：RAG 文档 chunk 支持 embedding 入库，支持 `mode="vector"` 向量检索。
- V2-3：支持 `mode="hybrid"`，把 BM25 和 vector 结果做归一化、去重、融合，并记录可观测字段。

Hybrid Search 解决的是“召回覆盖面”问题：尽量把可能相关的 chunk 找出来。但 Hybrid 的排序仍然依赖 BM25 分数、余弦相似度和手工权重，不能完全理解 query 与候选 chunk 的深层语义相关性。

Rerank 重排的目标是：在 Hybrid 召回出一批候选 chunk 后，再调用专门的重排序模型，对 query 和每个候选 chunk 做相关性判断，把最贴合当前问题的资料排到最前。

本阶段使用阿里云百炼 `qwen3-rerank`。根据阿里云百炼官方文档，`qwen3-rerank` 使用接口：

```text
POST https://dashscope.aliyuncs.com/compatible-api/v1/reranks
```

请求体中 `model`、`query`、`documents`、`top_n`、`instruct` 位于同一层级，不使用 `input` 或 `parameters` 包裹。

参考文档：

- https://help.aliyun.com/zh/model-studio/rerank
- https://help.aliyun.com/zh/model-studio/text-rerank-api

## 目标

本阶段实现以下能力：

- 新增 `backend_python/rerank_client.py`，封装百炼 `qwen3-rerank` 调用。
- 新增配置项 `DASHSCOPE_RERANK_MODEL`，默认值为 `qwen3-rerank`。
- 新增 `rerank_hits(query, hits, top_n)` 能力，对 Hybrid 候选结果重排。
- `retrieve_chunks(mode="hybrid_rerank")` 支持先 Hybrid 召回，再 Rerank 重排。
- Rerank 成功时返回 `retrievalMode="hybrid_rerank"`。
- Rerank 命中结果保留：
  - `rerankScore`
  - `rerankIndex`
  - `preRerankRank`
  - `matchedRetrievalModes`
  - `hybridScore`
  - `bm25Score`
  - `vectorScore`
- Rerank 失败时不影响主流程，自动降级为 Hybrid 原排序。
- RAG 日志能够记录 `retrievalMode="hybrid_rerank"` 和 rerank 调试字段。

## 非目标

本阶段不实现以下内容：

- 不做 qwen3-vl-rerank 多模态重排。
- 不引入 LangChain、LlamaIndex 等框架。
- 不引入 Qdrant、pgvector、Milvus。
- 不做大模型语义切分。
- 不做 RAG 评估集自动评分。
- 不把主面试流程默认切换到 `hybrid_rerank`。
- 不做前端页面重构。
- 不做批量离线 rerank，因为 rerank 是 query 相关能力，不适合提前离线计算。

## 为什么 Rerank 放在 Hybrid 之后

RAG 一般分两层：

```text
召回：快速找出一批可能相关的候选内容
排序：对候选内容做更精细的相关性判断
```

BM25 和 vector 更适合做召回，因为它们速度较快，适合从较大的 chunk 集合里找候选。Rerank 更适合做排序，因为它会把 query 和每个候选文档一起输入模型，计算成本和延迟更高，不适合直接对全量知识库执行。

本项目采用：

```text
BM25 Top N
-> Vector Top N
-> Hybrid 合并去重
-> Rerank Top K
-> Prompt 上下文
```

## 接口设计

### Rerank Client

新增文件：

```text
backend_python/rerank_client.py
```

核心函数：

```python
def build_rerank_payload(
    *,
    model_name: str,
    query: str,
    documents: list[str],
    top_n: int,
    instruct: str,
) -> dict[str, Any]:
    ...


def extract_rerank_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    ...


async def rerank_documents(
    *,
    query: str,
    documents: list[str],
    top_n: int,
    instruct: str = DEFAULT_RERANK_INSTRUCT,
    model_name: str = DASHSCOPE_RERANK_MODEL,
) -> list[dict[str, Any]]:
    ...
```

`rerank_documents` 返回结构：

```python
[
    {"index": 0, "relevance_score": 0.93},
    {"index": 2, "relevance_score": 0.81},
]
```

### Retrieval Service

`backend_python/retrieval_service.py` 新增：

```python
def hit_to_rerank_document(hit: dict[str, Any]) -> str:
    ...


def apply_rerank_results(
    hits: list[dict[str, Any]],
    rerank_results: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    ...


def retrieve_hybrid_rerank_chunks(...) -> list[dict[str, Any]]:
    ...
```

`retrieve_chunks` 新增模式：

```python
retrieve_chunks(
    db,
    user_id=user_id,
    knowledge_base="role_knowledge",
    query=query,
    limit=3,
    mode="hybrid_rerank",
)
```

## 请求体设计

`qwen3-rerank` 请求体：

```json
{
  "model": "qwen3-rerank",
  "query": "请追问 RAG 日志如何用于排查召回质量",
  "documents": [
    "标题：RAG 日志工程化\n内容：RAG 命中日志需要记录 query_text、retriever_name、hit_count、quality。",
    "标题：FastAPI 模块化\n内容：FastAPI 可以使用 APIRouter 拆分后端路由。"
  ],
  "top_n": 2,
  "instruct": "根据 query 判断候选文档与 AI 模拟面试追问场景的相关性。"
}
```

## 返回结构

重排后的 hit 示例：

```json
{
  "source": "database",
  "retrievalMode": "hybrid_rerank",
  "matchedRetrievalModes": ["bm25", "vector", "rerank"],
  "chunkId": 12,
  "documentId": 3,
  "knowledgeBase": "role_knowledge",
  "title": "RAG 日志工程化",
  "content": "RAG 命中日志需要记录 query_text、retriever_name、hit_count、quality。",
  "score": 0.93,
  "rerankScore": 0.93,
  "rerankIndex": 0,
  "preRerankRank": 2,
  "hybridScore": 0.71,
  "bm25Score": 2.43,
  "vectorScore": 0.87,
  "matchedTokens": ["rag", "quality"],
  "matchedKeywords": ["RAG", "quality"],
  "metadata": {
    "category": "technical"
  }
}
```

说明：

- `score` 与 `rerankScore` 保持一致，兼容现有调用方。
- `preRerankRank` 表示重排前在 Hybrid 结果中的位置。
- `rerankIndex` 表示该文档在传入 rerank documents 数组里的下标。
- `matchedRetrievalModes` 追加 `rerank`，保留它经历过的检索链路。

## 降级策略

Rerank 调用失败时，不能让面试主流程失败。

失败场景包括：

- 没有配置 `DASHSCOPE_API_KEY`。
- 网络超时。
- 百炼接口返回 4xx/5xx。
- 返回结果格式不符合预期。
- 返回 index 越界。

降级规则：

```text
Hybrid 候选为空
-> 返回 []

Hybrid 候选非空，但 rerank 失败
-> 返回 Hybrid 原排序
-> retrievalMode 仍可标记为 hybrid
-> 不追加 rerankScore
```

这样做的原因是：Rerank 是排序增强，不是主流程的唯一依赖。系统必须先保证可用性，再追求排序质量。

## 日志设计

`rag_logging.summarize_hit` 需要保留以下字段：

- `retrievalMode`
- `matchedRetrievalModes`
- `hybridScore`
- `bm25Score`
- `vectorScore`
- `rerankScore`
- `rerankIndex`
- `preRerankRank`

后续在 RAG Debug 页面里可以据此解释：

- 候选内容是否由 BM25 命中。
- 是否由 vector 命中。
- Rerank 是否改变了排序。
- Rerank 分数是否和 Hybrid 分数差异较大。

## 测试策略

新增或补充测试：

- `build_rerank_payload` 请求体结构正确。
- `extract_rerank_results` 能解析顶层 `results`。
- `extract_rerank_results` 对缺失或异常字段抛出明确错误。
- `rerank_documents` 不泄露 API Key。
- `hit_to_rerank_document` 能把 hit 转成适合模型判断的文档文本。
- `apply_rerank_results` 能按 relevance_score 重排 hit。
- `apply_rerank_results` 能记录 `rerankScore`、`rerankIndex`、`preRerankRank`。
- `retrieve_chunks(mode="hybrid_rerank")` 能返回 rerank 后结果。
- Rerank 失败时 `hybrid_rerank` 降级为 Hybrid。
- RAG 日志能保留 rerank 调试字段。

## 验收标准

- `qwen3-rerank` 客户端有单元测试覆盖。
- `retrieve_chunks(mode="hybrid_rerank")` 有独立测试覆盖。
- `bm25`、`vector`、`hybrid` 原有测试继续通过。
- Rerank 失败不会影响 Hybrid 返回。
- RAG 日志保留 rerank 调试字段。
- 全量后端测试通过。
- 前端 smoke 测试通过。

## 面试表达建议

可以这样讲：

> 我在 Hybrid Search 后面接了 Rerank。Hybrid 负责扩大候选召回范围，Rerank 负责对 Top N 候选 chunk 做更精细的相关性排序。我使用的是百炼的 qwen3-rerank，把 query 和候选 chunk 文本传给排序模型，拿到 relevance_score 后重新排序。为了保证稳定性，我把 Rerank 设计成增强链路：如果重排模型超时或失败，系统会自动降级使用 Hybrid 原排序，不影响面试主流程。同时日志里会记录 rerankScore、preRerankRank、matchedRetrievalModes 等字段，方便排查重排是否真的改善了召回质量。

