# Admin Observability UX V3 设计文档

更新时间：2026-06-20

## 1. 阶段定位

上一阶段 `Admin & Report Productization V2` 已经把管理员强制下线、AI 调试 tabs、RAG/Agent dashboard 和报告出题依据做成可演示能力。但公网测试继续暴露出一个更深的问题：

```text
后台已经能展示很多诊断信息，但信息组织仍然偏“日志墙”，管理员每次定位问题都要上下翻很久。
```

本阶段目标不是继续堆更多日志，也不是重做数据库模型，而是把后台从“技术日志展示页”升级为“按一次面试链路组织的诊断工作台”。

阶段名称：

```text
Admin Observability UX V3
```

简历价值：

```text
在 AI 模拟面试系统上线后，基于真实公网使用反馈，将 RAG 召回日志、Agent 决策日志、LLM 请求链路和面试报告按用户、投递档案、面试记录、问题轮次进行聚合展示，构建可观测性诊断工作台，提升 AI 系统问题定位效率和后台可读性。
```

## 2. 当前问题

### 2.1 强制下线确认弹窗按钮样式缺陷

公网截图显示“取消”右侧的确认按钮是空白按钮。代码层确认按钮文案存在：

```vue
<button data-testid="confirm-force-logout">确认下线</button>
```

根因是页面样式使用了未定义 token：

```css
background: var(--color-primary);
color: #fff;
```

项目实际 design token 是 `--color-accent`，没有 `--color-primary`。浏览器无法解析背景色时，白色文字落在白底按钮上，看起来像空白按钮。

### 2.2 RAG 质量诊断仍然像列表堆叠

当前后台虽然有总览卡片和知识库质量分布，但下方明细仍然是按技术模块展开：

- RAG 质量诊断一段。
- Agent 决策日志一段。
- RAG 文档概览一段。
- AI 调试控制台一段。

管理员要回答“某一次面试为什么问出这道题”时，需要在多个区域之间来回翻。

### 2.3 Agent 决策日志缺少业务归属

Agent 日志现在能展示动作和原因，但缺少更自然的归属路径：

```text
哪个用户？
哪个投递档案？
哪一次面试？
哪一轮问题？
最后生成了哪份报告？
```

这导致日志虽然存在，但演示时很难讲成“我可以追踪一次面试从 RAG 到 Agent 到报告的完整链路”。

### 2.4 AI 调试详情仍偏开发者视角

AI 调试 tabs 已经解决“一股脑铺开”的问题，但入口仍然是“最近 AI 请求”。更符合管理员心智的入口应该是：

```text
先选一次面试/报告
再看这次面试每一轮问题的 RAG、Agent、LangGraph、LLM 请求
```

## 3. 总体目标

完成后后台应该从：

```text
按技术模块展示很多日志
```

升级为：

```text
按用户 / 档案 / 面试记录 / 问题轮次组织诊断链路
```

管理员打开后台后，默认先看到少量结论：

- 最近面试是否正常完成。
- 空召回和弱相关集中在哪些知识库。
- fallback 和降难度主要发生在哪些面试。
- 哪些用户/档案需要补资料。

点开一条面试记录后，再进入详情：

```text
面试概览
-> 每轮问题
-> 该轮 RAG 召回
-> Agent 决策
-> LangGraph/LLM trace
-> 报告和训练任务结果
```

## 4. 范围

### 4.1 要做

1. 修复确认下线按钮样式
   - 把 `--color-primary` 改成项目已定义的 `--color-accent`。
   - 增加回归测试，避免再次引用未定义 token。

2. 后台信息架构调整
   - 保留平台概览、账号管理、系统配置。
   - 将 RAG 质量诊断、Agent 决策日志、AI 调试控制台合并成“诊断工作台”区域。
   - 诊断工作台默认展示摘要，不默认展开长日志。

3. 新增“面试诊断列表”
   - 后台新增一个以面试记录为单位的列表。
   - 每行展示：
     - 用户邮箱
     - 投递档案名称或岗位
     - 面试时间
     - 报告状态
     - RAG 健康状态
     - Agent fallback 次数
     - 问题轮次数
   - 支持按用户、档案、状态筛选。

4. 新增“面试诊断详情”
   - 点击某次面试后，在右侧详情区或抽屉中展示：
     - 面试摘要
     - 每轮问题列表
     - 每轮问题的 RAG 命中摘要
     - 每轮问题的 Agent 动作
     - 每轮问题的诊断建议
   - 原始 JSON 仍保留，但放到最后的“开发排查”tab，默认折叠。

