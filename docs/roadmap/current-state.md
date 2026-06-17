# AI 模拟面试系统当前状态与下一阶段路线

更新时间：2026-06-14

## 0. 当前执行焦点

当前 active 开发阶段：

```text
面试训练闭环增强 V3
```

当前 active spec：

```text
docs/specs/active/interview-training-loop-v3-design.md
```

当前 active plan：

```text
docs/plans/active/interview-training-loop-v3.md
```

当前实现进度：

```text
LangGraph 主链路灰度迁移 V5 已完成并归档。当前准备执行 CBA 路线中的 C 阶段：面试训练闭环增强 V3，目标是把训练任务从列表状态推进为可作答、可反馈、可更新掌握度的专项练习会话。
```

上一阶段完成目标：

```text
Project Directory Cleanup V1 已完成：新增后端、Vue3 前端和本地开发启动脚本，旧启动脚本改为兼容入口，README 明确 8000 是后端 API/旧入口、5173 是 Vue3 当前主前端，并用测试锁住旧原生前端文件仍保留。
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
- AI Debug Console V1：
  - 最近 AI trace 列表。
  - 单次 trace 详情。
  - RAG 召回链路摘要。
  - Agent 决策链路摘要。
  - LangGraph checkpoint / nodeTrace 摘要。
  - fallback、空召回、弱召回、缺少 checkpoint、human review 等规则诊断建议。

主要证据：

- `backend_python/routes/admin.py`
- `backend_python/ai_debug.py`
- `tests/test_admin_auth.py`
- `tests/test_admin_routes.py`
- `tests/test_admin_rag_quality.py`
- `tests/test_admin_ai_debug.py`
- `tests/frontend_admin_permissions.test.mjs`
- `tests/frontend_admin_dashboard.test.mjs`
- `frontend/src/api/admin.ts`
- `frontend/src/stores/admin.ts`
- `frontend/src/pages/app/AdminPage.vue`
- `frontend/src/pages/app/admin-page.test.ts`
- `frontend/src/stores/admin.test.ts`

当前边界：

- 后台已从 MVP 进入可观测性增强阶段，但仍不是完整运营后台。
- AI Debug Console V1 对旧日志使用 best-effort 关联，缺少请求时统一写入的强 traceId。
- 没有复杂筛选、导出、运营配置、审计日志和完整 RBAC 写操作。

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
Vue3 前端重构 V1 已经完成阶段性版本，Vue3 管理员后台 V1 也已经落地。当前新主线不是重复搭建 Vue3 工程，而是在现有 Vue3 前端上继续产品化用户工作台 V2，重点打磨档案、面试和训练闭环。
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

由于用户当前已经完成 Agent / RAG / 后端生产化 / Docker + Nginx 部署基线 / Vue3 前端 V1 / Vue3 管理员后台 V1 等阶段性能力，并且希望让项目页面更像正式产品，当前推荐路线更新为：

```text
第一步：面试体验增强 V3 + LangGraph 深化（已完成阶段性版本）
第二步：后端生产化 V1：数据库适配 + Redis + Celery（已完成阶段性版本）
第三步：Docker + Nginx + VPS 上线 V1（已完成本地容器化演练并合并 main）
第四步：Vue3 前端重构 V1（已完成阶段性版本）
第五步：Vue3 管理员后台 V1（已完成阶段性版本）
第六步：Vue3 用户工作台 V2（已完成阶段性版本）
第七步：Vue3 面试报告与训练闭环 V1（已完成阶段性版本）
第八步：Vue3 知识库页面产品化 V1（已完成阶段性版本）
第九步：AI Debug Console V1（已完成阶段性版本）
第十步：LangGraph Runtime Governance V3（已完成阶段性版本）
第十一步：RAG Document Ingestion V2（已完成阶段性版本）
第十二步：Interview Workbench Experience V4（已完成阶段性版本）
第十三步：Training Center V2（已完成阶段性版本）
第十四步：Project Directory Cleanup V1（已完成阶段性版本）
第十五步：LangGraph 主链路灰度迁移 V5（已完成阶段性版本）
第十六步：下一阶段方向待讨论，可在 LangGraph 主链路继续生产化、训练系统继续增强、RAG 生产化补强、最终项目讲解之间选择。
```

理由：

- RAG、Agent、训练闭环、后台 MVP 已经具备阶段性能力。
- Vue3 前端 V1 和管理员后台 V1 已经完成阶段性版本。
- LangGraph V1 POC 和 V2 旁路工作流已经完成，下一步不应重复做 V1/V2。
- 部署工程化 V1 已经完成本地容器化演练和 GitHub 合并，真实 VPS 可作为后续独立阶段。
- 管理员后台不应承载普通用户的面试和档案主流程。
- 用户工作台 V2 已经完成档案页、面试页和训练页的阶段性产品化。
- 面试报告与训练闭环 V1 已经完成历史、报告和训练任务的闭环产品化。
- Vue3 知识库页面产品化 V1 已经把 RAG 文档、chunks、状态管理和 debug 解释接入 Vue3 页面。
- AI Debug Console V1 已经把 RAG、Agent 和 LangGraph 的调试链路接入管理员后台。
- LangGraph Runtime Governance V3 已经完成 checkpoint summary、interrupt / resume、runtime 灰度切换和 AI Debug Console runtime 可观测性。
- RAG Document Ingestion V2 已经完成文件上传、文本解析、文本清洗、chunk 预览、入库任务状态和 Vue3 文件导入入口。
- Project Directory Cleanup V1 已完成并归档，下一步不应继续执行旧 active plan，应先讨论新的阶段方向。
- LangGraph 主链路灰度迁移 V5 已完成，LangGraph 已从旁路候选 runtime 推进到管理员可灰度选择的可见链路，但 classic Agent 仍是默认稳定主链路。

## 6. 当前 spec / plan 状态

当前 `docs/specs/active/` 应包含：

```text
暂无
```

当前 `docs/plans/active/` 应包含：

```text
暂无
```

当前不要再执行已经归档的 Vue3 前端重构 V1、管理员后台 V1、用户工作台 V2、报告训练闭环 V1、知识库页面产品化 V1、AI Debug Console V1、Interview Workbench Experience V4、Training Center V2 和 Project Directory Cleanup V1 plan。
LangGraph Runtime Deepening V4 和 LangGraph 主链路灰度迁移 V5 也已完成并归档，下一步应先讨论新的阶段方向，再写新的 active spec 和 active plan。

它们已经移动到：

```text
docs/specs/completed/vue3-frontend-rebuild-v1-design.md
docs/specs/completed/vue3-admin-console-v1-design.md
docs/specs/completed/vue3-user-workbench-v2-design.md
docs/specs/completed/vue3-report-training-loop-v1-design.md
docs/specs/completed/vue3-knowledge-base-productization-v1-design.md
docs/specs/completed/ai-debug-console-v1-design.md
docs/specs/completed/interview-workbench-experience-v4-design.md
docs/specs/completed/training-center-v2-design.md
docs/specs/completed/project-directory-cleanup-v1-design.md
docs/specs/completed/langgraph-mainline-canary-v5-design.md
docs/plans/completed/vue3-frontend-rebuild-v1.md
docs/plans/completed/vue3-admin-console-v1.md
docs/plans/completed/vue3-user-workbench-v2.md
docs/plans/completed/vue3-report-training-loop-v1.md
docs/plans/completed/vue3-knowledge-base-productization-v1.md
docs/plans/completed/ai-debug-console-v1.md
docs/plans/completed/interview-workbench-experience-v4.md
docs/plans/completed/training-center-v2.md
docs/plans/completed/project-directory-cleanup-v1.md
docs/plans/completed/langgraph-mainline-canary-v5.md
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

