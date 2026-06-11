# 前端产品化重构如何承接 RAG 和 Agent 能力

## 1. 为什么不是重写 RAG / Agent

本阶段的目标不是重新开发 RAG 检索链路，也不是重写 Agent Orchestrator。

后端已经有三类 RAG、文档生命周期、metadata filter、query rewrite、hybrid search、rerank、RAG 日志、Agent State、Tool Calls、Agent Decision、fallback、guardrail、topic shift 和训练任务等能力。

前端产品化要解决的问题是：这些工程能力怎样被用户和管理员看懂。

如果继续把字段直接堆在页面上，用户看到的是 `nextAction`、`toolCalls`、`queryVariants`、`rerankExplanation` 这一类技术字段，会觉得系统像调试工具。产品化后的页面要把它们翻译成：

- 为什么这样问；
- 参考了哪些资料；
- 当前知识库是否可用；
- 哪些召回质量差；
- 下一步应该练什么。

## 2. 信息架构怎么拆

本轮重构仍然保持原生前端结构：

```text
index.html
styles.css
app.js
tests/*.mjs
```

没有引入 React、Vue、Next.js，也没有修改后端 API 合约。

页面被拆成五个主区域：

- 账号与档案；
- 面试工作台；
- 训练中心；
- 知识库与 RAG；
- 管理员后台。

这样做的意义是把用户路径变清楚：

```text
登录
-> 建立投递档案
-> 开始面试
-> 查看为什么这样问
-> 生成报告
-> 进入训练中心继续练
```

管理员路径也变清楚：

```text
后台概览
-> 查看 RAG 质量问题
-> 查看低质量召回样例
-> 判断是空召回、弱召回，还是未进入 Prompt
```

## 3. RAG 可解释怎么展示

RAG 后端返回的字段偏工程化，例如：

```text
status
visibility
chunkCount
duplicateChunkCount
queryVariants
matchedQueryVariant
rerankExplanation
```

前端产品化后的展示方式是：

- `status` 转成启用、停用、归档；
- `visibility` 转成私有、公开；
- `chunkCount` 告诉用户文档被切成多少块；
- `duplicateChunkCount` 告诉用户文档是否存在重复切片；
- `queryVariants` 展示为多路 query；
- `matchedQueryVariant` 展示为命中 query；
- `rerankExplanation` 展示为重排解释。

这样用户和管理员看到的不只是“召回结果”，还能知道召回为什么发生、质量问题可能在哪里。

## 4. Agent 可观测怎么展示

Agent 后端的关键字段包括：

```text
agentDecision
toolCalls
nodeTrace
fallbackUsed
guardrailApplied
topicShift
selectedTrainingTask
```

这些字段不应该默认全部展示给普通用户。

本轮重构采用两层展示：

普通用户层：

- 为什么这样问；
- 当前动作，比如降低难度、切换话题、继续深挖；
- 参考了岗位知识库、题库 RAG、候选人画像中的哪些工具；
- 推荐训练任务。

开发调试层：

- nodeTrace；
- toolCalls；
- fallback；
- guardrail；
- topic shift；
- 触发规则。

这样既能让用户看懂面试官的行为，也保留了工程排查能力。

## 5. 面试时怎么讲

可以这样表达：

```text
我做的不是单纯页面美化，而是 AI 应用的前端产品化重构。

后端已经具备 RAG 和 Agent 工程能力，但这些能力如果直接以 JSON 字段展示，用户很难理解。
所以我把页面拆成面试工作台、训练中心、知识库与 RAG、管理员后台几个区域。

在面试工作台里，我把 Agent Decision 转译成“为什么这样问”，同时保留开发者调试区查看 nodeTrace、toolCalls、fallback 和 topic shift。

在知识库与 RAG 页面里，我把文档生命周期、权限、chunk 数、重复 chunk、多路 query 和 rerank 解释展示出来，让 RAG 不再是黑箱。

在训练中心里，我把面试报告里的薄弱点转成训练行动计划，形成“面试 -> 复盘 -> 训练 -> 再练”的闭环。

管理员后台则把低质量召回拆成空召回、弱召回和未进入 Prompt，方便排查 RAG 质量问题。
```

这套改动体现的是：AI 应用不是只会调模型，还要把模型、RAG、Agent 的内部过程变成用户能理解、开发者能排查、管理员能运营的产品界面。
