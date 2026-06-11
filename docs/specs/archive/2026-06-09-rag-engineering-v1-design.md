# RAG 工程化增强 V1 设计

## 1. 文档目的

本文档用于约束 AI 模拟面试系统阶段三：RAG 工程化增强 V1。

阶段二已经完成 Agent 工程化增强，系统具备 `Agent State`、`ToolCalls`、`nodeTrace` 和 `Interview Orchestrator Agent`。阶段三的重点是让三个 RAG 不只是“能召回内容”，而是具备更清楚的数据边界、元数据规范、质量评估和可解释命中日志。

本阶段目标是让项目在面试中能讲清楚：

- 三个 RAG 分别存什么、查什么、服务哪个业务目标。
- RAG 文档和 chunk 的元数据如何设计。
- 一次问题生成时，query 怎么构造，命中了哪些内容，为什么命中。
- 如何判断召回质量高低。
- 为什么当前阶段不急着直接上向量数据库或复杂 RAG 框架。
- 后续如何从关键词 / BM25 / hybrid 检索迁移到更完整的向量 RAG。

## 2. 当前基础

当前项目已经具备以下 RAG 能力：

- `backend_python/rag.py`
  - 岗位知识库 RAG。
  - 支持 JSON 种子数据和数据库 chunk 检索回退。
  - 输出岗位知识、评分点、风险信号和追问方向。

- `backend_python/question_rag.py`
  - 题库 RAG。
  - 支持岗位标签、阶段、难度、题目、参考答案和答题要点。

- `backend_python/candidate_memory.py`
  - 候选人画像 RAG。
  - 基于历史面试记录、回答、报告风险点和训练建议召回候选人薄弱点。
  - 已具备用户隔离和投递档案优先召回雏形。

- `backend_python/retrieval_service.py`
  - 已支持 BM25、vector、hybrid、hybrid_rerank 等检索函数。
  - 当前业务链路主要使用轻量 BM25 / 数据库 chunk 检索。

- `backend_python/rag_logging.py`
  - 已具备 RAG 命中日志基础能力。

- `backend_python/rag_evaluation.py`
  - 已具备轻量 RAG 质量评估脚本基础。

当前不足：

- 三个 RAG 的文档 / chunk 元数据字段还不够统一。
- RAG 命中日志更偏技术调试，普通用户还不容易理解“为什么问这道题”。
- 质量评估样例集还不够系统，无法稳定比较不同召回策略。
- RAG 检索结果和 Agent ToolCalls 已经打通，但还需要更清晰地展示命中原因、召回质量和进入 prompt 的证据。
- 知识库文档管理页面已有雏形，但还需要围绕工程化字段做增强。

## 3. 阶段三 V1 目标

阶段三 V1 的目标是：

```text
把三个 RAG 从“能召回内容”升级为“边界清晰、元数据统一、命中可解释、质量可评估、日志可复盘”的工程化 RAG 模块。
```

完成后应能回答：

- 岗位知识库 RAG、题库 RAG、候选人画像 RAG 的职责边界是什么？
- 每个 chunk 至少应该带哪些 metadata？
- 一次 RAG 调用如何记录 query、命中 chunk、分数、命中原因和是否进入 prompt？
- 什么是 Hit@K、MRR、关键词覆盖率，它们在本项目里怎么落地？
- 如果 AI 面试官问得不好，如何判断是知识库问题、召回问题、重排问题、prompt 问题，还是 Agent 决策问题？
- 未来如何升级到 embedding + hybrid search + rerank？

## 4. 非目标

阶段三 V1 明确不做：

- 不直接引入新的向量数据库，例如 Qdrant、Milvus、Chroma、pgvector。
- 不直接引入 LangChain 或 LangGraph。
- 不做复杂 OCR、PDF 多格式解析流水线。
- 不做 Celery / Redis 异步任务队列。
- 不做 Docker、Nginx、云服务器上线。
- 不重构前端框架，不引入 React、Vue、Next.js。
- 不新增复杂管理员后台。
- 不把现有 RAG 全部推倒重写。
- 不追求一次性实现企业级完整 RAG 平台。

