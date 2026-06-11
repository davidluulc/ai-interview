# RAG 知识体系与评估数据集 V2 设计

## 1. 文档目的

本文档用于约束 AI 模拟面试系统下一阶段：RAG 知识体系与评估数据集 V2。

当前项目已经具备三类 RAG、RAG 命中日志、RAG 质量评估样例、Agent State、ToolCalls、nodeTrace 和 Interview Orchestrator Agent。下一步的重点不是继续增加框架名词，而是补足知识库内容质量，让系统能更稳定地围绕「AI 应用开发岗」和「Python 后端开发岗」生成高质量面试问题。

用户希望知识库尽量覆盖：

- Python 后端岗：从基础入门、项目开发、工程化到进阶能力。
- AI 应用开发岗：从模型调用、Prompt、RAG、Agent 到前沿工具和工程化实践。

因此本阶段采用两层设计：

```text
第一层：岗位知识地图
尽量完整地列出 Python 后端岗和 AI 应用开发岗需要学习、面试、复习的知识点。

第二层：本轮 RAG 落地数据集
优先把高频、可追问、可评估、能改善当前面试体验的知识点写入 seed 数据和评估 case。
```

这样既保留长期学习路线，也避免本轮开发变成无法验收的百科全书工程。

## 2. 当前项目基础

当前已有数据文件：

```text
data/role_knowledge_seed.json
data/question_bank_seed.json
data/rag_evaluation_cases.json
```

当前已有后端模块：

```text
backend_python/rag.py
backend_python/question_rag.py
backend_python/candidate_memory.py
backend_python/retrieval_service.py
backend_python/rag_evaluation.py
backend_python/rag_evaluation_seed.py
backend_python/rag_metadata.py
backend_python/rag_explain.py
backend_python/rag_logging.py
```

当前已有 RAG 能力：

- 岗位知识库 RAG：提供岗位知识、追问方向、评分点、风险信号。
- 题库 RAG：提供结构化问题、参考答案、答题要点。
- 候选人画像 RAG：提供历史回答、薄弱点、训练建议。
- RAG 评估：已有固定 case，支持 Hit@K、MRR、关键词覆盖等基础指标。
- RAG 调试：已有命中日志和前端调试展示。

当前主要不足：

- AI 应用开发岗知识点还不够系统，尤其是 Agent、RAG 评估、模型调用工程化、前沿协议和可观测性。
- Python 后端岗知识点还不够完整，尤其是 Python 基础、FastAPI 深入、数据库、缓存、测试、部署、安全和性能。
- 题库样例数量偏少，无法覆盖从基础到项目深挖的面试节奏。
- 评估 case 数量偏少，不能稳定证明 RAG 在不同岗位、不同主题下都能命中正确内容。
- 知识地图和 RAG seed 数据还没有明确边界，容易出现“想补什么就补什么”的无序扩展。

## 3. 阶段目标

本阶段目标：

```text
建立 Python 后端岗与 AI 应用开发岗的系统知识地图，
并落地一批高质量 RAG seed 数据和评估 case，
让面试系统能围绕这两个岗位生成更贴近真实面试的题目。
```

完成后应能回答：

- Python 后端岗从基础到进阶应该学习哪些内容？
- AI 应用开发岗从模型调用到 Agent 工程化应该学习哪些内容？
- 本轮哪些知识点进入 RAG seed，哪些只进入长期知识地图？
- 每条知识点如何被 RAG 检索、被 Agent 使用、被评估 case 验证？
- 如果面试问题质量变差，如何判断是知识库缺失、query 构造问题、召回问题、题库不足，还是 Agent 决策问题？

## 4. 非目标

本阶段明确不做：

- 不做全网爬虫，不批量抓取网络资料。
- 不把所有后端和 AI 知识一次性写成百科全书。
- 不引入新的向量数据库，例如 Qdrant、Milvus、Chroma、pgvector。
- 不直接引入 LangChain 或 LangGraph。
- 不直接引入 OpenAI Agents SDK 或 MCP SDK。
- 不做 Docker、Nginx、云服务器上线。
- 不重构前端框架，不引入 React、Vue、Next.js。
- 不做管理员后台。
- 不改现有 API 兼容性。

说明：

这里的“不做”不是永远不做，而是避免本轮失焦。本轮先把知识体系、seed 数据和评估集打牢。

## 5. Python 后端岗知识地图

