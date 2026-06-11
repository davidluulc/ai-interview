# AI 模拟面试系统产品化 V2 Spec：训练中心 + 管理后台 MVP + LangGraph 预留

## 1. 文档目的

本文档用于规划 AI 模拟面试系统的下一阶段产品化升级。

上一阶段项目已经具备：

- 用户系统。
- 求职档案。
- 三类 RAG。
- RAG 文档管理。
- BM25、向量检索、Hybrid Search、Rerank。
- RAG 命中日志和质量解释。
- Interview Orchestrator Agent。
- coach / interview 双模式。
- weakTag 训练模板。
- 历史面试复盘。
- 一键重练薄弱点入口。

当前项目已经不再是最初的 MVP，但还没有完全变成一个清晰的“用户端 + 管理端 + 训练闭环平台”。

本阶段要解决三个问题：

```text
第一，用户端需要从单一面试工作台升级为训练中心。
第二，后台需要有最小管理员能力，用来管理知识库、题库、用户和日志。
第三，Agent 已经接近 LangGraph 的状态图形态，但本阶段先做迁移预留，不直接引入框架。
```

本文档既是设计 spec，也是后续“追求目标”模式的总控依据。它会覆盖足够多的阶段，但实现时必须按阶段推进，不能一次性把所有内容糊成一个大改动。

## 2. 当前项目状态

### 2.1 已完成能力

产品能力：

- 用户注册、登录、刷新 token、退出登录。
- 求职档案：简历、目标岗位、JD、公司要求。
- 面试工作台。
- 历史面试记录。
- 逐题复盘和训练建议。
- 一键重练薄弱点。
- RAG 调试面板。
- Agent 决策日志展示。

RAG 能力：

- 岗位知识库 RAG。
- 题库 RAG。
- 候选人画像 RAG。
- 文档管理和 chunk 存储。
- metadata。
- BM25 检索。
- embedding 向量检索。
- Hybrid Search。
- Rerank。
- RAG 命中日志。
- RAG 质量评估样例和指标解释。

Agent 能力：

- Agent State。
- ToolCalls。
- Agent Decision。
- fallback。
- normalize。
- guardrail。
- nodeTrace。
- coach / interview 模式。
- 连续弱回答识别。
- 重复问题保护。
- topic shift。
- weaknessStrategy。
- trainingTemplateHint。

工程化能力：

- FastAPI 后端。
- SQLAlchemy 数据模型。
- SQLite 本地开发数据库。
- Alembic 迁移设计。
- pytest 后端测试。
- `.mjs` 前端测试。
- 中文学习文档。
- spec / plan 驱动开发流程。

### 2.2 当前主要短板

用户端短板：

- 页面还没有清晰拆成“面试、训练、档案、历史”几个稳定入口。
- 一键重练薄弱点还偏入口级功能，没有形成训练任务列表。
- 用户看不到自己当前有哪些长期训练任务。
- 用户看不到每个薄弱点的掌握度变化。

后台短板：

- 还没有管理员身份。
- 还没有后台入口。
- 还没有统一查看用户、知识库、题库、RAG 日志、Agent 日志的管理页面。
- 当前知识库管理更偏用户端调试，不像平台后台。

Agent / LangGraph 短板：

- Agent 节点已经显式化，但仍是自研 orchestrator。
- 还没有 checkpoint。
- 还没有 human-in-the-loop。
- 还没有真正状态图。
- Agent State 字段仍在快速演进，暂不适合直接重构到 LangGraph。

部署短板：

- 本阶段不做真实 Docker / Nginx / 云服务器上线。
- Redis、生产数据库、监控告警仍是后续阶段。

## 3. 本阶段总目标

本阶段目标是：

```text
把 AI 模拟面试系统从“能模拟面试”升级为“能持续训练、能后台管理、能解释 Agent 决策，并为后续 LangGraph 迁移打基础”的产品化版本。
```

具体目标：

- 用户端形成更清晰的信息架构。
- 新增训练任务系统，让 weakTags 从“报告字段”升级为“可跟踪训练目标”。
- 新增掌握度评分，让用户知道自己不是只被标记薄弱，而是在逐步改善。
- 新增管理员后台 MVP，用于管理用户、RAG 文档、题库和日志。
- 后端继续模块化，把训练任务和后台管理逻辑从面试接口中拆出去。
- 保持现有 `/api/interview/next-question` 兼容。
- 不直接引入 LangGraph，但让 Agent 节点、状态、日志继续向 LangGraph 可迁移结构靠拢。
- 每个阶段完成后补充中文学习文档，方便用户第二天复盘。

## 4. 非目标

本阶段明确不做：

