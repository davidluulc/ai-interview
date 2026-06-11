# RAG 工程化

## RAG 主线

当前项目已经不是简单 RAG demo，而是具备一套生产级工程化雏形：

```text
文档管理
-> 文本切分 chunk
-> BM25 / 向量 / hybrid / rerank
-> metadata filter
-> query rewrite / multi-query
-> 质量评估
-> 命中日志
-> 后台质量面板
-> VectorStore 迁移抽象
```

## 文档治理

RAG 文档有：

- `enabled / disabled / archived` 生命周期；
- `private / public` 权限边界；
- `contentHash` 文档去重；
- `chunkHash` chunk 去重；
- `duplicateChunkCount` 重复统计。

这让知识库可管理、可审计、可治理。

## 检索增强

当前支持：

- BM25 关键词检索；
- embedding 向量检索；
- hybrid search；
- rerank 重排；
- metadata filter；
- query rewrite；
- multi-query 召回。

metadata filter 负责业务边界：

```text
岗位、分类、难度、面试阶段、来源
```

query rewrite 负责扩展检索表达：

```text
base / role / stage / weakness
```

## 质量评估

系统有 RAG evaluation case。

指标包括：

- Hit@K：前 K 条是否命中预期；
- MRR：正确资料排第几；
- keywordCoverage：关键词覆盖率；
- metadataMatch：元数据是否匹配；
- emptyRecall：是否空召回。

## 可观测性

系统记录：

- query_text；
- retriever_name；
- retrieval_mode；
- hit_count；
- hits_json；
- used_in_prompt；
- quality。

管理员后台可以看到低质量召回：

- 空召回；
- 弱召回；
- 未进入 prompt。

## 向量库迁移

当前 embedding 仍保存在 SQLite，但已经抽象出 `VectorStore`：

- 当前实现：`SQLiteVectorStore`
- 后续可迁移：Qdrant / pgvector

面试表达：

```text
我当前为了降低部署复杂度使用 SQLite 保存 embedding，但业务代码不直接绑定 SQLite，而是通过 VectorStore 协议访问向量检索能力。
后续迁移 Qdrant 或 pgvector 时，只需要实现新的 VectorStore 适配器。
```

## 面试表达

```text
我的 RAG 模块不是只做相似度搜索。
我补了文档生命周期、private/public 权限边界、metadata filter、query rewrite、多路召回、hybrid 权重、rerank 解释、evaluation case 和低质量召回面板。
这些能力让 RAG 可以被管理、被评估、被调试，也为后续迁移 Qdrant 或 pgvector 留出了接口。
```

