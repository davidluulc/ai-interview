# AI 模拟面试系统当前状态与下一阶段路线

更新时间：2026-06-12

## 0. 当前执行焦点

当前下一阶段已经确定为：

```text
Vue3 前端重构 V1
```

当前 active spec：

```text
docs/specs/active/vue3-frontend-rebuild-v1-design.md
```

阶段目标：

```text
在保留旧原生 HTML/CSS/JS 页面作为兜底入口的前提下，新建 Vue3 + Vite + TypeScript 前端工程，优先完成产品壳、登录态、投递档案和面试训练主流程，让项目从“功能堆叠型单页 MVP”升级为“结构清晰、视觉高级、可继续演进的前后端分离产品前端”。
```

本阶段不做：

```text
不重构后端 API，不重构 RAG / Agent，不替换 LangGraph 主流程，不删除旧前端，不做 Kubernetes，不做复杂 CI/CD，不处理大陆服务器备案。
```

本文档是当前项目的唯一可信路线入口。判断项目进度时，优先看本文档，再看 `project-progress.md` 的历史执行记录。旧 spec、旧 plan、旧学习手册只作为背景资料，不再直接决定下一步开发路线。

## 1. 判断原则

当前状态以代码、测试和数据库模型为准，不以旧文档里的“下一步建议”为准。

判断顺序：

```text
代码是否存在
-> 测试是否覆盖
-> project-progress.md 是否记录过验证
-> 再参考旧 spec / plan
```

如果旧文档和本文档冲突，以本文档为准。

## 2. 已经真实落地的能力

### 2.1 后端基础

已落地：

- FastAPI 后端应用。
- 路由模块拆分。
- Pydantic schema。
- SQLAlchemy ORM。
- SQLite 本地开发数据库。
- Alembic 迁移脚本。
- 统一错误响应、请求日志和健康检查。

主要证据：

- `backend_python/main.py`
- `backend_python/routes/`
- `backend_python/schemas.py`
- `backend_python/db_models.py`
- `backend_python/database.py`
- `alembic/versions/`
- `backend_python/core/`

### 2.2 用户系统

已落地：

- 用户注册。
- 用户登录。
- access token。
- refresh token。
- refresh token 撤销式退出登录。
- 当前用户接口。
- 用户角色字段。
- 管理员权限依赖。

主要证据：

- `backend_python/routes/auth.py`
- `backend_python/auth.py`
- `backend_python/db_models.py`
- `tests/test_auth.py`
- `tests/test_admin_auth.py`
- `tests/frontend_auth_refresh.test.mjs`

尚未落地：

- Redis token 黑名单。
- 踢人下线。
- 邮箱验证码。
- 找回密码。

这些属于上线或商业化阶段，不是当前主线。

### 2.3 投递档案和历史复盘

已落地：

- 投递档案 CRUD。
- 面试历史保存。
- 历史记录按用户隔离。
- 历史统计。
- 保存失败时前端 localStorage 兜底。

主要证据：

- `backend_python/routes/application_profiles.py`
- `backend_python/routes/history.py`
- `tests/test_application_profiles.py`
- `tests/test_history_auth.py`
- `tests/test_history_application_profile_link.py`
- `tests/frontend_history_review.test.mjs`

### 2.4 简历和岗位匹配

已落地：

- 简历解析入口。
- 岗位匹配 Agent 入口。
- 岗位模板数据。

主要证据：

- `backend_python/routes/resume.py`
- `backend_python/resume_parser.py`
- `backend_python/routes/position_agent.py`
- `backend_python/position_agent.py`
- `data/position_templates.json`

当前边界：

- 简历解析仍是轻量能力，不是完整 OCR / PDF / Word 生产级解析系统。
- 岗位匹配 Agent 是规则和模型结合的轻量版本，不是完整招聘推荐系统。

### 2.5 RAG 工程化

已落地：