本知识地图用于长期学习和后续持续扩充 RAG，不要求本轮全部写入 seed。

### 5.1 Python 语言基础

入门：

- 变量、基础类型、字符串、列表、元组、字典、集合。
- 条件判断、循环、函数、模块导入。
- 文件读写、异常处理。
- 虚拟环境、pip、requirements.txt。

进阶：

- 可变对象与不可变对象。
- 浅拷贝与深拷贝。
- 作用域、闭包、装饰器。
- 迭代器、生成器。
- 上下文管理器。
- dataclass。
- 类型注解。
- Python 包结构。

高级：

- GIL。
- 多线程、多进程、协程。
- asyncio。
- 性能分析。
- 内存管理和垃圾回收。
- 常见 Pythonic 写法。

本项目优先落地点：

- 类型注解。
- 异常处理。
- async / await 基础。
- requirements.txt。
- 模块化组织。

### 5.2 Web 后端基础

入门：

- HTTP 请求与响应。
- URL、method、header、body。
- GET、POST、PUT、DELETE。
- 常见状态码：200、201、400、401、403、404、409、422、500。
- JSON 数据格式。
- Cookie、Session、Token。

进阶：

- RESTful API。
- 跨域 CORS。
- Authorization header。
- 请求参数校验。
- 统一错误响应。
- 分页、排序、过滤。
- 幂等性。

高级：

- SSE 与 WebSocket 区别。
- 接口限流。
- 超时与重试。
- 熔断与降级。
- OpenAPI / Swagger。
- API 版本管理。

本项目优先落地点：

- HTTP 请求链路。
- JSON 请求响应。
- 422 参数校验错误。
- Authorization Bearer token。
- SSE / WebSocket 是否需要升级的判断。

### 5.3 FastAPI

入门：

- `FastAPI()` 应用实例。
- `APIRouter`。
- 路由函数。
- 请求体和查询参数。
- Pydantic schema。
- Swagger 文档。
- Uvicorn 启动。

进阶：

- `Depends` 依赖注入。
- `get_db` 数据库会话依赖。
- `get_current_user` 鉴权依赖。
- 中间件。
- 异常处理器。
- response model。
- 静态文件。
- 路由模块化。

高级：

- async endpoint。
- 后台任务。
- lifespan。
- StreamingResponse。
- 大文件上传。
- 性能优化。
- 测试客户端。

本项目优先落地点：

- `main.py`、`routes`、`schemas`、`database` 的职责。
- `Depends(get_db)`。
- `Depends(get_current_user)`。
- Pydantic 请求校验。
- 路由层和业务层边界。

### 5.4 数据库与 ORM

入门：

- 表、字段、主键、外键。
- SQL 基础：select、insert、update、delete。
- where、order by、limit。
- 一对多、多对多。

进阶：

- SQLAlchemy 模型。
- Session。
- commit、rollback、flush。
- ForeignKey。
- relationship。
- 懒加载与关联查询。
- Alembic 数据库迁移。

高级：

- 事务 ACID。
- 隔离级别。
- 索引。
- B+ 树。
- 慢查询。
- N+1 查询问题。
- 数据库连接池。
- SQLite、MySQL、PostgreSQL 区别。

本项目优先落地点：

- User 与 InterviewRecord 的用户归属。
- RefreshToken 与 User 的关系。
- ApplicationProfile 与 InterviewRecord 的关系。
- Alembic 为什么像“数据库表结构的 Git”。

### 5.5 用户认证与权限

入门：

- 注册。
- 登录。
- 密码哈希。
- token。
- 当前用户查询。

进阶：

- JWT access token。
- refresh token。
- token 过期刷新。
- 退出登录。
- 用户数据隔离。
- 401 与 403。

高级：

- Redis token 黑名单。
- 双 token 轮换。
- 设备管理。
- 强制下线。
- RBAC。
- OAuth2。
- 多租户权限。

本项目优先落地点：

- access token + refresh token。
- refresh token 哈希入库。
- 退出登录撤销 refresh token。
- 后续 Redis 黑名单作为增强点。

### 5.6 缓存与 Redis

入门：

- Redis 基础数据结构：string、hash、list、set、zset。
- 过期时间。
- 缓存命中和缓存未命中。

进阶：

- 缓存穿透。
- 缓存击穿。
- 缓存雪崩。
- 分布式锁。
- 限流计数器。
- session 缓存。

高级：