下一步需要先讨论新的阶段方向，再写新的 spec 和 plan。

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
## 2026-06-12 本轮补充记录：Vue3 管理员后台 V1

Vue3 管理员后台 V1 已完成阶段性实现：

- `frontend/src/api/admin.ts`：封装只读管理员后台接口。
- `frontend/src/stores/admin.ts`：集中管理后台概览、账号列表、RAG 质量、Agent 日志和系统配置状态。
- `frontend/src/pages/app/AdminPage.vue`：实现管理员后台页面。
- `frontend/src/App.vue`：应用启动时恢复登录态，避免刷新后台页误判权限。
- `frontend/src/layouts/AppLayout.vue`：普通用户隐藏后台入口，移动端限制外层横向溢出。
- `docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md`：新增学习复盘文档。

已验证：

```text
frontend: npm.cmd run test
frontend: npm.cmd run build
backend: python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_admin_rag_quality.py -q
browser: 普通用户无后台入口，管理员可访问后台，移动端无外层横向溢出
```

后续如果继续做管理员后台，应新开 V2 spec，重点考虑审计日志、分页筛选、账号写操作保护和更完整的 RBAC，而不是重复实现 V1。

## 2026-06-12 本轮补充记录：Vue3 用户工作台 V2

Vue3 用户工作台 V2 已完成阶段性实现：

