# Admin & Report Productization V2 设计文档

更新时间：2026-06-20

## 1. 阶段定位

上一阶段 `Production UX & Auth Hardening V1` 已经把 Redis session、管理员强制下线、报告依据去重、训练筛选和 AI 调试聚合等底层能力接上，但公网验证暴露出一个关键问题：

```text
工程能力已经存在，但用户和演示者肉眼感受到的产品化变化不够明显。
```

本阶段目标不是继续堆新技术栈，也不是重做 RAG 或数据库关系，而是把已经落地的能力做成“看得见、点得明白、讲得清楚”的产品形态。

阶段名称：

```text
Admin & Report Productization V2
```

## 2. 当前问题

### 2.1 强制下线像“假按钮”

管理员页面已经出现“强制下线”按钮，但当前体验存在明显缺口：

- 点击前没有确认，用户不知道操作后果。
- 点击后没有 loading、成功或失败反馈。
- 旧版登录态的 access token 可能没有 `sid`，管理员踢人后不一定立刻失效。
- 管理员不知道踢掉了几个 session / refresh token。
- 被踢用户侧没有稳定、友好的“你已被管理员下线”提示。

因此它虽有后端能力，但演示时像一个没有闭环的按钮。

### 2.2 AI 调试控制台仍然像日志堆叠

当前 AI 调试控制台虽然出现了“总览 / RAG 召回 / Agent 决策 / 诊断建议 / 原始日志”等文字，但它更像标题，不是真正的 tabs：

- 内容仍然在一个页面里向下堆叠。
- 用户无法只看 RAG、只看 Agent 或只看原始日志。
- 最近 AI 请求、RAG 召回、LangGraph、诊断建议之间视觉权重不清楚。
- 演示时很难一句话说明“这个后台在帮助我定位什么问题”。

### 2.3 RAG 质量诊断、Agent 决策日志、RAG 文档概览仍然偏原始

后台已有 RAG 质量诊断、Agent 决策日志、RAG 文档概览，但仍接近工程日志列表：

- 缺少 dashboard 总览：总量、空召回、弱相关、高相关、最近问题。
- 缺少可读分组：按知识库、质量标签、请求类型聚合。
- 缺少“下一步该做什么”的诊断建议。
- RAG 文档概览没有突出 ready chunk、embedding 模型、知识库覆盖情况。

### 2.4 报告页“出题依据”仍然太像 RAG reason

报告页标题已经从“为什么这样问”改为“出题依据”，但内容仍然偏内部解释：

- 文案仍像直接展示 RAG reason。
- 部分依据和题目关联不够直观。
- 没有把“简历 / JD / 岗位知识 / 题库 / 历史回答”翻译成用户能理解的理由。
- 看起来像改了名字，但解释质量没有明显提升。

## 3. 总体目标

完成后，项目应达到：

```text
管理员后台：从日志堆叠变成可演示的诊断 dashboard。
AI 调试详情：从分区标题变成真正 tabs，用户一次只看一个维度。
强制下线：从像假按钮变成有确认、有反馈、能验证的安全操作。
报告页：出题依据从 RAG 原始解释变成面向候选人的人话说明。
```

简历价值：

```text
在 AI 模拟面试系统上线后，基于真实公网演示反馈，对管理员后台可观测性、RAG 诊断体验、JWT + Redis session 强制下线闭环和报告解释质量进行产品化重构；将内部日志和检索链路聚合为可读 dashboard，提升系统可演示性、可诊断性和安全可控性。
```

## 4. 范围

### 4.1 要做

1. 强制下线产品化
   - 管理员点击“强制下线”前出现确认弹窗。
   - 按钮有 loading 状态，避免重复点击。
   - 成功后显示“已下线该用户，撤销 X 个会话 / Y 个 refresh token”。
   - 失败后显示可读错误。
   - 被踢用户刷新或继续请求时清 token 并跳登录页。
   - 对无 `sid` 的旧 access token 做明确兼容策略：在 session 鉴权开启后，缺少 `sid` 的 access token 视为需要重新登录。

2. AI 调试控制台真 tabs
   - 最近 AI 请求列表保留在左侧。
   - 右侧详情区改为真正 tabs：
     - 总览
     - RAG 召回
     - Agent 决策
     - LangGraph
     - 诊断建议
     - 原始日志
   - 默认只展示“总览”。
   - 点击 tab 后只展示该 tab 的内容。
   - 原始日志默认折叠，只在“原始日志”tab 内查看。

3. 管理员后台 dashboard 化
   - RAG 质量诊断改为总览卡片 + 聚合列表：
     - 总日志数
     - 高相关数
     - 弱相关数
     - 空召回数
     - 未用于 prompt 数
   - 按知识库展示质量分布：
     - 候选人画像
     - 题库
     - 岗位知识库
   - Agent 决策日志展示最近动作分布：
     - 继续深挖
     - 降低难度
     - 切换主题
     - fallback
   - RAG 文档概览突出：
     - ready 文档数
     - ready chunk 数
     - embedding 模型
     - 每个 knowledgeBase 的覆盖情况