- Redis 持久化。
- 主从复制。
- 哨兵。
- 集群。
- 缓存一致性。

本项目优先落地点：

- token 黑名单。
- 接口限流。
- 面试会话状态缓存。
- RAG 检索结果短期缓存。

本轮只写知识点，不接入 Redis。

### 5.7 日志、测试与工程化

入门：

- print 和 logging 的区别。
- 单元测试。
- 接口测试。
- pytest。

进阶：

- 请求日志。
- 错误日志。
- 结构化日志。
- 测试隔离。
- mock 外部模型调用。
- 测试数据库。

高级：

- 可观测性。
- trace id。
- 指标监控。
- 告警。
- CI/CD。

本项目优先落地点：

- HTTP 请求日志。
- LLM 调用日志。
- RAG 命中日志。
- Agent 决策日志。
- pytest 覆盖核心业务。

### 5.8 部署与运维

入门：

- 云服务器。
- Linux。
- 端口。
- 环境变量。
- Uvicorn。

进阶：

- Gunicorn / Uvicorn worker。
- Nginx 反向代理。
- HTTPS。
- Dockerfile。
- Docker Compose。
- PostgreSQL。
- Redis。

高级：

- 日志收集。
- 健康检查。
- 自动重启。
- 灰度发布。
- 备份恢复。
- 负载均衡。

本项目优先落地点：

- 先写部署知识，不在本轮开发。
- 后续进入上线阶段时再实现 Docker / Nginx / PostgreSQL / Redis。

## 6. AI 应用开发岗知识地图

本知识地图用于长期学习、项目扩展和面试准备。

### 6.1 大模型基础与模型调用

入门：

- 什么是大模型。
- prompt。
- system / user / assistant message。
- token。
- temperature。
- max_tokens。
- API key。
- JSON 输出。

进阶：

- 参数调优。
- 结构化输出。
- function calling / tool calling。
- 超时。
- 重试。
- 错误分类。
- 模型降级。
- usage 统计。
- 成本控制。

高级：

- 多模型路由。
- 小模型与大模型协作。
- 质量评估。
- 内容安全。
- 批处理。
- 流式输出。

本项目优先落地点：

- 不同任务使用不同 temperature。
- 报告生成更低 temperature。
- 问题生成更自然但仍受约束。
- JSON 输出校验和 fallback。
- API key 放后端。

### 6.2 Prompt 工程

入门：

- 角色设定。
- 任务说明。
- 输入变量。
- 输出格式。
- few-shot 示例。

进阶：

- prompt 模板化。
- 分任务 prompt。
- 结构化 prompt。
- 约束模型不要编造。
- 把 RAG 上下文注入 prompt。

高级：

- prompt 版本管理。
- prompt A/B 测试。
- prompt 评估集。
- prompt 注入防护。

本项目优先落地点：

- 面试问题生成 prompt。
- 报告生成 prompt。
- Agent Decision prompt。
- RAG context 格式化。

### 6.3 RAG

入门：

- RAG 是检索增强生成。
- 文档解析。
- 文本清洗。
- chunk 切分。
- query 构造。
- 召回。
- prompt 注入上下文。

进阶：

- BM25。
- embedding。
- 向量数据库。
- hybrid search。
- metadata filter。
- rerank。
- 引用出处。
- 多路召回。
- query rewrite。

高级：

- 语义切分。
- 层级索引。
- 多 query 检索。
- 权限隔离。
- 增量更新。
- 去重。
- RAG 评估。
- RAG 可观测性。

本项目优先落地点：

- 三类 RAG 职责边界。
- BM25 / 关键词检索可解释基线。
- metadata 统一。
- RAG 命中日志。
- Hit@K、MRR、关键词覆盖率、metadataMatch、emptyRecall。

### 6.4 Agent

入门：

- Agent 不只是一次 LLM 调用。
- state。
- action。
- tool。
- memory。
- observation。

进阶：

- ReAct 思想。
- tool calling。
- 多步骤规划。
- fallback。
- guardrails。
- trace。
- human-in-the-loop。
- checkpoint。

高级：

- 多 Agent 协作。
- handoff。
- 长短期记忆。
- 状态机。
- LangGraph StateGraph。
- Agent 评估。
- 生产级 Agent 可观测。

本项目优先落地点：

- Interview Orchestrator Agent。
- Agent State。
- ToolCalls。
- Agent Decision。
- nodeTrace。
- coach / interview 模式。
- 连续弱回答处理。
- 重复问题保护。
- LangGraph 迁移设计。

