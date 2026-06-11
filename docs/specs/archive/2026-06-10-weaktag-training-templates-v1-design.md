# weakTag 训练模板系统 V1 设计

## 1. 文档目的

本文档用于设计 AI 模拟面试系统的下一阶段训练闭环增强：

```text
让系统不只知道候选人哪里薄弱，
还知道每个薄弱点应该怎么训练、怎么追问、怎么给答题要点。
```

上一阶段已经完成：

- 报告里能生成 `weakTags`。
- 历史记录能沉淀 `weakTags`。
- 候选人画像能聚合 `candidateProfile.frequentWeakTags`。
- Agent State 能看到 `candidateProfile.frequentWeakTags`。
- Agent Decision 能生成 `weaknessStrategy`。
- `nodeTrace` 和 Agent 日志能观察弱点策略。

当前仍然存在一个缺口：

```text
Agent 已经知道用户长期薄弱点，
但还没有一套稳定的训练模板告诉它：
这个 weakTag 应该怎么练、从什么难度开始、coach/interview 分别怎么问。
```

本阶段目标就是补齐这个缺口，让训练闭环从“弱点识别”升级为“弱点训练”。

## 2. 当前上下文

### 2.1 已有数据链路

当前弱点链路是：

```text
questionReviews[*].weakTags
-> trainingPlan.weakTopics[*].weakTags
-> 历史面试记录
-> candidateProfile.frequentWeakTags
-> Agent State
-> weaknessStrategy
-> Agent Decision
-> 下一题生成
```

这个链路已经能做到：

```text
系统知道候选人长期薄弱点是什么。
```

但还不能稳定做到：

```text
系统知道这个薄弱点应该如何分层训练。
```

### 2.2 已有三类 RAG

当前项目有三类 RAG：

- 岗位知识库 RAG：提供岗位标准、技术知识、评分依据。
- 题库 RAG：提供可参考的问题、参考答案、答题要点。
- 候选人画像 RAG：提供历史表现、薄弱点、训练建议。

训练模板不是第四个 RAG。

它更像一个规则化的“训练策略索引层”，负责把稳定的 weakTag 映射为可训练结构。

### 2.3 已有 Agent 能力

当前 Interview Orchestrator Agent 已经具备：

- `observe_state`
- `analyze_answer`
- `retrieve_context`
- `select_weakness_strategy`
- `select_action`
- `generate_question`
- `update_memory`
- `toolCalls`
- `nodeTrace`
- `coach / interview` 双模式
- fallback / normalize / guardrail

因此本阶段不需要重写 Agent，只需要让 `weaknessStrategy` 能拿到训练模板，并把模板摘要传入下一题生成策略。

## 3. 总目标

本阶段新增一个轻量训练模板系统：

```text
weakTag
-> training template
-> coach/interview mode question strategy
-> next-question payload
-> Agent Decision / 日志 / 学习文档
```

最终效果：

- `rag_quality` 不再只是一个标签，而是能映射到 Hit@K、MRR、关键词覆盖率、命中日志、质量面板等训练内容。
- `agent_state` 不再只是一个标签，而是能映射到 Agent State、ToolCalls、Decision、nodeTrace、fallback/normalize/guardrail 等训练内容。
- coach 模式下，系统优先按模板里的基础阶梯拆小训练。
- interview 模式下，系统优先按模板里的真实追问阶梯进行深挖。
- 问题生成 payload 能看到模板摘要，减少模型自由发挥导致的问题飘移。
- 日志能记录本轮用了哪个 weakTag 模板，方便排查和面试讲解。

## 4. 非目标

本阶段明确不做：

- 不新增数据库表。
- 不做完整训练任务系统。
- 不做训练进度条或掌握度评分。
- 不做管理员后台维护模板。
- 不把模板做成可视化编辑器。
- 不做前端大重构。
- 不引入 React / Vue / Next.js。
- 不引入 LangGraph / LangChain。
- 不做 Docker / Nginx / 云服务器上线。
- 不替代题库 RAG。
- 不要求模板覆盖所有 weakTags。

如果后续要做“训练路径系统”或“掌握度评分系统”，应另写 spec。

## 5. 关键概念

### 5.1 weakTag

`weakTag` 是标准化薄弱点标签。

例如：

```text
rag_quality
rag_retrieval
agent_state
backend_fastapi
database_modeling
project_storytelling
```

