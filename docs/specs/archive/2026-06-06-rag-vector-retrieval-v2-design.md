# RAG 向量检索 V2 设计说明

## 背景

当前系统已经完成 RAG V2-1：

- 岗位知识库 RAG 和题库 RAG 复用统一 `RetrievalService`。
- 数据库 chunk 检索已从自定义关键词匹配升级为 BM25。
- RAG 日志可以记录 `retrievalMode="bm25"`。
- 候选人画像 RAG 仍保留用户隔离和投递档案优先的业务召回逻辑。

下一步目标是引入 Embedding 向量检索，让系统不只依赖关键词重合，也能召回语义相近的知识片段。例如用户 query 中没有精确出现“命中日志”，但表达了“记录检索结果用于排查”，系统也应该有机会召回 RAG 日志相关 chunk。

百炼模型可用性检查已经确认当前账号可以调用：

- 文本生成：`qwen-plus`
- 向量模型：`text-embedding-v4`
- 重排模型：`qwen3-rerank`

本阶段只接入 `text-embedding-v4`，不做 hybrid search 和 rerank。

## 目标

RAG Vector Retrieval V2-2 要实现以下目标：

- 新增 Embedding 客户端，封装百炼 `text-embedding-v4` 调用。
- 为 `RagChunk` 增加 embedding 存储字段和 embedding 状态字段。
- 创建或更新 RAG 文档时，为每个 chunk 生成 embedding。
- 在 `RetrievalService` 中支持 `mode="vector"`。
- 使用余弦相似度对数据库 chunk 做向量检索。
- 检索结果返回 `retrievalMode="vector"`、`score`、`embeddingStatus`、`chunkId`、`metadata` 等字段。
- RAG 日志能够记录向量检索模式。
- BM25 检索继续保留，不被替换。

## 非目标

本阶段不实现以下能力：

- 不做 BM25 + Vector 的 hybrid search。
- 不接入 `qwen3-rerank`。
- 不引入 Qdrant、Milvus、Chroma 或 pgvector。
- 不做大模型语义切分。
- 不做异步任务队列。
- 不做批量历史文档重建任务。
- 不重构候选人画像 RAG。
- 不重做前端页面主体验。

这些能力后续分阶段实现。

## 为什么先用 SQLite + JSON 存向量

当前项目仍处于本地学习和 MVP 工程化阶段，数据库使用 SQLite。直接引入向量数据库会额外增加部署、连接、数据同步和运维成本，不利于先理解 RAG 主链路。

本阶段建议先把向量存储在 `RagChunk` 表中：

- `embedding_json`：保存向量数组 JSON。
- `embedding_model`：记录使用的 embedding 模型。
- `embedding_status`：记录 `pending`、`ready`、`failed`。

这样可以先验证：

- embedding 是否能生成。
- chunk 是否能存向量。
- query 是否能生成向量。
- 余弦相似度是否能召回语义相关 chunk。
- RAG 日志是否能区分 BM25 和 vector。

后续切换到 pgvector 或 Qdrant 时，只需要替换存储和查询实现，不需要推翻业务层。

## 数据模型设计

在 `rag_chunks` 表增加字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `embedding_json` | Text | chunk embedding 向量 JSON |
| `embedding_model` | String | 生成该向量的模型名 |
| `embedding_status` | String | pending、ready、failed |

默认值：

- `embedding_json = "[]"`
- `embedding_model = ""`
- `embedding_status = "pending"`

SQLite 兼容策略：

- Alembic migration 增加字段。
- `database.py` 的 SQLite 自动建表/补字段逻辑同步更新。

## Embedding 客户端设计

新增模块：

```text
backend_python/embedding_client.py
```

职责：

- 读取 `DASHSCOPE_API_KEY`。
- 读取 `DASHSCOPE_EMBEDDING_MODEL`，默认 `text-embedding-v4`。
- 调用百炼兼容模式 embedding 接口。
- 返回 `list[float]`。
- 处理超时、网络错误、模型错误。
- 不在日志中输出 API Key。

建议核心函数：

```python
async def embed_text(text: str, model_name: str = DASHSCOPE_EMBEDDING_MODEL) -> list[float]:
    ...
```

本阶段使用单条文本 embedding，后续再考虑批量 embedding 和异步任务。

## Chunk 入库流程

当前文档创建流程：

```text
创建 RagDocument
→ 切分 content 为 chunks
→ 为每个 chunk 提取关键词
→ 写入 RagChunk
```

V2-2 后流程：

```text
创建 RagDocument
→ 切分 content 为 chunks
→ 为每个 chunk 提取关键词
→ 调用 embedding 模型生成向量
→ 写入 RagChunk.embedding_json / embedding_model / embedding_status
```

错误策略：