### 6.5 AI 应用可观测与评估

入门：

- 日志。
- 请求耗时。
- 错误记录。
- 模型输出保存。

进阶：

- RAG 命中日志。
- Agent 决策日志。
- prompt 输入输出摘要。
- usage 统计。
- 人工标注。
- 质量评估样例集。

高级：

- 自动化评估。
- 幻觉率。
- faithfulness。
- context precision。
- answer relevancy。
- trace 可视化。
- 在线监控。

本项目优先落地点：

- RAG 命中日志。
- Agent 决策日志。
- ToolCalls。
- nodeTrace。
- RAG evaluation cases。

### 6.6 前沿方向

本阶段只写进知识地图和少量 seed，不直接引入依赖。

#### 6.6.1 LangGraph

关键概念：

- StateGraph。
- node。
- edge。
- checkpoint。
- persistence。
- human-in-the-loop。
- memory。
- fault tolerance。

和本项目关系：

```text
当前自研 Agent 节点
-> 未来可映射到 LangGraph nodes

Agent State
-> 未来可作为 Graph State

Agent 决策日志
-> 未来可扩展为 graph trace

面试暂停恢复
-> 未来可使用 checkpoint
```

#### 6.6.2 OpenAI Agents SDK 类工具思想

关键概念：

- agent。
- tools。
- handoffs。
- guardrails。
- tracing。

和本项目关系：

```text
三类 RAG
-> 可抽象为 tools

Interview Orchestrator Agent
-> 可对应 agent orchestration

Agent 决策日志
-> 可对应 tracing 思路

coach / interview 模式
-> 可视为不同 agent policy 或不同 instruction
```

#### 6.6.3 MCP

关键概念：

- tools。
- resources。
- prompts。
- client / server。

和本项目关系：

```text
知识库、日志、评估脚本
-> 未来可作为 MCP server 暴露给 Agent

RAG 文档
-> 可理解为 resources

检索、评估、报告生成
-> 可理解为 tools
```

#### 6.6.4 RAGAS / RAG 评估框架

关键概念：

- faithfulness。
- context precision。
- context recall。
- answer relevancy。

和本项目关系：

```text
当前 Hit@K / MRR / 关键词覆盖率
-> 适合做第一版检索质量基线

后续自动评估报告质量
-> 可引入 faithfulness / relevancy 等指标
```

## 7. 本轮 RAG 落地范围

本轮不追求把第 5、6 节所有知识点都写入 seed。

本轮优先落地以下内容。

### 7.1 Python 后端岗优先主题

第一批 role knowledge：

- Python 后端项目整体链路。
- FastAPI 路由、schemas、Depends、database、db_models。
- Pydantic 请求校验和 422 错误。
- SQLAlchemy 外键、relationship、Session。
- JWT access token + refresh token。
- 用户数据隔离。
- HTTP 请求响应与常见状态码。
- localStorage 与后端数据库区别。
- Uvicorn、FastAPI、Nginx、云服务器关系。
- Alembic 数据库迁移。
- 日志中间件和统一错误处理。
- pytest 后端测试。

第一批 question bank：

- FastAPI 后端结构怎么讲？
- Depends(get_db) 和 Depends(get_current_user) 分别解决什么问题？
- db_models.py 和 database.py 是什么关系？
- ForeignKey 和 relationship 怎么理解？
- 为什么正式产品不能只用 localStorage？
- JWT 双 token 方案怎么设计？
- 退出登录为什么可以撤销 refresh token？
- Uvicorn、Nginx、云服务器分别是什么？
- Alembic 是什么，为什么需要数据库迁移？
- 你如何排查 422 / 500 错误？

### 7.2 AI 应用开发岗优先主题

第一批 role knowledge：

- AI 应用开发项目主链路。
- 模型调用参数调优。
- JSON 输出校验和 fallback。
- Prompt 模板化。
- 三类 RAG 职责边界。
- BM25 与向量检索区别。
- hybrid search 与 rerank 的作用。
- RAG 质量评估指标。
- Agent State、ToolCalls、Agent Decision。
- coach / interview 模式差异。
- Agent 重复问题保护。
- RAG 日志与 Agent 日志。
- LangGraph 迁移思路。
- MCP、Agents SDK、RAGAS 的概念性了解。

第一批 question bank：

