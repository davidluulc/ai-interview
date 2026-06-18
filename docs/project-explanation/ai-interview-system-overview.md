# AI 模拟面试系统项目总讲解

## 一句话介绍

这是一个面向大学生和社会求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 面试编排链路，生成贴近岗位和个人经历的面试问题，并在结束后生成复盘报告和训练任务。

## 业务背景

应届生缺少真实面试经验，社会求职者也常常不清楚目标岗位考察重点。普通 AI 聊天容易泛泛而谈，难以结合用户简历、岗位 JD 和历史回答持续追问，也很难解释“为什么问这个问题”。

这个项目的目标是把模拟面试从普通聊天升级成一个可观察、可复盘、可训练的 AI 应用：

- 面试问题要贴合岗位。
- 追问要结合候选人的真实回答。
- 系统要能解释 RAG 召回和 Agent 决策。
- 面试后要生成训练任务，形成闭环。

## 核心用户流程

```text
注册 / 登录
-> 创建投递档案
-> 输入简历、岗位 JD、公司信息
-> 开始模拟面试
-> 三类 RAG 召回上下文
-> Agent / LangGraph 构造状态并决策下一步
-> LLM 生成下一道题
-> 记录 RAG 命中日志和 Agent 决策日志
-> 面试结束生成报告
-> 根据 weakTags 生成训练任务
-> 管理员后台观察系统链路
```

## 系统架构

项目采用 Vue3 前端 + FastAPI 后端 + SQLAlchemy ORM + RAG + Agent/LangGraph 的结构。

前端负责用户登录、投递档案、面试页面、历史报告、训练中心、知识库管理和管理员后台。后端负责认证、档案、面试编排、RAG 检索、文档摄取、训练任务、管理员可观测性和部署配置。

生产化路径上，本地默认 SQLite，生产兼容 PostgreSQL；Redis 用于缓存、限流、token blacklist 和 Celery broker；Celery worker 用于处理 RAG 文档摄取等慢任务；Nginx 负责静态资源和 API 反向代理。

## 三类 RAG 协作

项目没有把所有资料混在一个知识库里，而是拆成三类 RAG：

- 岗位知识库 RAG：提供岗位 JD、技术栈、业务场景和岗位要求。
- 题库 RAG：提供面试题、考察点、追问模板和标准表达。
- 候选人画像 RAG：提供简历摘要、历史回答、weakTags 和训练记录。

拆分的原因是三类数据来源、更新频率、权限边界和用途都不同。拆开后可以分别维护、评估召回质量、记录命中日志，也方便后续扩展。

## Agent / LangGraph 编排

Agent 不只是调用大模型，而是先观察当前状态：

- 用户档案。
- 历史问答。
- 上一轮回答质量。
- 三类 RAG 命中结果。
- 当前面试轮次和剩余轮次。
- 训练 weakTags 和策略。

然后 Agent 决定下一步动作，例如继续追问、降低难度、切换话题或结束面试。LangGraph mainline 用节点化工作流承接 observe、retrieve、policy、generate 等步骤，classic Agent 保留为 fallback/debug 路径。

## 可观测性设计

系统记录：

- RAG 命中日志。
- RAG 质量摘要。
- Agent 决策日志。
- workflow trace。
- runtime audit。
- RAG ingestion task 状态。

这样管理员可以定位问题发生在哪一层：知识库没有资料、召回质量差、metadata filter 过滤过度、Agent 决策不合理，还是 LLM 没遵守决策。

## 训练闭环

面试结束后，系统从报告里提取 weakTags，生成训练任务。用户可以进入训练中心查看专项练习题、回答要点、常见错误和一分钟表达模板，提交练习后更新掌握度和练习次数。

这让项目不只是“模拟一次面试”，而是形成：

```text
面试暴露问题 -> 报告复盘 -> 训练任务 -> 专项练习 -> 下一次面试验证提升
```

## 生产化设计

项目已经补齐了一批上线前常见工程能力：

- access token blacklist。
- 基础限流。
- provider 错误脱敏。
- RAG upload 幂等。
- retry 并发保护。
- Redis/Celery 基础设施状态。
- Celery worker readiness。
- PostgreSQL 兼容配置。
- Docker Compose 服务图。
- Nginx 反向代理配置。
- 上线 runbook 和 checklist。

## 技术取舍

项目没有一开始就把所有生产组件强行接入。核心取舍是：

- 本地默认 SQLite，保持开发效率。
- 生产兼容 PostgreSQL，保证后续上线路径。
- 本地 Celery eager，测试不依赖真实 Redis。
- 生产 worker 模式，慢任务从 HTTP 链路拆出。
- LangGraph 作为主链路工作流，但保留 classic fallback。
- 可观测性优先，避免 AI 黑箱。

这种路线比单纯堆技术栈更适合面试讲解，因为每个组件都有明确业务动机和工程取舍。
