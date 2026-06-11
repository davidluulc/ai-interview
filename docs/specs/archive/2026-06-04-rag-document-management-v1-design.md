# RAG 知识库文档管理 V1 设计说明

## 背景

当前系统已经具备三个召回来源：岗位知识库、题库、候选人画像。岗位知识库和题库仍主要依赖 `data/*.json` 静态种子文件，适合 MVP，但不利于后续上线和工程化扩展。真实业务里的 RAG 通常需要把资料拆成“文档”和“切片”两层：文档用于管理来源、类型、权限和生命周期，切片用于实际检索和进入 prompt。

## 目标

本版本建设一个轻量但可扩展的 RAG 文档管理后端能力：

- 支持登录用户创建、查看、删除自己的 RAG 文档。
- 文档创建后自动按段落切分为多个 chunk。
- chunk 保存知识库类型、标题、内容、关键词、元数据和顺序。
- 岗位知识库和题库检索优先使用数据库中的 chunk。
- 数据库没有命中时继续使用当前 JSON 种子数据兜底。
- 后端接口按用户隔离，用户只能看到和检索自己的文档。

## 非目标

V1 暂不实现以下能力：

- PDF、Word、图片 OCR 自动解析。
- 向量数据库、embedding、reranker。
- 知识库版本管理和增量重建。
- 完整后台管理 UI。
- 异步任务队列。

这些能力会放到后续 RAG 工程化阶段逐步补强。

## 核心概念

`RagDocument` 表示一份知识库文档。它保存文档标题、知识库类型、来源类型、原文内容、用户归属和创建时间。知识库类型使用 `role_knowledge` 和 `question_bank`，分别对应岗位知识库和题库。

`RagChunk` 表示一段可被检索的知识切片。它保存切片标题、正文、关键词、元数据、chunk 顺序和用户归属。模型最终使用的是命中的 chunk，而不是整篇文档。

`metadata_json` 保存结构化扩展信息，例如岗位标签、分类、难度、页码、章节。V1 先使用 JSON 字符串保存，后续迁移到 PostgreSQL 或 MySQL 时可以保留这个设计。

## 数据流

1. 用户登录。
2. 用户通过 `/api/rag/documents` 创建文档。
3. 后端根据空行和段落长度把 `content` 切分成 chunk。
4. 每个 chunk 自动提取关键词，并继承文档的知识库类型、标题和元数据。
5. 面试提问、报告生成或 RAG 调试时，检索函数先查当前用户的数据库 chunk。
6. 如果数据库 chunk 有命中，返回数据库结果。
7. 如果没有命中，回退到当前 JSON 种子知识库。
8. RAG 日志继续记录 retriever 名称、query、命中数量和命中摘要。

## 接口设计

`GET /api/rag/documents`

返回当前用户的文档列表。支持可选参数 `knowledgeBase` 过滤知识库类型。

`POST /api/rag/documents`

创建文档并同步生成 chunks。请求体字段：

- `title`: 文档标题。
- `knowledgeBase`: `role_knowledge` 或 `question_bank`。
- `sourceType`: 来源类型，V1 默认 `manual`。
- `content`: 文档正文。
- `metadata`: 可选对象，例如 `{"positionTag": "ai_app_intern", "category": "technical"}`。

`GET /api/rag/documents/{document_id}`

返回文档详情和对应 chunks。

`DELETE /api/rag/documents/{document_id}`

删除当前用户自己的文档，同时删除对应 chunks。

## 检索策略

V1 继续使用关键词检索，原因是可解释、易调试、适合当前学习阶段。数据库 chunk 检索规则：

- query 来自目标岗位、岗位标签、简历、JD、公司要求和当前面试阶段。
- 对 title、content、keywords、metadata 进行关键词匹配。
- 关键词命中权重大于普通 token 命中。
- `question_bank` 会对 `positionTag` 和 stage/category 做额外加权。
- 返回结构保持兼容现有前端和 prompt 格式。

## 测试策略

后端测试覆盖：

- 未登录不能访问文档接口。
- 用户可以创建、列表、详情、删除文档。
- 文档创建后会生成 chunks。
- 用户只能访问自己的文档。
- 岗位知识库检索能命中数据库 chunk。
- 题库检索能命中数据库 chunk。
- 数据库没有命中时仍能使用 JSON 种子兜底。

## 面试可解释口径

可以这样描述这一阶段的设计：

> 我们没有一开始就上向量数据库，而是先把 RAG 拆成文档层和切片层。文档层负责来源、权限和生命周期，切片层负责召回。第一版使用关键词检索保证可解释性，并保留静态种子数据作为兜底。这样后续接入 embedding、Qdrant、reranker 或异步入库时，不需要推翻业务结构。