4. 报告页出题依据人话化
   - 不直接把 RAG reason 原样作为主解释。
   - 把依据聚合成 1 段候选人能理解的话：
     - “这题来自 JD 对 xxx 的要求”
     - “结合你上一轮回答中 xxx 没讲清楚”
     - “参考了岗位知识库/题库中的 xxx”
   - RAG 命中来源作为次级列表，最多 3 条。
   - 如果依据弱相关，显示轻量提示：“本题主要根据当前档案和面试上下文生成，知识库命中较弱。”
   - 不展示明显内部化字段名作为主文案。

5. 文档同步
   - 更新 `docs/roadmap/current-state.md` active spec。
   - 更新 `docs/plans/README.md` active spec。
   - 本阶段完成后再归档。

### 4.2 不做

本阶段不做：

- 不重做数据库表关系。
- 不重写 RAG 检索算法。
- 不引入 Qdrant / pgvector。
- 不全站 UI 重构。
- 不新增复杂 RBAC。
- 不做多设备管理完整页面。
- 不做监控告警系统。
- 不把后台做成完整运营平台。

## 5. 产品设计

### 5.1 强制下线交互

账号管理表格中每个非当前管理员用户显示“强制下线”。

点击后弹窗：

```text
确认强制下线该用户？

用户：demo@example.com
操作后，该用户当前登录态会失效，需要重新登录。

[取消] [确认下线]
```

确认后：

```text
按钮状态：下线中...
成功提示：已下线 demo@example.com，撤销 1 个会话、1 个 refresh token。
失败提示：强制下线失败：<可读错误>
```

被踢用户侧：

```text
当前登录会话已失效，请重新登录。
```

### 5.2 AI 调试详情 tabs

布局：

```text
AI 调试控制台

左侧：最近 AI 请求列表
右侧：详情

[总览] [RAG 召回] [Agent 决策] [LangGraph] [诊断建议] [原始日志]
```

总览 tab：

```text
请求类型：interview / next_question
模型状态：正常 / fallback
RAG 总命中：30
主要动作：降低难度
质量摘要：候选人画像高相关，岗位知识库弱相关
一句话诊断：本轮问题主要由候选人上一轮回答缺口触发，RAG 提供辅助依据。
```

RAG 召回 tab：

```text
候选人画像：命中 4 条，高相关，出现 4 次
题库：命中 13 条，高相关，出现 4 次
岗位知识库：命中 13 条，弱相关，出现 4 次
```

Agent 决策 tab：

```text
动作：降低难度
原因：候选人上一轮对日志字段具体名称回答不出，agent 降低难度。
难度：basic
fallback：否
```

LangGraph tab：

```text
Runtime：langgraph_mainline
Quality Gate：通过
Checkpoint：已保存
执行节点：observe_state -> retrieve_context -> select_action -> generate_question
```

诊断建议 tab：

```text
岗位知识库弱召回
岗位知识库召回质量偏弱，建议补充题库样例或优化 chunk 标题。
出现 6 次
```

原始日志 tab：

```text
折叠 JSON，仅用于开发排错。
```

### 5.3 Dashboard 化后台区域

RAG 质量诊断：

```text
[总日志 105] [高相关 80] [弱相关 15] [空召回 10] [未入 Prompt 6]

知识库质量分布
候选人画像：高相关 20 / 弱相关 3 / 空召回 2
题库：高相关 40 / 弱相关 2 / 空召回 1
岗位知识库：高相关 20 / 弱相关 10 / 空召回 7

主要诊断
1. 岗位知识库弱召回出现 6 次
2. 候选人画像为空出现 3 次
3. query rewrite 后仍无命中出现 2 次
```

Agent 决策日志：

```text
[总决策 29] [fallback 2] [降低难度 7] [继续深挖 15] [切换主题 5]

最近决策
继续深挖：候选人回答可追问
降低难度：候选人缺少基础字段认知
```

RAG 文档概览：

```text
[文档 6] [Ready chunk 15] [Embedding embedding-3] [知识库 2 类]

role_knowledge：ready 7 chunks
question_bank：ready 8 chunks
candidate_profile：暂无 ready chunks
```

### 5.4 报告页出题依据

当前“出题依据”板块改成：

```text
出题依据

这道题围绕 RAG 日志字段定位展开，因为岗位 JD 要求你理解检索增强生成链路，而你上一轮回答没有说清楚空召回时应查看哪些日志字段。系统参考了岗位知识库和题库中的相关材料，用来检查你能否把理论落到实际排查步骤。

参考来源
- 岗位知识库：RAG Agent 与 LangGraph 项目知识
- 题库：PostgreSQL、Redis、Celery 生产化职责
- 候选人画像：Python 后端开发实习生
```

