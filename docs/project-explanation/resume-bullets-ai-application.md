# AI 应用开发岗简历项目表达

## 项目名称

AI 模拟面试系统

## 项目描述

面向大学生和求职者的 AI 模拟面试系统。系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 面试工作流，根据用户简历、岗位 JD、历史回答和训练弱点动态生成面试问题，并通过 RAG 命中日志、Agent 决策日志和 workflow trace 提升 AI 应用可观测性。

## 技术栈

FastAPI、Vue3、RAG、hybrid search、rerank、query rewrite、LangGraph、Agent workflow、Redis、Celery、PostgreSQL 兼容配置、Docker Compose。

## 可选职责表达

- 设计三类 RAG 协作链路，将岗位知识、题库内容和候选人画像拆分维护，并通过 hybrid search、rerank、query rewrite 和 evaluation case 提升召回质量。
- 设计 Agent/LangGraph 面试编排链路，根据 agent state、RAG 命中结果、回答质量和训练弱点动态决策追问、降难度、切换话题或结束面试。
- 建设 AI 可观测性能力，记录 RAG 命中日志、Agent 决策日志、runtime audit 和 workflow trace，支持管理员后台定位召回、决策和生成问题。
- 构建面试复盘和训练闭环，根据报告 weakTags 生成专项训练任务，帮助用户从模拟面试进入针对性练习。
- 为 RAG 文档摄取设计异步任务链路，使用 Celery worker 处理慢任务，并通过任务状态和失败原因提升工程可维护性。

## 面试时可以强调的亮点

- 不是普通聊天框，而是“RAG + Agent/LangGraph + 训练闭环”的 AI 应用。
- Agent 决策和 LLM 生成分层，降低模型随机性对业务流程的影响。
- RAG 命中和 Agent 决策都有日志，便于解释为什么这么问。
- 支持 coach/interview 思路和弱回答策略，面试体验更接近真实场景。

## 注意边界

可以写 LangGraph，因为项目已经有 LangGraph mainline / workflow trace / runtime audit；但不要夸大为复杂多 Agent 平台。更准确的表达是“使用 LangGraph 承接面试工作流编排”。
