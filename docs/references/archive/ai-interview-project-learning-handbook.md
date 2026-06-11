# AI 模拟面试系统阶段性学习手册

> 历史说明：这份文档用于后续复习和面试准备。它不是单纯的 README，也不是某一轮开发计划，而是把当时的项目从产品目标、后端架构、RAG、Agent、日志、测试到后续开发路线系统整理一遍。
>
> 当前开发路线请以 `docs/roadmap/current-state.md` 为准。本文档中的“后续开发路线建议”和“当前最推荐的下一步”已经可能落后于代码实际进度，不能再直接作为追求目标或下一阶段 spec 的依据。

## 1. 项目一句话定位

本项目是一个面向大学生、应届生和社会求职者的 AI 模拟面试训练系统。

它的核心目标不是做一个普通聊天页面，而是把求职训练业务流程拆成几个工程模块：

```text
用户投递档案
-> 简历 / JD / 公司要求
-> 三个 RAG 召回依据
-> Agent 判断下一步策略
-> 大模型生成面试问题
-> 用户回答
-> 历史记忆与报告复盘
-> 日志和评估保证可观测
```

面试时可以这样概括：

> 我做的是一个 AI 模拟面试系统，用户可以填写或上传简历、输入目标岗位 JD 和公司要求。系统会结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 召回上下文，再由 Interview Orchestrator Agent 根据当前回答质量、剩余轮次、RAG 命中质量和历史问答决定下一步是深挖、降难度、切换话题还是结束面试。面试结束后系统生成报告、复盘总结和训练建议，同时记录 RAG 命中日志与 Agent 决策日志，避免 AI 调用变成黑箱。

## 2. 当前项目已经做到什么程度

当前项目已经不是最初的 MVP 了，已经具备一个 AI 应用开发项目的雏形。

已具备能力：

- 用户注册、登录、刷新 token、退出登录。
- 投递档案管理：简历文本、目标岗位、JD、公司要求。
- 简历上传入口：支持 PDF 和图片简历解析的设计与部分实现。
- 历史面试记录：后端保存，前端在保存失败时可用 localStorage 兜底。
- 三个 RAG：
  - 岗位知识库 RAG。
  - 题库 RAG。
  - 候选人画像 RAG。
- RAG 工程化：
  - 文档管理雏形。
  - chunk 概念。
  - BM25 / 关键词召回基础。
  - 向量检索、hybrid search、rerank 的代码基础或预留。
  - RAG 命中日志。
  - RAG 质量评估样例集和指标。
- Agent 工程化：
  - Agent State。
  - Agent Decision。
  - ToolCalls。
  - nodeTrace。
  - coach / interview 两种模式。
  - 连续弱回答处理。
  - 重复问题保护。
  - fallback / normalize 兜底。
  - LangGraph 迁移设计预留。
- 前端：
  - 面试工作台页面。
  - 登录态体验。
  - RAG 调试信息展示。
  - Agent 决策说明展示。
- 测试：
  - 后端 pytest。
  - 前端 `.mjs` 测试。

当前仍未进入的阶段：

- 生产级 Docker / Nginx / 云服务器部署。
- PostgreSQL 生产数据库替换。
- Redis 限流、缓存、token 黑名单。
- 完整管理员后台。
- 完整 LangGraph 重构。
- 完整企业级 RAG 平台。

## 3. 技术栈总览

后端：

- Python。
- FastAPI：负责 HTTP API、请求处理、接口文档。
- Pydantic：负责请求参数和响应结构校验。
- SQLAlchemy：负责数据库表模型和 ORM 操作。
- Alembic：负责数据库表结构迁移。
- SQLite：当前本地开发数据库。
- 后续可切 PostgreSQL：更适合生产环境。

大模型：

- DashScope / Qwen OpenAI 兼容接口。
- AsyncOpenAI 风格调用或兼容调用。
- 通过 prompt、temperature、JSON 输出约束和 fallback 让模型更稳定。

RAG：