## 5. 三个 RAG 职责边界

### 5.1 岗位知识库 RAG

职责：

- 存岗位 JD、岗位相关技术栈、业务场景、能力要求、评分点和风险信号。
- 为面试问题生成提供岗位能力依据。
- 为报告生成提供评分维度和风险判断依据。
- 为 Agent 判断追问方向提供可解释上下文。

典型内容：

- AI 应用开发岗位对 RAG、Agent、模型调用、FastAPI、数据库、缓存、部署的要求。
- 后端开发岗位对接口设计、鉴权、数据库事务、日志、异常处理的要求。
- 面试中常见项目深挖点和风险信号。

不负责：

- 不保存候选人私人简历全文。
- 不保存候选人历史回答。
- 不直接决定最终问题，只提供上下文和依据。

### 5.2 题库 RAG

职责：

- 存结构化面试题、参考答案、答题要点、岗位标签、阶段、难度和标签。
- 为模型生成问题提供可参考题目。
- 为报告生成提供答题要点覆盖依据。

典型内容：

- 技术基础题。
- 项目深挖题。
- 场景排查题。
- 行为面试题。
- HR 和规划类题。

不负责：

- 不存候选人个人数据。
- 不要求模型原样照搬题库题目。
- 不替代 Agent 的动作决策。

### 5.3 候选人画像 RAG

职责：

- 存当前用户的简历概况、历史回答、历史报告、薄弱点和训练建议。
- 优先按当前投递档案召回历史。
- 当前投递档案数据不足时，回退到当前用户全局历史。
- 为个性化追问、复盘报告和训练建议提供依据。

典型内容：

- 候选人某次面试中答不上来的问题。
- 高频薄弱点，例如 RAG 召回链路、数据库事务、项目职责表达。
- 历史训练建议和下一轮优先练习方向。

不负责：

- 不召回其他用户数据。
- 不把候选人历史当成岗位知识。
- 不编造候选人没有出现过的弱点。

## 6. 统一 Metadata 规范

阶段三 V1 要为可召回内容建立统一 metadata 规范。目标不是一次性补齐所有字段，而是让后续每个 chunk 都能被过滤、解释、评估和回溯。

### 6.1 必备字段

| 字段 | 含义 | 示例 |
| --- | --- | --- |
| `knowledgeBase` | 知识库类型 | `role_knowledge`、`question_bank`、`candidate_memory` |
| `documentId` | 所属文档 ID | `12` |
| `chunkId` | 切片 ID | `81` |
| `title` | 文档或 chunk 标题 | `RAG 召回链路追问` |
| `content` | 可召回正文 | `RAG 通常包含 query 构造、检索、重排...` |
| `source` | 来源 | `database`、`seed_json`、`interview_history` |
| `ownerUserId` | 所属用户 | `1` |
| `applicationProfileId` | 所属投递档案 | `3` |
| `positionTag` | 岗位标签 | `ai_application` |
| `interviewStage` | 面试阶段 | `技术追问` |
| `difficulty` | 难度 | `basic`、`medium`、`hard` |
| `tags` | 标签 | `["RAG", "BM25", "Agent"]` |
| `createdAt` | 创建时间 | `2026-06-09T10:00:00` |

### 6.2 字段命名约束

后端 Python 内部可以继续使用 snake_case，但接口返回给前端和日志 JSON 建议统一使用 camelCase。

必须避免同义字段混用：

- 使用 `knowledgeBase`，不再混用 `sourceType` 表示同一概念。
- 使用 `positionTag`，不再混用 `roleTag`、`jobTag`。
- 使用 `interviewStage`，不再混用 `stage`、`category` 表示阶段。
- 使用 `applicationProfileId` 表示投递档案，不用 `profileId`。

## 7. RAG 命中解释设计