它回答的问题是：

```text
用户薄弱在哪里？
```

### 5.2 Training Template

Training Template 是某个 weakTag 对应的训练模板。

它回答的问题是：

```text
这个薄弱点应该怎么练？
```

一个模板应包含：

- `weakTag`：对应的薄弱标签。
- `label`：中文名称。
- `description`：薄弱点说明。
- `coachQuestions`：学习辅导模式问题。
- `interviewQuestions`：真实面试模式问题。
- `difficultyLadder`：从基础到进阶的问题阶梯。
- `answerKeyPoints`：答题要点。
- `commonMistakes`：常见错误。
- `oneMinuteTemplate`：一分钟表达模板。
- `relatedTags`：相关 weakTags。

### 5.3 Template Hint

Template Hint 是模板给 Agent 和问题生成模型看的摘要。

它不是完整模板，而是本轮生成问题需要用到的最小信息。

例如：

```json
{
  "weakTag": "rag_quality",
  "label": "RAG 质量评估",
  "recommendedQuestion": "Hit@K、MRR、关键词覆盖率分别解决什么问题？",
  "answerKeyPoints": ["Hit@K 衡量前 K 条是否命中", "MRR 衡量首个正确结果排名", "关键词覆盖率衡量召回内容是否覆盖预期关键词"],
  "commonMistakes": ["只会说字段名，不会说明指标解决什么问题"]
}
```

它回答的问题是：

```text
本轮围绕这个 weakTag 训练时，最该问什么、看什么、避免什么？
```

## 6. 模板覆盖范围

V1 只覆盖 6 个高价值标签。

### 6.1 rag_quality

训练目标：

```text
让用户能讲清 RAG 质量评估，不再只会背字段名。
```

应覆盖：

- Hit@K。
- MRR。
- 关键词覆盖率。
- 空召回率。
- metadata 匹配率。
- RAG 命中日志字段。
- 质量面板为什么有用。

coach 问法示例：

```text
我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？
```

interview 问法示例：

```text
如果你说项目里做了 RAG 质量评估，请说清 Hit@K 和 MRR 分别怎么计算，以及它们各自解决什么问题。
```

### 6.2 rag_retrieval

训练目标：

```text
让用户能讲清 RAG 召回链路，而不是只说“用向量数据库检索”。
```

应覆盖：

- query 构造。
- 文本清洗。
- chunk 切分。
- BM25。
- embedding 向量检索。
- hybrid search。
- rerank。
- metadata filter。

coach 问法示例：

```text
先不用讲所有细节，你先按顺序说出一次 RAG 检索从 query 到 top chunks 的完整链路。
```

interview 问法示例：

```text
你项目里的 RAG 为什么先做 BM25，再做 hybrid search 和 rerank？如果 rerank 失败，系统怎么降级？
```

### 6.3 agent_state

训练目标：

```text
让用户能讲清 Agent 不是普通 LLM 调用，而是有状态、工具、决策和日志的流程控制层。
```

应覆盖：

- Agent State。
- ToolCalls。
- Agent Decision。
- fallback。
- normalize。
- guardrail。
- nodeTrace。
- LangGraph 迁移方向。

coach 问法示例：

```text
我们先从基础开始：Agent State、ToolCalls、Agent Decision 分别解决什么问题？
```

interview 问法示例：

```text
请结合你的项目说明，一轮 next-question 请求里 Agent State 是怎么构造出来的，Agent Decision 又如何影响最终问题生成？
```

### 6.4 backend_fastapi

训练目标：

```text
让用户能讲清 FastAPI 后端模块边界和接口链路。
```

应覆盖：

- `main.py`。
- `APIRouter`。
- `schemas.py`。
- `db_models.py`。
- `database.py`。
- `Depends(get_db)`。
- `Depends(get_current_user)`。
- 异常处理。
- 请求日志。

coach 问法示例：

```text
先按模块说：FastAPI 项目里 router、schema、db_model、database 分别负责什么？
```

interview 问法示例：

```text
请解释 `/api/interview/next-question` 从接收请求到返回下一题，中间经过了哪些后端模块。
```

### 6.5 database_modeling

训练目标：

```text
让用户能讲清用户、投递档案、面试记录、RAG 文档、日志之间的数据库关系。
```

应覆盖：

