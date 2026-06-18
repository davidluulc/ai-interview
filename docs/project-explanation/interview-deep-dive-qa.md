# 项目面试深挖问答库

## 为什么拆三个 RAG？

因为岗位知识、题库、候选人画像的数据来源、更新频率、权限边界和用途不同。岗位知识库负责岗位要求和技术栈，题库负责真实面试题和追问模板，候选人画像负责简历、历史回答和 weakTags。拆开后可以分别维护、评估召回质量和记录命中日志，也方便后续扩展。

## Agent 和普通 LLM 调用有什么区别？

普通 LLM 调用主要是输入 prompt 后生成回答。项目里的 Agent 会先观察状态，包括用户档案、历史问答、RAG 命中结果、回答质量和剩余轮次，再决策下一步动作，例如追问、降难度、切换话题或结束面试。LLM 最终负责把决策和上下文转成自然语言问题。

## 为什么需要 LangGraph？

当面试流程变成多节点工作流后，单个函数会越来越难维护。LangGraph 可以把 observe、retrieve、apply policy、generate、update memory 等步骤节点化，让状态流转、checkpoint、runtime audit 和 fallback 更清楚。项目里保留 classic fallback，是为了在 LangGraph 链路不稳定时仍能保证主流程可用。

## 为什么需要 Celery？

RAG 文档摄取涉及文件解析、清洗、切 chunk、embedding 和入库，属于慢任务。Celery 把慢任务从 HTTP 请求链路拆出去，接口快速返回 taskId，worker 后台处理，前端和管理员后台查看进度和失败原因。

## 为什么本地 SQLite，生产 PostgreSQL？

SQLite 启动快、适合本地开发和测试。PostgreSQL 更适合多人系统、并发读写、事务和后续扩展。项目保留 SQLite 默认路径，同时提供 PostgreSQL 生产兼容配置，避免为了生产化过早牺牲开发效率。

## Redis 在项目中承担什么职责？

Redis 可以承担缓存、基础限流、token blacklist 和 Celery broker 等职责。本地测试时可以使用 memory/fallback 路径，生产环境再切换到 Redis，保证测试稳定和部署可扩展。

## 如何排查 RAG 召回质量差？

先看 RAG 命中日志：是否空召回、弱召回、metadata filter 过滤过度或未进入 prompt。再看 evaluation case 指标，例如 Hit@K、MRR、关键词覆盖率。最后看 Agent decision 和 LLM 输出是否正确使用了召回内容。

## 如何避免 AI 黑箱？

通过 RAG 命中日志、Agent 决策日志、workflow trace、runtime audit 和管理员后台，把检索、决策、兜底和生成依据记录下来，方便复盘和调试。

## 如果模型输出不稳定怎么办？

项目有 normalize、guardrail、fallback decision 和 runtime quality gate。模型输出字段缺失、动作不合法、问题重复或风险过高时，系统会回退到规则兜底或 classic fallback，保证面试流程不中断。

## 如果用户连续答不上来怎么办？

Agent policy 会识别连续弱回答，先降低难度，必要时切换话题或进入 coach 风格解释，避免真实面试体验变成机械地卡在一个点上。

## 管理员后台有什么价值？

管理员后台不是单纯列表页，而是 AI 应用可观测性入口。它能查看 RAG 质量、RAG ingestion 任务、Agent workflow、runtime audit、基础设施状态和安全配置摘要，帮助定位系统问题。

## 这个项目有没有过度工程化？

项目没有为了堆技术栈而加入组件。RAG 是为了解决问题泛泛而谈，Agent/LangGraph 是为了解决多轮面试状态和决策，Celery 是为了解决文档摄取慢任务，Redis 是为了解决缓存/限流/队列，PostgreSQL 是为了解决生产数据存储。每个组件都有对应痛点。