5. 按现有字段做轻量聚合
   - 优先使用现有字段：
     - `user_id`
     - `application_profile_id`
     - `request_type`
     - `trace_id`
     - `thread_id`
     - `created_at`
     - `InterviewRecord.application_profile_id`
     - report payload 中的问题列表和 RAG reasons
   - 如果无法可靠归属到某次面试，先标记为“未归属日志”，不强行伪装。

6. 后台可读性优化
   - 页面默认不展示所有日志明细。
   - 长列表分页或限制最近 N 条。
   - RAG/Agent/LLM 详情使用 tabs 或抽屉。
   - 每个诊断项用人话解释，不直接显示 raw 枚举值。

### 4.2 不做

本阶段不做：

- 不重做数据库表关系。
- 不重写 RAG 检索算法。
- 不引入 Qdrant / pgvector。
- 不做全站 UI 重构。
- 不做完整 APM / Prometheus / Grafana。
- 不做完整多租户审计系统。
- 不把所有历史日志强行迁移成完美链路。

## 5. 产品设计

### 5.1 后台主导航结构

管理员后台建议分成 4 个主要区块：

```text
平台概览
账号管理
诊断工作台
系统配置
```

其中“诊断工作台”内部再分 tabs：

```text
[面试诊断] [知识库健康] [Agent 行为] [AI 请求] [开发排查]
```

默认打开“面试诊断”。

### 5.2 面试诊断列表

列表行示例：

```text
候选人：demo@example.com
档案：Python 后端实习 / RAG 项目
时间：2026-06-20 21:35
轮次：5 题
报告：已生成
RAG：2 高相关 / 1 弱相关 / 1 空召回
Agent：fallback 1 次，降难度 1 次
[查看诊断]
```

空状态：

```text
暂无可诊断的面试记录。完成一次模拟面试并生成复盘后，这里会展示 RAG 和 Agent 链路。
```

### 5.3 面试诊断详情

详情区结构：

```text
面试诊断详情

总览：
- 候选人、档案、岗位、面试时间、报告状态
- RAG 健康：高相关 / 弱相关 / 空召回
- Agent 行为：继续深挖 / 降低难度 / fallback

逐题链路：
1. 问题文本
   - 出题依据
   - RAG 命中：岗位知识库 2 条，题库 1 条，候选人画像 0 条
   - Agent 动作：继续深挖
   - 诊断：岗位知识库弱相关，建议补充 chunk 标题

2. 问题文本
   ...
```

每一题可以展开，不默认全展开。

### 5.4 知识库健康

从当前 RAG 质量诊断中抽离为独立 tab：

```text
知识库健康
- 总请求数
- 空召回数
- 弱相关数
- 未进入 prompt 数
- 按 knowledgeBase 分布
- 最近问题样例
```

默认只展示 Top 3 诊断，点击“查看全部”再展开。

### 5.5 Agent 行为

从当前 Agent 决策日志中抽离为独立 tab：

```text
Agent 行为
- 总决策次数
- fallback 次数
- 降低难度次数
- 切换话题次数
- 继续深挖次数
- 最近决策摘要
```

每条最近决策要显示“归属面试”。如果归属不到面试，明确显示：

```text
未归属到具体面试记录
```

### 5.6 AI 请求

保留当前 AI 调试控制台能力，但入口变成辅助视图：

```text
AI 请求
- 最近 trace 列表
- 总览 / RAG / Agent / LangGraph / 诊断 / 原始日志 tabs
```

区别是：如果从某次面试进入，则只展示该面试相关 trace；如果从全局进入，则展示最近 trace。

## 6. 数据和 API 设计

### 6.1 优先不新增核心业务表

本阶段优先新增聚合 API，不新增核心业务表：

```text
GET /api/admin/observability/interviews
GET /api/admin/observability/interviews/{record_id}
```

### 6.2 面试诊断列表响应

```json
{
  "items": [
    {
      "recordId": 12,
      "userId": 3,
      "userEmail": "demo@example.com",
      "applicationProfileId": 5,
      "profileTitle": "Python 后端实习",
      "createdAt": "2026-06-20T21:35:00",
      "questionCount": 5,
      "reportStatus": "ready",
      "ragSummary": {
        "goodCount": 2,
        "weakCount": 1,
        "emptyCount": 1
      },
      "agentSummary": {
        "fallbackCount": 1,
        "lowerDifficultyCount": 1,
        "deepenCount": 2
      }
    }
  ],
  "total": 1
}
```

