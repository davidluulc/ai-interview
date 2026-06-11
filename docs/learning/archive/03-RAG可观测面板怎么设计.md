# 03 RAG 可观测面板怎么设计

## 1. 本阶段做了什么

本阶段把 RAG 调试能力从“只返回原始命中结果和质量等级”，升级为“返回可读的命中解释，并在前端展示出来”。

后端 `/api/rag/debug` 现在会返回三类 RAG 的 `quality` 和 `explanations`：

- `roleKnowledge`：岗位知识库命中解释。
- `questionBank`：题库 RAG 命中解释。
- `candidateMemory`：候选人画像命中解释。

前端 RAG 调试面板会展示：

- 哪个 retriever 命中了资料。
- 命中了多少条。
- 当前质量等级是什么。
- 主要命中了哪些标题。
- 命中了哪些关键词。
- 一句面向开发者的摘要。

同时，本阶段还修复了移动端长文本撑破页面的问题。RAG 命中词、英文指标名、用户名和邮箱都可能很长，所以样式层给 RAG 解释卡片、调试明细和统计卡片增加了断行保护。

## 2. 为什么要做 RAG 可观测性

RAG 项目最怕的问题不是“模型不会回答”，而是开发者不知道模型为什么这样回答。

如果系统只把资料塞进 prompt，用户和开发者都很难判断：

- 是不是检索根本没有命中？
- 是不是命中了错误知识库？
- 是不是命中的资料和当前问题不相关？
- 是不是候选人画像没有被用上？
- 是不是题库 RAG 和岗位知识库混在一起了？

所以 RAG 工程化里需要可观测性。可观测性不是一个抽象概念，它在本项目里对应的就是：

- 后端记录和返回检索结果。
- 后端计算质量摘要。
- 后端生成可读解释。
- 前端把这些信息展示成调试面板。
- 测试保证接口字段和页面展示不会被后续改坏。

## 3. 后端怎么设计

本阶段新增了 `build_rag_debug_explanation()`。

它不调用大模型，而是用确定性代码整理检索结果：

- 先用 `normalize_rag_hit()` 把不同来源的 hit 统一成相近结构。
- 从 hit 里抽取 `title`、`matchedKeywords`、`matchedTokens` 和 metadata tags。
- 结合 `evaluate_retrieval_quality()` 的结果生成质量等级。
- 返回 `developerSummary`，方便前端直接展示。

这种设计的好处是稳定、便宜、可测试。调试解释不应该依赖大模型随机发挥，否则排查问题时反而会更混乱。

## 4. 前端怎么设计

前端新增了 `renderRagExplanationPanel()`。

它接收后端的 `explanations`，渲染成三类解释卡片。页面顺序是：

1. 先展示 RAG 质量概览。
2. 再展示 RAG 命中解释。
3. 最后展示原始命中明细。

这个顺序符合调试习惯：先看整体质量，再看原因摘要，最后需要深挖时再看原始资料。

## 5. 本阶段涉及的知识点

- **RAG hits**：检索器返回的原始命中资料。
- **质量摘要**：对命中数量、最高分、平均分、来源类型做结构化总结。
- **命中解释**：把原始命中结果整理成人能读懂的说明。
- **可观测性**：让系统内部发生了什么可以被看到、被记录、被排查。
- **接口兼容**：新增 `explanations` 字段，但保留原来的 `quality`、`roleKnowledge`、`questionBank`、`candidateMemory` 字段。
- **前端测试**：用 `.mjs` 测试验证页面会渲染命中解释，避免后续 UI 改动把调试信息弄没。
- **响应式长文本处理**：对不可控文本增加 `min-width: 0` 和 `overflow-wrap: anywhere`，避免手机端出现横向滚动。

## 6. 面试时怎么讲

可以这样表达：

> 我没有只做一个黑盒式 RAG 调用，而是给 RAG 链路加了可观测面板。后端 `/api/rag/debug` 会返回三类 RAG 的命中结果、质量摘要和命中解释，前端会把这些解释展示成调试卡片。这样当面试官问题不贴合简历或岗位时，我可以反查是岗位知识库没命中、题库没命中，还是候选人画像没有召回。这个设计提升了 RAG 系统的可排查性，也方便后续做检索质量评估和线上问题定位。

如果面试官继续深挖，可以补充：

> 命中解释没有交给大模型生成，而是用确定性代码从 hits 中抽取 title、matchedKeywords、matchedTokens 和质量等级。这样调试信息更稳定，也更容易写测试。

## 7. 本阶段验证

后端相关测试：

```text
python -m pytest tests/test_rag_debug_quality.py tests/test_rag_explain.py tests/test_rag_quality.py -q
```

结果：

```text
11 passed in 1.68s
```

前端相关测试：

```text
node tests/frontend_rag_quality.test.mjs
node tests/frontend_workbench_layout.test.mjs
```

结果：通过，无失败输出。

浏览器验证：

- 桌面端 1280px：页面可打开，没有 `undefined`，没有横向溢出，控制台无 error。
- 移动端 390px：RAG 命中解释可显示，没有 `undefined`，没有横向溢出，控制台无 error。
