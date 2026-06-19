# 项目开发基线

更新时间：2026-06-18

## 1. 项目定位

本项目是面向大学生、应届毕业生和社会求职者的 AI 模拟面试系统，主要解决两类问题：

- 应届生和转岗求职者缺少真实面试训练。
- 求职者不清楚目标岗位会重点考察什么，也不知道自己的简历经历该如何被追问。

用户创建投递档案，录入简历、岗位 JD 和公司信息后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 与 LangGraph Agent 工作流生成个性化面试问题。面试结束后，系统生成复盘报告和训练任务。管理员后台用于查看 RAG 命中、Agent 决策、LangGraph runtime 审计、基础设施状态和异步任务状态，从而提高系统可观测性。

## 2. 当前主入口

公网演示：

- 登录页：`http://124.221.230.218:8080/vue/auth/login`
- 健康检查：`http://124.221.230.218:8080/api/health`

本地开发：

- 后端 API：`http://127.0.0.1:8000`
- 后端接口文档：`http://127.0.0.1:8000/docs`
- Vue3 主前端：`http://127.0.0.1:5173/vue/app/interview`
- Vue3 管理员后台：`http://127.0.0.1:5173/vue/app/admin`

根目录 `index.html`、`app.js`、`styles.css` 是旧版原生前端兼容入口。当前主前端是 `frontend/` 下的 Vue3 应用。

## 3. 本地启动

```powershell
.\start-backend.cmd
.\start-vue-frontend.cmd
```

查看启动说明：

```powershell
.\start-dev.cmd
```

## 4. 测试和构建

```powershell
python -m pytest -q
```

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

## 5. 当前主链路

核心接口：

```text
POST /api/interview/next-question
```

主链路可以概括为：

```text
投递档案
-> 三类 RAG 检索
-> 构造 Agent State
-> LangGraph mainline 工作流
-> Agent Policy / Decision / Quality Gate
-> LLM 生成下一题
-> 记录 RAG 日志、Agent 日志、runtime audit 和 checkpoint summary
-> 面试报告
-> weakTags
-> 训练任务
```

当前默认 runtime 是 `langgraph_mainline`，`classic` 作为兼容和兜底链路保留。

## 6. 目录结构

- `backend_python/`：FastAPI 后端、认证、数据库模型、RAG、Agent、LangGraph、训练任务和管理员接口。
- `frontend/`：Vue3 + Vite + TypeScript 主前端。
- `tests/`：后端 pytest 测试、旧前端 `.mjs` 测试和部分部署配置测试。
- `alembic/`：数据库迁移脚本。
- `deploy/`：Nginx 等部署配置。
- `docs/`：路线、spec、plan、学习、部署和项目讲解文档。
- `scripts/`：本地维护脚本和演示账号脚本。
- `data/`：本地开发数据，不作为生产数据源。

## 7. 部署形态

当前公网部署使用：

- VPS：Ubuntu 22.04
- 容器编排：Docker Compose
- Web 入口：Nginx
- 后端：FastAPI / Uvicorn
- 前端：Vue3 build 后由 Nginx 服务 `/vue/`
- 数据库：PostgreSQL
- 缓存和消息中间件：Redis
- 异步任务：Celery worker

当前部署边界：

- 已完成公网 IP + 8080 端口演示。
- 已完成 PostgreSQL、Redis、Celery、Nginx 容器化部署。
- 已完成 Alembic 生产迁移修复。
- 尚未接入域名和 HTTPS。
- 尚未做完整日志轮转、监控告警、自动备份、对象存储和 CI/CD。

## 8. 演示账号策略

当前演示账号只用于开发和公网演示：

- 普通账号：`d77013643@gmail.com`
- 管理员账号：`1011569954@qq.com`

密码不要写入文档和简历。真实演示前应改强密码，并轮换已经暴露过的模型 API Key。

## 9. 下一阶段边界

下一阶段不建议继续无边界加功能。更合理的路线是：

1. 公网演示稳定化：完整 smoke test、演示数据、README 和部署文档校准。
2. 安全收尾：API Key 轮换、弱密码限制、管理员密码策略、HTTPS 方案。
3. 项目讲解和简历材料：业务背景、架构图、核心难点、技术取舍、线上故障复盘。
4. 后续增强再单独开 spec：HTTPS、备份恢复、RAG 高级能力、前端视觉再打磨或运营后台增强。
