# 18. RAG 元数据过滤与业务召回边界

## 1. metadata filter 解决什么问题

RAG 检索不能只看“文本像不像”。真实业务里，经常会出现这种情况：

```text
用户想面 AI 应用开发岗
但是知识库里也有 Python 后端岗、Java 后端岗、测试岗的资料
如果只靠相似度，系统可能召回“看起来也相关但岗位不对”的内容
```

metadata filter 的作用就是在排序前先限定候选范围：

```text
先按岗位、分类、难度、阶段、来源过滤
再做 BM25 / vector / hybrid / rerank 排序
```

它不是替代相似度，而是给相似度检索加业务边界。

## 2. 本轮支持的元数据字段

本轮第一版支持：

```text
positionTag    : 岗位标签，例如 ai_app_intern / python_backend_intern
category       : 资料分类，例如 technical / project / behavioral
difficulty     : 题目难度，例如 basic / medium / hard
interviewStage : 面试阶段，例如 self_intro / project / technical
source         : 来源，例如 manual / imported
```

这些字段都来自文档或 chunk 的 `metadata_json`。

## 3. metadata filter 和 BM25 / 向量检索的关系

可以把 RAG 召回拆成两层：

```text
第一层：业务过滤
  根据 metadata filter 去掉明显不该参与本场景的资料

第二层：相关性排序
  对剩下的候选资料做 BM25、向量检索、hybrid search 或 rerank
```

如果没有第一层，向量检索可能会因为语义相似召回错误场景的资料。

例如：

```text
query: RAG 日志怎么设计？

可能相关的资料：
1. AI 应用开发岗：RAG 命中日志字段设计
2. Java 后端岗：接口日志和链路追踪
3. 测试岗：缺陷日志记录规范
```

三者都可能“语义相关”，但只有第 1 条最贴合 AI 应用开发岗。

## 4. 本轮代码怎么实现

核心实现位置：

- `backend_python/rag_store.py`
  - `normalize_metadata_filter()`
  - `chunk_matches_metadata_filter()`
- `backend_python/retrieval_service.py`
  - `retrieve_chunks(..., metadata_filter=...)`
  - `retrieve_vector_chunks(..., metadata_filter=...)`
  - `retrieve_hybrid_chunks(..., metadata_filter=...)`
  - `retrieve_hybrid_rerank_chunks(..., metadata_filter=...)`
- `backend_python/rag.py`
  - `retrieve_role_context()` 会根据 `profile.positionTag` 传入过滤条件。
- `backend_python/question_rag.py`
  - `retrieve_questions()` 会根据 `profile.positionTag` 和可选 `profile.difficulty` 传入过滤条件。

## 5. 为什么要把 filter 摘要写回 hit

本轮命中结果里会带：

```text
metadataFilter
metadataMatch
```

这不是为了前端好看，而是为了调试和可观测性。

当用户问“为什么这条资料被召回”时，我们不仅能看到分数，还能看到：

```text
这次检索用了什么过滤条件
这条资料是否通过了过滤条件
```

这对后续 RAG 命中日志、低质量召回面板和面试复盘都很重要。

## 6. profile 推导 filter 为什么要做软回退

本轮有一个重要兼容细节：

```text
如果用户显式传入 metadata_filter，则严格过滤。
如果系统根据 profile.positionTag 自动推导 filter，则先按 filter 检索；
如果过滤后没有数据库命中，会回退到未过滤检索。
```

原因是早期用户自建知识库可能没有填写 `positionTag`。如果自动 filter 过于严格，旧资料会突然无法召回，导致面试主流程体验下降。

所以本项目采用：

```text
显式 filter = 严格规则
profile 推导 filter = 优先规则，空命中时兼容回退
```

面试时可以说：

```text
我区分了显式过滤和系统自动推导过滤。
显式 metadata filter 用于后台检索和质量评估时是强约束；
而面试主流程里根据 profile.positionTag 推导出来的 filter 是优先约束，
如果用户历史文档没有维护 metadata，系统会回退到未过滤检索，避免老数据不可用。
```

## 7. 面试表达模板

你可以这样讲：

```text
我的 RAG 检索不是直接把 query 扔给向量库或 BM25。
我先做了一层 metadata filter，把候选资料限制在当前岗位、题目分类、难度和面试阶段范围内。
比如用户选择 AI 应用开发岗，系统会优先只在 positionTag=ai_app_intern 的资料里召回。
然后再对过滤后的候选集做 BM25、向量检索、hybrid search 或 rerank。
这样可以减少语义相似但业务场景不匹配的误召回。
同时我会把 metadataFilter 和 metadataMatch 写入 hit，方便后续 RAG 日志排查。
```

## 8. 本轮测试

新增测试文件：

```text
tests/test_rag_metadata_filter.py
```

覆盖规则：

- `positionTag` 可以保留匹配 chunk；
- `positionTag` 可以排除不匹配 chunk；
- `category` 可以过滤分类；
- `difficulty` 可以过滤题库难度；
- `interviewStage + source` 可以组合过滤；
- 命中结果会返回 `metadataFilter` 和 `metadataMatch`。

同时更新：

```text
tests/test_rag_database_retrieval.py
```

验证：

- 岗位知识库 RAG 会把 `profile.positionTag` 传到底层检索；
- 题库 RAG 会把 `profile.positionTag` 传到底层检索；
- 上层返回结果保留 `metadataFilter` 和 `metadataMatch`。

局部验证：

```text
python -m pytest tests/test_rag_metadata_filter.py tests/test_rag_database_retrieval.py -q
```

结果：

```text
10 passed
```
