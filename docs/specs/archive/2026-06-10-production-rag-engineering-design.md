# AI 模拟面试系统生产级 RAG 工程化 Spec

## 1. 文档目的

本文档用于把当前 AI 模拟面试系统的 RAG 模块从“能用的 RAG”升级为“具备生产级工程化雏形的 RAG”。

这里的“生产级”不是指一次性接入所有昂贵组件，而是指核心链路具备清晰边界：

```text
文档可管理
权限可隔离
metadata 可过滤
检索可增强
结果可解释
质量可评估
日志可观测
向量库可迁移
```

本阶段仍然保持当前主系统稳定：

- 不破坏 `/api/interview/next-question`。
- 不直接引入 LangGraph / LangChain。
- 不引入 React / Vue / Next.js。
- 不做真实 Docker / Nginx / 云服务器部署。

## 2. 当前 RAG 状态

当前项目已经具备：

- 岗位知识库 RAG。
- 题库 RAG。
- 候选人画像 RAG。
- RAG 文档管理。
- chunk 切分。
- metadata 存储。
- BM25 检索。
- embedding 向量检索。
- hybrid search。
- rerank。
- RAG 命中日志。
- RAG 质量评估样例。
- 管理员后台只读查看 RAG 文档和日志。

当前短板：

- 文档没有明确生命周期状态。
- 文档没有公共/私有知识库边界。
- 检索不支持稳定 metadata filter。
- disabled 文档仍可能参与召回。
- 文档和 chunk 没有去重统计。
- hybrid 权重暂时写死。
- rerank 结果解释还不够清晰。
- evaluation case 还没有产品化管理。
- 低质量召回还没有后台质量面板。
- 向量库仍是本地 JSON embedding 字段，缺少迁移抽象。

## 3. 总体目标

本阶段完成后，项目应能在简历和面试中这样表达：

```text
我实现的不是简单 RAG demo，而是具备文档生命周期、公共/私有权限边界、metadata filter、混合检索、rerank 解释、评估 case、质量面板和向量库迁移抽象的 RAG 工程化模块。
```

## 4. 非目标

本阶段不做：

- 不接 OCR。
- 不引入 Celery / Redis 任务队列。
- 不真实接入 Qdrant / pgvector。
- 不做复杂多租户组织权限。
- 不做完整监控告警系统。
- 不做云服务器真实上线。
- 不把主流程迁移到 LangGraph。

如果实现过程中遇到以上内容，只做文档设计或抽象接口，不强行落地。

## 5. 阶段拆分

### 阶段 1：RAG 文档生命周期 + 权限边界 + metadata filter

目标：

```text
RagDocument 增加 status 和 visibility。
enabled 文档参与检索。
disabled / archived 文档不参与检索。
private 文档仅 owner 可检索。
public 文档可被所有用户检索。
检索支持基础 metadata filter。
```

状态字段：

```text
status:
  enabled
  disabled
  archived

visibility:
  private
  public
```

metadata filter 第一版支持：

```text
positionTag
category
difficulty
interviewStage
source
```

验收：

- disabled 文档不再被 BM25 / vector / hybrid / rerank 召回。
- public 文档能被非 owner 用户召回。
- private 文档不能被其他用户召回。
- metadata 不匹配的 chunk 不会进入召回结果。
- RAG 文档接口返回 status、visibility。

### 阶段 2：文档去重、chunk 去重和统计

目标：

```text
保存文档时计算 contentHash。
重复文档可被识别。
重复 chunk 可被识别或跳过。
文档详情返回 chunk 统计。
```

字段建议：

```text
content_hash
chunk_hash
duplicate_of_document_id
duplicate_chunk_count
```

第一版可以只做：

```text
content_hash
chunk_hash
duplicateChunkCount
```

不强制阻止重复上传，先让系统能识别和展示重复。

### 阶段 3：query rewrite / multi-query 检索

目标：

```text
把用户原始 query 扩展成多个检索 query。
结合岗位、阶段、简历、JD、上一轮回答做 query rewrite。
```

第一版不必调用大模型，可以先用规则生成：

```text
baseQuery
roleQuery
stageQuery
weaknessQuery
```

返回结果要记录：

```text
queryVariants
matchedQueryVariant
```

这样面试时能讲：

```text
系统不是只拿用户一句话检索，而是把岗位、面试阶段和候选人材料扩展成多路 query，提高召回覆盖。
```