- 当前重点是可解释的关键词 / BM25 检索。
- 已为 embedding、hybrid search、rerank 预留或部分实现。
- 后续可接向量数据库或 pgvector。

前端：

- 原生 HTML。
- 原生 CSS。
- 原生 JavaScript。
- 暂不引入 React、Vue、Next.js，目的是降低学习成本，先把业务链路跑通。

工程化：

- pytest 后端测试。
- Node `.mjs` 前端测试。
- 日志中间件。
- 统一错误响应。
- RAG 命中日志。
- Agent 决策日志。

## 4. 后端整体结构怎么理解

后端不是一个文件从头写到尾，而是按职责拆成不同模块。

可以把 FastAPI 后端理解成一栋楼：

```text
main.py
  负责创建 FastAPI 应用，把各个路由模块注册到应用上

routes/
  负责接收 HTTP 请求，比如登录、面试、RAG 文档、历史记录

schemas.py
  负责定义请求和响应的数据形状

db_models.py
  负责定义数据库表结构

database.py
  负责创建数据库连接和数据库会话

service / agent / rag 模块
  负责真正的业务逻辑
```

### 4.1 main.py 的作用

`main.py` 是 FastAPI 应用入口。

它一般负责：

- 创建 `FastAPI()` 对象。
- 注册中间件，比如请求日志、跨域。
- 注册异常处理器。
- 把不同路由模块挂到应用上。
- 暴露静态文件或前端页面。

“注册路由”可以理解为：

```text
告诉 FastAPI：
如果有人访问 /api/interview/next-question，
应该把这个请求交给 interview.py 里面对应的函数处理。
```

“挂到应用上”不是玄学，它就是把一个个路由模块接入 FastAPI 应用实例。

### 4.2 routes 目录的作用

routes 里面的文件负责 API 入口。

例如：

- `routes/auth.py`：注册、登录、刷新 token、退出登录。
- `routes/interview.py`：开始面试、生成下一题、保存报告。
- `routes/rag.py`：RAG 查询和调试。
- `routes/rag_documents.py`：知识库文档管理。

路由层应该做的事：

- 接 HTTP 请求。
- 做参数校验。
- 调用业务函数。
- 返回响应。

路由层不应该无限变胖。太多业务逻辑都写在路由里，会导致难测试、难维护、难讲清楚。所以我们后续会继续把复杂编排逻辑向 service / orchestrator 中迁移。

### 4.3 schemas.py 的作用

`schemas.py` 负责定义接口输入输出的数据结构。

例如一个生成下一题接口，需要知道：

- 用户回答是什么。
- 当前轮次是多少。
- 面试模式是什么。
- 返回问题文本。
- 返回 Agent 决策摘要。
- 返回 RAG 命中说明。

这些字段就适合写在 Pydantic schema 里。

面试表达：

> 我用 Pydantic schema 约束接口输入输出，避免前端传错字段或者后端返回结构不稳定。这样前后端协作和自动生成 Swagger 文档都更清晰。

### 4.4 db_models.py 和 database.py 的关系

`db_models.py` 定义“有哪些表、每张表有哪些字段、表之间有什么关系”。

`database.py` 定义“怎么连数据库、怎么创建 Session、接口里怎么拿到数据库会话”。

可以这样理解：

```text
db_models.py = 数据库表设计图纸
database.py = 连接数据库和操作数据库的工具箱
```

举例：

- `User` 表定义在 `db_models.py`。
- `InterviewRecord` 表定义在 `db_models.py`。
- `get_db()` 通常定义在 `database.py`。
- 接口里通过 `Depends(get_db)` 拿到数据库会话。

## 5. 数据库关系怎么理解

数据库表关系的核心问题只有一个：

```text
这条记录属于谁？
```

比如 `interview_records` 表里有一个 `user_id` 字段。

这表示：

```text
这一条面试记录属于 users 表里的某一个用户。
```

如果 `interview_records.user_id = 3`，意思就是：

```text
这条面试记录属于 id=3 的用户。
```

系统怎么保证不是别人的？

