# 当前项目状态与下一阶段路线

更新时间：2026-06-19

本文档是当前项目路线的可信入口。判断下一步开发方向时，以本文档为准；旧 spec、旧 plan 和历史学习材料只作为背景资料。

## 1. 当前结论

项目已经完成第一版公网部署，并完成了一轮公网演示稳定化收口。

- GitHub 仓库：`https://github.com/davidluulc/ai-interview`
- 公网入口：`http://124.221.230.218:8080/vue/auth/login`
- 健康检查：`http://124.221.230.218:8080/api/health`
- 部署形态：Docker Compose + Nginx + FastAPI + PostgreSQL + Redis + Celery worker
- 默认 Agent runtime：`langgraph_mainline`
- 兼容 fallback runtime：`classic`
- 生产 embedding：`zhipu / embedding-3`

当前不再处于“继续无限加功能”的阶段，而是进入“公网演示安全收口、项目讲解和简历包装”阶段。

## 2. Active 状态

当前 active spec：
```text
暂无。Public Demo Stabilization + Production RAG Seed V1 已完成并归档。
```

当前 active plan：
```text
暂无。Public Demo Stabilization + Production RAG Seed V1 已完成并归档。
```

最近完成归档：
```text
docs/specs/completed/public-demo-stabilization-rag-seed-v1-design.md
docs/plans/completed/public-demo-stabilization-rag-seed-v1.md
```

## 3. Public Demo Stabilization + Production RAG Seed V1 完成情况

本阶段已把公网演示链路从“能打开”推进到“能走完整闭环”：

- 生产 RAG seed 已接入，支持幂等执行，并使用当前 embedding provider 生成向量。
- 生产 PostgreSQL 中已有 `role_knowledge` 和 `question_bank` 的 `embedding-3 / ready` chunk。
- 面试启动入口已修复：未选择投递档案不能开始，第一题由后端根据档案、JD 和 RAG 生成。
- 占位提示不再写入 `answeredHistory`。
- 面试官思考中 loading 已接入，生成第一题和分析回答的等待文案已区分。
- HTML/502/504 错误已转成友好提示，不再把 Nginx HTML 错误塞进聊天框。
- 点击“结束并复盘”后会生成 report、保存 history、生成训练任务，并跳转到 `/vue/app/reports/:recordId`。
- 后端 report 生成遇到慢模型或网关超时时有结构化 fallback，保证演示闭环不中断。
- 用户端知识库页面已简化，metadata JSON 和 RAG 调试默认放入高级区域。
- 投递档案支持归档/恢复，不做物理删除，保留历史记录和审计链路。
- 管理员后台 RAG 空召回提示已区分：未 seed、模型不匹配、无 ready chunk、候选人画像为空等原因。
- Nginx 已提高慢模型请求超时时间，减少公网面试链路 504。

公网验证证据：

```text
RAG seed:
question_bank  | embedding-3 | ready | 8
role_knowledge | embedding-3 | ready | 7

Public API smoke:
first question not placeholder
ragReasonCount = 3
report saved
history record created
training tasks generated
route /vue/app/reports/:id
```

本地验证命令已通过：

```bash
python -m pytest -q
cd frontend && npm.cmd run test
cd frontend && npm.cmd run build
docker compose --env-file .env.production.example config --quiet
```

验证结果：

```text
backend pytest: 427 passed
frontend vitest: 31 files passed, 138 tests passed
frontend build: succeeded
compose config: succeeded
```

## 4. 已真实落地的核心能力

### 4.1 用户和权限

- 用户注册、登录、退出登录
- access token 和 refresh token
- token blacklist
- 管理员角色字段和管理员权限依赖
- 管理员后台只允许管理员访问

### 4.2 投递档案和面试

- 用户创建投递档案，录入简历、岗位 JD、公司信息和岗位标签
- 面试页基于当前档案进入模拟面试
- 面试接口：`POST /api/interview/next-question`
- 支持 coach / interview 模式
- 面试结束后生成复盘报告和 weakTags
- 面试历史记录持久化
- 基于报告生成训练任务

### 4.3 RAG 工程化

- 岗位知识库 RAG
- 题库 RAG
- 候选人画像 RAG
- RAG 文档管理
- RAG 文档生命周期：enabled / disabled / archived
- 文档可见性：private / public
- metadata 存储和过滤
- 文档 hash、chunk hash 和去重统计
- BM25、向量检索、hybrid search、rerank、query rewrite
- RAG 命中日志、RAG debug、RAG 质量诊断和 evaluation case
- RAG 文件上传和数据库持久化摄取任务
- Celery worker 处理 RAG ingestion task
- Production RAG seed

### 4.4 Agent 和 LangGraph

- Agent State
- Tool Calls
- Agent Decision
- fallback decision
- normalize / guardrail
- policy layer
- nodeTrace
- RAG tools 被 LangGraph `retrieve_context` 节点复用
- `langgraph_mainline` 作为默认主链路
- `classic` 保留为 fallback/debug 链路
- checkpoint summary、runtime audit、quality gate 和 fallback summary 接入观测

### 4.5 训练闭环

