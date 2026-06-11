# AI 模拟面试系统下一阶段 Spec：RAG 工程化 V3 + 上线前工程化准备

## 1. 文档目的

本文档用于规划 AI 模拟面试系统的下一阶段开发。

上一阶段产品化 V2 已经完成：

- 训练中心。
- 管理员后台 MVP。
- Agent 读取训练任务。
- LangGraph 迁移预留文档。
- 后端全量测试通过。
- 前端 `.mjs` 测试通过。

下一阶段不急着直接上 LangGraph，也不马上做真实云服务器部署。

本阶段目标是把项目继续往两个方向推进：

```text
B：RAG 工程化 V3
A：上线前工程化准备
```

虽然文档是 A+B 合并 spec，但实现顺序建议是：

```text
先 B，后 A。
```

原因是用户当前目标是找 AI 应用开发岗，RAG 工程化能力比单纯部署更贴合岗位；但项目最终要上线，所以数据层、配置、部署准备也要同步规划。

## 2. 回答三个关键问题

### 2.1 做完这一步后，RAG 后续还要继续升级吗

要分阶段看。

完成本阶段 RAG 工程化 V3 后，RAG 就不再是“只做 MVP 能跑”的水平，而是可以作为实习项目亮点来讲。

本阶段完成后，应该具备：

```text
文档管理更清晰
metadata 更可用
检索质量可评估
管理员能观察知识库和日志
RAG case 能用于回归测试
检索链路能讲清楚
```

但如果以后要做生产级系统，RAG 仍然可以继续升级。

后续生产级增强包括：

```text
异步入库任务队列
OCR 和多格式文档解析
Qdrant / Milvus / pgvector 持久化向量库
多租户知识库权限
更复杂的 rerank 评估
自动化评测集
召回率、幻觉率、引用准确率监控
知识库版本回滚
灰度发布知识库
```

所以结论是：

```text
本阶段做完后，RAG 足够支撑找实习和项目讲解。
后续还可以继续升级，但那是生产级增强，不是当前必须补齐的基础能力。
```

### 2.2 我们是不是快要引入 LangGraph 了

是接近了，但不建议立刻把主流程迁移到 LangGraph。

当前已经具备 LangGraph 迁移前提：

```text
Agent State
ToolCalls
nodeTrace
observe_state
retrieve_context
select_action
generate_question
update_memory
fallback
guardrail
训练任务信号
```

这说明项目已经有状态图雏形。

但还差两件事：

```text
RAG 工程化要更稳定。
前后端产品边界要更清晰。
```

建议路线：

```text
先做 RAG 工程化 V3
再做上线前工程化准备
再做一次阶段性项目讲解
然后做 LangGraph POC
```

注意，这里的 LangGraph POC 不应该直接替换主流程。

第一版只做实验接口：

```text
/api/agent/langgraph-poc/next-question
```

或者只在测试里跑：

```text
observe_state -> retrieve_context -> select_action -> generate_question
```

这样既能证明你了解 LangGraph，又不会把当前稳定的主流程改坏。

### 2.3 什么时候统一做前端页面

统一前端页面应该放在：

```text
RAG 工程化 V3 后端接口稳定之后
真实部署之前
```

原因是：

```text
前端页面依赖后端数据结构。
如果 RAG 文档、评估 case、后台接口还在变化，提前大重构前端会反复返工。
```

建议节奏：

```text
第一步：先做本阶段 RAG 工程化 V3 和上线前准备。
第二步：再单独写“前端信息架构 V2 spec”。
第三步：把用户端和后台管理端拆得更清楚。
第四步：再考虑是否继续原生 JS，还是引入前端框架。
```

当前阶段不建议直接引入 React/Vue/Next.js。

更稳的说法是：

```text
先稳定业务和接口，再统一前端信息架构。
```

## 3. 本阶段总目标

本阶段目标是：

```text
把 RAG 从“能检索、能展示日志”升级为“具备知识库管理、metadata 过滤、质量评估、case 回归和上线前配置边界”的工程化模块。
```

同时补充上线前工程化准备：

```text
环境变量清单
数据库切换准备
日志目录和运行记录
部署 checklist
本地启动方式整理
生产配置边界说明
```