### 6.3 面试诊断详情响应

```json
{
  "recordId": 12,
  "overview": {
    "userEmail": "demo@example.com",
    "profileTitle": "Python 后端实习",
    "createdAt": "2026-06-20T21:35:00",
    "reportStatus": "ready"
  },
  "turns": [
    {
      "turnIndex": 1,
      "question": "在 RAG 命中日志中，你会查看哪个字段来区分 BM25 和向量召回？",
      "answer": "我会看 retrieval_mode...",
      "ragSummary": [
        {
          "knowledgeBase": "role_knowledge",
          "label": "岗位知识库",
          "hitCount": 2,
          "qualityLabel": "高相关"
        }
      ],
      "agentDecision": {
        "actionLabel": "继续深挖",
        "reason": "候选人回答提到了字段，但没有说明排查路径。"
      },
      "diagnostics": [
        "题库命中较弱，建议补充 RAG 日志字段相关题目。"
      ],
      "traceIds": [101]
    }
  ],
  "unlinkedLogs": {
    "ragLogCount": 2,
    "agentLogCount": 1
  }
}
```

### 6.4 是否需要新增字段

第一版先不新增字段。如果聚合中发现 `created_at + user_id + application_profile_id` 无法稳定把日志归到某次面试，再进入 V3.1，补轻量字段：

```text
interview_record_id
turn_index
```

优先补到：

- `RagRetrievalLog`
- `AgentDecisionLog`

但这不是 V3 第一版的前置条件。

## 7. 验收标准

### 7.1 按面试组织

- 管理员后台存在“诊断工作台”。
- 默认展示“面试诊断”。
- 面试诊断列表以 `InterviewRecord` 为单位，而不是以散日志为单位。
- 每条面试记录能看到用户、档案、时间、轮次、RAG 健康、Agent 行为。

### 7.2 详情可读

- 点击某次面试后能看到逐题链路。
- 每题默认只展示摘要，可展开查看 RAG/Agent/trace。
- 原始 JSON 不默认展示。
- 无法归属的日志明确显示“未归属”，不假装属于某次面试。

### 7.3 页面不再日志墙

- RAG 质量诊断不默认展示全部明细。
- Agent 决策日志不默认展示全部明细。
- 长列表有分页、限制数量或“查看全部”。
- 管理员不用连续上下滚动很久才能定位一次面试。

### 7.4 样式缺陷修复

- 强制下线确认弹窗的确认按钮显示“确认下线”。
- 按钮背景使用项目已定义 token。
- 测试覆盖未定义 token 回归。

## 8. 测试策略

后端：

```bash
python -m pytest tests/test_admin_observability.py -q
python -m pytest tests/test_admin_ai_debug.py tests/test_admin_routes.py -q
python -m pytest -q
```

前端：

```bash
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts src/stores/admin.test.ts src/api/admin.test.ts
npm.cmd run test
npm.cmd run build
```

部署配置：

```bash
docker compose --env-file .env.production.example config --quiet
```

公网 smoke：

```text
1. 管理员登录后台。
2. 打开账号管理，点击强制下线，确认弹窗两个按钮均有可见文字。
3. 打开诊断工作台，默认看到面试诊断列表。
4. 点击某次面试，确认详情按逐题链路展示。
5. 切换知识库健康、Agent 行为、AI 请求、开发排查 tabs。
6. 确认长日志不再默认全部铺开。
```

## 9. 实施顺序

1. 先修确认按钮样式缺陷。
2. 写面试诊断聚合 API 测试。
3. 实现 `/api/admin/observability/interviews` 列表。
4. 实现 `/api/admin/observability/interviews/{record_id}` 详情。
5. 前端 store/API 接入。
6. 管理员后台重组为“诊断工作台”tabs。
7. 做公网 smoke。

## 10. 风险和降级

- 如果日志无法可靠归属到某次面试，不要强行归属，先展示“未归属日志”。
- 如果详情接口性能较慢，列表只返回摘要，详情按 record id 懒加载。
- 如果现有 report payload 中缺少逐题 answer 或 question，详情中显示“历史记录缺少该字段”，不报错。
- 如果 V3 第一版仍然太大，可以先交付：
  - 按面试记录的诊断列表
  - 单次面试详情总览
  - 原有 AI debug tabs 作为详情中的 trace 入口

