# 19. RAG 文档去重和 chunk 统计

## 1. 为什么生产级 RAG 要做去重

知识库长期使用后，很容易出现重复资料：

```text
同一份岗位 JD 被上传多次
同一段八股文被复制到多个文档
同一份简历被反复投递和解析
同一段项目介绍在不同资料里重复出现
```

如果不做去重，RAG 会出现几个问题：

- 重复 chunk 反复占据召回结果；
- BM25 统计被重复文本污染；
- 向量库体积膨胀；
- rerank 阶段浪费成本；
- RAG 质量评估时看不出真实覆盖率。

所以生产级 RAG 需要记录文档和 chunk 的 hash，至少先能识别重复。

## 2. 本轮为什么不直接禁止重复上传

本轮采用：

```text
允许上传
识别重复
返回统计
后续再做清理和治理
```

原因是当前项目还在从 MVP 往生产级雏形升级，如果一开始就强行拒绝重复上传，可能会影响用户体验和历史数据兼容。

更稳妥的做法是：

```text
第一阶段：先记录 contentHash / chunkHash / duplicateChunkCount
第二阶段：后台展示重复资料
第三阶段：管理员确认后再归档或清理
```

## 3. contentHash 是什么

`contentHash` 是整篇文档内容的 hash。

本项目会先对文本做空白规范化：

```text
"  hello   world  "
```

规范化为：

```text
"hello world"
```

再计算 SHA-256。

这样做可以避免因为前后空格、多个空格、换行差异导致同一份文档生成不同 hash。

## 4. chunkHash 是什么

`chunkHash` 是每个 chunk 内容的 hash。

如果同一文档里两个 chunk 内容完全一样，则它们会有相同的 `chunkHash`。

本轮还会标记：

```text
isDuplicate
```

第一条相同 chunk 记为：

```text
isDuplicate = false
```

后续重复出现的 chunk 记为：

```text
isDuplicate = true
```

文档层会返回：

```text
duplicateChunkCount
```

表示当前文档内部重复 chunk 数量。

## 5. 本轮代码怎么实现

主要代码位置：

- `backend_python/db_models.py`
  - `RagDocument.content_hash`
  - `RagDocument.duplicate_chunk_count`
  - `RagChunk.chunk_hash`
  - `RagChunk.is_duplicate`
- `backend_python/database.py`
  - SQLite 兼容迁移新增字段和索引。
- `backend_python/rag_store.py`
  - `normalize_hash_text()`
  - `compute_text_hash()`
  - `build_chunk_hash_records()`
  - 创建文档时计算 content hash、chunk hash 和重复 chunk 统计。
  - 序列化文档和 chunk 时返回 hash 与重复标记。

## 6. 面试表达模板

你可以这样讲：

```text
我在 RAG 文档管理里补了轻量去重能力。
系统保存文档时会先对内容做空白规范化，再计算 SHA-256 作为 contentHash；
每个 chunk 也会计算 chunkHash，并统计同一文档内部重复 chunk 的数量。
当前阶段我没有直接禁止重复上传，而是先把 duplicateChunkCount、chunkHash 和 isDuplicate 暴露出来，
这样后续可以在后台做重复资料治理、低质量召回分析和知识库清理。
这个设计比简单拦截更稳，因为它兼容历史数据，也保留人工审核空间。
```

## 7. 本轮测试

新增测试：

```text
tests/test_rag_document_dedup.py
```

覆盖：

- 同样内容的两篇文档会生成相同 `contentHash`；
- 同一文档里的重复 chunk 会生成相同 `chunkHash`；
- 文档返回 `duplicateChunkCount`；
- chunk 详情返回 `chunkHash` 和 `isDuplicate`。

局部验证：

```text
python -m pytest tests/test_rag_document_dedup.py tests/test_rag_documents.py tests/test_rag_document_lifecycle.py tests/test_rag_metadata_filter.py tests/test_rag_database_retrieval.py tests/test_interview_agent_route.py -q
```

结果：

```text
28 passed
```