- 不做真实云服务器上线。
- 不做 Docker / Nginx 真实部署。
- 不接入真实支付系统。
- 不做邮箱验证码、短信验证码。
- 不做复杂 RBAC 权限系统。
- 不做多租户企业组织架构。
- 不做完整运营数据大屏。
- 不做 LangGraph 正式迁移。
- 不安装 LangChain。
- 不把前端重构成 React、Vue、Next.js。
- 不重写整个 UI。
- 不删除大范围旧代码。
- 不为了消耗额度而牺牲测试和可读性。

如果执行过程中需要涉及以上内容，只能写成后续设计或学习文档，不在本阶段落地。

## 5. 设计原则

### 5.1 先产品闭环，再框架升级

当前最重要的不是马上引入 LangGraph，而是把训练闭环产品化。

原因：

- 用户端训练中心能直接改善产品体验。
- 管理后台能让知识库、题库和日志更像真实系统。
- Agent 状态继续稳定后，再迁移 LangGraph 更容易。

### 5.2 后台先做 MVP，不做大而全

后台只做最小可用版本：

- 管理员身份。
- 后台入口。
- 用户只读列表。
- RAG 文档管理。
- 题库 / 岗位知识库管理。
- RAG 日志查看。
- Agent 决策日志查看。

不做复杂权限和运营看板。

### 5.3 训练任务先做稳定数据闭环

训练任务系统的第一目标是让数据链路跑通：

```text
报告 weakTags
-> 候选人画像 frequentWeakTags
-> 训练任务
-> 用户训练
-> 掌握度变化
-> 下一轮面试参考
```

第一版不追求复杂学习算法，先让用户看得到、点得动、能保存、能复盘。

### 5.4 保持现有接口兼容

现有前端已经依赖：

- `/api/interview/next-question`
- `/api/interview/report`
- `/api/history`
- `/api/rag/debug`
- RAG 文档相关接口
- Agent 日志相关接口

新功能应新增接口或扩展可选字段，不破坏现有字段。

### 5.5 每阶段必须可测试

每个阶段必须有明确测试：

- 后端 pytest。
- 前端 `.mjs` 测试。
- 必要时浏览器验证。

不能只凭“页面看起来能点”作为完成标准。

## 6. 产品信息架构

### 6.1 用户端页面结构

用户端建议拆成四个主入口：

```text
面试工作台
历史复盘
薄弱点训练
求职档案
```

#### 面试工作台

已有主页面继续保留，但需要逐步变得更专注：

- 当前面试问题。
- 用户回答输入。
- Agent 模式选择：学习辅导 / 真实面试。
- 当前 RAG 命中解释。
- 当前 Agent 决策摘要。
- 保存报告入口。

不再把所有功能都堆在这个页面里。

#### 历史复盘

用于查看过去面试记录：

- 面试日期。
- 岗位方向。
- 分数。
- 风险点。
- 逐题复盘。
- weakTags。
- 一键生成训练任务。

#### 薄弱点训练

本阶段新增重点页面。

用于展示：

- 当前待训练任务。
- 高频薄弱点。
- 掌握度评分。
- 训练任务状态。
- 最近训练记录。
- 进入专项训练按钮。

#### 求职档案

用于维护：

- 简历文本。
- 目标岗位。
- JD。
- 公司要求。
- 当前默认档案。

### 6.2 管理后台页面结构

后台建议使用同一前端项目里的管理视图，不单独引入新框架。

后台主入口：

```text
后台总览
用户管理
知识库管理
题库管理
RAG 日志
Agent 日志
系统配置
```

#### 后台总览

MVP 只展示基础统计：

- 用户总数。
- 面试记录数。
- RAG 文档数。
- 最近 RAG 命中日志数。
- 最近 Agent 决策日志数。

#### 用户管理

第一版只读：

- 用户 ID。
- 邮箱。
- 用户名。
- 角色。
- 创建时间。
- 最近登录或最近面试时间。

不做封禁、改密码、删除用户。

#### 知识库管理

用于管理岗位知识库和普通 RAG 文档：

- 文档列表。
- 文档详情。
- chunk 列表。
- knowledgeBase。
- metadata。
- embedding 状态。
- 删除或禁用文档。

#### 题库管理

题库管理可以复用 RAG 文档能力，但页面语义要更清楚：

- 题目。
- 参考答案。
- 难度。
- 标签。
- 适用岗位。
- 是否启用。

第一版可先通过 `knowledgeBase = question_bank` 管理题库文档，不急着新增复杂题库表。

#### RAG 日志

展示：

- query。
- retrieverName。
- knowledgeBase。
- retrievalMode。
- hitCount。
- quality。
- top hit。
- 时间。
- 用户。

