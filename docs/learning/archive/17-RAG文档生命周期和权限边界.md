# 17. RAG 文档生命周期和权限边界

## 1. 本轮为什么要做这个能力

MVP 版 RAG 只需要“能把资料存进去、能把相似内容召回来”。但生产级 RAG 不能只追求能用，还要知道：

- 哪些文档允许参与检索；
- 哪些文档已经停用或归档；
- 哪些文档只能当前用户自己用；
- 哪些文档可以作为公共知识被其他用户召回；
- 检索结果为什么没有越权。

所以本轮给 `RagDocument` 增加了两个字段：

```text
status: enabled / disabled / archived
visibility: private / public
```

这两个字段让知识库从“资料堆”升级成“可管理、可隔离、可审计的资料系统”。

## 2. status 是什么

`status` 表示文档当前是否参与检索。

```text
enabled  : 正常启用，可以参与 RAG 召回
disabled : 暂时停用，不参与 RAG 召回
archived : 归档保留，不参与 RAG 召回
```

面试时可以这样讲：

```text
我没有直接删除文档，而是给文档设计了生命周期状态。
enabled 文档可以参与检索，disabled 和 archived 文档不会进入召回候选集。
这样做的好处是可以保留历史资料和审计痕迹，同时避免旧资料继续影响模型回答。
```

## 3. visibility 是什么

`visibility` 表示文档的可见范围。

```text
private : 用户私有知识库，只有 owner 可以检索
public  : 公共知识库，其他用户也可以检索
```

注意：本轮只开放“公共文档可被检索”，并没有开放“其他用户可编辑公共文档”。

面试时可以这样讲：

```text
我把知识库分成 private 和 public 两类。
private 文档只允许 owner 检索，public 文档可以被其他用户作为公共知识召回。
但是文档管理接口仍然做 owner 校验，普通用户不能修改别人的文档。
```

## 4. 检索过滤规则

本轮核心过滤规则是：

```text
文档必须 status == enabled
并且：
  文档属于当前用户
  或者文档 visibility == public
```

换成代码层面的思路就是：

```text
从 RagChunk 出发 join RagDocument
只保留 enabled 文档下的 chunk
只保留当前用户自己的文档，或者 public 文档
```

这比只写：

```text
RagChunk.user_id == current_user.id
```

更接近真实产品，因为真实系统里会同时存在“用户私有资料”和“平台公共知识库”。

## 5. 本轮改动对应的代码

主要代码位置：

- `backend_python/db_models.py`
  - `RagDocument` 增加 `status` 和 `visibility` 字段。
- `backend_python/database.py`
  - 给已有 SQLite 表补充新字段和索引。
- `backend_python/rag_store.py`
  - 创建文档时写入默认生命周期字段。
  - 序列化接口返回 `status` 和 `visibility`。
- `backend_python/retrieval_service.py`
  - BM25、vector、hybrid、rerank 都复用生命周期过滤规则。
- `backend_python/routes/rag_documents.py`
  - 创建文档时允许传 `visibility`。
  - 新增 `PATCH /api/rag/documents/{document_id}/status`。

## 6. 为什么这是生产级 RAG 的第一步

如果没有生命周期和权限边界，后面做再复杂的 embedding、hybrid search、rerank 都会有隐患：

- 停用资料仍可能影响回答；
- 其他用户的私有简历资料可能被错误召回；
- 管理后台无法控制知识库上下线；
- RAG 结果无法解释“为什么这个资料可以被用”。

所以生产级 RAG 的顺序通常是：

```text
先定义资料边界
再做检索增强
最后做质量评估和后台治理
```

## 7. 面试表达模板

你可以这样说：

```text
我的 RAG 模块不是只做了简单相似度检索。
我先给知识库文档设计了生命周期和权限边界：
文档有 enabled、disabled、archived 三种状态，只有 enabled 文档能参与召回；
同时文档区分 private 和 public，private 只能被 owner 检索，public 可以作为平台公共知识被其他用户召回。
实现上，我在检索时从 RagChunk join RagDocument，
统一过滤 status 和 visibility，这样 BM25、向量检索、hybrid search、rerank 都能复用同一套边界规则。
这样后续做 metadata filter、query rewrite、rerank 解释和质量面板时，基础数据边界是可靠的。
```

## 8. 本轮测试

新增测试文件：

```text
tests/test_rag_document_lifecycle.py
```

覆盖规则：

- disabled 文档不会被召回；
- public 文档可以被其他用户召回；
- private 文档不会被其他用户召回；
- 文档接口返回 `status` 和 `visibility`；
- owner 可以通过接口更新文档状态。

本轮局部验证：

```text
python -m pytest tests/test_rag_document_lifecycle.py tests/test_rag_documents.py tests/test_retrieval_service.py tests/test_rag_vector_retrieval.py tests/test_rag_hybrid_retrieval.py tests/test_rag_rerank_retrieval.py tests/test_interview_agent_route.py -q
```

结果：

```text
33 passed
```