- 主键。
- 外键。
- 一对多关系。
- `relationship`。
- refresh token。
- interview records 归属。
- RAG document / chunk。
- AgentDecisionLog。
- RagRetrievalLog。

coach 问法示例：

```text
先拿 interview_records 举例：这张表为什么需要 user_id？它和 users 表是什么关系？
```

interview 问法示例：

```text
如果面试官追问你的项目如何避免用户 A 查到用户 B 的历史面试记录，你会从数据库表和查询过滤两个层面怎么回答？
```

### 6.6 project_storytelling

训练目标：

```text
让用户能把项目讲成一条完整业务闭环，而不是零散罗列技术名词。
```

应覆盖：

- 项目背景。
- 目标用户。
- 业务流程。
- 技术架构。
- 个人职责。
- 技术难点。
- 效果验证。
- 后续规划。

coach 问法示例：

```text
先用 1 分钟讲清：你的 AI 模拟面试系统解决谁的什么问题，核心流程是什么？
```

interview 问法示例：

```text
请不要罗列技术栈，按背景、方案、难点、结果的顺序讲一下你为什么做这个 AI 模拟面试系统。
```

## 7. 数据结构设计

建议新增后端模块：

```text
backend_python/weakness_training_templates.py
```

核心数据结构：

```python
WEAKNESS_TRAINING_TEMPLATES = {
    "rag_quality": {
        "weakTag": "rag_quality",
        "label": "RAG 质量评估",
        "description": "用于训练候选人解释 RAG 评估指标和命中日志。",
        "coachQuestions": [...],
        "interviewQuestions": [...],
        "difficultyLadder": {
            "basic": [...],
            "medium": [...],
            "hard": [...]
        },
        "answerKeyPoints": [...],
        "commonMistakes": [...],
        "oneMinuteTemplate": "...",
        "relatedTags": [...]
    }
}
```

建议提供函数：

```python
get_training_template(weak_tag: str) -> dict
select_training_template_hint(
    *,
    weakness_strategy: dict,
    agent_mode: str,
    difficulty: str,
) -> dict
```

### 7.1 `get_training_template()`

职责：

```text
根据 weakTag 返回完整训练模板。
```

如果 weakTag 不存在，返回通用表达训练模板，不抛异常。

原因：

```text
Agent 主链路不能因为某个 weakTag 没有模板而失败。
```

### 7.2 `select_training_template_hint()`

职责：

```text
根据 weaknessStrategy、agentMode、difficulty 选出本轮最适合给 LLM 的模板摘要。
```

选择规则：

- `coach` 模式优先使用 `coachQuestions`。
- `interview` 模式优先使用 `interviewQuestions`。
- `difficulty=basic` 优先使用基础阶梯。
- `difficulty=medium` 优先使用中等阶梯。
- `difficulty=hard` 优先使用困难阶梯。
- 如果没有匹配难度，降级到基础问题。

返回示例：

```json
{
  "enabled": true,
  "weakTag": "rag_quality",
  "label": "RAG 质量评估",
  "mode": "coach",
  "difficulty": "basic",
  "recommendedQuestion": "Hit@K、MRR、关键词覆盖率分别解决什么问题？",
  "answerKeyPoints": ["Hit@K", "MRR", "关键词覆盖率"],
  "commonMistakes": ["只解释字段名，不解释指标用途"],
  "oneMinuteTemplate": "可以按指标定义、解决问题、项目落地三步回答。"
}
```

## 8. Agent 接入设计

### 8.1 接入位置

训练模板应接在 `weaknessStrategy` 之后：

```text
candidateProfile.frequentWeakTags
-> select_weakness_strategy()
-> select_training_template_hint()
-> Agent Decision
-> questionStrategy
-> generate_question
```

原因：

```text
weaknessStrategy 先决定本轮围绕哪个 weakTag，
trainingTemplate 再决定这个 weakTag 该怎么训练。
```

### 8.2 Agent State

Agent State 可以保留完整 `weaknessStrategy`，但不建议塞入完整训练模板。

原因：

- 完整模板信息较多，会让 state 变臃肿。
- Agent State 主要是状态快照，不是题库。
- 模板摘要更适合进入 Agent Decision 或 questionStrategy。

### 8.3 Agent Decision

建议在 Agent Decision 中增加：