- 三类 RAG：
  - 岗位知识库 RAG。
  - 题库 RAG。
  - 候选人画像 RAG。
- RAG 文档管理。
- 文档生命周期：enabled / disabled / archived。
- 文档可见性：private / public。
- metadata 存储和过滤。
- 文档 hash 和 chunk hash。
- chunk 去重统计。
- BM25 检索。
- embedding 向量检索。
- hybrid search。
- rerank。
- query rewrite / multi-query。
- RAG 命中日志。
- RAG debug 接口。
- RAG 命中解释。
- RAG evaluation case。
- Hit@K、MRR、关键词覆盖率等评估指标。
- 管理员低质量召回面板。
- VectorStore 抽象和 SQLiteVectorStore 实现。

主要证据：

- `backend_python/rag.py`
- `backend_python/question_rag.py`
- `backend_python/candidate_memory.py`
- `backend_python/retrieval_service.py`
- `backend_python/rag_store.py`
- `backend_python/rag_metadata.py`
- `backend_python/query_rewrite.py`
- `backend_python/embedding_client.py`
- `backend_python/rerank_client.py`
- `backend_python/vector_store.py`
- `backend_python/rag_evaluation.py`
- `backend_python/rag_explain.py`
- `backend_python/rag_quality.py`
- `backend_python/rag_logging.py`
- `backend_python/routes/rag.py`
- `backend_python/routes/rag_documents.py`
- `tests/test_rag_document_lifecycle.py`
- `tests/test_rag_metadata_filter.py`
- `tests/test_rag_document_dedup.py`
- `tests/test_rag_query_rewrite.py`
- `tests/test_rag_hybrid_retrieval.py`
- `tests/test_rag_rerank_retrieval.py`
- `tests/test_rag_hybrid_rerank_explain.py`
- `tests/test_rag_evaluation_management.py`
- `tests/test_admin_rag_quality.py`
- `tests/test_vector_store_contract.py`

尚未落地：

- OCR。
- Word / Excel / 网页解析。
- 异步入库任务队列。
- Redis / Celery。
- 真实 Qdrant / pgvector。
- 大规模知识库监控告警。

这些属于生产化深水区，后续可作为独立阶段。

### 2.6 Agent 工程化

已落地：

- Interview Orchestrator Agent。
- Agent State。
- Tool Calls。
- Agent Decision。
- fallback decision。
- normalize / guardrail。
- coach / interview 双模式。
- 连续弱回答识别。
- 重复问题保护。
- topic shift。
- nodeTrace。
- `observe_state`、`analyze_answer`、`retrieve_context`、`select_action`、`generate_question`、`update_memory` 轨迹。
- Agent 决策日志。
- Agent 日志接口。
- Agent Policy 策略层：
  - `backend_python/agent_policy.py`。
  - classic Agent 和 LangGraph 旁路共用同一套弱回答、重复追问、话题锁、coach/interview 差异策略。
  - policy 输出 `recommendedAction`、`difficulty`、`shouldExplainBeforeAsk`、`shouldAskUserChoice`、`requiresHumanReview`、`policyReasons` 和 `triggerRules`。
- LangGraph 迁移预留文档。
- LangGraph V1 旁路 POC。
- LangGraph V2 旁路工作流：
  - 真实/fake RAG adapter。
  - 真实/fake Agent decision adapter。
  - `apply_policy` 节点。
  - `threadId`。
  - `MemorySaver` checkpoint。
  - checkpoint summary 查询和 policy 摘要。
  - `POST /api/langgraph-agent/next-question-v2`。
  - `GET /api/langgraph-agent/checkpoint/{thread_id}`。

主要证据：