关键不是外键自动知道“当前登录用户是谁”，而是业务代码写入时要用当前登录用户的 id。

典型流程：

```text
用户带 token 请求接口
-> get_current_user 解析 token
-> 后端拿到当前用户 current_user
-> 保存面试记录时写入 current_user.id
-> 查询历史记录时过滤 user_id == current_user.id
```

所以用户隔离依赖两层：

- 数据库层：外键保证 `user_id` 必须指向真实存在的用户。
- 业务层：接口保存和查询时都使用当前登录用户 id。

面试表达：

> 外键保证数据关系合法，比如面试记录必须属于一个真实用户；用户隔离则由鉴权和查询条件保证。保存记录时使用当前 token 解析出的 user_id，查询记录时也按 current_user.id 过滤，避免跨用户读取数据。

### 5.1 ForeignKey 是什么

`ForeignKey("users.id")` 的意思是：

```text
当前表的这个字段，引用 users 表的 id 字段。
```

它解决的是“这条记录属于 users 表里的哪个用户”。

### 5.2 relationship 是什么

`relationship()` 是 SQLAlchemy 提供的对象导航能力。

外键更偏数据库层面：

```text
interview_records.user_id -> users.id
```

relationship 更偏 Python 对象层面：

```text
record.user
```

它让你可以从一条面试记录对象，直接访问它对应的用户对象。

可以这样理解：

```text
ForeignKey 负责表和表怎么连。
relationship 负责 Python 代码里怎么顺着关系拿对象。
```

## 6. 用户认证怎么讲

当前认证大致是：

```text
注册
-> 密码哈希入库
-> 登录
-> 签发 access token 和 refresh token
-> 前端带 access token 调用受保护接口
-> access token 过期后用 refresh token 换新 token
-> 退出登录时撤销 refresh token
```

access token：

- 短期有效。
- 用来访问接口。
- 通常是 JWT。
- 前端请求时放在 `Authorization: Bearer xxx`。

refresh token：

- 长期有效。
- 用来换新的 access token。
- 后端只保存哈希，不保存明文。
- 退出登录时撤销 refresh token。

为什么当前没上 Redis 黑名单：

- 当前是学习和本地展示阶段。
- 数据库 refresh token 已经能完成基本退出登录。
- Redis 黑名单可以后续在部署阶段补上，用来实现更强的踢人下线和 token 立即失效。

面试表达：

> 当前采用 access token + refresh token 方案。access token 负责短期接口访问，refresh token 存数据库用于续期和退出撤销。后续如果要做更强的强制下线，可以引入 Redis 黑名单记录已撤销 access token。

## 7. 三个 RAG 到底怎么协作

本项目不是一个 RAG，而是三个职责不同的 RAG。

### 7.1 岗位知识库 RAG

它解决的问题是：

```text
这个岗位到底需要什么能力？
```

它存：

- 岗位 JD。
- 岗位技术栈。
- 岗位业务场景。
- 岗位评分点。
- 风险信号。
- 常见追问方向。

它服务：

- 问题生成时贴合岗位。
- 报告评分时有岗位标准。
- Agent 判断追问方向时有依据。

### 7.2 题库 RAG

它解决的问题是：

```text
围绕这个岗位和当前阶段，可以参考哪些问题？
```

它存：

- 面试题。
- 参考答案。
- 答题要点。
- 难度。
- 阶段。
- 标签。

它服务：

- 给大模型生成问题时提供参考题型。
- 报告复盘时检查答题要点覆盖。

注意：题库 RAG 不是让模型机械照搬题目，而是提供参考依据。

### 7.3 候选人画像 RAG

它解决的问题是：

```text
这个用户历史上暴露过哪些薄弱点？
```

它存：

- 用户历史面试回答。
- 历史报告风险点。
- 历史训练建议。
- 当前投递档案下的薄弱点。
- 长期学习画像。

它服务：

- 个性化追问。
- 训练建议。
- 复盘报告。
- 避免每次面试都像第一次见到用户。

### 7.4 三个 RAG 在一次面试中的协作

一次生成下一题，大致流程是：