- `frontend/src/components/profiles/ProfileCurrentCard.vue`：新增当前档案摘要卡片。
- `frontend/src/components/profiles/ProfileList.vue`：新增档案列表、当前标识、设为当前和开始面试动作。
- `frontend/src/pages/app/ProfilesPage.vue`：升级为当前档案、新建档案和档案列表三段式页面。
- `frontend/src/stores/interview.ts`：新增 `agentMode` 和 `setAgentMode()`。
- `frontend/src/components/interview/InterviewModeSwitch.vue`：新增学习辅导 / 真实面试模式切换。
- `frontend/src/components/interview/CurrentProfileBanner.vue`：新增当前面试档案横幅。
- `frontend/src/components/interview/InterviewEvidencePanel.vue`：用“为什么这样问 / 本题参考资料”替代偏调试化表达。
- `frontend/src/pages/app/InterviewPage.vue`：新增未选档案引导、当前档案摘要和模式切换。
- `frontend/src/components/training/TrainingTaskList.vue`：新增训练任务列表和空状态。
- `frontend/src/pages/app/TrainingPage.vue`：从占位页升级为训练中心入口页。
- `docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md`：新增学习复盘文档。

已验证：

```text
frontend: npm.cmd run test
结果：13 passed, 39 tests passed

frontend: npm.cmd run build
结果：通过

browser:
- /vue/app/profiles：显示当前档案、新建档案、档案列表和开始面试入口。
- /vue/app/interview：未选档案时显示引导；已选档案时显示当前档案、模式切换和解释面板。
- /vue/app/training：显示训练来源说明、训练任务入口和空状态。
- 移动端 390px 左右无横向溢出。
- 页面未出现 undefined。
```

Vue3 用户工作台 V2 已完成，不要再重复执行本阶段旧 plan。

## 2026-06-13 本轮补充记录：Vue3 面试报告与训练闭环 V1

Vue3 面试报告与训练闭环 V1 已完成阶段性实现：

- `frontend/src/api/history.ts`：封装历史面试记录接口。
- `frontend/src/api/training.ts`：封装训练任务读取、生成、开始、完成和归档接口。
- `frontend/src/stores/history.ts`：集中管理历史记录、档案筛选、岗位搜索和排序。
- `frontend/src/stores/report.ts`：集中管理单场报告、逐题复盘、weakTags 和训练任务生成。
- `frontend/src/stores/training.ts`：集中管理训练任务列表、状态筛选、来源报告和 weakTag 筛选。
- `frontend/src/pages/app/HistoryPage.vue`：实现 Vue3 历史复盘页。
- `frontend/src/pages/app/ReportPage.vue`：实现 Vue3 单场面试报告页。
- `frontend/src/pages/app/TrainingPage.vue`：从训练入口升级为真实训练任务页。
- `docs/learning/15-Vue3面试报告历史复盘和训练闭环怎么串起来.md`：新增学习复盘文档。

已验证：

```text
frontend: npm.cmd run test
结果：19 个测试文件通过，54 个测试通过

frontend: npm.cmd run build
结果：通过

browser:
- /vue/app/history：历史记录、档案筛选、岗位关键词筛选和排序可用。
- /vue/app/reports/1219：报告总览、逐题复盘、weakTags、提问依据和训练入口可用。
- /vue/app/training?recordId=1219&weakTag=langgraph_checkpoint：训练任务筛选、开始、完成、归档和来源报告跳转可用。
- 桌面端和移动端已做基础验证。
```

后续如果继续做用户端工作台，应新开 spec，重点考虑：

- 知识库页面 Vue3 产品化。
- 专项训练题目内容继续扩充。
- 更细的移动端体验打磨。