- `backend_python/agent_state.py`
- `backend_python/agent_tools.py`
- `backend_python/agent_trace.py`
- `backend_python/agent_orchestrator.py`
- `backend_python/agent_policy.py`
- `backend_python/interview_agent.py`
- `backend_python/agent_logging.py`
- `backend_python/routes/agent.py`
- `tests/test_agent_state.py`
- `tests/test_agent_tools.py`
- `tests/test_agent_trace.py`
- `tests/test_agent_orchestrator.py`
- `tests/test_agent_policy.py`
- `tests/test_interview_agent.py`
- `tests/test_interview_agent_route.py`
- `tests/test_agent_logging.py`
- `tests/test_agent_logs_api.py`
- `tests/frontend_agent_logs.test.mjs`
- `backend_python/langgraph_agent/`
- `backend_python/routes/langgraph_agent.py`
- `tests/test_langgraph_agent_state.py`
- `tests/test_langgraph_agent_nodes.py`
- `tests/test_langgraph_agent_checkpoint.py`
- `tests/test_langgraph_agent_adapters.py`
- `tests/test_langgraph_agent_graph.py`
- `tests/test_langgraph_agent_graph_v2.py`
- `tests/test_langgraph_agent_route.py`

尚未落地：

- checkpoint 持久化。
- human-in-the-loop 中断恢复。

LangGraph V1 POC 已经证明 StateGraph 节点链路可以跑通。LangGraph V2 已经在旁路流程里接入真实/fake RAG、真实/fake Agent 决策和 checkpoint/thread state，同时继续保持主面试接口稳定。当前 V3 阶段新增 Agent Policy 作为 classic Agent 与 LangGraph 旁路的公共策略层，并在 LangGraph 图中加入 `apply_policy` 节点。后续如果继续深入 LangGraph，应进入 checkpoint 持久化、真正的 human-in-the-loop interrupt 或 runtime 灰度切换设计，而不是重复 V1/V2。

### 2.7 训练闭环

已落地：

- 报告里的逐题复盘。
- weakTags 标准化。
- candidateProfile.frequentWeakTags 聚合。
- weaknessStrategy。
- weakTag 训练模板。
- 训练任务表。
- 从报告生成训练任务。
- 训练任务开始 / 完成 / 归档。
- Agent 读取候选训练任务。
- Agent 使用训练模板 hint。

主要证据：

- `backend_python/training_tags.py`
- `backend_python/weakness_strategy.py`
- `backend_python/weakness_training_templates.py`
- `backend_python/training_tasks.py`
- `backend_python/routes/training.py`
- `backend_python/routes/interview.py`
- `tests/test_training_tags.py`
- `tests/test_weakness_strategy.py`
- `tests/test_weakness_training_templates.py`
- `tests/test_training_tasks.py`
- `tests/test_training_task_generation.py`
- `tests/test_agent_training_tasks.py`

当前边界：

- 训练模板覆盖了一批核心 weakTag，但题库内容仍可以继续扩充。
- 掌握度评分仍是规则版。
- 专项训练体验还没有独立成完整产品页面。

### 2.8 管理员后台

已落地：

- 管理员角色。
- 管理员权限依赖。
- 后台 summary。
- 用户只读列表。
- RAG 文档只读列表。
- RAG 日志只读列表。
- RAG 质量摘要。
- Agent 日志只读列表。
- 后台配置只读接口。

主要证据：

- `backend_python/routes/admin.py`
- `tests/test_admin_auth.py`
- `tests/test_admin_routes.py`
- `tests/test_admin_rag_quality.py`
- `tests/frontend_admin_permissions.test.mjs`
- `tests/frontend_admin_dashboard.test.mjs`

当前边界：

- 后台仍是 MVP。
- 没有复杂筛选、分页、导出、运营配置和审计日志。

### 2.9 前端

已落地：

- 原生 HTML / CSS / JavaScript 单页应用。
- 登录 / 注册 / token 自动刷新。
- 面试训练工作台。
- 简历上传入口。
- RAG 文档管理入口。
- RAG debug 面板。
- RAG 日志面板。
- Agent 日志面板。
- 历史复盘。
- 训练中心。
- 管理员后台入口。
- 桌面端和移动端基本适配。
- 前端产品化 V2：
  - 产品级导航分区。
  - 面试工作台 Agent 决策解释层。
  - RAG 文档生命周期和命中解释展示。
  - 训练中心行动计划。
  - 管理员 RAG 质量诊断面板。