```text
前端提交用户回答
-> 后端读取当前用户和投递档案
-> 构造 query
-> 岗位知识库 RAG 召回岗位依据
-> 题库 RAG 召回参考题目
-> 候选人画像 RAG 召回历史薄弱点
-> 计算 retrievalQuality
-> 构造 Agent State
-> Agent 选择下一步动作
-> 大模型根据 RAG 上下文和 Agent Decision 生成下一题
```

面试表达：

> 我把 RAG 拆成三类，是因为它们解决的问题不同。岗位知识库负责岗位标准，题库负责问题模板和答题要点，候选人画像负责个性化历史记忆。这样比把所有内容塞进一个知识库更容易做权限隔离、metadata 过滤、召回质量分析和日志排查。

## 8. RAG 工程化怎么讲

RAG 不只是“把资料丢进去让模型搜”。

工程化 RAG 至少要考虑：

- 文档怎么来。
- 文本怎么解析。
- 文本怎么清洗。
- chunk 怎么切。
- metadata 怎么设计。
- query 怎么构造。
- 召回策略是什么。
- 召回结果如何排序。
- 召回结果是否进入 prompt。
- 如何记录命中日志。
- 如何评估召回质量。

当前项目重点先做可解释 RAG，不急着一次性上最复杂方案。

### RAG 知识体系 V2

这一阶段我把知识库建设拆成两层：第一层是岗位知识地图，用来尽量完整覆盖 Python 后端岗和 AI 应用开发岗从基础到进阶的知识范围；第二层是 RAG seed 数据和评估 case，只把高频、可追问、可评估、能改善当前面试体验的知识点分批落地。这样既能保证长期学习路线完整，也能避免一次性把知识库写成无法维护的百科全书。

### 8.1 为什么第一阶段先做 BM25 / 关键词检索

原因：

- 容易解释。
- 容易调试。
- 命中依据清楚。
- 适合小规模知识库。
- 方便建立质量评估基线。

如果一开始就上向量数据库、rerank、复杂框架，可能会出现：

- 问题问得不好，但不知道是 query 问题、embedding 问题、rerank 问题还是 prompt 问题。
- 系统变复杂，但没有证明效果真的更好。

面试表达：

> 我先用 BM25 和关键词检索建立可解释基线，因为当前知识库规模不大，先保证 query、命中内容、metadata、日志和评估链路可观测。等基线稳定后，再引入 embedding、hybrid search 和 rerank，用评估指标判断是否真的提升效果。

### 8.2 RAG 质量评估指标

Hit@K：

```text
前 K 条召回结果里，有没有命中预期相关内容。
```

例如 Hit@3 = 1，说明前三条里至少有一条是相关的。

MRR：

```text
正确结果排得越靠前，分数越高。
```

如果第一条就是正确结果，MRR 高；如果第三条才是正确结果，MRR 会低一些。

关键词覆盖率：

```text
预期关键词里，有多少出现在召回内容中。
```

比如预期关键词是 `RAG`、`chunk`、`rerank`、`metadata`，召回内容覆盖了 3 个，则覆盖率是 3/4。

empty recall：

```text
检索结果为空的比例。
```

如果经常空召回，说明知识库太少、query 构造不好，或者过滤条件太严。

metadata match：

```text
召回结果的岗位、阶段、知识库类型是否符合预期。
```

例如问 AI 应用开发岗位，却召回了 Java 后端岗位资料，就说明 metadata 过滤或 query 有问题。

## 9. Agent 模块怎么从头理解

Agent 不是“随便调一次大模型”。

在本项目里，Agent 的核心价值是：

```text
观察当前状态
-> 调用工具拿资料
-> 分析用户回答
-> 决定下一步动作
-> 约束大模型生成问题
-> 记录决策过程
```

普通 LLM 调用更像：

```text
用户输入 -> 模型输出
```

Agent 更像：

```text
当前状态 + 工具结果 + 历史记忆 + 规则约束
-> 决策
-> 行动
-> 记录日志
```