- 面试报告生成 weakTags
- weakTags 生成训练任务
- 训练任务支持开始、完成、归档
- 专项练习面板展示练习题、答题要点、常见错误和一分钟表达模板
- 提交练习后更新 masteryScore、attemptCount 和 lastPracticedAt

### 4.6 Vue3 前端

- Vue3 + Vite + TypeScript 主前端
- 登录 / 注册
- 用户工作台
- 档案页面
- 面试页面
- 知识库页面
- 历史复盘和报告页面
- 训练中心
- 管理员后台

### 4.7 部署工程化

- Dockerfile
- docker-compose.yml
- Nginx 反向代理和 Vue 静态资源服务
- PostgreSQL 生产数据库
- Redis
- Celery worker
- Alembic migration
- `.env.production.example`
- 部署、排错、备份回滚和 HTTPS 参考文档

## 5. 上线过程中暴露并修复的问题

### 5.1 PostgreSQL schema 缺字段

表现：
```text
登录、知识库或管理员后台出现 Internal server error
```

根因：
本地 SQLite 有自动补表逻辑，但生产 PostgreSQL 依赖 Alembic migration。部分模型字段已经被代码使用，但旧迁移没有完整创建字段。

处理：
- 线上热修缺失字段
- 补充正式 Alembic migration
- 增加迁移防漏测试

面试讲法：
这是典型生产化问题，可以包装成“本地开发环境与生产数据库迁移差异导致的线上 500 排查和修复”。

### 5.2 生产 RAG 数据为空

表现：
```text
后台 RAG 质量诊断大量 empty recall，面试问题参考资料弱相关。
```

根因：
生产 PostgreSQL 初始没有 `rag_chunks`，切到智谱 embedding 后需要用当前模型重新 seed 或重新入库。

处理：
- 新增幂等 Production RAG seed
- 使用 `embedding-3` 生成 ready chunk
- 补充 RAG 日志字段相关种子资料，提升命中解释能力

### 5.3 慢模型导致 Nginx 504

表现：
```text
POST /api/interview/next-question 出现 504 Gateway Time-out。
```

根因：
后端 LLM 请求最终能返回，但耗时超过 Nginx 默认等待时间。

处理：
- 提高 Nginx `proxy_read_timeout` / `proxy_send_timeout`
- 前端增加 thinking loading
- 前端把 HTML/504 转成友好错误
- report 链路增加 fallback，避免复盘保存被慢模型彻底卡死

### 5.4 面试结束没有沉淀历史

表现：
```text
点击“结束并复盘”后跳到页面，但没有历史记录和训练任务。
```

根因：
旧前端只做路由跳转，没有串联 report -> history -> training。

处理：
- 前端完成结束复盘闭环
- 保存 `InterviewRecord`
- 生成训练任务
- 跳转到报告详情页

## 6. 当前仍未完成的边界

- 域名
- HTTPS
- API Key 轮换
- 管理员强密码策略
- 注册弱密码限制
- 自动备份
- 日志轮转
- 监控告警
- 对象存储
- CI/CD
- Qdrant / pgvector
- OCR、Word、Excel、网页解析

这些不是当前演示闭环的阻塞项，建议分阶段处理。

## 7. 推荐下一阶段

### 推荐 A：Pre-Launch Stabilization V1

目标：
把项目从“公网可运行”整理成“可以稳定发给 HR 演示”。

范围：
- 用虚构演示资料完整跑一遍 smoke test。
- 修复公网链路中剩余的小 bug。
- 轮换暴露过的 DashScope / 智谱 API Key。
- 管理员账号改强密码。
- 注册弱密码限制。
- README、current-state 和部署文档校准。
- 准备一组演示数据。
- 记录上线问题复盘。

推荐优先级：最高。

### 可选 B：HTTPS 和域名

目标：
把 `http://IP:8080` 升级成更正式的 HTTPS 访问。

范围：
- 购买域名
- DNS 解析
- Nginx 80/443
- Certbot 或 Cloudflare HTTPS
- 更新 CORS / 前端 API base URL

推荐优先级：中高。适合在演示链路稳定后做。

### 可选 C：项目讲解和简历包装

目标：
把项目整理成面试能讲清楚的故事。

范围：
- 业务背景
- 系统架构
- 核心链路
- RAG、Agent、LangGraph、部署和生产事故复盘
- 简历 bullet
- 面试深化问答

推荐优先级：高。可以和 A 并行，但不要替代 A。

### 暂缓 D：继续重功能开发

包括：
- Qdrant / pgvector
- OCR / Word / Excel / 网页解析
- 更复杂 RBAC
- CI/CD
- 更完整运营后台

原因：
这些能力有价值，但当前继续堆功能的边际收益低于把公网演示、安全和项目讲解打稳。

## 8. 下一步建议

下一步建议先写并执行：

```text
Pre-Launch Stabilization V1：公网演示安全收口与材料整理
```

最小可交付：

1. 用虚构简历和 JD 走完一次完整演示链路。
2. 修复链路中剩余的小 bug。
3. 轮换 API Key 和管理员密码。
4. 更新 README、部署文档和项目状态。
5. 写一份“上线问题复盘 + 面试讲法”。

完成后，再进入：

```text
HTTPS / 域名
-> 项目讲解和简历包装
-> 继续开发下一轮增强功能
```
