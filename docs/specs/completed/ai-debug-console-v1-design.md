# AI Debug Console V1：RAG 召回链路与 LangGraph 决策链路可观测设计

## 1. 文档目的

本阶段用于设计 AI 模拟面试系统的下一轮核心增强：把已经存在的 RAG、Agent、LangGraph、日志和管理员后台能力串成一个可观察、可解释、可调试的闭环。

当前项目已经完成了多轮基础建设：

- RAG 侧已经具备文档管理、metadata、BM25、向量检索、hybrid search、rerank、评测、命中日志和质量解释。
- Agent 侧已经具备 Agent State、Tool Calls、Agent Decision、fallback、normalize、Agent Policy、nodeTrace、coach/interview 双模式。
- LangGraph 侧已经具备 POC、真实 RAG adapter、真实 Agent decision adapter、threadId、MemorySaver checkpoint 和旁路实验接口。
- 前端侧已经具备 Vue3 用户工作台、知识库页面、训练闭环、报告页和管理员后台。

因此，本阶段不再重复建设某一个单点能力，而是把一次 AI 面试问题生成过程拆成可观察链路，让管理员和开发者能回答：

```text
这一次为什么这样问？
RAG 到底召回了什么？
召回质量好不好？
Agent 为什么选择深挖、降难度、切话题或结束？
LangGraph 路径中每个节点做了什么？
fallback 有没有触发？
如果结果不好，应该补文档、改策略，还是改提示词？
```

## 2. 本阶段定位

本阶段名称：

```text
AI Debug Console V1
```

它不是普通的“日志列表”，而是面向 AI 应用开发的调试控制台。

它的核心价值是把黑箱 AI 调用拆成工程上可解释的链路：

```text
用户输入
-> 候选人档案 / 岗位 JD / 历史问答
-> 三类 RAG 召回
-> RAG 质量摘要
-> Agent State
-> Agent Policy
-> Agent Decision
-> LangGraph nodeTrace / checkpoint
-> 最终问题
-> 日志与诊断建议
```

完成后，项目在面试中可以表达为：

```text
我的项目不是只调用大模型生成面试题，而是做了一套 AI 应用调试链路。系统会记录 RAG 召回、Agent 状态、决策原因、兜底规则、LangGraph 节点轨迹和 checkpoint 摘要，管理员可以通过后台定位某次提问为什么发生，以及应该从知识库、策略层还是 prompt 层进行优化。
```

## 3. 非目标

本阶段明确不做以下内容：

- 不重写 RAG 检索算法。
- 不新增 OCR、Word、Excel、网页解析。
- 不引入新的向量数据库。
- 不把主面试接口强制替换成 LangGraph。
- 不删除 classic Agent。
- 不做真实 human-in-the-loop interrupt/resume。
- 不做 Docker、Nginx、VPS、域名、HTTPS 上线。
- 不做复杂 RBAC 和账号写操作。
- 不做大规模 UI 全站重构。

如果开发过程中遇到以上内容，只做预留说明，不进入本阶段实现范围。

## 4. 当前问题

虽然项目已经具备 RAG 和 Agent 工程化能力，但当前可观测性仍然分散：

- 管理员后台能看到 RAG 质量、RAG 文档和 Agent 决策日志，但用户理解成本偏高。
- RAG 命中日志、Agent 决策日志、LangGraph checkpoint 之间缺少统一入口。
- 某次面试问题为什么这样问，仍然需要开发者在多个接口和日志里手动拼接。
- LangGraph 目前是旁路能力，已经可以运行，但它的调试价值还没有充分展示到产品页面。
- RAG 低质量召回和 Agent 错误追问之间缺少关联解释。

本阶段要解决的是“链路可解释”问题，而不是继续堆功能。

## 5. 总体目标

本阶段完成后，管理员后台应新增或增强一个 AI 调试控制台能力，支持查看最近一次或最近若干次 AI 面试链路。

控制台至少能展示：

