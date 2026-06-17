# AI 模拟面试系统

面向大学生、应届生和社会求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 工作流生成面试问题，面试结束后生成复盘报告和训练任务。管理员后台提供 RAG 命中、Agent 决策、LangGraph checkpoint、fallback 和 quality gate 观测。

## 当前主入口

- 后端 API / 旧兼容入口：`http://127.0.0.1:8000`
- 后端接口文档：`http://127.0.0.1:8000/docs`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- Vue3 主前端：`http://127.0.0.1:5173/vue/app/interview`
- Vue3 管理员后台：`http://127.0.0.1:5173/vue/app/admin`

`http://localhost:8000/` 当前仍可能显示旧版原生前端或后端根入口，不是当前主页面。根目录 `index.html`、`app.js`、`styles.css` 是旧版原生前端兼容入口，当前主前端是 `frontend/` 下的 Vue3 应用。

## 本地启动

分别启动后端和 Vue3 前端：

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

也可以先打开启动说明：

```powershell
.\start-dev.cmd
```

## 测试和构建

后端测试：

```powershell
python -m pytest -q
```

前端测试：

```powershell
cd frontend
npm.cmd run test
```

前端构建：

```powershell
cd frontend
npm.cmd run build
```

## 当前主链路

- 面试接口：`POST /api/interview/next-question`
- 默认 Agent runtime：`langgraph_mainline`
- 兼容兜底链路：`classic`
- RAG 接入：岗位知识库、题库、候选人画像三类 RAG 作为 `retrieve_context` 节点复用。
- 可观测性：RAG 日志、Agent 决策日志、runtime audit、checkpoint summary、quality gate。

## 文档入口

- 当前路线：`docs/roadmap/current-state.md`
- 开发基线：`docs/project-baseline.md`
- 当前 spec：`docs/specs/active/`
- 当前 plan：`docs/plans/active/`
- 审计记录：`docs/audits/project-closure-audit-v1.md`

## 当前阶段边界

本阶段不引入 Redis、Celery、PostgreSQL，不做 Docker/Nginx/VPS/HTTPS 上线，不重构 RAG、Agent、LangGraph 或 Vue3 主链路。下一阶段再讨论后端生产化底座。
