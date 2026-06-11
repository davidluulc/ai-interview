# 前端产品化重构 V2 Spec

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段开发：前端产品化重构 V2。

当前项目已经完成了较多后端、RAG、Agent 和训练闭环能力，但前端仍以单页堆叠为主。用户、管理员和开发调试视角混在同一个页面里，导致已有工程化能力没有被清晰地产品化展示。

本阶段目标不是继续重复开发 RAG 底层检索链路，也不是重写 Agent 编排链路，而是把已经完成的 RAG 工程化和 Agent 工程化能力承接到更清晰的产品界面里。

## 2. 当前项目状态

当前项目真实状态以 `docs/roadmap/current-state.md` 为准。

已经阶段性完成：

- 用户注册、登录、token 刷新和退出登录。
- 投递档案和历史复盘。
- 三类 RAG：岗位知识库、题库、候选人画像。
- RAG 文档生命周期、权限边界、metadata filter、query rewrite、hybrid search、rerank、评估指标、质量面板和 VectorStore 抽象。
- Interview Orchestrator Agent：Agent State、ToolCalls、Agent Decision、fallback、guardrail、nodeTrace、coach/interview 双模式。
- weakTag、训练模板、训练任务和训练中心。
- 管理员后台 MVP。
- 前端 `.mjs` 测试和后端 pytest 测试。

当前主要短板：

- 前端仍是 `index.html + app.js + styles.css` 的大单页结构。
- 用户端、训练中心、知识库管理、RAG 调试、Agent 日志和管理员后台混在一起。
- RAG 和 Agent 的工程化能力存在，但普通用户不容易理解。
- 管理员能看到后台数据，但信息层级和排版仍偏 MVP。
- `app.js` 继续膨胀，后续维护成本上升。
- 移动端可用，但页面密度和层级还不够产品化。

## 3. 总目标

本阶段总目标：

```text
把 AI 模拟面试系统从“功能堆叠的单页 demo”
升级为“信息架构清晰、RAG/Agent 可解释、用户训练闭环明确的面试训练工作台”。
```

完成后用户应能清楚完成：

```text
登录
-> 建立投递档案
-> 开始模拟面试
-> 理解本题为什么这样问
-> 查看报告和训练建议
-> 进入训练中心继续练习
```

管理员应能清楚查看：

```text
系统概览
-> 用户和面试数据
-> RAG 文档
-> RAG 低质量召回
-> Agent 决策日志
```

## 4. 非目标

本阶段明确不做：

- 不改后端 API 合约。
- 不重写 RAG 检索链路。
- 不重写 Agent Orchestrator。
- 不引入 React、Vue、Next.js。
- 不直接引入 LangGraph / LangChain。
- 不做 Docker、Nginx、云服务器真实上线。
- 不真实接入 Qdrant / pgvector。
- 不引入 Redis / Celery。
- 不开发复杂商业化功能，例如支付、短信、邮箱验证码。
- 不做大规模数据库结构重构。

如果实现过程中发现以上需求，只记录为后续阶段，不在本阶段强行落地。

## 5. 设计原则

### 5.1 保持原生前端

继续使用：

```text
index.html
styles.css
app.js
tests/*.mjs
```

不引入前端框架。

原因：

- 当前用户重点学习 Python 后端和 AI 应用工程。
- 引入框架会增加学习成本和迁移风险。
- 原生前端已经有测试基础，适合先做信息架构整理。

### 5.2 不破坏已有流程

以下流程必须保持兼容：

- 登录 / 注册 / token 刷新。
- 投递档案创建和选择。
- 简历上传入口。
- `/api/interview/next-question`。
- `/api/interview/report`。
- 历史复盘保存和加载。
- RAG 文档管理。
- RAG debug 和日志。
- Agent 日志。
- 训练任务。
- 管理员后台入口。

### 5.3 普通用户和开发调试分层

同一份 RAG / Agent 数据要分两层展示：

普通用户层：

```text
这道题为什么问
参考了哪些资料
你哪里薄弱
下一步建议怎么练
```

开发调试层：

```text
nodeTrace
toolCalls
retrievalQuality
queryVariants
rerankExplanation
fallback / guardrail
```

默认展示普通用户层，调试信息通过折叠面板展开。

### 5.4 先整理结构，再追求视觉细节

本阶段优先解决：

- 页面分区。
- 信息层级。
- 导航结构。
- 可读性。
- 移动端稳定性。

不追求一次性做成最终商业 UI。

## 6. 页面信息架构

### 6.1 顶层结构

建议把当前单页体验整理为 5 个主区域：

```text
1. 账号与档案
2. 面试训练工作台
3. 训练中心
4. 知识库与 RAG
5. 管理员后台
```

仍然可以是一个 HTML 文件，但视觉上要像多页面产品。

### 6.2 账号与档案

目标：

- 登录状态清楚。
- 投递档案入口清楚。
- 简历、岗位 JD、公司要求和目标岗位信息集中管理。

应展示：

- 当前用户。
- 登录 / 注册 / 退出。
- 投递档案列表。
- 当前选中档案。
- 简历上传入口。
- 岗位匹配入口。

