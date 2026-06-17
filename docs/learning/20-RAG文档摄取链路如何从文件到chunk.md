# 20 RAG 文档摄取链路如何从文件到 chunk

## 1. 为什么 RAG 不只是检索

很多人一提 RAG，只会想到“向量数据库”和“语义检索”。但真实工程里，检索只是后半段。前半段更基础，也更容易出线上问题：资料怎么进入知识库。

如果资料入口不可靠，后面的 BM25、embedding、hybrid search、rerank 都会被影响。比如：

- 文件解析失败，知识库里根本没有内容。
- 文本清洗不干净，chunk 里混入乱码、空行、重复内容。
- chunk 切得太碎，语义不完整。
- metadata 缺失，后续无法按岗位、章节、权限过滤。
- 入库失败没有任务状态，用户只看到“没效果”，开发者也不好排查。

所以生产级 RAG 链路一般分成两段：

```text
文档摄取链路：文件 -> 文本 -> 清洗 -> chunk -> metadata -> 入库
检索生成链路：query -> 召回 -> 重排 -> prompt -> LLM 生成
```

本阶段补的是第一段。

## 2. 文件上传后后端做了什么

当前系统新增了文件导入入口。用户在 Vue3 知识库页面上传文件后，前端会用 `FormData` 把标题、知识库类型、可见性、metadata 和文件一起发给：

```text
POST /api/rag/documents/upload
```

后端拿到请求后，主要做这些事：

1. 创建 `rag_ingestion` 任务状态。
2. 校验文件名和扩展名，只允许 txt、md、pdf。
3. 校验文件是否为空、是否超过大小限制。
4. 从文件中提取文本。
5. 清洗文本。
6. 生成 preview，包括文本长度、chunk 数量和 warning。
7. 调用现有 `create_rag_document_with_embeddings()`。
8. 写入 `RagDocument` 和 `RagChunk`。
9. 成功时记录 document 和 preview。
10. 失败时记录错误原因。

这一步没有重写 RAG 检索算法，而是复用了已有入库和 embedding 逻辑。

## 3. 文本解析、清洗、chunk 切分分别解决什么问题

文本解析解决的是“文件里的内容怎么拿出来”。

- txt 和 md：按 UTF-8 解码。
- pdf：优先使用本地 PDF 解析库，如果依赖不可用或解析失败，返回明确错误。

文本清洗解决的是“拿出来的文本能不能用”。

当前清洗逻辑会处理：

- Windows / Unix 换行差异。
- 控制字符。
- 多余空格和 tab。
- 过多空行。
- 每行首尾空白。

chunk 切分解决的是“模型和检索系统一次看多大一段资料”。

当前阶段复用已有的 `split_content_into_chunks()`：

- 优先按段落切。
- 段落太长时按最大字符数切。
- 切完后生成 chunk hash 和关键词。

面试时可以这样表达：

```text
我把 RAG 的数据入口拆成解析、清洗和切分三步。解析负责把不同文件类型转成文本，清洗负责让文本变得稳定可处理，chunk 切分负责把长文档拆成适合召回和 prompt 注入的小片段。
```

## 4. 为什么需要 ingestion task

文件导入不是一个瞬时小动作。真实系统里，它可能包含：

- 文件上传。
- 文本解析。
- chunk 切分。
- embedding 生成。
- 向量库写入。
- 去重。
- metadata 校验。

任何一步都可能失败。如果没有任务状态，用户只会感觉“点了没反应”。开发者也不知道失败发生在解析、清洗、embedding，还是数据库写入。

所以本项目使用 `task_status.py` 记录导入任务：

```text
pending -> running -> success
pending -> running -> failed
```

成功时任务结果里会有：

- document。
- preview。
- textLength。
- chunkCount。
- warnings。

失败时会有：

- error。
- message。

这就是工程化里的可观测性。

## 5. 它和 Celery / Redis 的关系

当前阶段用的是内存任务状态，这是一个轻量版本。它适合本地开发和 MVP 演示，但服务重启后任务记录会丢失。

未来如果要升级到生产级，可以这样迁移：

```text
FastAPI 接收上传请求
-> 保存原始文件或临时文件
-> 创建数据库任务记录
-> 投递 Celery 任务
-> Celery worker 解析、清洗、切 chunk、embedding、入库
-> Redis / 数据库记录任务进度
-> 前端轮询任务状态
```

也就是说，本阶段先把接口契约、任务状态字段和页面体验跑通，后续再把执行方式从“同步执行”替换成“异步 worker 执行”。

## 6. 面试时怎么讲

可以这样讲：

```text
我做的 RAG 不是只停留在检索阶段，还补了文档摄取链路。用户可以在知识库页面上传 txt、md 或 pdf 文件，后端会先校验文件类型和大小，然后提取文本、清洗文本、生成 chunk 预览，再复用已有的 create_rag_document_with_embeddings 写入 RagDocument 和 RagChunk。

整个导入过程会创建 rag_ingestion 任务状态，成功时能看到 documentId、文本长度和 chunk 数，失败时能看到明确错误原因。这样做的好处是把 RAG 入库过程从黑箱变成可观测流程，后续也可以平滑迁移到 Celery + Redis 的异步入库架构。
```

如果面试官追问“为什么不一开始就上 Celery”，可以回答：

```text
我先做同步导入加任务状态，是为了把接口契约、错误处理、文本解析和前端体验跑通。Celery 主要改变任务执行方式，不改变业务链路本身。等链路稳定后，再把任务状态从内存迁移到 Redis 或数据库，把解析入库逻辑放到 worker 里，会更稳。
```