## 2026-06-13 本轮补充记录：Vue3 知识库页面产品化 V1

Vue3 知识库页面产品化 V1 已完成阶段性实现：

- `frontend/src/api/knowledge.ts`：封装 RAG 文档列表、创建、详情、状态更新、删除和 debug 接口。
- `frontend/src/stores/knowledge.ts`：集中管理知识库文档、筛选条件、文档详情、debug 结果、加载状态和 metadata JSON 错误。
- `frontend/src/pages/app/KnowledgePage.vue`：从占位页升级为知识库工作台，包含文档列表、筛选、新增文档、详情 chunks、状态管理和 RAG debug。
- `frontend/src/api/knowledge.test.ts`：覆盖知识库 API 请求路径、payload 和 query params。
- `frontend/src/stores/knowledge.test.ts`：覆盖加载、筛选、metadata 校验、创建、详情、状态更新、删除和 debug。
- `frontend/src/pages/app/knowledge-page.test.ts`：覆盖页面渲染、筛选、表单、详情、删除确认和三类 RAG debug 展示。
- `docs/learning/16-Vue3知识库页面如何承接RAG工程能力.md`：新增学习复盘文档。

已验证：

```text
frontend: npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
结果：3 个测试文件通过，14 个测试通过

frontend: npm.cmd run test
结果：22 个测试文件通过，68 个测试通过

frontend: npm.cmd run build
结果：通过

browser:
- /vue/app/knowledge 桌面端：文档管理、空状态、新增文档、详情 chunks、RAG debug 可用。
- 实际新增一条 FastAPI Depends 测试样例后，文档列表、状态、可见性和详情 chunks 正常展示。
- RAG debug 显示岗位知识库、题库、候选人画像三类命中区域和召回质量解释区域。
- 移动端 390px 左右无横向溢出。
- 页面未出现 undefined。
```

本阶段已归档到：

```text
docs/specs/completed/vue3-knowledge-base-productization-v1-design.md
docs/plans/completed/vue3-knowledge-base-productization-v1.md
```

后续如果继续做知识库，应新开 spec，重点考虑：

- 文件上传和批量导入。
- 异步入库任务进度。
- OCR / Word / Excel / 网页解析。
- Qdrant / pgvector 持久化向量数据库。
- 管理员 RAG 审核与质量监控 V2。

## 2026-06-13 本轮补充记录：RAG Document Ingestion V2

RAG Document Ingestion V2 已完成阶段性实现：

- `backend_python/rag_ingestion.py`：新增文件名校验、文件大小校验、txt / md / pdf 文本解析、文本清洗和 ingestion preview。
- `backend_python/routes/rag_documents.py`：新增 `POST /api/rag/documents/upload` 和 `GET /api/rag/documents/ingestion-tasks/{task_id}`。
- `tests/test_rag_document_ingestion.py`：覆盖文件类型、空文件、文本清洗、preview 和 txt 解析。
- `tests/test_rag_documents_upload_route.py`：覆盖 txt / md 上传、任务状态查询、不支持文件类型和非法 metadata。
- `frontend/src/api/client.ts`：让 `FormData` 请求不再被错误设置为 `application/json`。
- `frontend/src/api/knowledge.ts`：新增文件上传和 ingestion task 查询 API。
- `frontend/src/stores/knowledge.ts`：新增上传状态、上传错误、ingestionTask 和 `uploadFile()`。
- `frontend/src/pages/app/KnowledgePage.vue`：新增文件导入面板，显示支持格式、任务结果和解析预览。
- `docs/learning/20-RAG文档摄取链路如何从文件到chunk.md`：新增中文学习文档。

已验证：

```text
backend focused: python -m pytest tests/test_rag_document_ingestion.py tests/test_rag_documents_upload_route.py -q
结果：12 passed

backend full: python -m pytest -q
结果：308 passed

frontend focused: npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
结果：3 个测试文件通过，19 个测试通过

frontend full: npm.cmd run test
结果：22 个测试文件通过，77 个测试通过

frontend build: npm.cmd run build
结果：通过

browser:
- /vue/app/knowledge 桌面端显示“文件导入”和“支持 txt、md、pdf”。
- 通过真实上传接口导入 txt 文件后，Vue3 知识库页面显示新文档 Browser Verify RAG Upload。
- 点击文档详情后可以看到导入文件生成的 chunk 内容。
- 移动端 390px 左右无横向溢出，clientWidth = scrollWidth = 375。
- 页面未出现 undefined。
```

