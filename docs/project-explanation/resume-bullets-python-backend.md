# Python 后端岗简历项目表达

## 项目名称

AI 模拟面试系统

## 项目描述

基于 FastAPI、SQLAlchemy、Vue3、RAG 和 Agent/LangGraph 构建的 AI 模拟面试系统，支持用户创建投递档案、结合岗位知识库/题库/候选人画像生成面试问题，面试后生成复盘报告和训练任务，并提供管理员后台观测 RAG 命中、Agent 决策和异步任务状态。

## 技术栈

FastAPI、SQLAlchemy、Alembic、SQLite、PostgreSQL 兼容配置、Redis、Celery、Vue3、TypeScript、Docker Compose、Nginx、pytest。

## 可选职责表达

- 设计 FastAPI 后端模块，拆分认证、档案、面试、RAG、训练、管理员后台等路由，使用 SQLAlchemy 建模用户、面试记录、RAG 文档、摄取任务和日志数据。
- 设计 RAG 文档摄取链路，支持文件解析、文本清洗、chunk 入库、任务状态持久化、失败原因记录和 retry。
- 引入 Redis/Celery 生产化底座，将 RAG 文档摄取等慢任务从 HTTP 请求链路拆分为后台任务，并在管理员后台展示任务状态。
- 实现 token blacklist、接口限流、错误脱敏、幂等和 retry 并发保护，提高后端安全性和可维护性。
- 编写 pytest 覆盖认证、RAG、Agent、训练任务、管理员后台和部署配置等核心链路。

## 面试时可以强调的亮点

- 慢任务异步化：RAG 文档摄取不阻塞 HTTP 请求，接口返回 taskId，worker 后台处理。
- 可观测性：管理员后台能看到 RAG 命中、Agent 决策、runtime audit 和 ingestion 任务状态。
- 生产兼容：本地 SQLite 保持开发效率，生产支持 PostgreSQL、Redis、Celery 和 Nginx。
- 稳定性：限流、token blacklist、幂等、retry 并发保护和 provider 错误脱敏。

## 注意边界

不要把项目描述为已经大规模商业化上线。更准确的说法是：项目已经完成本地开发、生产化配置和部署演练，具备上线准备和演示能力。
