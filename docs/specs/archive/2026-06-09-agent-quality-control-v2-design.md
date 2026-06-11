# Agent 质量控制 V2 设计

## 1. 文档目的

本文档用于约束 AI 模拟面试系统下一阶段的 Agent 质量控制能力。

当前项目已经具备三类 RAG、Agent State、Agent Decision、fallback、normalize、Agent 日志、coach/interview 两种模式等基础能力。但在真实体验中仍然存在一个核心问题：

```text
当候选人连续答不上来时，Agent 可能继续围绕同一个知识点机械追问，导致体验不像真实面试，也不利于学习。
```

本阶段目标不是引入 LangGraph，也不是重写整个 Agent，而是在现有 FastAPI 后端中增强自研 Interview Orchestrator Agent 的质量控制能力，让它具备更清楚的状态判断、重复问题保护、连续失败处理和可解释日志。

## 2. 当前问题

### 2.1 机械追问

历史体验中出现过类似情况：

- 第一题围绕 RAG 日志 JSON 追问。
- 候选人连续多轮回答“不知道”“不会写”。
- 后续问题仍继续要求写 RAG 日志 JSON。
- 最终八轮问题都集中在同一细节上。

这类问题说明 Agent 虽然有“深挖”能力，但缺少“停止无效深挖”的控制策略。

### 2.2 模式差异不够明显

当前系统已有：

- `coach`：学习辅导模式。
- `interview`：真实面试模式。

但下一步需要让两种模式在策略上更加清晰：

- `coach` 模式应该更关注解释、降难度、给候选人台阶。
- `interview` 模式可以保留压力，但不能无限重复卡死同一个问题。

### 2.3 日志解释还不够面向排错

当前 Agent 日志已经记录了 state、decision、triggerRules、fallbackUsed 等信息。

下一阶段需要让日志更能回答：

- 为什么这一轮降难度？
- 为什么这一轮切换话题？
- 是否检测到连续答不上来？
- 是否检测到重复问题？
- 这次 decision 是模型输出，还是 fallback/guardrail 修正后的结果？

## 3. 阶段目标

Agent 质量控制 V2 的目标是：

```text
让 Agent 在多轮面试中既能深挖，也能识别无效深挖，并根据用户状态切换到更合适的提问策略。
```

完成后，系统应满足：

- 连续答不上来时，Agent 不再一直追问同一个高难细节。
- 连续重复问题时，Agent 能触发重复问题保护。
- `coach` 模式优先解释概念、降低难度、给训练建议。
- `interview` 模式保留真实压力，但最多连续追问有限轮次。
- Agent 日志能记录触发的规则和原因。
- `/api/interview/next-question` 保持兼容，不破坏现有前端调用。

## 4. 不做什么

本阶段明确不做以下内容：

- 不引入 LangGraph。
- 不安装 LangChain。
- 不重写三类 RAG 检索链路。
- 不修改数据库表结构，优先复用现有 `AgentDecisionLog` 的 JSON 字段。
- 不做 Docker、Nginx、云服务器上线。
- 不做前端大重构，只在后端响应字段兼容前端已有展示。
- 不让大模型完全自主决定是否切题，必须保留规则兜底。

## 5. 核心概念

### 5.1 Agent State

Agent State 是 Agent 当前做决策时看到的状态包。它不是数据库表，而是一次决策过程中的上下文。

本阶段重点关注以下字段：

```json
{
  "agentMode": "coach",
  "history": [],
  "lastAnswer": {},
  "answerStatus": "不会",
  "answerAnalysis": {
    "weakAnswerStreak": 3,
    "repeatedQuestionCount": 2,
    "topicLock": {
      "topic": "RAG 日志 JSON",
      "count": 3
    },
    "triggerSignals": ["weak_answer_streak", "repeated_question"]
  },
  "retrievalQuality": {
    "roleKnowledge": {},
    "questionBank": {},
    "candidateMemory": {}
  }
}
```

### 5.2 Agent Decision

Agent Decision 是 Agent 根据 State 输出的下一步动作。

本阶段重点关注：

```json
{
  "nextAction": "switch_topic",
  "difficulty": "basic",
  "focus": "RAG 基础链路",
  "reason": "候选人连续三轮答不上来，系统从细节 JSON 追问切换到基础概念确认。",
  "triggerRules": ["weak_answer_streak", "topic_shift", "repeat_guard"],
  "fallbackUsed": false
}
```

### 5.3 Guardrail

Guardrail 指保护规则。它不直接替代大模型，但会约束或修正模型输出。

例如：

- 模型继续生成完全相同的问题时，后端改写为换话题问题。
- 模型在候选人连续答不上来时仍然提高难度，后端改为降难度或切换话题。
- 模型输出非法 `nextAction` 时，使用 fallback decision。

## 6. 回答质量分析规则

### 6.1 回答状态

回答状态继续使用现有四类思想：