### 7.1 命中日志目标

RAG 命中日志用于回答：

```text
这次模型为什么看到了这些资料？
这些资料来自哪个知识库？
命中分数是多少？
命中了哪些关键词？
是否进入 prompt？
如果问题问得不好，应该排查哪里？
```

### 7.2 日志结构建议

单次 retriever 日志建议包含：

```json
{
  "requestType": "next_question",
  "queryText": "AI 应用开发实习生 RAG 技术追问",
  "retrieverName": "role_knowledge",
  "retrievalMode": "bm25",
  "hitCount": 3,
  "usedInPrompt": true,
  "quality": {
    "level": "good",
    "hitCount": 3,
    "topScore": 0.91
  },
  "hits": [
    {
      "chunkId": 81,
      "documentId": 12,
      "title": "RAG 召回链路追问",
      "score": 0.91,
      "matchedTokens": ["rag", "召回", "检索"],
      "metadata": {
        "knowledgeBase": "role_knowledge",
        "positionTag": "ai_application",
        "interviewStage": "技术追问"
      }
    }
  ]
}
```

### 7.3 普通解释与开发者调试分层

普通用户不需要看到大段 JSON。

普通视图展示：

- 本题考察点。
- 追问依据。
- 参考能力点。
- 建议补强方向。

开发者调试视图展示：

- queryText。
- retrieverName。
- retrievalMode。
- hitCount。
- score。
- matchedTokens / matchedKeywords。
- metadata。
- usedInPrompt。

## 8. RAG 质量评估 V1

阶段三 V1 先做轻量评估，不引入完整评估框架。

### 8.1 样例集设计

建立固定评估样例，每条样例包含：

```json
{
  "caseId": "role-rag-001",
  "retrieverName": "role_knowledge",
  "queryText": "AI 应用开发实习生 RAG 召回链路",
  "expectedKeywords": ["RAG", "召回", "chunk", "重排"],
  "expectedKnowledgeBase": "role_knowledge",
  "expectedPositionTag": "ai_application",
  "expectedStage": "技术追问",
  "topK": 3
}
```

### 8.2 指标解释

| 指标 | 通俗理解 | 本项目用法 |
| --- | --- | --- |
| Hit@K | 前 K 条里有没有命中预期内容 | 判断检索结果是否至少召回相关资料 |
| MRR | 正确结果排得越靠前越好 | 判断好资料是不是排在前面 |
| 关键词覆盖率 | 预期关键词命中了多少 | 判断召回内容是否覆盖关键能力点 |
| 空召回率 | 没有命中内容的比例 | 判断知识库是否太少或 query 构造不准 |
| metadata 匹配率 | 岗位、阶段、知识库是否匹配 | 判断过滤和元数据是否可靠 |

### 8.3 第一阶段验收阈值

阶段三 V1 不追求特别高的指标，但要建立可复跑基线：

- 评估样例不少于 12 条。
- 三个 RAG 每类至少 4 条样例。
- 每次运行评估脚本能输出整体结果。
- Hit@3、MRR、关键词覆盖率必须有数值结果。
- 空召回 case 必须能被识别。

## 9. 排查链路设计

当 AI 面试体验不好时，按以下顺序排查：

1. 看 Agent Decision
   - 是否一直 `deep_follow_up`。
   - 是否触发 `lower_difficulty` 或 `switch_topic`。
   - 是否出现 fallback。

2. 看 ToolCalls
   - 三个 RAG 是否成功调用。
   - hitCount 是否为 0。
   - 耗时是否异常。

3. 看 RAG 命中日志
   - query 是否合理。
   - 命中 chunk 是否相关。
   - 分数是否过低。
   - metadata 是否匹配岗位和阶段。

4. 看 Prompt 输入
   - 命中内容是否进入 prompt。
   - 上下文是否过长或噪声过多。

5. 看最终问题
   - 是否使用了 RAG 内容。
   - 是否重复问题。
   - 是否超出候选人资料边界。