### 9.1 当前 Agent 工作流

当前 Interview Orchestrator Agent 可以按这个顺序理解：

```text
1. retrieve_context
   调用三个 RAG，拿到 role_hits、question_hits、memory_hits。

2. observe_state
   收集用户档案、历史问答、当前轮次、剩余轮次、模式。

3. analyze_answer
   判断用户上一轮回答是完整、一般、不会，是否连续弱回答。

4. build_agent_state
   把档案、历史、RAG 命中、回答状态、轮次信息打包成 Agent State。

5. select_action
   Agent 根据 state 决定 deep_follow_up、lower_difficulty、switch_topic、finish 等动作。

6. normalize / fallback
   如果模型决策不合法，用规则兜底修正。

7. generate_question
   大模型根据 RAG 上下文、Agent Decision 和历史记录生成下一题。

8. write_log
   写入 Agent 决策日志和 RAG 命中日志。
```

### 9.2 Agent State 是什么

Agent State 是当前这一轮 Agent 决策需要看的“状态快照”。

它不是数据库表，也不是永久记忆，而是每一轮临时构造出来给 Agent 判断用的结构化上下文。

里面通常包括：

- 当前用户档案。
- 当前投递档案。
- 上一轮问题和回答。
- 历史问答。
- 当前轮次。
- 剩余轮次。
- agentMode：coach 或 interview。
- 三个 RAG 的命中结果摘要。
- retrievalQuality。
- answerAnalysis。
- nodeTrace。
- toolCalls。

### 9.3 ToolCalls 是什么

ToolCalls 不是工具本身，而是工具调用记录。

例如：

```text
工具本身：岗位知识库 RAG 检索函数
ToolCall：本轮调用了岗位知识库 RAG，query 是什么，命中了几条，是否成功，耗时多少
```

这样做的意义是：

- 方便调试。
- 方便日志记录。
- 方便前端展示。
- 方便未来迁移到 LangGraph 或正式 tool calling。

### 9.4 Agent Decision 是什么

Agent Decision 是 Agent 对下一步动作的结构化决定。

它可能包含：

- nextAction：下一步动作。
- difficulty：下一题难度。
- stage：下一阶段。
- focus：下一题关注点。
- reason：为什么这么问。
- tools：本轮参考了哪些工具。
- shouldUpdateMemory：是否建议更新候选人记忆。
- fallbackUsed：是否使用兜底。

它不是最终展示给用户的问题，而是生成问题前的决策。

真正的问题通常由：

```text
RAG 上下文 + Agent Decision + 历史问答 + 用户档案 + prompt
```

一起交给大模型生成。

### 9.5 normalize 和 fallback 是什么

大模型输出并不一定稳定。

它可能输出：

- 缺字段。
- JSON 格式不对。
- nextAction 不在允许范围。
- difficulty 不合法。
- tools 不是 list。

所以需要 normalize：

```text
检查模型输出是否合法，不合法就替换成默认值或 fallback 值。
```

fallback 是规则兜底决策。

例如：

- 用户连续答不上来：降难度。
- 连续多次围绕同一问题：切换话题。
- 剩余轮次为 0：结束面试。

面试表达：

> 我没有完全相信模型输出，而是先构造规则 fallback，再让模型基于 Agent State 做决策，最后用 normalize 校验模型输出。如果模型输出不合法，就用 fallback 兜底，保证接口返回稳定。

## 10. coach 模式和 interview 模式

当前项目支持两种 Agent 模式。

### 10.1 coach 学习辅导模式

目标：

```text
帮助用户学会，而不是一直施压。
```

特点：

- 答不上来时更容易降难度。
- 会倾向于拆解基础概念。
- 会给训练建议。
- 更像老师或面试教练。

适合：

- 用户还没学会某个知识点。
- 用户想用系统补基础。
- 当前阶段以学习为主。

### 10.2 interview 真实面试模式

目标：

```text
尽量模拟真实面试压力。
```

特点：

- 会保留一定追问压力。
- 会检查回答是否自洽。
- 会关注项目细节。
- 但不能无意义重复卡死。