主要证据：

- `index.html`
- `styles.css`
- `app.js`
- `tests/frontend_*.test.mjs`
- `docs/specs/completed/frontend-productization-v2-design.md`
- `docs/plans/completed/frontend-productization-v2.md`

当前边界：

- 仍是单页堆叠式结构。
- `app.js` 体积较大。
- 用户端、训练中心、知识库管理、后台管理已有产品分区，但还没有拆成多页面或 JS 模块化架构。
- 视觉和交互已有阶段性改善，但还不是最终商业级 UI。

### 2.10 部署工程化

已落地：

- `.env.example`。
- 本地 SQLite 配置。
- PostgreSQL 连接示例。
- Alembic 基础迁移脚本。
- 本地启动脚本。
- 部署技术选型文档。
- 上线前检查清单。
- `.env.production.example`。
- `.dockerignore`。
- `Dockerfile`。
- `docker-compose.yml`。
- Nginx 反向代理配置。
- PostgreSQL / Redis / Celery worker / Nginx 的 Docker Compose 编排。
- Docker + Nginx + VPS 上线 V1 文档。
- 故障排查、备份回滚、Cloudflare/HTTPS 文档。
- 部署配置测试。

主要证据：

- `.env.example`
- `alembic.ini`
- `alembic/`
- `start-python-server.cmd`
- `docs/roadmap/deployment-tech-selection.md`
- `docs/roadmap/deployment-preflight-checklist.md`
- `.env.production.example`
- `.dockerignore`
- `Dockerfile`
- `docker-compose.yml`
- `deploy/nginx/ai-interview.conf`
- `docs/deployment/`
- `tests/test_deployment_config.py`

尚未落地：

- 真实云服务器部署。
- HTTPS。
- 对象存储。
- 日志轮转。
- 生产环境监控。

Docker + Nginx + VPS 上线 V1 已完成本地容器化演练和 GitHub 合并；真实 VPS、域名、HTTPS 实机部署仍属于后续可选阶段。

## 3. 不要重复执行的旧路线

以下内容已经阶段性完成，不要再作为新阶段主线重复执行：

- RAG 文档管理。
- RAG 生命周期和权限边界。
- metadata filter。
- query rewrite。
- hybrid search。
- rerank 解释。
- RAG evaluation case。
- 低质量召回面板。
- VectorStore 抽象。
- Agent V3 nodeTrace。
- coach / interview 双模式。
- weakTag 训练模板 V1。
- 训练任务系统。
- 管理员后台 MVP。
- LangGraph 迁移预留文档。

这些可以复盘、查漏补缺，但不应再被旧 spec 当成“下一步待执行”。

## 4. 真正待开发的大方向

### 方向 A：Vue3 前端重构

目标：

```text
把当前原生 HTML/CSS/JS 单页应用，渐进式重构为 Vue3 + Vite + TypeScript 的前后端分离产品前端。
```

当前状态：

```text
前端产品化 V2 已经完成阶段性版本，但仍然是原生单页堆叠结构。当前新主线是 Vue3 前端重构 V1，采用新旧前端并行方式，先保留旧页面作为兜底入口。
```

适合解决的问题：

- 页面堆叠感强。
- 工作台、训练中心、知识库、后台混在一个页面。
- `app.js` 越来越大。
- 项目展示效果不够专业。

建议范围：

- 新建 `frontend/` Vue3 工程。
- 使用 Vite + TypeScript。
- 使用 Vue Router 拆分页面。
- 使用 Pinia 管理登录态和核心业务状态。
- 封装 API client。
- 设计用户端信息架构和极简视觉系统。
- 保留旧页面作为兜底入口。
- 保持现有后端 API 兼容。
- 补前端测试和浏览器验证。

