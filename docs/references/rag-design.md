# RAG 设计文档

本文档说明 AI 模拟面试系统的 RAG 设计。

## 为什么要加 RAG

只靠大模型生成问题时，模型可能会：

- 问题太泛。
- 缺少岗位针对性。
- 评分标准不稳定。
- 不能稳定围绕题库和岗位知识追问。

RAG 的作用是：在生成问题和报告前，先检索相关岗位知识、评分点和常见追问，再把这些内容放进 prompt。

## RAG 1：岗位知识库 RAG

### 第一版实现方式

当前第一版是轻量 RAG：

```text
本地 JSON 知识库 + 关键词检索 + prompt 增强
```

知识库文件：

```text
data/role_knowledge_seed.json
```

检索模块：

```text
backend_python/rag.py
```

接入位置：

```text
backend_python/routes/interview.py
```

## 当前知识库内容

当前种子知识库包含：

- AI 应用项目经历追问。
- 大模型 API 调用基础。
- RAG 基础流程。
- 后端接口设计。
- 数据库与持久化。
- STAR 行为面试结构。

每条知识包含：

- role：适用岗位。
- category：知识类别。
- title：标题。
- keywords：关键词。
- content：知识内容。
- scoring_points：评分点。

## 检索流程

1. 前端提交候选人档案、简历、JD、公司要求和下一阶段。
2. 后端把这些内容拼成 query。
3. `rag.py` 根据关键词匹配知识库。
4. 取前几条相关内容。
5. 格式化成“岗位知识库上下文”。
6. 放入模型 prompt。
7. 模型基于上下文生成下一题或报告。

## 调试接口

可以用这个接口查看检索结果：

```text
GET /api/rag/search?q=AI应用开发实习生&stage=技术追问
```

## RAG 2：候选人画像 RAG

候选人画像 RAG 用来让系统记住用户历史训练中的弱点和建议。

数据来源：

- 历史面试记录。
- 历史回答。
- 历史报告分数。
- 历史风险点。
- 历史训练建议。

实现模块：

```text
backend_python/candidate_memory.py
```

接入位置：

```text
backend_python/routes/interview.py
```

调试接口：

```text
GET /api/memory/search?name=张同学&role=AI应用开发实习生
```

聚合调试接口：

```text
GET /api/rag/debug?name=张同学&role=AI应用开发实习生&stage=技术追问
```

这个接口会同时返回：

- 岗位知识库命中结果。
- 候选人画像命中结果。

前端的“RAG 检索调试”面板就是调用这个接口。

当前流程：

1. 用户完成一次面试后，记录保存到 SQLite。
2. 下次生成问题或报告时，后端根据候选人姓名、目标岗位、简历和 JD 检索历史记录。
3. 提取历史风险点、训练建议和最近回答阶段。
4. 把候选人画像作为上下文放进 prompt。
5. 模型可以针对重复弱点继续追问或给出更连续的建议。

这样系统就不只是“一次性模拟面试”，而是开始具备长期训练记忆。

## 当前限制

- 还不是真正的向量检索。
- 不支持 embedding。
- 不支持语义相似度。
- 知识库内容还比较少。
- 还没有 rerank。
- 候选人画像目前基于 SQLite 历史记录和关键词匹配。

## 本轮升级：可解释 RAG

这一版 RAG 的重点不是先上复杂向量数据库，而是先把链路做清楚、可观察、可解释。

当前岗位知识库每条资料包含：

- `keywords`：用于检索的关键词。
- `content`：给模型看的岗位或项目知识。
- `follow_up_questions`：面试官可以参考的追问方向。
- `scoring_points`：生成报告时参考的评分点。
- `risk_signals`：候选人回答中可能暴露的风险。

检索流程：

1. 后端把目标岗位、简历、JD、公司要求、当前面试阶段拼成 query。
2. `backend_python/rag.py` 把 query 拆成关键词。
3. 系统用关键词命中、词频和角色匹配计算分数。
4. 返回分数最高的几条知识。
5. 每条命中资料会带上 `score`、`matchedKeywords`、`matchedTokens`。
6. 面试接口把这些资料放进 prompt，让模型基于资料继续追问或评分。