适合：

- 用户准备正式面试。
- 用户想检查自己能不能扛住追问。
- 项目讲解已经有一定基础。

## 11. 日志系统为什么重要

AI 应用最容易被质疑的问题是黑箱。

如果面试官问：

```text
为什么系统问了这道题？
为什么它一直追问这个点？
为什么 RAG 召回了这些资料？
```

如果没有日志，就只能说“模型生成的”。

这在工程项目里不够。

所以当前项目引入：

- HTTP 请求日志。
- LLM 调用日志。
- RAG 命中日志。
- Agent 决策日志。
- nodeTrace。
- toolCalls。

### 11.1 HTTP 请求日志

记录：

- 请求路径。
- 请求方法。
- 状态码。
- 耗时。
- 错误信息。

作用：

- 判断接口是否正常。
- 定位 422、500 等错误。
- 观察接口耗时。

### 11.2 RAG 命中日志

记录：

- queryText。
- retrieverName。
- retrievalMode。
- hitCount。
- 命中的 chunk。
- score。
- matchedKeywords。
- metadata。
- usedInPrompt。

作用：

- 判断召回结果是否相关。
- 判断知识库是否缺数据。
- 判断 query 是否构造不好。
- 判断 metadata filter 是否过严。

### 11.3 Agent 决策日志

记录：

- Agent State 摘要。
- Agent Decision。
- nextAction。
- focus。
- reason。
- fallbackUsed。
- triggerRules。
- nodeTrace。
- toolCalls。

作用：

- 判断为什么下一轮要深挖。
- 判断为什么降难度。
- 判断为什么切换话题。
- 判断是否因为模型输出异常触发 fallback。

面试表达：

> 我给 RAG 和 Agent 都做了日志可观测。RAG 日志解释“模型看到了哪些资料”，Agent 日志解释“系统为什么采取这个面试策略”。这样如果问题体验不好，可以沿着 Agent Decision、ToolCalls、RAG 命中、Prompt 输入逐层排查。

## 12. 一次 next-question 接口链路

这是当前项目最核心的链路。

可以这样讲：

```text
前端提交用户上一轮回答
-> FastAPI 路由接收请求
-> Depends(get_current_user) 获取当前用户
-> Depends(get_db) 获取数据库会话
-> 读取当前投递档案和历史记录
-> 构造 RAG query
-> 调用岗位知识库 RAG
-> 调用题库 RAG
-> 调用候选人画像 RAG
-> 生成 RAG 命中质量摘要 retrievalQuality
-> 构造 Agent State
-> Agent 生成或选择 Agent Decision
-> normalize / fallback 保证决策合法
-> 根据 decision + RAG context + history 生成下一题
-> 写入 RAG 命中日志和 Agent 决策日志
-> 返回前端：问题文本、决策摘要、RAG 依据、调试信息
```

面试时如果只能讲一条主链路，就讲这一条。

## 13. 当前项目的优势

和普通 AI 聊天 demo 相比，当前项目优势是：

- 有明确业务场景：面试训练。
- 有用户系统：不是匿名玩具。
- 有投递档案：输入更接近真实求职。
- 有三个 RAG：不是单知识库硬塞。
- 有 Agent 决策：不是一问一答。
- 有日志可观测：能解释系统行为。
- 有测试：不是纯手工试。
- 有后续部署规划：能往上线产品走。

面试中应该突出：

```text
业务闭环 + AI 能力 + 工程化可观测 + 可迭代路线
```

## 14. 当前项目的短板

必须诚实承认短板，否则面试官一追问就容易露怯。

当前短板：

- 知识库样例数据仍偏少。
- 前端页面还没有彻底产品化重构。
- RAG 虽然有工程化雏形，但还不是企业级 RAG 平台。
- Agent 目前是自研轻量工作流，不是完整 LangGraph。
- 没有生产级 Docker / Nginx / PostgreSQL / Redis 部署。
- 没有完整管理员后台。
- 没有真实大量用户数据验证。

可以这样表达：

