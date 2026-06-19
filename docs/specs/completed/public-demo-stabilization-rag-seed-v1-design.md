# Public Demo Stabilization + Production RAG Seed V1 Design

更新时间：2026-06-19

## 1. 背景

项目已经完成第一版公网部署，当前公网形态为：

- Vue3 前端：`http://124.221.230.218:8080/vue/auth/login`
- FastAPI API：`http://124.221.230.218:8080/api/*`
- 部署架构：Nginx + FastAPI + PostgreSQL + Redis + Celery worker
- 默认 Agent runtime：`langgraph_mainline`
- embedding provider：已切到智谱 `embedding-3`

公网完整面试测试暴露出一组演示稳定性问题：

1. 生产 PostgreSQL 中 `rag_chunks` 为空，导致真实生产知识库没有可检索 chunk。
2. 点击“结束并复盘”后只跳转历史复盘页，没有生成报告、保存面试记录、生成训练任务。
3. 面试页允许在未真正生成第一题时提交“开始吧”，把占位提示当成真实面试问题。
4. 模型响应时间较长时，聊天框缺少“面试官思考中”的等待态，用户会误以为页面卡死。
5. 用户端知识库页面暴露 `metadata JSON` 和 RAG 调试面板，普通用户难以理解。
6. 投递档案缺少归档能力，用户无法整理无效档案。

本阶段目标不是继续堆新技术栈，而是把公网演示链路从“能打开”推进到“能稳定给 HR/面试官演示”。

## 2. 目标

本阶段交付一个稳定的公网演示闭环：

```text
生产知识库 seed
-> 用户创建/选择投递档案
-> 系统生成真正第一题
-> 用户完成多轮面试
-> 点击结束并复盘
-> 后端生成报告
-> 保存历史面试记录
-> 生成训练任务
-> 跳转报告页
-> 管理员后台可观测 RAG、Agent、LangGraph 和训练闭环
```

核心目标：

- 生产环境有可检索的岗位知识库和题库 chunk。
- 面试结束后一定沉淀 `InterviewRecord`。
- 候选人画像 RAG 能从历史面试记录中逐步形成，而不是一直空。
- 用户不会在未选档案/未生成第一题时误提交回答。
- 慢模型请求期间有清晰 loading 反馈。
- 用户端知识库页面更像产品功能，不像开发调试台。
- 档案可以被归档，历史记录保留可追溯性。

## 3. 非目标

本阶段不做：

- 不接 FreeLLMAPI。
- 不做 LLM 多模型自动轮换。
- 不引入 Qdrant / pgvector。
- 不做域名、HTTPS、Cloudflare。
- 不做 OCR、Word、Excel、网页解析。
- 不重构 LangGraph 主链路。
- 不删除历史面试记录、RAG 日志或审计日志。

LLM fallback、FreeLLMAPI、HTTPS 等内容可以作为后续阶段继续做，但不能阻塞本阶段的演示闭环修复。

## 4. 当前证据

### 4.1 生产库 RAG chunk 为空

生产 PostgreSQL 查询结果：

```sql
select knowledge_base, embedding_model, embedding_status, count(*) as chunk_count
from rag_chunks
group by knowledge_base, embedding_model, embedding_status;
```

结果：

```text
(0 rows)
```

结论：

- 当前公网生产库没有真实 RAG chunk。
- 这不是 DashScope 旧向量隔离问题。
- 这不是智谱 embedding 不可用问题。
- 需要做生产 RAG seed 或数据导入。

### 4.2 面试结束没有保存历史

当前 `frontend/src/pages/app/InterviewPage.vue` 中：

```ts
function finishInterview(): void {
  void router.push("/vue/app/history");
}
```

结论：

- 结束按钮只做页面跳转。
- 没有调用 `/api/interview/report`。
- 没有调用 `/api/history` 保存面试记录。
- 没有调用 `/api/training/tasks/generate-from-report`。
- 候选人画像缺少历史来源，后续一直 miss 是合理结果。

### 4.3 面试启动入口不严谨

当前 `frontend/src/stores/interview.ts` 默认消息为：

```ts
const openingQuestion = "请选择投递档案，然后开始一次模拟面试。";
```

当前 `submitAnswer()` 会从消息列表中找最后一条 interviewer 消息作为 `lastQuestion`。如果用户直接输入“开始吧”，这个占位提示会进入 history，导致后端把它当成真实面试问题处理。