- 为什么你的系统设计三个 RAG？
- RAG query 是怎么构造的？
- BM25 和向量检索各有什么优缺点？
- 什么是 Hit@K、MRR、关键词覆盖率？
- Agent State 里应该包含什么？
- ToolCalls 是工具本身还是工具调用记录？
- Agent Decision 和最终问题生成是什么关系？
- fallback 和 normalize 分别解决什么问题？
- 为什么现在不直接上 LangGraph？
- 如果 AI 面试官一直重复追问，你怎么解决？

### 7.3 每条知识 seed 的质量要求

岗位知识库每条记录必须包含：

- `id`：稳定唯一。
- `role`：岗位名称。
- `category`：知识分类。
- `title`：清晰标题。
- `keywords`：可检索关键词。
- `content`：不少于 80 字，讲清概念、场景和本项目落地方式。
- `follow_up_questions`：至少 3 条。
- `scoring_points`：至少 4 条。
- `risk_signals`：至少 3 条。

题库每条记录必须包含：

- `id`：稳定唯一。
- `category`：technical、project、scenario、behavioral 等。
- `position_tag`：`ai_app_intern` 或 `python_backend_intern`。
- `difficulty`：basic、medium、hard。
- `question`：问题文本。
- `reference_answer`：参考回答。
- `key_points`：至少 4 个。
- `tags`：至少 4 个。

## 8. 评估数据集设计

评估 case 用于证明 RAG 能不能按预期召回。

### 8.1 Python 后端岗评估方向

新增 case 应覆盖：

- FastAPI 模块化。
- Depends 依赖注入。
- Pydantic 请求校验。
- SQLAlchemy 外键与 relationship。
- JWT 双 token。
- localStorage 与数据库。
- Uvicorn / Nginx / 云服务器。
- Alembic 迁移。
- HTTP 状态码。
- 请求日志与错误排查。

示例：

```json
{
  "id": "py_backend_depends_get_db",
  "query": "FastAPI Depends(get_db) 是什么，为什么接口里要用它？",
  "knowledgeBase": "role_knowledge",
  "expectedKnowledgeBase": "role_knowledge",
  "expectedPositionTag": "python_backend_intern",
  "expectedStage": "技术基础",
  "expectedTitle": "FastAPI Depends 依赖注入",
  "expectedKeywords": ["Depends", "依赖注入", "数据库会话", "get_db"]
}
```

### 8.2 AI 应用开发岗评估方向

新增 case 应覆盖：

- RAG 基础链路。
- 三类 RAG 边界。
- BM25 与向量检索。
- hybrid search。
- rerank。
- RAG 质量评估。
- Agent State。
- ToolCalls。
- Agent Decision。
- fallback / normalize。
- Agent 日志。
- LangGraph 迁移。
- MCP / Agents SDK / RAGAS 概念。

示例：

```json
{
  "id": "ai_agent_state_toolcalls",
  "query": "Agent State 和 ToolCalls 在 AI 模拟面试系统里分别起什么作用？",
  "knowledgeBase": "role_knowledge",
  "expectedKnowledgeBase": "role_knowledge",
  "expectedPositionTag": "ai_app_intern",
  "expectedStage": "Agent 追问",
  "expectedTitle": "Agent State 与 ToolCalls",
  "expectedKeywords": ["Agent State", "ToolCalls", "状态", "工具调用记录"]
}
```

### 8.3 验收指标

本轮完成后应满足：

- `role_knowledge_seed.json` 至少新增 20 条高质量知识：
  - Python 后端岗不少于 10 条。
  - AI 应用开发岗不少于 10 条。
- `question_bank_seed.json` 至少新增 20 条高质量题目：
  - Python 后端岗不少于 10 条。
  - AI 应用开发岗不少于 10 条。
- `rag_evaluation_cases.json` 至少新增 20 条评估 case：
  - Python 后端岗不少于 10 条。
  - AI 应用开发岗不少于 10 条。
- 每条新增 role knowledge 必须有 follow_up_questions、scoring_points、risk_signals。
- 每条新增 question bank 必须有 reference_answer、key_points、tags。
- 评估脚本能正常运行。
- 后端测试和前端测试保持通过。

## 9. 数据命名规范

新增 id 建议：

Python 后端岗：

```text
py_backend_basic_001
py_backend_fastapi_001
py_backend_db_001
py_backend_auth_001
py_backend_deploy_001
```

AI 应用开发岗：