#### Agent 日志

展示：

- 用户。
- nextAction。
- difficulty。
- focus。
- reason。
- fallbackUsed。
- guardrailApplied。
- nodeTrace。
- toolCalls。
- 时间。

#### 系统配置

MVP 可以先不做真实配置写入，只展示当前配置摘要：

- 默认 RAG 检索模式。
- 当前模型名。
- embedding 模型名。
- rerank 模型名。
- 环境变量是否配置。

## 7. 用户角色与权限

### 7.1 角色设计

第一版只需要两个角色：

```text
user
admin
```

`user`：

- 使用面试工作台。
- 查看自己的历史复盘。
- 查看自己的训练任务。
- 管理自己的求职档案。

`admin`：

- 具备 user 能力。
- 可以访问管理后台。
- 可以查看用户列表。
- 可以管理公共 RAG 文档和题库。
- 可以查看 RAG 日志和 Agent 日志。

### 7.2 权限边界

第一版不做复杂 RBAC。

后端只需要两个依赖：

```text
get_current_user
require_admin_user
```

普通用户访问后台接口应返回 403。

未登录用户访问后台接口应返回 401。

### 7.3 数据隔离

用户端接口仍然只允许用户访问自己的数据。

后台接口可以查看跨用户日志，但第一版只允许 admin。

面试表达：

```text
第一版后台权限采用最小角色模型，只区分 user 和 admin。普通用户只能访问自己的训练任务、求职档案和历史记录；管理员可以进入后台查看用户、知识库和日志。这样避免一开始就引入复杂 RBAC，同时满足后台 MVP 的权限隔离要求。
```

## 8. 训练任务系统设计

### 8.1 为什么需要训练任务

当前系统已经能生成 weakTags，但 weakTags 只是标签。

它不能直接回答：

```text
我今天应该练什么？
这个薄弱点练了几次？
有没有进步？
下一轮面试是否还需要继续问？
```

训练任务系统就是把 weakTags 变成可跟踪的产品对象。

### 8.2 训练任务来源

训练任务可以来自：

- 面试报告的 `questionReviews[*].weakTags`。
- 面试报告的 `trainingPlan.weakTopics`。
- 候选人画像的 `frequentWeakTags`。
- 用户点击“一键重练薄弱点”。
- 后续管理员或系统推荐。

### 8.3 训练任务核心字段

建议新增 `TrainingTask` 概念。

字段设计：

```text
id
user_id
application_profile_id
source_interview_record_id
weak_tag
weak_label
title
description
status
priority
mastery_score
attempt_count
last_practiced_at
next_review_at
created_at
updated_at
metadata_json
```

字段解释：

- `weak_tag`：标准薄弱点标签，例如 `rag_quality`。
- `weak_label`：中文名，例如 `RAG 质量评估`。
- `title`：训练任务标题。
- `description`：训练任务说明。
- `status`：`todo`、`in_progress`、`done`、`archived`。
- `priority`：`low`、`medium`、`high`。
- `mastery_score`：0 到 100 的掌握度。
- `attempt_count`：训练次数。
- `last_practiced_at`：最近训练时间。
- `next_review_at`：建议下次复习时间。
- `metadata_json`：保存模板摘要、来源报告、相关题目等扩展信息。

### 8.4 训练任务状态流转

状态流转：

```text
todo
-> in_progress
-> done
-> archived
```

规则：

- 新生成任务默认 `todo`。
- 用户开始专项训练后变为 `in_progress`。
- 用户完成一次训练并达到基础要求后可变为 `done`。
- 用户不想继续练时可以归档为 `archived`。

### 8.5 去重规则

同一个用户、同一个求职档案、同一个 weakTag，不应无限生成重复任务。

建议规则：

```text
如果存在相同 weakTag 且 status 不是 archived 的任务：
  更新 priority、description、metadata_json、next_review_at
  attempt_count 不变
否则：
  新建任务
```

这样可以避免历史复盘里每次点击“一键训练”都堆出重复任务。

### 8.6 训练任务与 trainingTemplateHint 的关系

训练任务不是替代训练模板。

关系是：

```text
weakTag
-> trainingTemplateHint
-> 生成 TrainingTask
-> 用户进入训练
-> Agent 使用 TrainingTask + trainingTemplateHint 生成训练问题
```

训练模板负责“怎么练”。

训练任务负责“用户是否正在练、练了几次、掌握度如何”。

## 9. 掌握度评分设计

### 9.1 为什么需要掌握度

如果系统只告诉用户“你在 RAG 质量评估上薄弱”，用户会焦虑，但不知道自己有没有进步。