本阶段不新增复杂用户中心。

### 6.3 面试训练工作台

目标：

```text
这是用户进入系统后的核心工作区。
```

应包含：

- 当前投递档案摘要。
- coach / interview 模式切换。
- 面试轮次进度。
- 当前问题。
- 用户回答输入框。
- 提交回答按钮。
- 本题解释区域。
- 报告入口。

本题解释区域应承接 RAG 和 Agent：

- Agent 为什么问这题。
- 本题参考了哪些 RAG 资料。
- 是否根据 weakTag 或训练任务生成。
- 如果触发降难度或换话题，用中文说明。

### 6.4 训练中心

目标：

```text
承接面试报告里的 weakTags 和训练任务。
```

应包含：

- 训练任务列表。
- 当前任务详情。
- weakTag 标签。
- 掌握度。
- 推荐训练问题。
- 开始 / 完成 / 归档操作。

本阶段可以优化展示，不强制新增后端字段。

### 6.5 知识库与 RAG

目标：

```text
把 RAG 从调试功能变成可管理、可解释的产品能力。
```

应包含：

- RAG 文档列表。
- 文档创建表单。
- 文档详情。
- 文档状态：enabled / disabled / archived。
- 可见性：private / public。
- 知识库类型：role_knowledge / question_bank / candidate_memory。
- chunk 数量。
- duplicateChunkCount。
- metadata 摘要。
- 当前检索上下文。
- 最近命中日志。

RAG 命中解释应展示：

- 命中的知识库。
- 命中文档标题。
- 命中词。
- 质量等级。
- hitCount。
- queryVariants / matchedQueryVariant。
- rerankScore / rankChange / rerankExplanation。

如果某些字段后端暂未返回，前端应优雅降级，不显示 `undefined`。

### 6.6 管理员后台

目标：

```text
让管理员能从系统角度观察用户、RAG 和 Agent。
```

应包含：

- 系统概览卡片。
- 用户只读列表。
- RAG 文档只读列表。
- RAG 日志只读列表。
- RAG 低质量召回面板。
- Agent 日志只读列表。

RAG 低质量召回面板应更清楚展示：

- empty_recall：空召回。
- weak_recall：弱召回。
- unused_in_prompt：未进入 prompt。
- recommendation：建议动作。

Agent 日志应更清楚展示：

- nextAction。
- focus。
- reason。
- fallbackUsed。
- guardrailApplied。
- nodeTrace。
- toolCalls。

## 7. RAG 能力承接

本阶段不重复实现 RAG 底层能力。以下能力已经存在，应在前端产品化时承接展示：

- 文档生命周期。
- 文档可见性。
- metadata filter。
- query rewrite。
- hybrid search。
- rerank 解释。
- evaluation case 和指标。
- 低质量召回面板。
- VectorStore 抽象。

### 7.1 用户侧 RAG 解释

用户不需要看到一大段技术 JSON。用户侧应转译成：

```text
本题参考了岗位知识库中的「xxx」。
题库命中了「xxx」类型问题。
候选人画像显示你之前在「xxx」上薄弱。
```

### 7.2 开发侧 RAG 调试

开发侧可展开查看：

- raw hits。
- matchedTerms。
- queryVariants。
- rerankExplanation。
- retrievalQuality。

### 7.3 管理侧 RAG 质量

管理员侧应看到：

- 哪些 query 经常空召回。
- 哪些文档可能 metadata 不完整。
- 哪些召回没有进入 prompt。
- 后续应该补什么知识。

## 8. Agent 能力承接

本阶段不重复实现 Agent V3 编排。以下能力已经存在，应在前端产品化时承接展示：

- Agent State。
- ToolCalls。
- Agent Decision。
- nodeTrace。
- fallback。
- guardrail。
- topic shift。
- coach / interview 双模式。
- weakTag 训练模板。
- selectedTrainingTask。

### 8.1 用户侧 Agent 解释

用户侧应展示：

```text
本轮选择：降低难度 / 继续深挖 / 切换话题 / 训练薄弱点。
原因：上一轮回答较弱，所以先拆小问题。
参考：岗位知识库命中 2 条，题库命中 1 条。
```

### 8.2 开发侧 Agent 调试

开发侧可展开：

- observe_state。
- analyze_answer。
- retrieve_context。
- select_weakness_strategy。
- select_training_template。
- select_action。
- generate_question。
- update_memory。

每个节点展示：

- 输入摘要。
- 输出摘要。
- 是否 fallback。
- 耗时。
- 错误信息。

### 8.3 训练任务影响说明

当 Agent 读取训练任务或 weakTag 模板时，前端应尽量解释：

```text
本题来自你的薄弱点：RAG 质量评估。
系统建议你先练 Hit@K、MRR 和关键词覆盖率。
```

## 9. 前端模块化建议

当前仍保持一个入口文件，但可以逐步整理函数边界。

建议优先整理为以下逻辑区：

```text
auth state
application profile state
interview state
history state
training state
rag document state
rag debug state
agent log state
admin dashboard state
render helpers
api helpers
event binding
```

本阶段不强制拆成多个 JS 文件。若拆分，应先补测试，并确保浏览器加载路径稳定。