本阶段已归档到：

```text
docs/specs/completed/rag-document-ingestion-v2-design.md
docs/plans/completed/rag-document-ingestion-v2.md
```

当前边界：

- PDF 解析依赖本地 `pypdf`，依赖不可用时会明确失败。
- 任务状态仍为内存态，服务重启会丢失，后续可迁移到 Redis / 数据库任务表。
- 本阶段是小文件同步导入，后续如果做生产级 RAG V3，可继续扩展批量导入、Celery 异步入库、OCR、Word / Excel / 网页解析和对象存储。
## 2026-06-14 本轮补充记录：LangGraph 主链路灰度迁移 V5

当前 active 开发阶段：

```text
LangGraph 主链路灰度迁移 V5
```

当前 active spec：

```text
暂无
```

当前 active plan：

```text
暂无
```

本阶段目标：

```text
在保留 classic Agent 默认稳定主链路的前提下，让管理员或实验账号可以请求 LangGraph canary。LangGraph 可见输出必须经过 runtime policy、quality gate、fallback classic 和 runtime audit，避免把不稳定输出直接暴露给普通用户。
```

本轮已落地：

- `runtime_policy.py`：判断用户是否允许使用实验 runtime。
- `runtime_audit.py`：记录 requestedRuntime、allowedRuntime、visibleRuntime、fallbackUsed 和原因。
- `agent_runtime.py`：支持 `langgraph_canary`，门禁通过时可见 LangGraph，失败时回退 classic。
- `/api/interview/next-question`：兼容可选 `agentRuntime` 字段，普通用户请求 canary 会降级 classic，管理员 canary 可以进入 LangGraph 可见链路。
- Vue3 面试页：管理员可见实验 runtime 开关，普通用户隐藏。
- AI Debug 后台：展示 Runtime 审计摘要。
- 模型供应商请求失败时，next-question 会返回安全兜底问题，并在 `agentDecision.triggerRules` 和 `runtimeAudit.qualityGateReasons` 中记录原因。

本阶段已归档到：

```text
docs/specs/completed/langgraph-mainline-canary-v5-design.md
docs/plans/completed/langgraph-mainline-canary-v5.md
```

已验证：

```text
python -m pytest -q
结果：339 passed, 1 warning

cd frontend; npm.cmd run test
结果：28 个测试文件通过，106 个测试通过

cd frontend; npm.cmd run build
结果：通过

browser:
- 桌面端面试页：管理员可见实验链路和 LangGraph 灰度，无 undefined，无横向溢出。
- 桌面端真实 canary 提交：没有请求失败，成功进入下一题。
- 桌面端管理员后台：Runtime 对比和 Runtime 审计可见，无 undefined，无横向溢出。
- 移动端面试页和管理员后台：无横向溢出，面试页从档案进入后可见 LangGraph 灰度。
```

## 2026-06-17 本轮补充记录：CBA 路线与面试训练闭环增强 V3

当前 active 开发阶段：

```text
面试训练闭环增强 V3
```

当前 active spec：

```text
docs/specs/active/interview-training-loop-v3-design.md
```

当前 active plan：

```text
docs/plans/active/interview-training-loop-v3.md
```

当前总路线文档：

```text
docs/roadmap/cba-development-roadmap.md
```

本阶段目标：

```text
把训练任务从“列表和状态按钮”升级为“专项练习会话”：用户能查看 weakTag 对应练习题、回答要点、常见错误和一分钟表达模板，输入练习回答并自评，提交后更新 masteryScore、attemptCount、lastPracticedAt 和任务状态，再回到面试台验证提升效果。
```

本阶段明确不做：

- 不重写 RAG 检索链路。
- 不重写 Agent 决策链路。
- 不引入新的 LangGraph 主链路。
- 不做生产级 RAG 异步入库、OCR、Qdrant 或 pgvector。
- 不做 Docker / Nginx / VPS 真实上线。

后续推荐顺序：

```text
C：面试体验与训练闭环 V3
-> B：LangGraph / Agent 工作流深化
-> A：生产级 RAG V3
```