推荐程度：当前主线。

原因：

```text
项目功能已经较多，继续堆在原生单页里会增加维护成本。Vue3 重构既能提升展示效果，也能体现前端工程化能力，并为后续知识库、训练中心、管理后台迁移提供更清晰的页面边界。
```

### 方向 B：部署工程化实战

目标：

```text
让项目从本地可运行，升级到可以在云服务器上部署。
```

适合解决的问题：

- 项目已经有 Docker / Nginx / Compose 本地演练，但还没有真实 VPS 部署。
- 域名、HTTPS、Cloudflare 和真实公网访问还没落地。
- 生产环境日志轮转和监控还可以继续增强。

建议范围：

- Dockerfile。
- docker-compose.yml。
- PostgreSQL 或 MySQL 生产数据库。
- Nginx 反向代理配置。
- 环境变量整理。
- 日志目录和日志轮转方案。
- 部署文档。

推荐程度：已完成 V1 本地演练，真实 VPS 部署暂缓。

原因：

```text
Docker + Nginx + VPS 上线 V1 已经完成本地容器化基线和文档闭环，并已合并到 main。用户当前希望转向 Vue3 前端重构，真实 VPS 部署后续再做。
```

### 方向 C：LangGraph 深化

目标：

```text
在已经完成 LangGraph V2 的基础上，继续评估 checkpoint 持久化、human-in-the-loop、agentRuntime 灰度切换或更完整的工作流治理。
```

适合解决的问题：

- 用户目标岗位涉及 Agent 开发。
- 项目已经有 Agent State、ToolCalls、Decision、nodeTrace。
- LangGraph V1 POC 和 V2 旁路工作流已经跑通。
- 后续可以从“能接入框架”继续升级到“能治理工作流状态、人工中断和灰度切换”。

建议范围：

- 不替换主流程。
- 保留 V1 / V2 旁路接口。
- 不直接替换主流程。
- 可选设计 `agentRuntime = classic | langgraph`。
- 可选引入持久化 checkpoint。
- 可选设计 human-in-the-loop interrupt / resume。
- 可选把 LangGraph V2 的运行结果接入更完整的后台调试页面。

推荐程度：高，但建议和面试体验增强合并推进。

原因：

```text
用户目标岗位涉及 Agent 开发；LangGraph V2 已完成，继续深化可以从“框架接入”推进到“工作流治理”。但这一步改动风险更高，建议先讨论清楚是否要做持久化 checkpoint、human-in-the-loop，还是先转向前端重构或面试体验增强。
```

### 方向 D：知识库和面试体验小幅增强

目标：

```text
继续补充题库和训练内容，让面试体验更自然。
```

适合解决的问题：

- 某些岗位知识样例仍少。
- 某些 weakTag 的训练问题不够丰富。
- 面试题长期使用可能重复。

建议范围：

- 扩充 seed 数据。
- 扩充 evaluation case。
- 扩充 weakTag 模板问题池。
- 小幅优化 Agent 问题生成策略。

推荐程度：中。

原因：

```text
这条线已经做过一轮，再做会有收益递减。适合作为其他阶段中的小任务，而不是下一阶段主线。
```

## 5. 当前推荐路线

由于用户当前已经完成 Agent / RAG / 后端生产化 / Docker + Nginx 部署基线等阶段性能力，并且希望让项目页面更像正式产品，当前推荐路线更新为：

```text
第一步：面试体验增强 V3 + LangGraph 深化（已完成阶段性版本）
第二步：后端生产化 V1：数据库适配 + Redis + Celery（已完成阶段性版本）
第三步：Docker + Nginx + VPS 上线 V1（已完成本地容器化演练并合并 main）
第四步：Vue3 前端重构 V1（当前准备执行）
第五步：最终项目讲解、简历表达和面试训练
```