- 如果 embedding 成功：`embedding_status="ready"`。
- 如果 embedding 失败：chunk 仍然入库，`embedding_status="failed"`，`embedding_json="[]"`。
- 文档创建不能因为某个 chunk embedding 失败而整体失败。
- 后续 BM25 仍可检索该 chunk。

这样能保证 AI 模型服务短暂异常时，知识库文档管理不至于完全不可用。

## 向量检索设计

`RetrievalService` 增加 `mode="vector"`：

```python
retrieve_chunks(
    db,
    user_id=user_id,
    knowledge_base="role_knowledge",
    query=query,
    limit=3,
    mode="vector",
)
```

流程：

1. 对 query 调用 embedding 模型生成 query vector。
2. 查询当前用户、指定 knowledge_base 下 `embedding_status="ready"` 的 chunks。
3. 解析每个 chunk 的 `embedding_json`。
4. 计算 query vector 和 chunk vector 的余弦相似度。
5. 只返回 score 大于 0 的结果。
6. 按 score 倒序取 Top K。
7. 返回统一 hit 结构。

返回示例：

```json
{
  "source": "database",
  "retrievalMode": "vector",
  "chunkId": 1,
  "documentId": 1,
  "knowledgeBase": "role_knowledge",
  "title": "RAG 日志工程化",
  "content": "chunk 正文",
  "score": 0.82,
  "matchedTokens": [],
  "embeddingStatus": "ready",
  "metadata": {
    "category": "technical"
  }
}
```

## 与 BM25 的关系

本阶段不做自动 hybrid。

原因：

- BM25 和 Vector 的分数范围不同，直接相加不稳定。
- 需要先分别观察两种检索模式的命中质量。
- hybrid 权重应该基于日志和测试集调出来，而不是拍脑袋。

因此 V2-2 只要求：

- BM25 可以独立运行。
- Vector 可以独立运行。
- 日志可以区分 `bm25` 和 `vector`。
- 后续 V2-3 再做 hybrid 合并、去重、权重归一化。

## 接入范围

本阶段优先接入 `RetrievalService` 层和文档入库层。

岗位知识库 RAG 和题库 RAG 的默认检索模式暂时仍保持 BM25，避免上线体验突然变化。

向量检索先通过后端测试和调试接口验证。确认质量后，下一阶段再考虑让面试生成链路切换到 hybrid。

也就是说：

- 文档创建时生成 embedding。
- `RetrievalService` 支持 `mode="vector"`。
- RAG Debug 或测试可以调用 vector 检索。
- 面试主流程默认仍先走 BM25。

## 配置项

`.env` 和 `.env.example` 增加或保留：

```text
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
```

后续可增加：

```text
RAG_DEFAULT_RETRIEVAL_MODE=bm25
```

但本阶段不强制引入默认模式切换。

## 测试策略

后端测试覆盖：

- Embedding 客户端能解析百炼 embedding 响应。
- Embedding 客户端不会泄露 API Key。
- 余弦相似度函数能正确计算相似度。
- 文档创建时能保存 chunk embedding。
- embedding 失败时 chunk 仍然入库，状态为 `failed`。
- `retrieve_chunks(mode="vector")` 能返回相似度最高的 ready chunk。
- `retrieve_chunks(mode="vector")` 不返回 embedding 缺失或 failed 的 chunk。
- BM25 现有测试继续通过。

可选真实检查：

- 使用现有百炼 API Key 调用 `text-embedding-v4` 做一次真实 smoke test。

## 验收标准

- `RagChunk` 支持 embedding 字段。
- 创建 RAG 文档后，chunk 有 embedding 状态。
- `RetrievalService` 支持 `mode="vector"`。
- 向量检索结果包含 `retrievalMode="vector"`。
- embedding 失败不影响文档创建。
- 现有 BM25、RAG 日志、面试报告、用户系统测试仍通过。
- 不打印、不保存 API Key。

## 后续路线

V2-2 完成后：

1. V2-3：实现 BM25 + Vector hybrid search。
2. V2-4：接入 `qwen3-rerank` 做重排。
3. V2-5：建立 RAG 评估集，对比 BM25、Vector、Hybrid、Rerank。
4. V2-6：替换本地 JSON 向量存储为 pgvector 或 Qdrant。

## 面试表达建议

可以这样讲：

> 我在 BM25 之后没有立刻做 hybrid，而是先单独接入 embedding 向量检索。这样可以分别观察关键词召回和语义召回的效果，避免多种策略混在一起导致问题难以定位。当前本地版本先把 embedding 存在 SQLite 的 JSON 字段中，用余弦相似度完成向量检索；后续上线时可以替换成 pgvector 或 Qdrant。这个设计保留了统一 RetrievalService 接口，所以业务层不需要关心底层是 BM25、vector 还是 hybrid。