掌握度评分解决的是：

```text
这个薄弱点目前练到什么程度？
```

### 9.2 第一版评分原则

第一版不做复杂机器学习评分。

采用可解释规则：

- 初始分根据报告风险程度决定。
- 用户答不上来则降低或保持低分。
- 用户能说出部分要点则小幅加分。
- 用户能结构化回答并覆盖关键点则明显加分。
- 多次训练后仍答不上来，任务保持高优先级。

### 9.3 建议评分规则

初始分：

```text
高风险 weakTag：30
中风险 weakTag：45
低风险 weakTag：60
```

训练后更新：

```text
answerStatus = 不会：mastery_score - 5
answerStatus = 模糊：mastery_score + 8
answerStatus = 完整：mastery_score + 15
```

边界：

```text
mastery_score 最低 0
mastery_score 最高 100
```

任务状态建议：

```text
mastery_score < 60：todo 或 in_progress
60 <= mastery_score < 80：in_progress
mastery_score >= 80：done
```

### 9.4 为什么先用规则评分

面试表达：

```text
第一版掌握度评分我先采用规则化方式，而不是直接让模型打分。原因是规则评分可解释、稳定、容易测试。后续如果需要更细的评价，可以把模型评分作为辅助信号，但不会完全替代可解释规则。
```

## 10. 训练中心用户体验

### 10.1 训练中心首页

训练中心首页展示：

- 今日建议训练。
- 高频薄弱点。
- 待完成任务。
- 已完成任务。
- 最近训练记录。
- 掌握度趋势摘要。

### 10.2 训练任务卡片

任务卡片展示：

- weakTag 中文名。
- 任务标题。
- 掌握度。
- 优先级。
- 状态。
- 最近训练时间。
- 按钮：开始训练、查看详情、归档。

### 10.3 训练详情页或详情面板

详情展示：

- 任务来源。
- 推荐训练问题。
- 答题要点。
- 常见错误。
- 历史训练次数。
- 最近一次回答。
- 进入 coach 模式训练。
- 进入 interview 模式检验。

### 10.4 从报告生成训练任务

历史复盘页面保留“一键重练薄弱点”，但行为升级：

```text
点击一键重练薄弱点
-> 后端根据 report weakTags 生成或更新 TrainingTask
-> 前端跳转到训练中心
-> 展示本次新增或更新的训练任务
```

### 10.5 训练任务如何影响下一轮面试

当用户开始新一轮面试时，后端可以读取：

- 当前求职档案的高优先级训练任务。
- 当前用户的 frequentWeakTags。
- 最近未完成任务。

然后写入 Agent State：

```text
candidateTrainingTasks
```

Agent 可以根据它决定：

- 是否优先训练某个 weakTag。
- coach 模式下是否先解释基础概念。
- interview 模式下是否安排真实追问。

## 11. 管理后台 MVP 设计

### 11.1 后台入口

前端根据当前用户角色决定是否显示后台入口。

```text
currentUser.role == "admin"
-> 显示“后台管理”
```

普通用户不显示入口。

即使普通用户手动访问后台接口，后端也必须返回 403。

### 11.2 用户管理

第一版用户管理只读。

列表字段：

- 用户 ID。
- 邮箱。
- 用户名。
- 角色。
- 创建时间。
- 面试记录数。
- 训练任务数。

不做：

- 删除用户。
- 修改密码。
- 封禁用户。
- 强制下线。

### 11.3 RAG 文档管理

后台 RAG 文档管理需要比用户端更偏平台视角。

功能：

- 查看全部公共知识库文档。
- 按 knowledgeBase 过滤。
- 查看文档 chunk。
- 查看 embedding 状态。
- 查看 metadata。
- 创建文档。
- 更新文档。
- 删除或归档文档。

注意：

第一版可以继续复用现有 RAG 文档表，不急着新建后台专用表。

### 11.4 题库管理

题库可以先作为 `knowledgeBase = question_bank` 的特殊文档类型。

第一版功能：

- 新增题库文档。
- 编辑题库文档。
- 查看题库 chunk。
- 按岗位、难度、标签过滤。

如果后续题库结构变复杂，再考虑新增 `QuestionItem` 表。

### 11.5 RAG 日志查看

后台 RAG 日志页面展示：

- 用户。
- retrieverName。
- knowledgeBase。
- retrievalMode。
- queryText。
- hitCount。
- quality。
- createdAt。

详情面板展示：

- hitsJson。
- matchedTokens。
- bm25Score。
- vectorScore。
- hybridScore。
- rerankScore。
- metadata。

### 11.6 Agent 日志查看

后台 Agent 日志页面展示：