```json
{
  "trainingTemplateHint": {
    "enabled": true,
    "weakTag": "rag_quality",
    "label": "RAG 质量评估",
    "recommendedQuestion": "Hit@K、MRR、关键词覆盖率分别解决什么问题？",
    "answerKeyPoints": ["Hit@K", "MRR", "关键词覆盖率"]
  }
}
```

这样前端、日志和测试都能看到本轮是否用了训练模板。

### 8.4 questionStrategy

`/api/interview/next-question` 构造问题生成 payload 时，应把模板摘要写入：

```json
{
  "questionStrategy": {
    "trainingTemplateHint": {...}
  }
}
```

这能约束最终问题生成模型：

```text
不要只知道弱点标签，还要参考模板里的推荐问题、答题要点和常见错误。
```

## 9. 与题库 RAG 的关系

训练模板不是题库 RAG 的替代品。

两者关系如下：

```text
题库 RAG：
根据岗位、阶段、JD、简历召回参考题目。

训练模板：
根据候选人长期 weakTag 选择训练阶梯和答题要点。
```

当两者同时存在时：

```text
题库 RAG 提供“这类岗位真实会怎么问”；
训练模板提供“这个候选人的薄弱点应该怎么练”。
```

问题生成时应同时参考：

- 岗位知识库 RAG。
- 题库 RAG。
- 候选人画像 RAG。
- Agent Decision。
- `trainingTemplateHint`。

如果题库 RAG 和训练模板冲突：

- coach 模式下，优先保证训练模板的基础训练目标。
- interview 模式下，优先保证题库 RAG 和真实面试语境，但可以用训练模板控制追问方向。

## 10. 日志与可观测性

本阶段应让日志能看到：

- 是否启用训练模板。
- 使用了哪个 `weakTag`。
- 使用了哪个中文标签。
- 本轮推荐问题是什么。
- 模板来自 coach 还是 interview。
- 模板选择时的 difficulty。

可以写入：

- `AgentDecisionLog.decision_json.trainingTemplateHint`
- `nodeTrace.select_training_template`

建议新增 nodeTrace 节点：

```text
select_training_template
```

节点顺序建议：

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

如果 V1 不想新增节点，也可以先写入 `select_action.outputSummary`。

推荐 V1 直接新增 `select_training_template`，原因是：

- 和 `select_weakness_strategy` 边界清楚。
- 更方便后续迁移 LangGraph。
- 更好给面试官解释“先选弱点，再选训练方法”。

## 11. API 兼容性

必须保持：

```text
POST /api/interview/next-question
```

现有请求兼容。

不要求前端新增字段。

响应可以在已有字段中增强：

```text
agentDecision.trainingTemplateHint
decisionSummary
```

不新增顶层必填字段。

前端如果暂时不展示模板摘要，也不影响主流程。

## 12. 测试计划

### 12.1 模板单元测试

新增：

```text
tests/test_weakness_training_templates.py
```

覆盖：

- `rag_quality` 能返回训练模板。
- `agent_state` 能返回训练模板。
- 未知 weakTag 能返回通用模板。
- coach 模式优先选择 coach 问题。
- interview 模式优先选择 interview 问题。
- 不同 difficulty 能选择不同阶梯问题。

### 12.2 Agent 集成测试

更新：

```text
tests/test_interview_agent.py
tests/test_agent_orchestrator.py
```

覆盖：

- `weaknessStrategy.primaryWeakTag=rag_quality` 时，Agent Decision 带有 `trainingTemplateHint`。
- `nodeTrace` 包含 `select_training_template`。
- unknown weakTag 不会导致 Agent 主流程失败。

### 12.3 路由测试

更新：

```text
tests/test_interview_agent_route.py
```

覆盖：

- 历史记录里有 `rag_quality`。
- 下一题接口返回的 `agentDecision.trainingTemplateHint.weakTag=rag_quality`。
- 生成问题 payload 中的 `questionStrategy.trainingTemplateHint` 能被模型看到。
- AgentDecisionLog 中能查到 `trainingTemplateHint`。

### 12.4 前端测试

V1 不强制改前端。

如果只把模板摘要放入 `agentDecision`，已有 Agent 日志面板能展示原始 JSON，则不需要改前端。

如果要做模板摘要展示，再另补 `.mjs` 测试。

## 13. 风险与边界

### 13.1 模板过硬导致问题机械

风险：

```text
系统每次 rag_quality 都问同一道题。
```