### 阶段 4：hybrid search 权重配置与 rerank 解释

目标：

```text
hybrid search 的 bm25Weight / vectorWeight 可配置。
rerank 结果记录 preRerankRank、rerankScore、rankChange、explanation。
```

第一版配置可以来自：

```text
函数参数
环境变量
固定配置对象
```

不做复杂后台写配置。

### 阶段 5：RAG evaluation case 管理

目标：

```text
维护 evaluation case。
运行评测。
输出 Hit@K、MRR、关键词覆盖率、metadataMatch。
```

第一版可以继续使用本地 seed / JSON / Python 数据结构，不强制建数据库表。

但要形成稳定测试和可解释结果。

### 阶段 6：低质量召回日志与后台质量面板

目标：

```text
识别低质量召回。
管理员后台展示低质量 query、retriever、hitCount、qualityLevel、建议动作。
```

低质量条件第一版可以定义为：

```text
hitCount == 0
quality.level == weak
metadataMatch == false
keywordCoverage < 0.3
```

### 阶段 7：向量库持久化抽象设计

目标：

```text
保留当前 SQLite embedding_json。
新增 VectorStore 抽象文档和轻量接口。
后续可迁移 Qdrant / pgvector。
```

第一版不真实接入 Qdrant / pgvector。

输出：

```text
docs/learning/生产级向量库迁移设计.md
可选 backend_python/vector_store.py 抽象接口
```

## 6. 数据结构设计

### 6.1 RagDocument 新字段

```text
status: enabled / disabled / archived
visibility: private / public
content_hash: 文档内容 hash
```

### 6.2 RagChunk 新字段

```text
chunk_hash: chunk 内容 hash
```

### 6.3 RAG hit 扩展字段

```text
documentStatus
documentVisibility
metadataFilter
queryVariant
rankChange
rerankExplanation
```

## 7. 权限设计

普通用户可检索：

```text
自己的 private 文档
所有 public 文档
```

普通用户不可检索：

```text
其他用户的 private 文档
disabled / archived 文档
```

管理员后台可查看：

```text
所有文档
所有 RAG 日志
所有低质量召回
```

但第一版仍以只读为主，避免误删。

## 8. 测试策略

每阶段必须先写测试。

阶段 1 测试：

- disabled 文档不参与检索。
- public 文档可被其他用户检索。
- private 文档不能被其他用户检索。
- metadata filter 生效。
- 文档接口返回 status / visibility。

阶段 2 测试：

- 相同 content 生成相同 contentHash。
- 相同 chunk 生成相同 chunkHash。
- 文档详情返回 duplicateChunkCount。

阶段 3 测试：

- query rewrite 生成多个 queryVariants。
- multi-query 命中记录 queryVariant。

阶段 4 测试：

- hybrid 权重影响排序。
- rerank 结果包含解释字段。

阶段 5 测试：

- evaluation case 可运行。
- Hit@K、MRR、关键词覆盖率输出稳定。

阶段 6 测试：

- 低质量召回可被识别。
- admin quality endpoint 返回低质量摘要。

阶段 7 测试：

- VectorStore 抽象接口不依赖具体 Qdrant / pgvector。

## 9. 学习文档要求

每阶段完成后新增中文学习文档：

```text
17-RAG文档生命周期和权限边界.md
18-RAG文档去重和chunk统计.md
19-query-rewrite和multi-query检索.md
20-hybrid权重和rerank解释.md
21-RAG评测case和质量指标.md
22-低质量召回日志和后台质量面板.md
23-向量库持久化迁移设计.md
```

## 10. 面试表达目标

本阶段完成后，你应该能讲：

```text
我的 RAG 模块不是只做了相似度搜索，而是补了工程化链路：文档有 enabled/disabled/archived 生命周期，知识库区分 private/public 权限，检索支持 metadata filter；保存文档时会做 hash 和 chunk 统计；检索阶段支持 query rewrite、多路召回、hybrid 权重和 rerank 解释；质量侧有 evaluation case、Hit@K、MRR、关键词覆盖率和低质量召回面板；向量库侧保留本地实现，同时抽象出后续迁移 Qdrant 或 pgvector 的接口。
```

## 11. 当前执行建议

第一轮只实现阶段 1。

原因：

```text
文档生命周期、权限边界和 metadata filter 是后续所有生产级 RAG 能力的地基。
```

阶段 1 完成后，再继续阶段 2 和阶段 3。
