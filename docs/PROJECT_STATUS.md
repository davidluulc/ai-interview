# 项目状态总览

更新时间：2026-06-21

本文是公开项目状态短入口。更完整、可执行的状态说明以 [docs/roadmap/current-state.md](roadmap/current-state.md) 为准。

## 当前结论

AI 模拟面试训练系统已经完成第一版公网部署和核心业务闭环：

- 公网入口：`http://124.221.230.218:8080/vue/auth/login`
- 健康检查：`http://124.221.230.218:8080/api/health`
- 部署形态：Docker Compose + Nginx + FastAPI + PostgreSQL + Redis + Celery worker
- 当前主前端：`frontend/` 下的 Vue3 应用
- 默认 Agent runtime：`langgraph_mainline`
- 生产 embedding：`zhipu / embedding-3`

项目当前已经从“继续堆功能”进入“公网演示、项目讲解、README 和简历包装”阶段。

## 已落地能力

- 用户注册、登录、refresh token、Redis session 和管理员强制下线。
- 投递档案管理：简历、JD、公司信息、岗位标签和归档状态。
- AI 面试主链路：基于档案、RAG 和 Agent 决策生成面试问题。
- 面试复盘：生成报告、逐题复盘、weakTags 和训练计划。
- 训练闭环：根据报告生成训练任务，支持专项练习和 AI 批改提示。
- RAG 工程化：岗位知识库、题库、候选人画像、chunk、embedding、命中日志和质量诊断。
- Agent/LangGraph 可观测：Agent State、Tool Calls、Decision、fallback、nodeTrace 和 runtime audit。
- 管理员诊断工作台：按面试记录组织 RAG、Agent 和 AI trace。
- 生产部署：PostgreSQL、Redis、Celery、Nginx、Docker Compose 和 Alembic migration。

## 当前边界

- 已完成 IP + 8080 端口公网演示，尚未接入域名和 HTTPS。
- 已完成 Docker Compose 部署，尚未引入 Kubernetes、CI/CD、监控告警平台。
- 已有备份和回滚文档，尚未做生产数据库定时备份自动化。
- 已有 RAG/Agent/AI debug 诊断，统一 trace id 和更精细的跨表关联可作为后续版本。
- 根目录旧版 `index.html`、`app.js`、`styles.css` 暂保留为兼容入口，当前主前端为 `frontend/`。

## 推荐下一步

1. 完成 README、数据模型、部署和排障文档整理。
2. 准备公网演示数据和演示账号。
3. 把项目亮点沉淀为私有求职材料，不提交公开仓库。
4. 后续再考虑域名、HTTPS、备份自动化、统一 trace id 和监控告警。
