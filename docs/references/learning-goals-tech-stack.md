一、总体目标
短期目标不是“学完 AI Agent”，而是做出一个能投简历的项目。
这个项目最好能证明我具备：
Python 后端开发能力
FastAPI 接口设计能力
数据库建模能力
LLM API 接入能力
Agent 工具调用能力
RAG 检索增强能力
异步任务 / 缓存 / 部署等工程化能力
能把 AI 功能和真实业务流程结合起来

二、学习路线总纲

Python 后端基础
FastAPI Web 后端
数据库与缓存
LLM API 工程化
RAG 知识库
Agent 工作流
项目工程化与简历包装

三、Python 后端基础
需要掌握到“能写工程代码”的程度，而不只是语法。
重点学：
Python 类型标注：list[str]、dict[str, Any]、Optional、Literal
Pydantic：请求参数校验、响应模型、配置管理
异步编程：async/await、协程、异步 IO、并发请求
面向对象：Service、Repository、DTO、接口抽象
异常处理：自定义异常、统一错误响应
日志：logging、请求日志、错误日志
配置管理：.env、环境变量、多环境配置
包结构：app/api、app/services、app/models、app/core
测试：pytest、mock、接口测试

四、FastAPI 后端
FastAPI 是找 Python 后端实习的主武器之一。
必须掌握：
路由拆分：APIRouter
请求体验证：Pydantic Schema
响应模型：统一返回格式
依赖注入：数据库 Session、当前用户、权限校验
中间件：CORS、日志、耗时统计
文件上传：简历 PDF / Word 上传
流式响应：SSE 模拟 AI 打字输出
后台任务：简单任务用 FastAPI BackgroundTasks，复杂任务再用 Celery
自动文档：Swagger / OpenAPI
异常处理：统一错误码
FastAPI 官方文档里依赖注入、后台任务这些是重点

五、数据库与缓存
数据库这块决定像不像“后端开发”。
需要学：
PostgreSQL 基础
表设计
主键、外键、索引
一对多、多对多关系
SQLAlchemy ORM
Session 生命周期
事务提交与回滚
Alembic 数据库迁移
Redis 缓存
Redis 分布式锁
Redis 存会话状态 / 限流
SQLAlchemy 重点是 Session 和事务，官方文档里也强调 Session 是 ORM 和数据库交互的核心对象

Redis 可以用于：

面试会话临时状态
AI 流式生成锁
限制用户频繁请求
异步任务状态缓存
热门岗位 JD 缓存

六、LLM API 工程化
这部分是区别于普通后端实习生的地方。
要学：
大模型的 API 调用
模型参数：temperature、max_tokens、top_p
Prompt 模板管理
多轮对话历史压缩
流式输出
结构化输出 JSON
Function Calling / Tool Calling
超时、重试、降级
Token 计费统计
多模型适配器
OpenAI 的 Function Calling 和 Structured Outputs 很值得学，尤其是 strict: true 这种 schema 约束思想

项目里可以把 LLM 分成几类能力，例如：
简历解析模型
JD 解析模型
面试问题生成模型
追问模型
答案评分模型
报告生成模型
训练计划生成模型

要把所有 Prompt 写在一个文件里。可以这样拆，例如：
app/prompts/
  resume_parser.py
  jd_analyzer.py
  interviewer.py
  evaluator.py
  coach.py

 七、RAG 学习路线
RAG 是项目的一个核心亮点，但不要硬堆概念，要和业务结合。

需要掌握：

文档加载：PDF、Markdown、文本
文档清洗
Chunk 切分
Embedding
向量数据库：Chroma / Milvus / pgvector
相似度检索
元数据过滤
BM25 关键词检索
Hybrid Search
Rerank
引用来源返回
RAG 评估
Chroma 的核心概念是 collection、documents、metadata、embeddings 和 query

项目里 RAG 不应该只是“上传文档问答”，而应该做成，例如：

岗位知识库：后端开发、Agent 开发、RAG 开发岗位要求
面试题知识库：Python、FastAPI、数据库、Redis、Agent、RAG
公司面经知识库：不同公司常见问题
用户个人知识库：用户简历、项目经历、历史回答

RAG 评估可以参考 Ragas 的指标，比如 Faithfulness、Response Relevancy、Context Precision 等

八、Agent 学习路线
你现在要学 Agent，不要只停留在“让大模型自己想”。

你要重点学：

Tool Calling
Agent 状态管理
多 Agent 分工
Memory
人工确认 Human-in-the-loop
Guardrails
Trace 调试
Workflow 编排
LangGraph 或 OpenAI Agents SDK 选一个深入
LangGraph 的优势是状态图和持久化，它的官方文档强调可以用 checkpoint 保存 graph state，适合多轮、可恢复的 Agent 流程

OpenAI Agents SDK 的优势是 tools、handoffs、guardrails、tracing 更一体化，官方 tracing 文档里提到它会记录 LLM 生成、工具调用、handoff、guardrail 等事件

推荐技术栈

后端：FastAPI
数据库：PostgreSQL
ORM：SQLAlchemy
缓存：Redis
异步任务：Celery
向量库：ChromaDB，后期可换 Milvus 或 pgvector
Agent：LangGraph 或 OpenAI Agents SDK
LLM：DeepSeek / OpenAI / 通义千问
前端：Vue3 + Element Plus
部署：Docker Compose
测试：pytest
文档：Swagger + README