这条排查链路要能在面试中讲出来，它体现的是 AI 应用工程化能力。

## 10. 后端模块设计

阶段三 V1 推荐演进文件：

```text
backend_python/rag_metadata.py
backend_python/rag_explain.py
backend_python/rag_evaluation.py
backend_python/rag_evaluation_seed.py
backend_python/rag_logging.py
backend_python/retrieval_service.py
backend_python/routes/rag.py
backend_python/routes/rag_documents.py
```

职责建议：

- `rag_metadata.py`
  - 统一 chunk metadata 字段。
  - 提供 metadata normalize 函数。
  - 提供 metadata filter 判断函数。

- `rag_explain.py`
  - 把命中结果转成普通用户能读懂的追问依据。
  - 把命中结果转成开发者调试摘要。

- `rag_evaluation.py`
  - 继续承载 Hit@K、MRR、关键词覆盖率等评估逻辑。
  - 输出结构化评估报告。

- `rag_evaluation_seed.py`
  - 管理固定评估样例集。
  - 覆盖三个 RAG。

- `rag_logging.py`
  - 扩展日志摘要字段。
  - 确保不记录敏感明文。

- `retrieval_service.py`
  - 保持检索算法入口。
  - 后续支持 BM25、vector、hybrid、rerank 策略对比。

## 11. 前端设计

阶段三 V1 前端只做增强，不做整体重构。

### 11.1 RAG 调试面板

增强内容：

- 展示 queryText。
- 展示 retrieverName。
- 展示 retrievalMode。
- 展示 hitCount。
- 展示 top score。
- 展示 matchedTokens / matchedKeywords。
- 展示 metadata。
- 展示 usedInPrompt。

### 11.2 普通用户解释

在面试问题或复盘中，逐步加入：

- “这道题为什么问”。
- “参考了哪些能力点”。
- “你的回答缺了哪些要点”。
- “下一轮建议怎么练”。

不要把大段 JSON 直接暴露给普通用户。

## 12. 数据安全与权限

阶段三 V1 必须守住：

- 用户只能召回自己的候选人画像。
- 用户只能查看自己的 RAG 日志。
- 用户只能管理自己的私有知识库文档。
- 系统公共岗位知识和题库可以共享。
- 日志中不记录 API Key、密码、refresh token。
- 简历和回答内容进入日志时只保留摘要，不保存过长全文。
- Debug 接口不能跨用户读取数据。

## 13. 测试策略

后端测试：

- `test_rag_metadata.py`
  - 验证 metadata normalize。
  - 验证字段命名稳定。
  - 验证缺失字段的默认值。

- `test_rag_explain.py`
  - 验证命中结果能生成普通解释。
  - 验证空召回能生成合理兜底解释。

- `test_rag_evaluation.py`
  - 验证 Hit@K。
  - 验证 MRR。
  - 验证关键词覆盖率。
  - 验证三个 RAG 样例都能跑。

- `test_rag_retrieval_logs.py`
  - 验证日志包含 query、retriever、hitCount、quality、metadata。
  - 验证日志不泄露其他用户数据。

前端测试：

- `frontend_rag_logs.test.mjs`
  - 验证命中日志展示 query、retriever、score、metadata。

- `frontend_rag_quality.test.mjs`
  - 验证质量评估结果展示 Hit@K、MRR、关键词覆盖率。

全量验证：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 14. 阶段三 V1 开发顺序

推荐分四轮开发：

### 14.1 Metadata 标准化

目标：

- 新增 `rag_metadata.py`。
- 统一 chunk metadata 输出。
- 确保三个 RAG 命中结果都能转成统一摘要。

### 14.2 命中解释增强

目标：

- 新增 `rag_explain.py`。
- 为普通用户生成“追问依据”。
- 为开发者生成“命中调试摘要”。

### 14.3 质量评估样例集

目标：

- 扩展 `rag_evaluation_seed.py`。
- 三个 RAG 各不少于 4 条样例。
- 输出 Hit@K、MRR、关键词覆盖率。