- 用户。
- action。
- difficulty。
- focus。
- reason。
- fallbackUsed。
- guardrailApplied。
- createdAt。

详情面板展示：

- state_json。
- decision_json。
- nodeTrace。
- toolCalls。

### 11.7 后台系统配置

第一版只读展示：

- 当前模型名。
- embedding 模型名。
- rerank 模型名。
- 默认检索模式。
- 是否配置 API key。
- 数据库类型。

不要在第一版做在线修改配置。

## 12. 后端 API 设计

### 12.1 用户端训练任务接口

建议新增：

```text
GET /api/training/tasks
POST /api/training/tasks/generate-from-report
GET /api/training/tasks/{task_id}
PATCH /api/training/tasks/{task_id}
POST /api/training/tasks/{task_id}/start
POST /api/training/tasks/{task_id}/complete
POST /api/training/tasks/{task_id}/archive
```

接口说明：

- `GET /api/training/tasks`：查询当前用户训练任务。
- `POST /api/training/tasks/generate-from-report`：从报告 weakTags 生成训练任务。
- `GET /api/training/tasks/{task_id}`：查看任务详情。
- `PATCH /api/training/tasks/{task_id}`：更新任务标题、状态、优先级等。
- `POST /start`：开始训练，状态变为 `in_progress`。
- `POST /complete`：完成训练，更新掌握度和状态。
- `POST /archive`：归档任务。

### 12.2 管理后台接口

建议新增：

```text
GET /api/admin/summary
GET /api/admin/users
GET /api/admin/rag/documents
GET /api/admin/rag/logs
GET /api/admin/agent/logs
GET /api/admin/config
```

如果复用现有 RAG 文档创建和编辑接口，需要加 admin 权限版本或在已有接口中明确权限策略。

### 12.3 用户角色接口

现有认证响应建议增加：

```text
user.role
```

但必须保持兼容。

如果旧前端没有读取 role，也不应影响登录流程。

### 12.4 Agent State 扩展

`/api/interview/next-question` 可选扩展：

```json
{
  "candidateTrainingTasks": [
    {
      "weakTag": "rag_quality",
      "title": "RAG 质量评估基础训练",
      "masteryScore": 45,
      "priority": "high",
      "status": "in_progress"
    }
  ]
}
```

这可以先作为内部 state 字段，不要求前端立即展示全部内容。

## 13. 数据库设计

### 13.1 User 增加 role

建议给 `users` 表增加：

```text
role VARCHAR(20) DEFAULT 'user'
```

允许值：

```text
user
admin
```

第一版可以通过本地脚本或数据库直接把指定账号设为 admin。

不要在前端开放“自助注册管理员”。

### 13.2 新增 TrainingTask 表

建议表名：

```text
training_tasks
```

字段：

```text
id INTEGER PRIMARY KEY
user_id INTEGER NOT NULL
application_profile_id INTEGER NULL
source_interview_record_id INTEGER NULL
weak_tag VARCHAR(80) NOT NULL
weak_label VARCHAR(120) NOT NULL
title VARCHAR(200) NOT NULL
description TEXT NOT NULL
status VARCHAR(40) NOT NULL DEFAULT 'todo'
priority VARCHAR(40) NOT NULL DEFAULT 'medium'
mastery_score INTEGER NOT NULL DEFAULT 40
attempt_count INTEGER NOT NULL DEFAULT 0
last_practiced_at DATETIME NULL
next_review_at DATETIME NULL
metadata_json TEXT NOT NULL DEFAULT '{}'
created_at DATETIME NOT NULL
updated_at DATETIME NOT NULL
```

关系：

```text
TrainingTask.user_id -> User.id
TrainingTask.application_profile_id -> ApplicationProfile.id
TrainingTask.source_interview_record_id -> InterviewRecord.id
```

### 13.3 是否新增 TrainingAttempt 表

第一阶段不强制新增 `training_attempts`。

理由：

- 当前最重要的是任务闭环，而不是记录每一次训练细节。
- 训练详情可以先写入 `metadata_json`。
- 等训练中心稳定后，再新增 `TrainingAttempt` 表保存每次训练回答、评分和模型反馈。

后续可扩展：

```text
training_attempts
  id
  task_id
  user_id
  mode
  question
  answer
  answer_status
  mastery_delta
  created_at
```

## 14. 前端设计

### 14.1 不引入新框架

本阶段继续使用：

- `index.html`
- `styles.css`
- `app.js`
- 前端 `.mjs` 测试

不引入 React、Vue、Next.js。

### 14.2 导航结构

建议在页面上形成稳定导航：

```text
面试
训练
历史
档案
后台
```

其中“后台”仅管理员可见。