前端的 “RAG 检索调试” 面板会展示：

- 命中的知识标题。
- 命中分数。
- 命中词。
- 资料内容。
- 追问方向。
- 评分点。
- 风险信号。

这样做的好处是：如果 AI 面试官问得不准，我们可以先看是不是检索错了；如果检索命中了正确资料但问题仍然不好，再去调 prompt。

面试或简历中可以这样讲：

> 我没有一开始就直接接向量数据库，而是先做了一个可解释的轻量 RAG。岗位知识库里不仅存资料，还存追问方向、评分点和风险信号。检索时会返回命中分数和命中词，前端调试面板可以看到模型参考了哪些资料。这样方便排查问题：到底是检索没召回，还是 prompt 没用好检索结果。后续再把关键词检索升级成 embedding + 向量数据库会更稳。

## 岗位匹配 Agent 和题库 RAG

这一轮新增了两个更接近真实 AI 面试系统的模块。

### 岗位匹配 Agent

文件位置：

```text
backend_python/position_agent.py
data/position_templates.json
backend_python/routes/position_agent.py
```

它的职责是：根据候选人简历、目标岗位、JD 和公司要求，推荐更适合的岗位方向。

当前实现方式：

1. `position_templates.json` 里维护岗位模板。
2. 每个岗位模板包含核心技能、加分技能、项目关键词、重点追问方向。
3. Agent 把用户简历和 JD 拼成 query。
4. 根据技能和关键词命中情况给岗位打分。
5. 返回推荐岗位、匹配分数、匹配原因。

这不是最复杂的 Agent，但已经具备 Agent 的核心含义：它不是只做文本生成，而是在一个业务流程中做决策。

### 题库 RAG

文件位置：

```text
backend_python/question_rag.py
data/question_bank_seed.json
```

它的职责是：根据岗位、当前面试阶段、简历和 JD，从题库里找出更适合参考的面试题。

题库里的每条题目包含：

- `position_tag`：适用岗位。
- `category`：题目类型，例如 technical、project、behavioral。
- `difficulty`：难度。
- `question`：题面。
- `reference_answer`：参考答案。
- `key_points`：答题要点。
- `tags`：检索标签。

面试官生成下一题时，会同时参考：

```text
岗位知识库 RAG
+ 题库 RAG
+ 候选人画像 RAG
+ 当前简历/JD/历史回答
```

可以这样理解三类上下文：

```text
岗位知识库 RAG：告诉模型这个岗位要考什么、怎么评分。
题库 RAG：给模型提供可参考的真实题目和答题要点。
候选人画像 RAG：告诉模型这个候选人过去哪里薄弱。
```

面试时可以这样讲：

> 我在项目里做了一个轻量岗位匹配 Agent。它会根据简历和 JD 对岗位模板打分，推荐更适合的岗位方向。开始面试后，系统会用岗位标签、当前阶段、简历和 JD 去题库 RAG 里检索题目，同时结合岗位知识库 RAG 和候选人画像 RAG，让 AI 面试官的问题既贴合岗位，也能针对候选人弱点继续追问。

## 后续升级路线

后续可以升级成真正的向量 RAG：

1. 文档切片。
2. 调用 embedding 模型。
3. 存入向量数据库。
4. 根据 query 做语义检索。
5. 加 rerank。
6. 把结果放进 prompt。

可选技术：

- Chroma。
- FAISS。
- Milvus。
- PostgreSQL + pgvector。

## 面试时怎么讲

可以这样说：

> 项目第一版 RAG 没有直接上向量数据库，而是先用本地 JSON 知识库和关键词检索打通流程。这样可以先验证“检索上下文进入 prompt 后是否能提升面试问题质量”。后续如果要提升召回效果，可以把知识库切片后做 embedding，接入 Chroma 或 pgvector。