理由：

- RAG、Agent、训练闭环、后台 MVP 已经具备阶段性能力。
- 前端产品化 V2 已经完成阶段性版本。
- LangGraph V1 POC 和 V2 旁路工作流已经完成，下一步不应重复做 V1/V2。
- 用户目标岗位是 AI 应用开发岗，继续做 LangGraph 深化有价值；用户同时希望面试体验更自然，因此本阶段采用合并 spec。
- 部署工程化 V1 已经完成本地容器化演练和 GitHub 合并，真实 VPS 可作为后续独立阶段。
- 当前前端仍是原生单页堆叠结构，继续扩展会让维护和展示压力增加。
- Vue3 重构能同时服务三件事：视觉展示、前端工程化学习、产品体验提升。
- 重构采用新旧前端并行策略，先保留旧页面作为兜底入口，降低迁移风险。

## 6. 当前 spec / plan 状态

当前 `docs/specs/active/` 应包含：

```text
docs/specs/active/vue3-frontend-rebuild-v1-design.md
```

当前 `docs/plans/active/` 应为空，等待用户 review Vue3 spec 后再编写 implementation plan。

```text
docs/plans/active/
```

当前已落地的部署 V1 骨架：

- `.env.production.example`
- `.dockerignore`
- `Dockerfile`
- `docker-compose.yml`
- `deploy/nginx/ai-interview.conf`
- `docs/deployment/`
- `docs/learning/12-Docker-Nginx-VPS上线链路怎么理解.md`
- `tests/test_deployment_config.py`

当前已完成的部署 V1 验证：

- `python -m pytest tests/test_deployment_config.py -q` 通过。
- `python -m pytest -q` 通过。
- 全部前端 `.mjs` 测试通过。
- `docker build -t ai-interview-app:local .` 通过。
- `docker compose -p ai-interview --env-file .env.production.example config` 通过。
- `docker compose -p ai-interview --env-file .env.production.example up -d --no-build` 通过。
- PostgreSQL 干净数据卷下 `alembic upgrade head` 通过。
- Nginx 入口 `http://127.0.0.1:8080/api/health` 通过。
- FastAPI docs 入口 `http://127.0.0.1:8080/docs` 通过。
- Celery worker 已注册 health 和 RAG evaluation 任务。

Docker + Nginx + VPS 上线 V1 已完成并归档到：

```text
docs/specs/completed/docker-nginx-vps-deployment-v1-design.md
docs/plans/completed/docker-nginx-vps-deployment-v1.md
```

下一步是 review Vue3 前端重构 V1 spec，确认后编写 implementation plan。

后端生产化 V1 已完成并归档到：

```text
docs/specs/completed/backend-production-v1-postgres-redis-celery-design.md
```

对应 plan：

```text
docs/plans/completed/backend-production-v1-postgres-redis-celery.md
```

本阶段明确本地继续默认 SQLite，不要求立即安装 PostgreSQL；Redis 和 Celery 已完成基础设施和最小异步任务闭环，尚未做 Docker/Nginx/云服务器上线。

面试体验增强 V3 + LangGraph 深化已完成并归档到：

```text
docs/specs/completed/interview-experience-v3-langgraph-deepening-design.md
```

主题：

```text
面试体验增强 V3 + LangGraph 深化：通过 Agent Policy 连接 classic Agent 与 LangGraph 旁路工作流。
```

对应 plan：

```text
docs/plans/completed/interview-experience-v3-langgraph-deepening.md
```

## 7. 追求目标模式使用规则

如果 `docs/specs/active/` 为空，不要直接启动追求目标开发。

正确流程：

```text
先看本文档
-> 讨论下一阶段
-> 写新的 spec 到 docs/specs/active/
-> 写新的 plan 到 docs/plans/active/
-> 再复制追求目标文本执行
```

如果某个旧文档提出的“下一步”和本文档冲突，以本文档为准。