## 4. 非目标

本阶段不做：

- 不做真实云服务器部署。
- 不配置真实 Nginx。
- 不构建真实 Docker 镜像上线。
- 不引入 LangGraph / LangChain。
- 不重写前端为 React / Vue / Next.js。
- 不做复杂多租户权限。
- 不做完整运营后台。
- 不做支付系统。
- 不做大规模 UI 重构。
- 不替换当前 `/api/interview/next-question` 主流程。

如果开发中遇到这些需求，只记录到后续计划，不强行实现。

## 5. RAG 工程化 V3 设计

### 5.1 RAG 文档状态管理

当前 RAG 文档已经能新增和切片。

下一阶段建议增加更明确的文档状态：

```text
enabled
disabled
archived
```

第一版可以只落地：

```text
enabled / disabled
```

用途：

```text
enabled：参与检索。
disabled：保留文档，但不参与检索。
```

这样管理员可以临时停用质量差的知识库文档，而不是只能删除。

### 5.2 metadata filter

当前 metadata 已经存在，但还不够产品化。

下一阶段建议让检索支持基础 metadata filter：

```text
knowledgeBase
positionTag
difficulty
category
sourceType
enabled
```

用途：

```text
岗位知识库只召回当前岗位方向内容。
题库可以按难度或类别过滤。
管理员可以排查某个 category 的召回质量。
```

第一版不要做复杂查询语言，只做后端固定字段过滤。

### 5.3 RAG Evaluation Case 管理

当前已有一些 RAG evaluation 测试和 seed。

下一阶段建议把 evaluation case 产品化为可维护对象。

字段建议：

```text
id
name
query
knowledgeBase
expectedKeywords
expectedDocumentTitle
expectedMinHitCount
metadataFilter
createdAt
updatedAt
```

第一版可以先用 JSON 文件或数据库表，具体实现 plan 时再决定。

目标是让项目能讲清楚：

```text
我不是只凭感觉说 RAG 检索质量好，而是维护了一组评测 case，用 Hit@K、MRR 或关键词覆盖率做回归验证。
```

### 5.4 RAG 质量面板增强

当前已有 RAG 命中日志和 debug 面板。

下一阶段可以增强：

```text
按 retrieverName 统计命中数量
按 knowledgeBase 统计命中数量
展示最近低质量召回
展示 top query
展示 evaluation case 结果
展示 hitCount / quality / topScore
```

第一版以管理员后台只读为主，不做复杂图表。

### 5.5 RAG 日志可解释性增强

RAG 日志建议继续保留：

```text
queryText
retrieverName
retrievalMode
hitCount
hits_json
quality
usedInPrompt
createdAt
```

可以新增或派生：

```text
topScore
topTitle
matchedKeywords
metadataSummary
qualityLevel
```

注意：

```text
日志字段要服务调试，不要为了好看无限扩展。
```

## 6. 上线前工程化准备设计

### 6.1 环境变量整理

需要整理：

```text
DASHSCOPE_API_KEY
QWEN_MODEL
QWEN_VISION_MODEL
DASHSCOPE_EMBEDDING_MODEL
DASHSCOPE_RERANK_MODEL
SECRET_KEY
DATABASE_URL
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
LOG_LEVEL
```

输出：

```text
.env.example 更新
docs/deployment-preflight-checklist.md 更新
```

### 6.2 数据库切换准备

当前本地是 SQLite。

上线前建议准备 PostgreSQL 或 MySQL 切换说明。

本阶段不一定真实切换数据库，但要让项目具备：

```text
DATABASE_URL 配置说明
SQLite 和生产数据库差异说明
迁移注意事项
备份注意事项
```

### 6.3 Alembic 迁移整理

当前项目已经有 Alembic 设计。

下一阶段需要检查：

```text
当前 db_models.py 和迁移文件是否一致。
新增字段是否应该写 migration。
本地 SQLite 兼容补列和正式 migration 的边界。
```

原则：

```text
开发阶段可以有 SQLite compatibility。
上线阶段必须依赖 migration 管理表结构。
```

### 6.4 日志与运行目录

上线前需要明确：

```text
请求日志
错误日志
LLM 调用日志
RAG 日志
Agent 决策日志
```