如果 RAG 弱相关：

```text
出题依据

这道题主要根据你的投递档案、岗位 JD 和上一轮回答生成。当前知识库命中较弱，因此系统更多依赖面试上下文来追问。
```

## 6. 数据和 API 设计

### 6.1 不新增核心业务表

本阶段优先复用现有数据：

- `AgentDecisionLog`
- `RagRetrievalLog`
- `RagDocument`
- `RagChunk`
- `RefreshToken`
- Redis session keys
- report payload 中的 `decisionSummary` / `ragReasons`

只在必要时新增 API 返回字段，不做数据库迁移。

### 6.2 后端聚合建议

管理员 dashboard 可在现有 admin API 中增加聚合字段：

```json
{
  "summary": {
    "totalLogCount": 105,
    "goodCount": 80,
    "weakCount": 15,
    "emptyRecallCount": 10,
    "unusedInPromptCount": 6
  },
  "knowledgeBaseSummary": [
    {
      "knowledgeBase": "role_knowledge",
      "label": "岗位知识库",
      "goodCount": 20,
      "weakCount": 10,
      "emptyCount": 7,
      "readyChunkCount": 7
    }
  ],
  "diagnosticSummary": [
    {
      "title": "岗位知识库弱召回",
      "message": "建议补充题库样例或优化 chunk 标题。",
      "count": 6
    }
  ]
}
```

强制下线 API 保持：

```text
POST /api/admin/users/{user_id}/force-logout
```

返回：

```json
{
  "ok": true,
  "revokedSessions": 1,
  "revokedRefreshTokens": 1
}
```

补充约束：

```text
如果 access token 缺少 sid，且后端已启用 session 鉴权，则返回 session_revoked，要求重新登录。
```

## 7. 验收标准

### 7.1 强制下线

- 点击按钮出现确认弹窗。
- 确认后按钮进入 loading。
- 成功后显示撤销会话数和 refresh token 数。
- 被踢用户刷新页面或请求接口后跳回登录页。
- 旧版无 `sid` access token 在 session 鉴权开启后不再继续访问受保护接口。

### 7.2 AI 调试控制台

- 详情区域使用真正 tabs。
- 默认只显示“总览”tab 内容。
- 点击 RAG / Agent / LangGraph / 诊断建议 / 原始日志后，只显示对应内容。
- 原始 JSON 不再默认出现在总览或 RAG 区域。
- RAG 召回和诊断建议不重复刷屏。

### 7.3 Dashboard

- RAG 质量诊断有总览卡片和知识库质量分布。
- Agent 决策日志有动作统计和最近决策摘要。
- RAG 文档概览显示 ready chunk、embedding 模型和 knowledgeBase 覆盖。
- 后台用户能在 10 秒内看出“主要问题在哪里”。

### 7.4 报告页

- “出题依据”主段落是候选人能读懂的人话。
- RAG 命中来源作为次级参考来源展示。
- 弱相关依据不会伪装成强解释。
- 不把内部字段名作为主解释。

## 8. 测试策略

后端：

```bash
python -m pytest tests/test_auth.py tests/test_admin_users.py tests/test_admin_ai_debug.py -q
python -m pytest tests/test_question_reviews.py -q
python -m pytest -q
```

前端：

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
npm.cmd run test -- src/pages/app/report-page.test.ts
npm.cmd run test -- src/api/client.test.ts src/stores/admin.test.ts src/app.test.ts
npm.cmd run test
npm.cmd run build
```

部署配置：

```bash
docker compose --env-file .env.production.example config --quiet
```

公网手动 smoke：

```text
1. 管理员登录后台。
2. 打开 AI 调试控制台，切换每个 tab。
3. 查看 RAG 质量诊断 dashboard。
4. 查看 Agent 决策日志 dashboard。
5. 查看 RAG 文档概览。
6. 用测试用户登录另一个浏览器。
7. 管理员强制下线测试用户。
8. 测试用户刷新页面，应回到登录页。
9. 打开一份报告，确认出题依据是人话解释。
```

## 9. 推荐实施顺序

1. 强制下线闭环产品化
   - 最容易验证真假，直接回应“按钮像假的”问题。
2. AI 调试控制台真 tabs
   - 立刻改善“一股脑堆在一起”的观感。
3. RAG / Agent / 文档 dashboard
   - 把后台从日志页面变成诊断页面。
4. 报告页出题依据人话化
   - 提升候选人侧和 HR 演示观感。
5. 全量验证和 VPS 更新
   - 确认公网实际看到变化。

## 10. 非目标提醒

如果开发中出现以下想法，应放到后续阶段：

- “顺手重写 RAG 检索算法”
- “顺手引入 pgvector”
- “顺手重做整个后台 UI”
- “顺手做完整多设备登录管理”
- “顺手做完整监控告警”

本阶段只解决一个问题：

```text
让已经存在的能力在公网演示中真正看得见、点得通、讲得清楚。
```