结论：

- 需要区分 `idle / starting / ready / answering / reporting / completed` 等面试状态。
- 需要“开始面试”动作单独生成第一题。
- 未生成第一题前不能提交回答。

### 4.4 504 是慢请求，不是服务崩溃

Nginx 日志：

```text
upstream timed out while reading response header from upstream
POST /api/interview/next-question -> 504
```

FastAPI 日志显示后端最终返回：

```text
POST /api/interview/next-question -> 200 151694.24ms
```

结论：

- Nginx 等待超时，但后端仍在执行。
- 需要前端 loading 和友好超时提示。
- 需要优先使用更快的模型配置，后续再做 LLM fallback。

## 5. 功能设计

### 5.1 Production RAG Seed

新增生产知识库 seed 能力，把项目内核心知识点写入生产 PostgreSQL。

要求：

- 支持岗位知识库 `role_knowledge`。
- 支持题库 `question_bank`。
- 暂不手动 seed 候选人画像 `candidate_memory`，候选人画像优先从面试历史自然沉淀。
- 使用当前环境变量中的 embedding provider 生成向量。
- 当前生产环境使用：

```env
EMBEDDING_PROVIDER=zhipu
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

seed 内容建议覆盖：

- Python 后端基础：语法、函数、异常、类型、面向对象。
- FastAPI：路由、依赖注入、Pydantic、鉴权、中间件、异常处理。
- 数据库：SQL、索引、事务、SQLAlchemy、ForeignKey、relationship、Alembic。
- Redis / Celery：缓存、限流、异步任务、任务状态、失败重试。
- RAG：chunk、metadata、BM25、向量检索、hybrid、rerank、质量评估。
- Agent：Agent State、Tool Calls、Decision、policy、guardrail、fallback、nodeTrace。
- LangGraph：状态图、节点、checkpoint、interrupt、runtime audit。
- 部署：Docker Compose、Nginx、PostgreSQL、Redis、Celery、VPS 排错。
- 项目深挖题：业务背景、架构设计、技术取舍、可观测性、线上故障复盘。

幂等规则：

- 文档使用稳定标题或 stable seed key。
- 重复执行不会插入重复文档。
- 已存在同名 seed 文档时可跳过，或按固定策略更新。
- seed 完成后输出文档数量、chunk 数量、embedding ready 数量。

验收：

```sql
select knowledge_base, embedding_model, embedding_status, count(*)
from rag_chunks
group by knowledge_base, embedding_model, embedding_status;
```

应看到 `role_knowledge` 和 `question_bank` 下存在 `embedding-3 / ready` chunk。

### 5.2 面试结束闭环

用户点击“结束并复盘”时，前端不再直接跳转历史页，而是执行完整链路：

```text
interview.answeredHistory
-> POST /api/interview/report
-> POST /api/history
-> POST /api/training/tasks/generate-from-report
-> router.push(/vue/app/reports/:recordId)
```

要求：

- 至少完成 1 轮问答后才能结束。
- 结束过程中显示“正在生成复盘报告”。
- 保存成功后跳转报告详情页。
- 保存失败时显示可读错误，不丢失当前回答。
- 保存历史时带上 `applicationProfileId`。
- 报告中保留 `questionReviews`、`trainingPlan`、`ragReasons`、`decisionSummary` 等可解释字段。

后端已有：

- `/api/interview/report`
- `/api/history`
- `/api/training/tasks/generate-from-report`

本阶段优先把前端链路接完整，除非后端接口缺字段才补后端。

验收：

- 完成一次面试后，历史页出现新记录。
- 报告页可以打开。
- 训练中心出现由报告生成的任务。
- 后台候选人画像在下一次面试中有机会命中历史记录。

### 5.3 面试启动入口

当前占位提示不能进入真实面试 history。

设计：

- 新增面试 session 状态：

```text
idle: 还没开始
starting: 正在生成第一题
ready: 已有第一题，可以回答
answering: 正在提交回答并生成追问
reporting: 正在生成报告
completed: 已结束
```

- `idle` 状态显示“开始面试”按钮。
- 没有 `applicationProfileId` 时禁用开始按钮，并提示去创建/选择档案。
- 点击开始时，前端调用 `/api/interview/next-question`，但 history 传空数组。
- 后端根据 profile、JD、知识库生成第一题。
- 第一题返回后才允许输入回答。
- `openingQuestion` 只作为 UI 空状态文案，不再作为 history question。

验收：

- 未选择档案时不能提交“开始吧”。
- 第一条真实面试官消息来自后端生成。
- `answeredHistory[0].question` 不会等于“请选择投递档案，然后开始一次模拟面试。”

### 5.4 面试官思考中 Loading

新增聊天等待态，降低模型慢请求造成的焦虑。

要求：

- 提交回答后，候选人消息立即显示。
- 面试官区域显示 loading 气泡。
- loading 文案按阶段展示：

```text
AI 面试官正在分析你的回答...
正在检索岗位知识库、题库和候选人画像...
正在生成下一道追问...
```

- loading 时禁用提交按钮，避免重复提交。
- 发生 504、timeout、HTML 错误页时，不把原始 HTML 塞进聊天框。
- 用户看到友好错误：

```text
模型响应超时，请稍后重试。本轮回答已保留。
```

验收：

- 慢请求期间有可见 loading。
- 重复点击提交不会产生多条重复请求。
- 504 不以 HTML 形式展示给用户。

### 5.5 知识库用户页简化

当前知识库页面暴露 `metadata JSON`，普通用户难以理解。本阶段将其产品化。

设计：

- 默认表单只显示：
  - 标题
  - 知识库类型
  - 可见性
  - 内容或文件
- `metadata JSON` 移入“高级设置”折叠区。
- 上传文件表单也同样隐藏 metadata JSON。
- 默认 metadata 为 `{}`。
- 可以提供结构化可选字段替代 JSON：
  - 岗位方向 `positionTag`
  - 难度 `difficulty`
  - 面试阶段 `interviewStage`
  - 来源 `source`

RAG 调试与解释板块定位：

- 它是开发者/管理员排查工具，不是普通用户日常功能。
- 作用是输入 query 后查看：
  - 岗位知识库命中什么
  - 题库命中什么
  - 候选人画像命中什么
  - 质量为什么是 good / weak / miss
  - 哪些内容会进入 prompt
- 本阶段用户端默认折叠为“高级调试”。
- 管理员后台继续保留完整 RAG 质量诊断能力。

验收：

- 普通用户首次进入知识库页不会直接看到 metadata JSON。
- 仍能创建手动文档和上传文件。
- 高级调试展开后仍可使用原 RAG debug 能力。

### 5.6 投递档案归档

本阶段可以补档案整理能力，但不做物理删除。

设计：

- 增加档案状态：

```text
active
archived
```

- 用户默认档案列表只显示 active。
- 档案卡片提供“归档”按钮。
- 可选提供“查看已归档”和“恢复”。
- 已有关联历史记录不删除。
- 管理员后台和历史报告仍可追溯档案摘要。

为什么不硬删除：

- 面试记录需要保留档案上下文。
- RAG 日志、Agent 日志、训练任务需要可审计。
- 真实业务里简历投递档案通常是归档，而不是直接从数据库抹掉。

验收：

- 归档后默认档案列表不显示该档案。
- 历史报告仍能显示该档案摘要。
- 恢复后档案重新出现在列表。

### 5.7 RAG 空召回引导

管理员后台当前会显示空召回，但普通用户不容易理解原因。

本阶段补充更清晰的提示：

- 如果 `rag_chunks` 为空，提示“当前生产知识库尚未初始化，请执行 Production RAG Seed”。
- 如果某知识库没有 ready chunk，提示“该知识库暂无可检索内容”。
- 如果 embedding model 不匹配，提示“当前 embedding 模型与历史 chunk 不一致，需要重新向量化或重新入库”。
- 候选人画像 miss 时说明“候选人画像来自历史面试记录，完成并保存多次面试后会逐步形成”。

验收：

- RAG 质量诊断不只显示“空召回”，还给出可执行原因。
- 用户能区分“知识库没资料”和“候选人画像暂无历史”。

## 6. 数据流

### 6.1 面试主链路

```text
用户选择档案
-> 点击开始面试
-> next-question(history=[])
-> 后端检索 role_knowledge/question_bank/candidate_memory
-> Agent State
-> Agent Decision
-> LLM 生成第一题
-> 前端展示第一题
-> 用户回答
-> next-question(history=[...])
-> 多轮循环
```

### 6.2 复盘保存链路

```text
用户点击结束并复盘
-> report(profile, answers)
-> history.create(profile, answers, report, applicationProfileId)
-> training.generateFromReport(report, sourceInterviewRecordId)
-> router.push(/vue/app/reports/:recordId)
```

### 6.3 候选人画像链路

```text
InterviewRecord
-> report weakTags / risks / actions
-> retrieve_candidate_memory
-> build_candidate_profile
-> Agent State.candidateProfile
-> weakness_strategy / Agent Decision
```

## 7. 测试策略

优先测试驱动开发。

后端测试：

- seed 脚本幂等。
- seed 后生成 `rag_documents` 和 `rag_chunks`。
- seed 使用当前 embedding model 写入 `embedding_model`。
- 档案归档不删除历史记录。
- history 保存带 `applicationProfileId`。

前端测试：

- 未选档案不能开始面试。
- 点击开始面试会用空 history 请求第一题。
- 占位提示不会进入 `answeredHistory`。
- 点击结束并复盘会依次调用 report、history、training。
- 保存成功后跳转报告页。
- 保存失败保留回答并显示错误。
- loading 气泡在请求期间可见。
- 504/HTML 错误转成友好错误。
- 知识库 metadata 默认隐藏。
- 高级调试默认折叠。
- 档案归档后默认列表隐藏。

验证命令：

```bash
python -m pytest -q
cd frontend && npm.cmd run test
cd frontend && npm.cmd run build
docker compose --env-file .env.production.example config --quiet
```

公网验证：

```text
1. 服务器拉取最新代码并 rebuild。
2. 执行 Production RAG Seed。
3. SQL 验证 rag_chunks 存在 embedding-3 ready chunk。
4. 普通用户创建/选择档案。
5. 开始面试，确认第一题不是占位提示。
6. 完成 2-3 轮回答。
7. 点击结束并复盘。
8. 确认跳转报告页。
9. 历史页出现记录。
10. 训练中心出现任务。
11. 管理员后台可查看 RAG、Agent、AI Debug。
```

## 8. 风险与取舍

### 8.1 生产 seed 会调用 embedding 额度

seed 会消耗智谱 embedding token。  
控制方式：

- seed 内容先保持演示规模，不一次性写入所有学习资料。
- chunk 数控制在合理范围。
- seed 幂等，避免重复消耗。

### 8.2 面试 report 仍可能被慢模型拖慢

本阶段先通过 loading 和友好错误处理提升体验。  
LLM 自动轮换放到后续 `LLM Model Fallback V1`。

### 8.3 档案归档涉及数据库字段

如果 `ApplicationProfile` 当前没有 status 字段，需要补模型、迁移、SQLite auto-init 和测试。  
必须避免硬删除破坏历史记录。

### 8.4 知识库页面不能过度简化

metadata 对 RAG 质量有价值，但普通用户不应默认看到 JSON。  
因此采用“默认隐藏，高级设置保留”的方案。

## 9. 验收标准

本阶段完成后必须满足：

- 生产库 `rag_chunks` 不再为空。
- `role_knowledge` 和 `question_bank` 至少各有一批 `embedding-3 / ready` chunk。
- 未选择档案时无法开始真实面试。
- 开始面试后第一题由后端根据档案/JD/RAG 生成。
- 占位提示不会进入历史问答。
- 提交回答时有面试官思考 loading。
- 点击“结束并复盘”后生成报告、保存历史、生成训练任务并跳转报告页。
- 历史页能看到刚完成的面试记录。
- 候选人画像能在后续面试中基于历史记录逐步命中。
- 知识库页面默认不暴露 metadata JSON。
- RAG 调试与解释默认折叠或弱化。
- 档案支持归档，历史记录不丢失。
- 后端、前端、build、compose 配置验证通过。

## 10. 面试讲法

本阶段可以包装成：

> 上线后我做了一轮公网演示稳定化。主要解决了生产库没有 RAG chunk、面试结束没有沉淀历史、候选人画像无法形成、慢模型请求缺少等待反馈、知识库页面过于开发者化等问题。我补了生产 RAG seed、完整复盘保存链路、面试启动状态控制、loading 和用户端知识库简化，并采用档案归档而不是硬删除，保证历史记录和审计链路可追溯。

可强调的工程能力：

- 公网问题排查。
- 生产数据初始化。
- 前后端闭环设计。
- RAG 可观测性。
- 用户体验和工程稳定性的取舍。
- 数据审计和软删除意识。