应对：

- 模板提供问题池，而不是单题。
- 根据 difficulty 和 agentMode 选择问题。
- 仍保留 RAG 和历史回答作为上下文。

### 13.2 模板覆盖不足

风险：

```text
某些 weakTag 没有模板，导致主流程失败。
```

应对：

- 未知 weakTag 返回通用表达训练模板。
- 日志记录 fallback。

### 13.3 和题库 RAG 职责混乱

风险：

```text
训练模板变成另一个硬编码题库。
```

应对：

- 模板只定义训练目标、问题阶梯和答题要点。
- 题库 RAG 仍负责真实面试题和参考答案。
- 模板不替代 RAG 检索。

### 13.4 一次性做太大

风险：

```text
同时做模板、掌握度评分、前端路线图、训练任务表，导致代码质量下降。
```

应对：

- V1 只做后端模板和 Agent 接入。
- 不新增数据库表。
- 不做前端大改。

## 14. 验收标准

本阶段完成后应满足：

- 有 `backend_python/weakness_training_templates.py`。
- 至少覆盖 6 个核心 weakTags。
- 每个模板包含 coach / interview 问题、难度阶梯、答题要点、常见错误。
- `select_training_template_hint()` 能根据 `weaknessStrategy` 选择模板摘要。
- Agent Decision 中能看到 `trainingTemplateHint`。
- `/api/interview/next-question` 的问题生成 payload 能看到 `questionStrategy.trainingTemplateHint`。
- Agent 日志或 nodeTrace 能看到训练模板选择原因。
- 不破坏现有 next-question 接口。
- 不新增数据库表。
- 后端测试通过。
- 如未改前端，则说明未运行前端 `.mjs` 的原因。
- 新增中文学习文档，说明 weakTag 训练模板怎么支撑训练闭环。

## 15. 建议实现阶段

### 阶段 A：模板模块

- 新增 `backend_python/weakness_training_templates.py`。
- 定义 6 个核心模板。
- 实现 `get_training_template()`。
- 实现 `select_training_template_hint()`。
- 补单元测试。

### 阶段 B：Agent 接入

- 在 Agent 决策链路中读取 `weaknessStrategy`。
- 生成 `trainingTemplateHint`。
- 写入 Agent Decision。
- 新增或增强 `nodeTrace`。
- 补 Agent 测试。

### 阶段 C：路由与日志验证

- 在 `/api/interview/next-question` 的 `questionStrategy` 中加入 `trainingTemplateHint`。
- 确认 AgentDecisionLog 写入模板摘要。
- 补路由测试。

### 阶段 D：学习文档和进度记录

新增：

```text
docs/learning/08-weakTag训练模板如何让Agent更会训练.md
```

更新：

```text
docs/pre-deployment-progress.md
```

## 16. 面试表达模板

可以这样讲：

```text
我在训练闭环里不只做了 weakTags 识别，还做了 weakTag 到训练模板的映射。
比如用户多次在 rag_quality 上薄弱，系统不会只记一个标签，而是会找到 RAG 质量评估模板。
这个模板里包含 coach 模式的问题、interview 模式的问题、从基础到进阶的训练阶梯、答题要点和常见错误。
下一轮 Agent 生成问题时，会先根据候选人画像选出 weaknessStrategy，再根据 weakTag 选择 trainingTemplateHint。
这样问题生成就不完全依赖模型自由发挥，而是被稳定的训练目标约束。
同时模板摘要会写入 Agent Decision 和 nodeTrace，方便解释为什么这一轮这样训练。
```

如果面试官问“这和题库 RAG 有什么区别”，可以这样答：

```text
题库 RAG 解决的是岗位和面试阶段下应该参考哪些真实问题。
weakTag 训练模板解决的是某个候选人的长期薄弱点应该如何训练。
前者偏资料召回，后者偏训练策略。
生成下一题时，我会同时参考题库 RAG 和训练模板：
题库保证问题像真实面试，模板保证问题能补用户薄弱点。
```

## 17. 后续扩展方向

本阶段完成后，后续可以继续做：

- weakTag 掌握度评分。
- 训练路径系统。
- 前端训练路线图。
- 每个 weakTag 的专项训练页。
- 后端训练任务表。
- 模板后台管理。
- LangGraph 状态图迁移。

这些都不属于 V1 范围。