| 状态 | 含义 | 示例 |
| --- | --- | --- |
| `完整` | 有结构、有解释、有例子或项目关联 | “我会先解析 query，再做 BM25 和向量召回...” |
| `模糊` | 有一点理解，但不完整 | “大概是用来查知识库的” |
| `不会` | 明确不知道、写不出来、空回答 | “不知道”“不会写”“空提交” |
| `跑题` | 回答内容明显偏离问题 | 问 RAG，却回答登录注册 |

当前实现里主要使用 `完整`、`模糊`、`不会`。`跑题` 可以先作为预留状态，不强制本轮实现。

### 6.2 连续弱回答

新增或强化 `weakAnswerStreak`：

```text
从最近一轮开始向前看，连续多少轮 answerStatus 属于 不会/跑题。
```

建议规则：

- `weakAnswerStreak = 1`：降难度或换一种问法。
- `weakAnswerStreak = 2`：coach 模式解释概念；interview 模式降低难度。
- `weakAnswerStreak >= 3`：触发话题切换，不继续卡同一个细节。

### 6.3 重复问题检测

当前系统已有简单的完全重复问题检测。

V2 需要把它扩展为两层：

1. **完全重复检测**
   - 最近问题文本完全相同或高度相似。
   - 触发 `repeated_prompt_guardrail`。

2. **话题锁定检测**
   - 最近多轮都围绕同一关键词或同一 focus。
   - 例如连续三轮都围绕 `RAG 日志 JSON`。
   - 触发 `topic_lock_guardrail`。

本阶段可以先使用轻量规则，不引入 embedding 相似度：

- 统计最近 3 轮问题中的核心关键词。
- 如果同一个关键词或 focus 出现 2 次以上，并且用户连续答不上来，则认为存在话题锁定风险。

## 7. 决策策略

### 7.1 coach 模式

`coach` 模式是学习辅导模式，策略应更温和。

建议规则：

| 条件 | nextAction | difficulty | 说明 |
| --- | --- | --- | --- |
| 回答完整 | `deep_follow_up` | `medium` 或 `hard` | 可以追问细节 |
| 回答模糊 | `lower_difficulty` | `basic` | 换更基础的问题确认概念 |
| 连续 1 轮不会 | `lower_difficulty` | `basic` | 降难度，引导回答 |
| 连续 2 轮不会 | `summarize_feedback` 或 `lower_difficulty` | `basic` | 先解释概念，再问一个更小问题 |
| 连续 3 轮不会 | `switch_topic` | `basic` | 切换到相邻基础话题 |
| 发现话题锁定 | `switch_topic` | `basic` | 避免机械死磕 |

coach 模式的问题生成应体现：

```text
先补一点概念，再问一个更小、更容易回答的问题。
```

### 7.2 interview 模式

`interview` 模式是真实面试模式，可以保留压力，但要避免无效重复。

建议规则：

| 条件 | nextAction | difficulty | 说明 |
| --- | --- | --- | --- |
| 回答完整 | `deep_follow_up` | `hard` | 深挖实现细节 |
| 回答模糊 | `deep_follow_up` 或 `lower_difficulty` | `medium` | 继续确认边界 |
| 连续 1 轮不会 | `lower_difficulty` | `basic` | 降一级确认基础 |
| 连续 2 轮不会 | `switch_topic` | `basic` | 不继续卡死 |
| 连续 3 轮不会 | `switch_topic` 或 `finish_interview` | `basic` | 视剩余轮次切换或进入复盘 |
| 发现话题锁定 | `switch_topic` | `basic` | 仍然保持压力，但换到相关基础题 |

interview 模式的问题生成应体现：

```text
保留面试压力，但不能连续多轮要求候选人完成同一个做不到的任务。
```

## 8. 话题切换规则

话题切换不是随机换题，而是从当前卡住点切到相邻层级。

示例：

```text
当前卡住点：RAG 命中日志 JSON 具体字段
相邻基础话题：为什么要记录 RAG 命中日志
再基础一点：RAG 检索结果为什么需要可观测性
```

建议切换顺序：

1. 从实现细节切到设计目的。
2. 从代码/JSON 切到流程解释。
3. 从复杂模块切到相关基础概念。
4. 从当前主题切到同岗位另一个核心主题。

不建议：

- 从 RAG 直接跳到完全无关的薪资问题。
- 从不会写 JSON 继续要求“必须写出合法 JSON”。
- 从一个高难细节切到另一个更高难细节。

## 9. 日志设计

本阶段优先复用现有 `AgentDecisionLog`。

建议在 `state_json` 中记录：

```json
{
  "answerAnalysis": {
    "weakAnswerStreak": 3,
    "repeatedQuestionCount": 1,
    "topicLock": {
      "topic": "RAG 日志 JSON",
      "count": 3
    },
    "triggerSignals": ["weak_answer_streak", "topic_lock_guardrail"]
  }
}
```

建议在 `decision_json` 中记录：