```text
一次请求的基础信息
RAG 召回摘要
RAG 质量诊断
Agent State 摘要
Agent Decision 摘要
Agent Policy 触发规则
fallback / normalize 状态
LangGraph nodeTrace
LangGraph checkpoint 摘要
诊断建议
```

其中“诊断建议”不是大模型生成的长篇报告，第一版可以用规则生成，例如：

```text
role_knowledge 命中为空 -> 建议补充岗位知识库文档
question_bank 命中弱 -> 建议补充题库或优化 query rewrite
candidate_memory 命中为空 -> 建议检查候选人档案或历史问答是否写入
fallbackUsed=true -> 建议检查模型 decision JSON 是否稳定
连续 repeatedQuestion=true -> 建议检查 Agent topic shift 策略
checkpoint 不存在 -> 说明该请求未走 LangGraph 旁路或 threadId 不一致
```

## 6. 信息架构设计

管理员后台新增一个“AI 调试”区域，或者在现有管理员后台中新增一个独立分区。

建议页面结构：

```text
AI 调试概览
├── 最近请求列表
├── 单次链路详情
│   ├── 请求摘要
│   ├── RAG 召回链路
│   ├── Agent 决策链路
│   ├── LangGraph 执行链路
│   └── 诊断建议
└── 空状态 / 错误状态 / 权限状态
```

### 6.1 最近请求列表

用于帮助管理员快速选择一条记录。

第一版字段建议：

```text
时间
用户
岗位 / 档案
agentMode
nextAction
difficulty
fallbackUsed
RAG 总命中数
LangGraph threadId
```

### 6.2 请求摘要

展示本次 AI 调用的基本上下文。

建议字段：

```text
requestId 或 logId
recordId
applicationProfileId
userId
agentMode
stage
roundCount
remainingRounds
lastQuestion
lastAnswerStatus
```

### 6.3 RAG 召回链路

展示三类 RAG 的命中情况：

```text
岗位知识库 RAG
题库 RAG
候选人画像 RAG
```

每类 RAG 展示：

```text
retrieverName
hitCount
qualityLevel
top hits
matched keywords
metadata
queryVariants
rerank explanation
```

第一版不要求展示所有原文，避免页面过载。优先展示标题、摘要、score 和命中原因。

### 6.4 Agent 决策链路

展示 Agent 为什么做出下一步动作。

建议字段：

```text
nextAction
stage
difficulty
focus
reason
policyReasons
triggerRules
tools
shouldExplainBeforeAsk
shouldAskUserChoice
requiresHumanReview
fallbackUsed
normalizedFields
```

重点不是展示 JSON 原文，而是把英文枚举转成中文解释：

```text
deepen -> 继续深挖
lower_difficulty -> 降低难度
shift_topic -> 切换话题
end_interview -> 结束面试
fallbackUsed=true -> 已启用兜底规则
```

### 6.5 LangGraph 执行链路

展示 LangGraph 旁路工作流的可观察信息。

建议展示：

```text
threadId
checkpoint exists
checkpoint roundCount
lastAction
lastQuestion
nodeTrace
```

nodeTrace 第一版展示节点名称、状态和摘要即可：

```text
observe_state
analyze_answer
retrieve_context
apply_policy
select_action
generate_question
update_memory
```

如果某次请求没有走 LangGraph，则显示：

```text
本次请求未启用 LangGraph 旁路。当前主流程仍由 classic Agent 执行。
```

这句话很重要，因为它能避免用户误解“有 LangGraph 代码就等于所有请求都跑 LangGraph”。

## 7. 后端设计

本阶段优先复用已有表和接口，不急着新建复杂数据表。

### 7.1 优先复用的数据来源

可复用模块：

```text
backend_python/routes/admin.py
backend_python/routes/agent.py
backend_python/routes/rag.py
backend_python/routes/langgraph_agent.py
backend_python/agent_logging.py
backend_python/rag_logging.py
backend_python/rag_explain.py
backend_python/rag_quality.py
backend_python/langgraph_agent/checkpoint.py
backend_python/langgraph_agent/service.py
```