> 当前项目重点是把 AI 面试主链路、RAG 可观测和 Agent 决策链路打通，还没有把部署、管理员后台和企业级 RAG 平台一次性做完。我后续的迭代路线是先补知识库数据和体验，再做生产部署链路，最后考虑 LangGraph 和更完整的 RAG 平台化。

## 15. 简历上可以怎么写

现在还不急着最终写简历，但可以先准备方向。

简历项目标题：

```text
AI 模拟面试训练系统｜Python FastAPI + RAG + Agent
```

简历描述可以写：

```text
基于 FastAPI 构建面向求职者的 AI 模拟面试系统，支持用户投递档案、简历解析、动态面试、历史复盘和训练报告。
```

亮点可以写：

- 设计岗位知识库、题库、候选人画像三类 RAG，分别支撑岗位依据、问题生成和个性化追问。
- 设计 Interview Orchestrator Agent，根据回答质量、剩余轮次、历史问答和 RAG 命中质量动态选择深挖、降难度、切换话题或结束面试。
- 实现 RAG 命中日志和 Agent 决策日志，记录 query、hitCount、metadata、nextAction、reason、fallbackUsed 等信息，提升 AI 应用可观测性。
- 基于 FastAPI、SQLAlchemy、Pydantic 实现用户认证、投递档案、面试记录和报告持久化。
- 编写 pytest 和前端脚本测试，覆盖 RAG 检索、Agent 决策和核心接口链路。

注意：

简历不要写得像已经是千万用户生产系统。

更稳妥的表达是：

```text
实现了核心链路和工程化雏形，具备继续产品化和上线部署的基础。
```

## 16. 面试高频问题与回答方向

### 16.1 为什么要做三个 RAG，而不是一个 RAG？

回答方向：

> 因为三类数据的职责、权限和使用方式不同。岗位知识库负责岗位标准，题库负责参考问题和答题要点，候选人画像负责用户历史薄弱点。如果混在一个知识库里，后续 metadata 过滤、权限隔离、召回质量分析都会变复杂。

### 16.2 你的 Agent 算不算真正的 Agent？

回答方向：

> 当前是轻量自研 Orchestrator Agent，不是完整 LangGraph Agent。它具备状态观察、工具调用、动作选择、问题生成、日志追踪和 fallback 兜底，所以已经具备 Agent 工作流雏形。后续可以把这些节点映射到 LangGraph StateGraph，并引入 checkpoint 和 human-in-the-loop。

### 16.3 为什么不一开始就用 LangGraph？

回答方向：

> 因为业务流程还在快速迭代，过早引入框架会增加学习和维护成本。我先用自研轻量 Agent 把状态、动作、工具、日志边界理清楚，等流程稳定后再迁移到 LangGraph，迁移时每个节点都有对应关系。

### 16.4 RAG 召回质量怎么评估？

回答方向：

> 我设计了固定评估样例集，每条样例包含 query、预期知识库、预期关键词、topK 等字段。评估时计算 Hit@K、MRR、关键词覆盖率、metadata match 和 empty recall，用来判断召回结果是否相关、是否排在前面、是否命中正确知识库。

### 16.5 如果 AI 问题问得不好，你怎么排查？

回答方向：

> 我会按链路排查：先看 Agent Decision 是否一直 deep_follow_up 或 fallback，再看 ToolCalls 里三个 RAG 是否成功调用，然后看 RAG 命中日志的 query、hitCount、score、metadata，接着看进入 prompt 的上下文，最后看模型生成问题是否偏离约束。

### 16.6 FastAPI 后端怎么分层？

回答方向：

> main.py 负责创建应用和注册路由，routes 负责接收 HTTP 请求，schemas 负责请求响应校验，db_models 定义数据库表，database 提供数据库连接和 Session，RAG、Agent、LLM 模块承载业务逻辑。这样接口层和业务层相对分离，方便测试和迭代。

## 17. 你需要重点补的知识

短期优先级：