## 10. 测试策略

### 10.1 前端测试优先

本阶段主要改前端，所以优先写或更新 `.mjs` 测试。

重点测试：

- 导航或区域切换不丢状态。
- 登录状态下显示正确入口。
- 非管理员不显示后台入口。
- RAG 文档卡片展示 status、visibility、chunk 统计。
- RAG 命中解释不出现 `undefined`。
- Agent 决策卡片展示 nextAction、focus、reason。
- nodeTrace 和 toolCalls 可折叠展示。
- 训练中心任务展示和操作保持可用。
- 移动端不出现横向溢出。

### 10.2 后端测试

本阶段原则上不改后端 API。

如果发现某个前端必须字段后端缺失，应先评估是否能前端降级处理。只有在确实影响产品解释时，才补小型后端字段和对应 pytest。

### 10.3 验证命令

每轮结束运行：

```powershell
python -m pytest -q
```

如果改了前端：

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

涉及页面体验时，还要验证：

```text
http://127.0.0.1:8000/
```

桌面端和移动端都要检查：

- 页面能打开。
- 无明显重叠。
- 无横向滚动。
- 无 `undefined`。
- 控制台无明显 error。

## 11. 阶段拆分

### 阶段 0：现状基线

目标：

- 运行当前测试基线。
- 截取或记录当前页面主要问题。
- 确认不改后端 API。

产出：

- 测试基线记录。
- 前端重构风险清单。

### 阶段 1：信息架构和导航整理

目标：

- 将页面整理成清晰主区域。
- 用户能知道自己在哪个功能区。
- 管理员入口、训练中心、知识库入口不再混乱。

优先文件：

- `index.html`
- `styles.css`
- `app.js`
- 前端 `.mjs` 测试。

### 阶段 2：面试训练工作台产品化

目标：

- 当前问题、回答区、轮次进度、本题解释、模式切换更清晰。
- Agent 决策摘要在工作台中以用户可理解方式展示。
- RAG 依据以简洁说明展示。

### 阶段 3：知识库与 RAG 面板产品化

目标：

- RAG 文档管理更清晰。
- RAG 命中解释更可读。
- RAG 日志和 debug 面板分层展示。

### 阶段 4：训练中心和历史复盘优化

目标：

- 训练任务更像用户下一步行动列表。
- 历史报告、逐题复盘和训练建议关系更清楚。

### 阶段 5：管理员后台产品化

目标：

- 后台概览、用户、RAG 质量、Agent 日志分区更清楚。
- 低质量召回和 Agent 决策日志从“数据列表”变成“可排查面板”。

### 阶段 6：移动端和整体验收

目标：

- 桌面端布局稳定。
- 移动端无横向溢出。
- 关键流程可用。
- 全量测试通过。

## 12. 学习文档要求

本阶段可以新增一篇精简学习文档：

```text
docs/learning/06-前端产品化重构如何承接RAG和Agent能力.md
```

内容只写：

- 为什么本阶段不是重写 RAG / Agent。
- 前端信息架构怎么拆。
- RAG 可解释如何展示。
- Agent 可观测如何展示。
- 面试时怎么说“我把工程能力产品化了”。

不要继续写很多零散学习文档。

## 13. 质量闸门

进入下一阶段前必须满足：

- `python -m pytest -q` 通过。
- 所有前端 `.mjs` 测试通过。
- 如果改页面，完成浏览器桌面端和移动端验证。
- `docs/roadmap/project-progress.md` 更新本轮进度。
- 不破坏登录、面试、报告、历史、训练任务、RAG 文档、管理员后台基础流程。

## 14. 风险与应对

### 风险 1：前端改动范围过大

应对：

- 分阶段改。
- 每轮只改一个主区域。
- 保留测试。
- 不一次性推倒重写。

### 风险 2：app.js 继续膨胀

应对：

- 先整理函数边界。
- 必要时再拆文件。
- 拆文件前先确认浏览器加载和测试方案。

### 风险 3：RAG / Agent 展示过于技术化

应对：

- 默认给用户看中文解释。
- 技术字段放到调试折叠区。

### 风险 4：误以为本阶段要重写底层

应对：

- 每轮开发前重读本文档非目标。
- RAG / Agent 底层只做小修，不做主线重构。

## 15. 完成后的项目表达

本阶段完成后，可以这样描述项目升级：

```text
在完成 RAG 和 Agent 工程化后，我继续做了前端产品化重构。
这一步不是单纯美化页面，而是把已有的 RAG 命中解释、Agent 决策日志、训练任务和管理员后台重新组织成清晰的产品工作台。
普通用户能看到为什么系统这么问、自己薄弱点是什么、下一步该怎么练；管理员能看到 RAG 低质量召回和 Agent 决策日志。
这样项目不只是后端能力堆叠，而是形成了可使用、可观察、可迭代的 AI 面试训练产品。
```

## 16. 下一步

本文档写完后，应继续写 implementation plan：

```text
docs/plans/active/frontend-productization-v2.md
```

实现时按 TDD 和小步迭代推进，不要一次性重写整个前端。