可复用数据：

```text
AgentDecisionLog.state_json
AgentDecisionLog.decision_json
RAG hit logs
RAG quality summary
LangGraph checkpoint summary
```

### 7.2 新增或增强接口

建议新增管理员只读接口：

```text
GET /api/admin/ai-debug/recent
GET /api/admin/ai-debug/{trace_id}
```

第一版也可以不新增独立表，trace_id 可使用最近 AgentDecisionLog 的 id。

`GET /api/admin/ai-debug/recent` 返回最近链路摘要。

`GET /api/admin/ai-debug/{trace_id}` 返回单次链路详情，包括：

```json
{
  "summary": {},
  "rag": {},
  "agent": {},
  "langgraph": {},
  "diagnostics": []
}
```

### 7.3 诊断建议生成

第一版用规则实现，不调用大模型。

规则示例：

```text
如果 roleKnowledge.hitCount == 0:
  诊断：岗位知识库没有命中，可能缺少岗位相关文档。

如果 questionBank.qualityLevel == "weak":
  诊断：题库召回质量偏弱，建议补充题库样例或检查 query rewrite。

如果 fallbackUsed == true:
  诊断：模型决策输出不稳定，系统已用 fallback 兜底。

如果 repeatedQuestion == true:
  诊断：Agent 存在重复追问风险，建议检查 topic shift 策略。
```

## 8. 前端设计

本阶段前端优先改 Vue3 管理员后台，不改旧版原生页面。

建议涉及文件：

```text
frontend/src/api/admin.ts
frontend/src/stores/admin.ts
frontend/src/pages/app/AdminPage.vue
frontend/src/pages/app/admin-page.test.ts
```

如果页面继续膨胀，可新增组件：

```text
frontend/src/components/admin/AiDebugPanel.vue
frontend/src/components/admin/RagTracePanel.vue
frontend/src/components/admin/AgentDecisionPanel.vue
frontend/src/components/admin/LangGraphTracePanel.vue
```

### 8.1 UI 风格

保持当前 Vue3 极简、干净、偏产品化的风格。

页面不应直接堆 JSON，而应优先展示中文解释。

JSON 原文可以折叠展示，作为调试细节。

### 8.2 交互设计

第一版交互建议：

```text
左侧或上方：最近 AI 请求列表
右侧或下方：选中请求详情
详情内使用分区：RAG / Agent / LangGraph / 诊断建议
```

移动端可以降级为纵向卡片布局。

## 9. 测试策略

继续遵循测试驱动。

### 9.1 后端测试

建议新增测试：

```text
tests/test_admin_ai_debug.py
```

覆盖：

- 普通用户不能访问 AI Debug 接口。
- 管理员可以访问最近 AI 请求列表。
- 单次详情包含 summary、rag、agent、langgraph、diagnostics。
- fallbackUsed=true 时生成兜底诊断建议。
- RAG 空召回时生成补充知识库建议。
- 无 LangGraph checkpoint 时返回清晰解释，而不是报错。

### 9.2 前端测试

建议新增或扩展：

```text
frontend/src/pages/app/admin-page.test.ts
frontend/src/stores/admin.test.ts
```

覆盖：

- 管理员后台显示 AI 调试入口。
- 最近请求列表能渲染。
- 选中请求后显示 RAG、Agent、LangGraph 三个分区。
- fallback、空召回、无 checkpoint 能显示中文解释。
- 分页、空状态和错误状态不破坏现有账号管理区域。

### 9.3 回归测试

每轮完成后至少运行：