```json
{
  "nextAction": "switch_topic",
  "difficulty": "basic",
  "focus": "RAG 可观测性设计",
  "reason": "候选人连续三轮未能写出 RAG 日志 JSON，Agent 切换到日志设计目的，避免无效重复。",
  "triggerRules": ["weak_answer_streak", "topic_shift", "topic_lock_guardrail"],
  "fallbackUsed": false,
  "guardrailApplied": true
}
```

### 9.1 日志排错口径

开发者排查时可以看：

- `answerAnalysis.weakAnswerStreak`：是否连续答不上来。
- `answerAnalysis.repeatedQuestionCount`：是否出现重复问题。
- `answerAnalysis.topicLock`：是否卡在同一话题。
- `decision.nextAction`：Agent 最终动作。
- `decision.triggerRules`：触发了哪些规则。
- `decision.fallbackUsed`：是否用了兜底决策。
- `decision.guardrailApplied`：是否被保护规则修正。

## 10. 接口兼容性

必须保持 `/api/interview/next-question` 兼容。

现有前端字段不应被破坏：

- `stage`
- `focus`
- `prompt`
- `agentDecision`
- `decisionSummary`

可以在 `agentDecision` 内追加字段：

```json
{
  "guardrailApplied": true,
  "topicShift": {
    "from": "RAG 日志 JSON",
    "to": "RAG 可观测性设计"
  }
}
```

前端可以暂时不展示这些字段，但后端日志和调试面板应能看到。

## 11. 测试计划

开发时优先测试驱动。

### 11.1 Agent 状态测试

需要覆盖：

- 连续 3 轮“不知道/不会/写不出来”时，`weakAnswerStreak = 3`。
- 最近 3 轮 focus 相同时，识别出 `topicLock`。
- 空回答也应被识别为 `不会`。
- `coach` 和 `interview` 模式都能进入 state。

### 11.2 Agent 决策测试

需要覆盖：

- `coach` 模式连续 3 轮不会时，`nextAction = switch_topic`。
- `interview` 模式连续 2 轮不会时，不再继续生成同一高难追问。
- 模型返回 `raise_difficulty` 但 state 显示连续不会时，应被 guardrail 修正。
- 模型返回非法 action 时，仍走 normalize/fallback。
- 触发话题切换时，`triggerRules` 包含 `topic_shift` 或 `topic_lock_guardrail`。

### 11.3 路由集成测试

需要覆盖：

- `/api/interview/next-question` 在重复问题场景下返回不同 prompt。
- 返回体中 `agentDecision` 包含触发规则。
- `AgentDecisionLog` 写入 state_json 和 decision_json。
- 旧前端请求不传新字段时仍能正常工作。

## 12. 推荐实现顺序

本阶段建议拆成三轮实现，避免一次改太大。

### 第一轮：状态分析增强

目标：

- 增强 `analyze_answer_history`。
- 增加 `topicLock` 或相近结构。
- 补充状态层测试。

涉及文件：

- `backend_python/agent_state.py`
- `backend_python/interview_agent.py`
- `tests/test_agent_state.py`
- `tests/test_interview_agent.py`

### 第二轮：决策 guardrail 增强

目标：

- 增强 `build_fallback_decision`。
- 增加“模型决策被规则修正”的逻辑。
- 补充决策层测试。

涉及文件：

- `backend_python/interview_agent.py`
- `tests/test_interview_agent.py`

### 第三轮：路由和日志闭环

目标：

- 确保 `/api/interview/next-question` 返回字段兼容。
- 确保 Agent 日志记录 guardrail 和 topic shift。
- 补充路由集成测试。

涉及文件：

- `backend_python/routes/interview.py`
- `backend_python/agent_logging.py`
- `tests/test_interview_agent_route.py`
- `tests/test_agent_logging.py`

## 13. 面试表达

可以这样讲：

```text
我们的 Agent 不是简单让大模型自由生成下一题，而是先构造 Agent State，里面包含历史问答、上一轮回答质量、三类 RAG 召回质量、剩余轮次和当前模式。

然后 Agent 会输出结构化 Decision，例如继续深挖、降难度、切换话题或结束面试。

为了避免模型机械追问，我在 Agent 层加入了质量控制规则：连续弱回答检测、重复问题检测、话题锁定检测和 guardrail 修正。

比如候选人连续三轮答不上来时，coach 模式会先解释概念并切到更基础的问题；interview 模式会保留压力，但不会无限卡同一个点。

同时每轮都会写入 Agent 决策日志，记录 state、decision、triggerRules、fallbackUsed 和 guardrailApplied，方便排查为什么这一轮这么问。
```

## 14. 成功标准

本阶段完成后，应满足：

- 后端测试全部通过。
- 连续答不上来的场景不会继续机械追问同一高难问题。
- 触发规则能写入 Agent 日志。
- coach/interview 模式策略差异更加明显。
- 不破坏现有前端使用。
- 不引入 LangGraph，但保留未来迁移空间。