### 14.3 用户端训练中心 UI

训练中心建议分三块：

```text
左侧：薄弱点和任务列表
中间：任务详情和训练入口
右侧：掌握度、答题要点、常见错误
```

移动端可以变成上下堆叠。

### 14.4 后台 UI

后台不需要华丽，但要清晰：

```text
左侧后台菜单
右侧内容区
表格 + 详情面板
```

后台页面风格应该偏工作台，不做营销页面。

### 14.5 前端状态管理

继续使用轻量 JS 状态。

建议把状态概念拆清楚：

```text
session.auth
session.interview
session.training
session.admin
```

如果 `app.js` 继续变大，后续可以拆成多个 JS 文件，但本阶段不强制。

## 15. Agent 与训练任务协作

### 15.1 当前 Agent 链路

当前链路：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_weakness_strategy
-> select_training_template
-> select_action
-> generate_question
-> update_memory
```

### 15.2 新增训练任务输入

训练任务系统稳定后，Agent State 可以增加：

```text
candidateTrainingTasks
```

来源：

- 当前用户高优先级任务。
- 当前求职档案相关任务。
- 最近未完成任务。

### 15.3 Agent 如何使用训练任务

规则：

- coach 模式优先选择 `high` 优先级且 `mastery_score < 60` 的任务。
- interview 模式可以选择 `mastery_score < 80` 的任务做真实追问。
- 如果用户连续答不上来，训练任务不应强行重复追问，应触发降难度或解释。
- 如果任务已 `done`，不应频繁重复训练。

### 15.4 日志要求

Agent Decision 中应能记录：

```text
selectedTrainingTaskId
selectedWeakTag
masteryScore
trainingTaskReason
```

这方便解释：

```text
为什么这一轮围绕这个薄弱点训练？
```

## 16. LangGraph 迁移预留

### 16.1 当前是否接近 LangGraph

概念上已经接近。

当前已有：

- Agent State。
- nodeTrace。
- ToolCalls。
- 显式节点。
- fallback。
- guardrail。
- update_memory。

这些都能映射到 LangGraph。

### 16.2 为什么本阶段不直接引入

原因：

- 训练任务系统还没有稳定。
- 管理后台还没有稳定。
- Agent State 还会继续增加训练任务字段。
- 现在引入框架会放大变更范围。
- 用户当前更需要先能讲清自研 Agent 的底层逻辑。

### 16.3 未来映射关系

未来可映射为：

```text
Agent State -> Graph State
observe_state -> node
analyze_answer -> node
retrieve_context -> tool node
select_weakness_strategy -> node
select_training_template -> node
select_action -> node
generate_question -> node
update_memory -> node
nextAction -> conditional edge
AgentDecisionLog -> checkpoint / trace persistence 的过渡形态
```

### 16.4 LangGraph POC 触发条件

满足以下条件后再做 LangGraph POC：

- 训练任务系统后端稳定。
- 用户端训练中心可用。
- 管理后台日志能观察 Agent 决策。
- Agent State 字段稳定。
- 当前 Agent 关键节点有测试覆盖。
- 用户能讲清自研 Agent 和 LangGraph 的映射关系。

### 16.5 POC 范围

未来 POC 只迁移一个最小链路：

```text
observe_state
-> retrieve_context
-> select_action
-> generate_question
```

不要一开始迁移完整训练闭环。

## 17. 分阶段实施计划

本 spec 适合拆成 6 个阶段执行。

### 阶段 0：设计确认与现状体检

目标：

- 确认当前测试基线。
- 确认已有接口和页面。
- 确认本阶段不触碰真实部署和 LangGraph。

产出：

- 更新进度文档。
- 记录当前后端 / 前端测试结果。

### 阶段 1：用户角色与后台权限基础

目标：

- 给 User 增加 role。
- 新增 `require_admin_user`。
- 后台接口能正确返回 401 / 403。
- 认证响应包含 role。

验收：

- 普通用户不能访问 admin 接口。
- 管理员可以访问 admin summary。
- 旧登录流程不受影响。

学习文档：

```text
docs/learning/10-用户角色与后台权限MVP怎么设计.md
```

### 阶段 2：训练任务后端

目标：

- 新增 TrainingTask 表。
- 新增训练任务 service。
- 新增训练任务 API。
- 从报告 weakTags 生成或更新任务。
- 掌握度评分规则落地。

验收：

- 能从报告生成训练任务。
- 同 weakTag 不重复创建未归档任务。
- complete 接口能更新 mastery_score 和 status。
- 用户只能看到自己的训练任务。

学习文档：

```text
docs/learning/11-训练任务系统如何承接weakTags.md
```

### 阶段 3：用户端训练中心

目标：

- 新增训练中心页面区域。
- 展示训练任务列表。
- 展示任务详情。
- 支持开始训练、完成训练、归档任务。
- 历史报告的一键重练升级为生成训练任务并跳转训练中心。

验收：

- 用户可以从报告生成训练任务。
- 用户可以在训练中心看到任务。
- 移动端不出现布局溢出。
- 前端 `.mjs` 测试覆盖训练中心核心交互。

学习文档：

```text
docs/learning/12-训练中心前端页面如何拆分.md
```

### 阶段 4：管理员后台 MVP

目标：

- 新增后台入口。
- 新增 admin summary。
- 新增用户只读列表。
- 新增 RAG 文档后台列表。
- 新增 RAG 日志后台列表。
- 新增 Agent 日志后台列表。

验收：

- admin 能访问后台。
- user 看不到后台入口。
- user 访问后台接口返回 403。
- 后台日志能展示关键字段。

学习文档：

```text
docs/learning/13-管理员后台MVP如何设计.md
```

### 阶段 5：Agent 读取训练任务

目标：

- next-question 构造 Agent State 时读取高优先级训练任务。
- Agent Decision 记录 selectedTrainingTaskId 和 trainingTaskReason。
- coach 模式优先补低掌握度任务。
- interview 模式可检验中等掌握度任务。

验收：

- 有高优先级任务时，Agent State 包含 candidateTrainingTasks。
- Agent Decision 能说明是否使用训练任务。
- 不破坏已有 weakTag 模板逻辑。
- 不导致重复问题死循环。

学习文档：

```text
docs/learning/14-训练任务如何影响Agent决策.md
```

### 阶段 6：LangGraph 迁移预留文档与 POC 计划

目标：

- 不写 LangGraph 代码。
- 写清当前自研 Agent 到 LangGraph 的映射。
- 写清 POC 触发条件和最小迁移范围。

产出：

```text
docs/learning/15-自研Agent如何迁移到LangGraph.md
```

验收：

- 用户能讲清为什么现在还不直接上 LangGraph。
- 用户能讲清未来 graph state、nodes、edges、checkpoint 的映射。

## 18. 测试策略

### 18.1 后端测试

必须覆盖：

- 用户 role 默认值。
- admin 权限依赖。
- 普通用户访问 admin 返回 403。
- TrainingTask 创建。
- TrainingTask 去重。
- TrainingTask 状态流转。
- mastery_score 更新。
- 从 report weakTags 生成任务。
- 用户任务隔离。
- Agent State 读取训练任务。

建议测试文件：

```text
tests/test_admin_auth.py
tests/test_admin_routes.py
tests/test_training_tasks.py
tests/test_training_task_generation.py
tests/test_agent_training_tasks.py
```

### 18.2 前端测试

必须覆盖：

- 非 admin 用户不显示后台入口。
- admin 用户显示后台入口。
- 训练中心能渲染任务列表。
- 点击一键重练后能进入训练中心。
- 任务状态更新后 UI 刷新。
- 后台日志列表能展示关键字段。

建议测试文件：

```text
tests/frontend_training_center.test.mjs
tests/frontend_admin_dashboard.test.mjs
tests/frontend_admin_permissions.test.mjs
```

### 18.3 浏览器验证

阶段 3 和阶段 4 完成后必须使用浏览器验证：

- 桌面端。
- 移动端。
- 登录态。
- 普通用户视角。
- 管理员视角。

验证地址：

```text
http://localhost:8000/
```

## 19. 中文学习文档要求

每个实现阶段结束后，必须新增或更新中文学习文档。

学习文档不要只写“改了什么”，还要写：

- 为什么要这样设计。
- 对应代码在哪。
- 面试时怎么讲。
- 当前边界是什么。
- 后续怎么升级。

本阶段至少产出：

```text
docs/learning/10-用户角色与后台权限MVP怎么设计.md
docs/learning/11-训练任务系统如何承接weakTags.md
docs/learning/12-训练中心前端页面如何拆分.md
docs/learning/13-管理员后台MVP如何设计.md
docs/learning/14-训练任务如何影响Agent决策.md
docs/learning/15-自研Agent如何迁移到LangGraph.md
```

## 20. 风险与控制

### 20.1 风险：范围过大

控制方式：

- spec 可以长，但实现必须分阶段。
- 每阶段必须能独立验收。
- 管理后台先做只读和基础管理。
- LangGraph 只做预留，不写代码。

### 20.2 风险：前端 app.js 继续膨胀

控制方式：

- 本阶段不强制重构框架。
- 如果改动集中，可以考虑把训练中心和后台逻辑拆成小函数。
- 不进行无关大重构。

### 20.3 风险：数据库迁移影响现有数据

控制方式：

- 新增字段设置默认值。
- 新表不破坏旧表。
- 测试覆盖初始化和迁移。
- 本地开发环境先验证。

### 20.4 风险：训练任务影响面试问题质量

控制方式：

- 第一阶段只把训练任务作为 Agent State 的辅助信息。
- 不替代现有 RAG 和 trainingTemplateHint。
- 保留 guardrail 防止死磕同一问题。

### 20.5 风险：后台权限不足导致数据泄露

控制方式：

- 所有 `/api/admin/*` 必须使用 `require_admin_user`。
- 用户端接口继续按 `current_user.id` 过滤。
- 测试覆盖普通用户访问后台失败。

## 21. 验收标准

本阶段最终验收标准：

### 产品验收

- 用户端有清晰训练中心。
- 用户能从报告生成训练任务。
- 用户能看到任务状态和掌握度。
- 管理员能进入后台。
- 管理员能查看用户、RAG 文档、RAG 日志、Agent 日志。
- 普通用户不能访问后台。

### 技术验收

- TrainingTask 数据模型稳定。
- admin 权限依赖稳定。
- 训练任务 API 有测试覆盖。
- 后台 API 有测试覆盖。
- 前端训练中心和后台入口有测试覆盖。
- `/api/interview/next-question` 保持兼容。
- Agent State 可选读取训练任务，不破坏现有 Agent 决策。

### 学习验收

- 用户能讲清为什么要把 weakTags 升级为 TrainingTask。
- 用户能讲清 user/admin 权限模型。
- 用户能讲清训练任务如何影响 Agent 决策。
- 用户能讲清为什么暂不直接引入 LangGraph。
- 用户能讲清后续 LangGraph 迁移路径。

## 22. 推荐追求目标执行边界

如果使用“追求目标”模式执行本 spec，建议目标文本只要求：

```text
持续推进 docs/superpowers/specs/2026-06-10-productization-v2-training-admin-langgraph-reserve-design.md。

优先按阶段执行：
1. 用户角色与后台权限基础。
2. 训练任务后端。
3. 用户端训练中心。
4. 管理员后台 MVP。
5. Agent 读取训练任务。
6. LangGraph 迁移预留文档。

每轮开发前先用中文解释本轮要学的知识点。
开发时优先测试驱动，先写或更新测试，再实现。
每阶段结束后运行相关后端 pytest 和前端 .mjs 测试。
每阶段结束后新增中文学习文档，并更新 docs/pre-deployment-progress.md。
本阶段不做 Docker、Nginx、云服务器上线。
本阶段不直接引入 LangGraph 或 LangChain。
本阶段不引入 React、Vue、Next.js。
```

## 23. 面试表达

这阶段完成后，可以这样讲：

```text
项目原来已经能完成模拟面试和报告复盘，但我发现 weakTags 只是报告字段，还没有变成用户可持续训练的产品能力。所以我设计了训练任务系统，把报告里的薄弱点转成 TrainingTask，并记录状态、优先级、掌握度和训练次数。

同时我把页面从单一面试工作台拆成用户端和管理端。用户端增加训练中心，管理员端提供用户、知识库、RAG 日志和 Agent 日志的管理入口。权限上第一版只区分 user 和 admin，避免一开始就做复杂 RBAC。

Agent 侧没有马上引入 LangGraph，而是继续稳定自研 Orchestrator 的状态、节点、工具和日志。等训练任务、后台日志和 Agent State 稳定后，再把 observe_state、retrieve_context、select_action、generate_question 等节点迁移到 LangGraph。
```

## 24. 最终结论

本阶段不是简单丰富页面，也不是盲目做后台。

它的核心是：

```text
让 AI 模拟面试系统从“问答工具”升级为“训练闭环平台”。
```

用户端解决：

```text
我现在该练什么，我练到什么程度了。
```

后台解决：

```text
系统资料、日志、用户和 Agent 行为如何被管理和观察。
```

LangGraph 预留解决：

```text
当前自研 Agent 未来如何升级为状态图工作流。
```

因此推荐执行顺序是：

```text
用户角色与后台权限基础
-> 训练任务后端
-> 训练中心前端
-> 管理员后台 MVP
-> Agent 读取训练任务
-> LangGraph 迁移文档
```

其中“用户角色与后台权限基础”放在最前面，是因为后续后台接口、后台页面和管理员可见入口都依赖它；真正的产品主线仍然是：

```text
训练任务后端
-> 训练中心前端
-> Agent 读取训练任务
-> 训练闭环持续优化
```