```text
python -m pytest tests/test_admin_ai_debug.py -q
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

阶段结束时运行：

```text
python -m pytest -q
npm.cmd run test
npm.cmd run build
```

并用浏览器验证：

```text
http://127.0.0.1:5173/vue/app/admin
```

桌面端和移动端都要检查。

## 10. 分阶段实现建议

### 阶段 1：后端 AI Debug 只读聚合接口

目标：

- 新增管理员只读接口。
- 聚合 AgentDecisionLog、RAG 摘要、LangGraph checkpoint 摘要。
- 生成第一版 diagnostics。

验收：

- 管理员可查。
- 普通用户 403。
- 没有 LangGraph checkpoint 不报错。
- 诊断建议可读。

### 阶段 2：Vue3 管理员后台 AI Debug 面板

目标：

- 在管理员后台新增 AI 调试区域。
- 展示最近请求列表。
- 展示选中请求详情。
- 把英文枚举转成中文解释。

验收：

- 页面不直接堆原始 JSON。
- RAG / Agent / LangGraph 信息能分区展示。
- 移动端不横向溢出。

### 阶段 3：链路关联增强

目标：

- 让 RAG 命中、Agent decision、LangGraph checkpoint 尽量通过 traceId、recordId、threadId 或 logId 关联。
- 如果暂时无法强关联，要在 UI 中明确标注“推断关联”或“未关联”。

验收：

- 开发者能从一次请求追到对应的决策和召回。
- 不因为缺少某一段日志导致整页失败。

### 阶段 4：学习文档与面试表达

目标：

- 新增中文学习文档，解释 AI Debug Console 的工程价值。
- 总结面试表达。

建议文档：

```text
docs/learning/18-AI调试控制台如何串起RAG-Agent-LangGraph.md
```

## 11. 风险与约束

### 11.1 日志关联不完整

当前历史数据可能没有统一 traceId。第一版可以先做“尽力关联”：

```text
优先 logId
其次 recordId
其次 threadId
最后按时间近似
```

如果是近似关联，前端必须显示说明，不能伪装成强一致关联。

### 11.2 页面信息过载

AI 调试数据天然复杂。第一版要避免把所有 JSON 一口气铺出来。

推荐层次：

```text
先看中文摘要
再看关键字段
最后按需展开 JSON
```

### 11.3 LangGraph 不是主流程

当前主面试流程仍以 classic Agent 为主。LangGraph 是旁路实验链路。

前端和文档必须明确这一点，避免误导：

```text
classic Agent：当前稳定主流程
LangGraph：可迁移工作流与 checkpoint 验证链路
```

## 12. 面试表达目标

完成本阶段后，你应该能这样讲：

```text
我在项目里做了 AI Debug Console，用来解决 AI 应用黑箱问题。一次面试问题生成不是只看最终模型输出，而是把用户档案、岗位 JD、历史问答、三类 RAG 召回、RAG 质量摘要、Agent State、Agent Policy、Agent Decision、fallback 状态、LangGraph nodeTrace 和 checkpoint 摘要串起来展示。

这样当面试官追问“为什么系统问了这个问题”时，我可以从 RAG 是否命中、Agent 是否判断用户答不上来、是否触发降难度或切话题、LangGraph 节点是否正常执行这几个角度解释。这个能力本质上是 AI 应用工程化里的可观测性和可调试性。
```

如果面试官问为什么不直接把主流程切到 LangGraph：

```text
我没有直接替换主流程，因为主流程已经承载真实面试、历史记录、训练任务和报告生成。直接替换风险太高。所以我先把 LangGraph 做成旁路工作流，接真实 RAG、真实 Agent Decision 和 checkpoint，验证稳定后再考虑 agentRuntime=classic/langgraph 的灰度切换。
```

## 13. 当前执行建议

下一步应先写 implementation plan：

```text
docs/plans/active/ai-debug-console-v1.md
```

再按测试驱动执行：

```text
后端测试
-> 后端聚合接口
-> 前端 store/API 测试
-> 管理员后台 AI Debug 面板
-> 浏览器验证
-> 学习文档
-> 全量测试
```

本 spec 写完后，不要直接复制旧的 completed plan 执行。必须基于本 spec 新写 plan。