哪些写数据库，哪些写文件，哪些只在控制台输出。

第一版目标：

```text
文档说清楚。
必要时补日志目录和配置项。
不做复杂监控系统。
```

### 6.5 部署 checklist

需要补充：

```text
启动命令
健康检查
环境变量检查
数据库连接检查
静态资源检查
模型 API key 检查
日志检查
回滚策略
```

本阶段不真实部署，但要让以后部署时有路线图。

## 7. 前端处理边界

本阶段不是统一前端大重构。

允许做：

```text
为了 RAG V3 必须新增的最小前端入口。
管理员后台里增加 RAG 质量只读区域。
训练中心或调试面板的小修小补。
```

不做：

```text
全站视觉重构。
引入前端框架。
拆成多个独立前端应用。
设计完整后台系统。
```

统一前端页面建议单独开下一份 spec：

```text
前端信息架构 V2：用户端 + 管理端 + 训练中心统一重构
```

## 8. LangGraph 处理边界

本阶段不引入 LangGraph。

但本阶段要保护后续迁移条件：

```text
Agent State 字段继续保持结构化。
nodeTrace 继续记录节点。
RAG 工具调用继续保持可观察。
训练任务信号继续保持独立字段。
```

本阶段完成后，下一阶段可以考虑：

```text
LangGraph POC spec
```

POC 范围建议：

```text
observe_state -> retrieve_context -> select_action -> generate_question
```

不要一上来迁移完整主流程。

## 9. 建议阶段拆分

### 阶段 1：RAG 文档状态与 metadata filter

目标：

```text
RAG 文档支持 enabled/disabled。
检索时默认只使用 enabled 文档。
检索支持基础 metadata filter。
```

输出：

```text
后端测试
必要前端小入口
中文学习文档
```

### 阶段 2：RAG Evaluation Case 管理

目标：

```text
维护一组可回归的 RAG 评测 case。
能运行评测并输出命中情况。
```

输出：

```text
评测 case 数据结构
评测 runner
pytest 覆盖
中文学习文档
```

### 阶段 3：RAG 质量后台面板增强

目标：

```text
管理员可以看到 RAG 文档、日志、低质量召回、评测结果摘要。
```

输出：

```text
admin RAG quality endpoint
前端只读面板
.mjs 测试
中文学习文档
```

### 阶段 4：上线前配置与数据库准备

目标：

```text
整理 env、数据库、Alembic、日志、启动命令、部署 checklist。
```

输出：

```text
.env.example 更新
deployment checklist 更新
数据库切换说明
中文学习文档
```

### 阶段 5：阶段性复盘与下一阶段选择

目标：

```text
决定下一步是前端信息架构 V2，还是 LangGraph POC，还是真实部署。
```

## 10. 验收标准

本阶段完成后，应满足：

```text
RAG 文档可以被禁用且不参与检索。
检索支持基础 metadata filter。
RAG evaluation case 可以被运行并产生可解释结果。
管理员后台能看到更清晰的 RAG 质量摘要。
上线前环境变量和数据库准备文档清晰。
没有引入 LangGraph / LangChain。
没有引入 React / Vue / Next.js。
没有破坏 /api/interview/next-question。
后端 pytest 通过。
前端 .mjs 测试通过。
新增中文学习文档。
更新 docs/pre-deployment-progress.md。
```

## 11. 面试表达

可以这样讲：

```text
在产品化 V2 后，我继续规划 RAG 工程化 V3。这个阶段的重点不是简单增加更多知识库内容，而是提升 RAG 的可管理性和可评估性。比如文档支持启用/禁用，检索支持 metadata filter，维护 evaluation case 做回归评估，后台能看到 RAG 质量摘要和低质量召回。这样我可以解释 RAG 为什么命中、命中质量如何、怎么持续优化。同时我也规划了上线前工程化准备，包括环境变量、数据库切换、Alembic 迁移和部署 checklist，为后续真实上线做准备。
```

## 12. 当前边界

本 spec 写完后，下一步应先写 implementation plan。

不要直接进入代码大改。

实现时继续遵循：

```text
先测试
再实现
每阶段写中文学习文档
每阶段更新进度文档
不做无关大重构
```