1. FastAPI 路由、Depends、Pydantic schema。
2. SQLAlchemy 表模型、外键、relationship、Session。
3. RAG 基础链路：query、chunk、metadata、BM25、embedding、rerank。
4. Agent 基础链路：state、tool、decision、fallback、trace。
5. HTTP 基础：请求响应、状态码、Authorization、SSE / WebSocket。
6. MySQL / PostgreSQL 基础：索引、事务、隔离级别。
7. Docker / Nginx / Redis：放到部署阶段集中学。

不要一口气把所有技术都学成专家。

当前目标是：

```text
面试官问基础问题，你能说清楚；
面试官问项目问题，你能结合项目落地讲。
```

## 18. 后续开发路线建议

根据当前项目状态，下一步不建议立刻做 Docker / Nginx 上线。

更推荐路线：

### 阶段 A：项目讲解与面试准备

目标：

- 你能完整讲清楚项目。
- 能回答 Agent、RAG、FastAPI、数据库关系相关问题。
- 能把项目写进简历且不虚。

产出：

- 30 秒项目介绍。
- 2 分钟项目介绍。
- 5 分钟技术深挖版。
- 高频面试问答清单。

### 阶段 B：补知识库数据和体验

目标：

- 让面试问题更像真实面试。
- 补充 AI 应用开发岗位、Python 后端岗位、RAG 岗、Agent 岗的知识库样例。
- 让 RAG 评估更有意义。

产出：

- 更丰富的 seed 数据。
- 更稳定的 RAG 评估结果。
- 更自然的问题生成体验。

### 阶段 C：前端产品化重构

目标：

- 把当前页面升级成更像真实产品的面试训练工作台。
- 保留原生 HTML / CSS / JS 或评估是否迁移 Vue。

产出：

- 更清晰的信息架构。
- 更专业的登录、档案、面试、报告、日志页面。
- 移动端可用。

### 阶段 D：上线部署工程化

目标：

- 项目能跑在云服务器上。
- 能通过公网访问。
- 数据保存到生产数据库。

产出：

- PostgreSQL。
- Redis。
- Docker Compose。
- Nginx 反向代理。
- HTTPS。
- 部署文档。

### 阶段 E：LangGraph / 状态机升级

目标：

- 把当前自研 Agent 节点映射到 LangGraph。
- 引入 checkpoint。
- 支持暂停恢复和 human-in-the-loop。

产出：

- LangGraph demo。
- 自研 Agent 与 LangGraph 对比文档。
- 面试可讲的 Agent 工作流升级方案。

## 19. 当前最推荐的下一步

现在最推荐的下一步不是继续盲目加功能，而是先做一次阶段性项目讲解。

推荐顺序：

```text
1. 你先按这份文档复习项目总链路。
2. 我带你准备 30 秒 / 2 分钟 / 5 分钟项目讲法。
3. 我开始追问你 Agent 和 RAG，你回答，我帮你修正表达。
4. 然后再进入下一轮开发：优先补知识库数据和 RAG 评估可视化，或者做前端产品化重构。
```

如果你急着继续开发，我建议下一轮开发选择：

```text
补充 AI 应用开发岗位知识库样例 + RAG 评估用例增强
```

原因：

- 这会直接改善面试体验。
- 也能让 RAG 评估指标更有意义。
- 面试时比单纯美化前端更能体现 AI 应用工程化能力。

## 20. 最后一段给你自己看的话

你现在觉得代码多、概念多、看不懂，是正常的。

后端、RAG、Agent、鉴权、数据库、前端、部署，本来就是多个方向叠在一起。你现在不是“智商不够”，而是在第一次接触一个接近完整项目的复杂度。

真正需要做的不是把每一行代码都背下来，而是先建立三层理解：

```text
第一层：业务链路怎么走。
第二层：每个模块负责什么。
第三层：关键代码为什么这么写。
```

面试时也不是让你像编译器一样解释每个语法，而是要能讲清楚：

- 为什么这样设计。
- 解决了什么问题。
- 当前有什么不足。
- 后续怎么优化。

这份文档就是你的第一版项目地图。