### 14.4 前端 RAG 调试展示

目标：

- 增强 RAG 日志展示。
- 增强 RAG 质量评估展示。
- 保持普通用户视图简洁。

## 15. 验收标准

阶段三 V1 完成后应满足：

- 三个 RAG 的职责边界在文档和代码中一致。
- RAG 命中结果具备统一 metadata 摘要。
- RAG 日志能展示 query、retriever、hitCount、score、matchedTokens、metadata、usedInPrompt。
- 普通用户能看到简洁追问依据。
- 开发者能看到详细命中调试信息。
- RAG 质量评估样例不少于 12 条。
- Hit@K、MRR、关键词覆盖率可以通过测试或脚本复跑。
- 不破坏现有 `/api/interview/next-question` 和 `/api/interview/report`。
- 不引入 LangGraph、LangChain、Docker、Nginx、云服务器上线。
- 后端全量测试通过。
- 前端 `.mjs` 测试通过。

## 16. 面试表达

可以这样介绍阶段三：

> 我在项目里把 RAG 拆成岗位知识库、题库和候选人画像三类。岗位知识库负责岗位能力点、评分标准和风险信号；题库 RAG 负责阶段化题目、参考答案和答题要点；候选人画像 RAG 负责用户历史回答、薄弱点和训练建议。为了避免 RAG 变成黑箱，我设计了统一 metadata、RAG 命中日志和质量评估样例集。这样当 AI 面试官问得不好时，我可以沿着 Agent Decision、ToolCalls、RAG 命中日志、Prompt 输入和最终问题逐层排查。

如果面试官问“为什么不直接上向量数据库”，可以这样回答：

> 当前阶段我先做可解释 RAG，是因为项目还在验证业务链路。先用 BM25 和结构化 metadata 建立可观测基线，能看清楚 query、命中内容、分数和进入 prompt 的证据。等基线稳定后，再引入 embedding、hybrid search 和 rerank，才能判断新方案是否真的提升召回质量，而不是只是堆技术名词。

如果面试官问“怎么评估 RAG 效果”，可以这样回答：

> 我会构建固定评估样例集，每条样例包含 query、预期知识库、预期关键词、岗位标签和阶段。然后用 Hit@K 判断前 K 条是否命中相关资料，用 MRR 判断正确结果是否排在前面，用关键词覆盖率判断召回内容是否覆盖关键能力点。这样可以对比不同检索策略，而不是凭感觉判断 RAG 好不好。

## 17. 追求目标模式建议

如果要用 Codex 的追求目标模式执行阶段三，可以输入：

```text
根据 docs/superpowers/specs/2026-06-09-rag-engineering-v1-design.md，
持续推进 AI 模拟面试系统阶段三：RAG 工程化增强 V1。

要求：
1. 每次开发前先用中文解释本轮要学的 RAG 工程化知识点。
2. 开发时优先遵循测试驱动，先写后端测试再实现。
3. 当前阶段优先改 backend_python 下的 RAG 相关模块和测试。
4. 保持 /api/interview/next-question 和 /api/interview/report 兼容。
5. 不直接引入 LangGraph，不安装 LangChain。
6. 不做 Docker、Nginx、云服务器上线。
7. 不引入新的向量数据库。
8. 每轮开发后总结改了哪些文件、为什么这么改、我面试时应该怎么讲。
9. 完成后运行 python -m pytest -q 和所有前端 .mjs 测试。
```

## 18. 后续衔接

阶段三 V1 完成后，可以进入阶段三 V2：

- 引入 embedding 向量检索。
- 对比 BM25、vector、hybrid。
- 接入 rerank。
- 支持 metadata filter。
- 做更完整的质量评估面板。

阶段三 V2 再之后，才建议进入：

- 前端页面彻底重构。
- Docker / Nginx / 云服务器上线。
- Redis、异步任务队列、监控等部署工程化。