```text
ai_app_llm_001
ai_app_prompt_001
ai_app_rag_001
ai_app_agent_001
ai_app_eval_001
ai_app_frontier_001
```

题库：

```text
qb_py_v2_001
qb_ai_v2_001
```

评估 case：

```text
eval_py_backend_001
eval_ai_app_001
```

注意：

- 不复用已有 id。
- 不引入中文 id。
- 不使用空泛标题，例如“后端知识”“AI 知识”。
- 每条 title 要能被面试官看懂。

## 10. 本轮对前端的影响

本轮优先补数据和评估，不主动重构前端。

如果现有前端 RAG 调试面板能显示命中内容，则不改前端。

只有在以下情况下才做小改动：

- 新增字段无法正常展示。
- RAG 命中原因缺少必要展示。
- 前端调试面板因新增数据结构报错。

不做：

- 不做页面大改版。
- 不重构聊天框。
- 不改登录页。

## 11. 本轮对 Agent 的影响

本轮不改 Agent 决策算法。

但更丰富的 RAG 数据会影响 Agent 的输入质量：

```text
更好的岗位知识
-> 更好的 role_context
-> 更准确的 Agent State
-> 更合理的 Agent Decision
-> 更贴合真实面试的问题
```

如果新增数据后发现 Agent 仍然重复追问或跑偏，再进入下一轮 Agent 策略优化。

## 12. 测试策略

### 12.1 数据格式测试

需要保证：

- JSON 文件合法。
- 新增 id 不重复。
- 必填字段完整。
- keywords、follow_up_questions、scoring_points、risk_signals 不是空数组。
- question bank 的 key_points 和 tags 不是空数组。

### 12.2 RAG 评估测试

需要保证：

- 新增评估 case 能被加载。
- 每个 case 有 expectedKeywords。
- 评估脚本输出 Hit@K、MRR、关键词覆盖率。
- 不因为新增 case 导致评估脚本崩溃。

### 12.3 业务回归测试

需要运行：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

## 13. 面试表达

本阶段完成后，可以这样讲：

> 我发现 RAG 系统不只是检索算法问题，知识库内容质量和评估数据集也非常关键。所以我为 AI 应用开发岗和 Python 后端岗设计了两层知识体系：第一层是岗位知识地图，覆盖从基础到进阶的学习范围；第二层是本项目真正落地的 RAG seed 数据和评估 case。落地时我没有盲目追求百科全书，而是优先选择高频、可追问、可评估的知识点，并为每条知识配置关键词、追问问题、评分点和风险信号。这样系统生成问题时有更稳定的依据，RAG 评估也能通过 Hit@K、MRR 和关键词覆盖率观察召回质量。

如果被问为什么不一次性覆盖所有知识，可以这样答：

> 我把“知识地图全覆盖”和“RAG 数据落地”分开处理。知识地图可以尽量完整，作为长期学习和扩展目录；但 RAG seed 必须可维护、可评估、可持续迭代。本轮先覆盖高频核心知识，后续再按评估结果和真实面试反馈增量扩充。

## 14. 后续演进

本阶段完成后，后续可以继续推进：

1. 增加更多岗位：
   - RAG 开发岗。
   - Agent 开发岗。
   - Python 后端实习岗。
   - AI 产品 / AI 工程化岗。

2. 引入更强检索：
   - embedding。
   - hybrid search。
   - rerank。
   - metadata filter 对比评估。

3. 做 RAG 评估面板：
   - 展示每次评估结果。
   - 对比不同检索策略。
   - 观察失败 case。

4. 做知识库管理增强：
   - 文档版本。
   - 增量更新。
   - 删除旧文档。
   - 重复内容检测。

5. 做 LangGraph / Agent 升级：
   - 把当前 Agent 节点映射成 StateGraph。
   - 增加 checkpoint。
   - 增加 human-in-the-loop。

## 15. 参考方向

以下资料只用于确定前沿方向和概念边界，本阶段不直接引入依赖：

- OpenAI Agents SDK：用于理解 agent、tools、handoffs、guardrails、tracing 等工程化概念。
- LangGraph 官方文档：用于理解 StateGraph、checkpoint、persistence、human-in-the-loop。
- Model Context Protocol：用于理解 tools、resources、prompts、client / server 的连接模型。
- RAGAS：用于理解 faithfulness、context precision、context recall、answer relevancy 等 RAG 评估方向。

