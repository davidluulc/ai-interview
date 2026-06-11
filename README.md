# AI 模拟面试系统

这是一个面向在校大学生、应届生和社会求职者的 AI 模拟面试训练项目。

项目目标不是只做一个聊天页面，而是把求职业务流程和 AI 能力结合起来：用户填写或上传简历，系统根据简历和 JD 推荐岗位方向，再结合岗位知识库、题库和历史面试记录生成动态追问，最后输出结构化面试报告。

## 当前能力

- 简历投递入口：候选人姓名、目标岗位、求职类型、简历亮点、JD、公司要求。
- 简历解析：支持 PDF 和图片简历解析。
- 岗位匹配 Agent：根据简历、JD 和岗位模板推荐更适合的岗位方向。
- 动态 AI 面试官：根据当前阶段、历史回答和 RAG 上下文生成下一题。
- 面试强度：支持快速 5 题、标准 8 题、深度 12 题。
- 岗位知识库 RAG：提供岗位知识、追问方向、评分点和风险信号。
- 题库 RAG：根据岗位标签、当前阶段和 JD 检索参考题目。
- 候选人画像 RAG：根据历史面试记录召回风险点、训练建议，并聚合长期画像，包括分数趋势、薄弱环节和训练重点。
- 面试报告：生成评分、优势、风险点和下一步训练建议。
- 历史复盘：后端 SQLite 保存历史记录，失败时前端 localStorage 兜底。
- RAG 调试面板：展示命中分数、命中词、题库命中和候选人画像命中。
- 工程化基础：统一错误响应、请求日志、接口耗时统计、健康检查接口。
- LLM 工程化：模型调用超时、重试、错误分类、usage 统计和日志记录。
- 用户认证：JWT access token + 数据库 refresh token，支持注册、登录、刷新、退出登录和当前用户查询。
- 自动化测试：使用 pytest 覆盖岗位匹配 Agent、RAG 检索和基础接口。

## 技术栈

- 后端：Python + FastAPI
- 数据校验：Pydantic
- 数据库：SQLite + SQLAlchemy，本地开发默认 SQLite，后续上线可切换 PostgreSQL
- 数据库迁移：Alembic
- 大模型：DashScope / Qwen OpenAI 兼容接口
- LLM 工程化：超时控制、失败重试、JSON 解析、usage 日志
- 简历解析：pypdf + Qwen Vision
- RAG：本地 JSON 知识库 + 可解释关键词检索
- 前端：HTML + CSS + JavaScript
- 测试：pytest
- 文档：Markdown + FastAPI Swagger

## 目录结构

```text
backend_python/
  main.py                  FastAPI 应用入口
  config.py                环境变量和路径配置
  schemas.py               请求和响应模型
  database.py              数据库连接和 Session
  db_models.py             SQLAlchemy 表模型
  llm_client.py            大模型调用
  core/                    日志、中间件、统一异常处理
  prompts/                 Prompt 模板
  resume_parser.py         PDF / 图片简历解析
  rag.py                   岗位知识库 RAG
  question_rag.py          题库 RAG
  candidate_memory.py      候选人画像 RAG
  position_agent.py        岗位匹配 Agent
  routes/                  API 路由

data/
  role_knowledge_seed.json 岗位知识库种子数据
  question_bank_seed.json  题库种子数据
  position_templates.json  岗位模板种子数据

docs/
  api.md
  deployment-tech-selection.md
  interview-notes.md
  learning-goals-tech-stack.md
  mvp-spec.md
  rag-design.md

tests/
  test_core_flows.py       核心流程测试

index.html
styles.css
app.js
requirements.txt
start-python-server.cmd
```

## 本地启动

1. 安装依赖：

```bash
python -m pip install -r requirements.txt
```

2. 复制环境变量模板：

```bash
copy .env.example .env
```

3. 在 `.env` 中填写 DashScope API key：

```text
DASHSCOPE_API_KEY=你的 API key
QWEN_MODEL=qwen-plus
QWEN_VISION_MODEL=qwen-vl-plus
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=1
SECRET_KEY=请换成一段足够长的随机字符串
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14
DATABASE_URL=sqlite:///data/app.db
```

4. 启动后端：

```bash
python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload
```

Windows 也可以双击：

```text
start-python-server.cmd
```

5. 打开页面：

```text
http://localhost:8000
```

接口文档：

```text
http://localhost:8000/docs
```

健康检查：

```text
http://localhost:8000/api/health
```

## 数据库迁移

当前本地默认使用 SQLite：

```text
DATABASE_URL=sqlite:///data/app.db
```

如果未来上线到云服务器，可以切换为 PostgreSQL：

```text
DATABASE_URL=postgresql+psycopg://ai_interview:your_password@127.0.0.1:5432/ai_interview
```

Alembic 用来管理数据库表结构版本。你可以把它理解成“数据库表结构的 Git”：代码版本由 Git 管，数据库表结构版本由 Alembic 管。

常用命令：

```bash
alembic upgrade head
alembic current
alembic history
```

`Base.metadata.create_all()` 适合本地快速开发，Alembic 更适合上线环境和团队协作。后续如果新增用户表、给面试记录增加字段，都应该通过 Alembic 迁移脚本完成。

## 用户认证

当前认证采用双 token：

```text
access_token：短期 JWT，用来访问受保护接口
refresh_token：长期随机 token，只保存哈希到数据库，用来换新的 access_token
```

退出登录时，后端会撤销 refresh token。当前版本暂不接 Redis 黑名单，所以已经签发且未过期的 access token 不会被立即踢下线。后续可以用 Redis 黑名单增强这一点。

认证接口：

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
```

历史记录和候选人画像 RAG 已经按当前用户隔离：用户只能保存、查看和召回自己的面试记录。

## 测试

运行核心测试：

```bash
python -m pytest -q
```

当前测试覆盖：

- 岗位匹配 Agent 是否能推荐 AI 应用开发实习生。
- 题库 RAG 是否能返回带分数的题目。
- 岗位知识库 RAG 是否能返回命中证据。
- 候选人画像 RAG 是否能聚合历史分数、风险点、薄弱环节和训练重点。
- 健康检查接口是否正常。
- 请求参数校验错误是否使用统一错误结构。
- LLM JSON 解析、payload 构造和 usage 统计。
- Alembic 配置和初始数据库迁移脚本是否存在。
- 用户注册、登录、刷新、退出登录和历史记录用户隔离。

## 当前学习重点

这个项目目前适合重点学习：

- FastAPI 路由拆分和 Pydantic 请求校验。
- SQLAlchemy Session 和数据库持久化。
- Alembic 数据库迁移、SQLite 开发模式和 PostgreSQL 上线模式。
- JWT 双 token 认证、密码哈希、refresh token 撤销和用户数据隔离。
- 大模型 API 调用、temperature、JSON 输出和异常兜底。
- RAG 的 query 构造、检索命中、prompt 注入和调试。
- 岗位匹配 Agent 如何在业务流程中做决策。
- 请求日志、中间件、统一异常处理和接口测试。
- LLM API 超时、重试、错误分类和调用日志。
- 如何把 AI 能力包装成真实求职训练产品。

## 后续计划

- 将 SQLite 升级为 PostgreSQL，并加入 Alembic 迁移。
- 加入 Redis 做会话状态、限流和缓存。
- 将关键词 RAG 升级为 embedding + Chroma / pgvector。
- 增加 Docker Compose 部署。
- 后期可重构前端为 Vue3 + Element Plus。
