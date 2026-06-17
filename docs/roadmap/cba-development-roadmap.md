# CBA 后续开发总路线

更新时间：2026-06-17

## 1. 路线定位

本路线用于承接当前项目已经完成的 RAG、Agent、LangGraph、Vue3、后台和本地部署工程化能力。它不是新的单阶段开发计划，而是未来三轮 active spec / active plan 的上层路线。

当前项目已经具备：

- Vue3 用户端：档案、面试、历史、报告、训练、知识库、后台页面。
- 三类 RAG：岗位知识库、题库、候选人画像，并已具备 BM25、embedding、hybrid、rerank、query rewrite、metadata、日志和评估。
- Agent：classic Interview Orchestrator、Agent State、Tool Calls、Decision、fallback、guardrail、coach/interview 模式、nodeTrace 和决策日志。
- LangGraph：旁路 POC、真实 RAG adapter、checkpoint summary、runtime governance、mainline canary 和管理员灰度开关。
- 后端生产化基础：PostgreSQL / Redis / Celery / Docker / Nginx 的本地演练和文档闭环。

因此，下一步不应重复已经完成的旧 spec，而应按照下面顺序继续深化。

## 2. 推荐顺序

```text
C：面试体验与训练闭环 V3
-> B：LangGraph / Agent 工作流深化
-> A：生产级 RAG V3
```

推荐理由：

1. C 阶段先补用户价值闭环。用户完成面试后，不应只看到报告和任务列表，还要能进入真实专项练习、提交回答、获得反馈、更新掌握度，并回到下一场面试验证提升。
2. B 阶段再深化 LangGraph。只有产品链路稳定后，checkpoint、human-in-the-loop、runtime 审计才有明确落点，否则容易做成“框架展示”。
3. A 阶段最后深化生产级 RAG。OCR、Word/Excel/web 解析、异步入库、持久化向量库、监控告警属于更重的基础设施工程，适合在用户闭环和 Agent 工作流稳定后推进。

## 3. 阶段 C：面试体验与训练闭环 V3

目标：

```text
档案 -> 面试 -> 报告 -> weakTags -> 训练任务 -> 专项练习 -> 掌握度更新 -> 再面试
```

本阶段重点：

- 把训练任务从“列表和状态按钮”升级为“可作答的专项练习会话”。
- 让训练模板里的 coachQuestions、interviewQuestions、answerKeyPoints、commonMistakes、oneMinuteTemplate 真正展示给用户。
- 用户提交练习回答后，系统根据 answerStatus 更新 masteryScore、attemptCount、lastPracticedAt 和任务状态。
- 训练中心展示“为什么练这个、练什么、怎么答、答完怎么更新掌握度”。
- 训练结果继续被候选人画像 / Agent 训练任务读取链路使用。

本阶段不做：

- 不重写 RAG 检索链路。
- 不重写 Agent 决策链路。
- 不引入新的 LangGraph 主链路。
- 不做生产级 RAG 异步入库。
- 不做 VPS / HTTPS 真实上线。

当前 active 文档：

```text
docs/specs/active/interview-training-loop-v3-design.md
docs/plans/active/interview-training-loop-v3.md
```

## 4. 阶段 B：LangGraph / Agent 工作流深化

阶段 C 完成后进入 B 阶段。

候选目标：

- checkpoint 持久化：从内存 summary 过渡到数据库可恢复的 graph state。
- human-in-the-loop：当 policy 判断 requiresHumanReview 时，支持暂停、审查、恢复。
- runtime 对比报告：管理员能查看 classic 与 LangGraph 的 action、difficulty、reason、quality gate 差异。
- LangGraph 节点边界稳定化：observe、retrieve、analyze、policy、decide、generate、update memory 的输入输出 schema 更明确。
- 可回放调试：通过 threadId / traceId 复现一轮 Agent 决策路径。

边界：

- 不为了写简历而强行替换稳定主链路。
- LangGraph 可以逐步从旁路、灰度、可观测链路走向主链路，但每一步都要有 fallback classic。
- 不把 LangGraph 和 RAG 生产化混在同一轮完成。

## 5. 阶段 A：生产级 RAG V3

阶段 B 完成后进入 A 阶段。

候选目标：

- 文档解析增强：Word、Excel、网页、图片 OCR。
- 异步摄取：Redis / Celery 承接大文件解析、chunk、embedding、入库任务。
- 持久化向量库：Qdrant 或 pgvector 二选一，先完成抽象适配，再替换 SQLiteVectorStore。
- 文档版本管理：同名文档更新、旧版本归档、chunk 去重和重建索引。
- 质量监控：低命中率、空召回率、rerank 失败率、metadata filter 误杀率的后台面板。
- 失败重试：解析失败、embedding 失败、入库失败的状态记录和重试入口。

边界：

- 不在本地 SQLite 默认开发阶段强行要求安装 PostgreSQL。
- 不一次性把所有解析器、队列、向量库都切到生产实现。
- 先保证抽象层和任务状态可观测，再逐步替换具体基础设施。

## 6. 追求目标模式规则

追求目标模式每次只执行一个 active spec + active plan。

不要把本文件直接作为执行 plan。本文件只负责告诉后续开发顺序。

正确执行方式：

```text
1. 打开 docs/roadmap/current-state.md 校准当前 active 阶段。
2. 执行 docs/specs/active/ 下唯一 active spec。
3. 执行 docs/plans/active/ 下唯一 active plan。
4. 完成后运行测试和浏览器验证。
5. 把 spec / plan 移动到 completed。
6. 更新 current-state.md、docs/specs/README.md、docs/plans/README.md。
7. 再讨论下一阶段是否进入 B 或 A。
```

