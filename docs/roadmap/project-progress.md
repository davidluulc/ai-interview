# 上线部署前综合补强进度记录

## 后端生产化 V1：数据库适配 + Redis + Celery 进度

当前阶段目标：在本地继续默认 SQLite 的前提下，通过 `DATABASE_URL`、Redis 可选基础设施和 Celery eager 任务框架，为后续 PostgreSQL/Redis/Celery/Docker/Nginx 上线链路打基础。

已完成阶段性内容：

- 数据库配置生产化：
  - `backend_python/database.py` 新增 `build_connect_args`、`build_engine_options`、`describe_database_url`。
  - 本地 SQLite 继续使用 `check_same_thread=false`。
  - PostgreSQL/MySQL 风格 URL 可被描述为外部服务，并启用 `pool_pre_ping` 配置。
- Redis 基础设施：
  - `backend_python/redis_client.py` 新增 disabled fallback、Redis health、可选 Redis client。
  - `/api/health` 返回 Redis 状态，本地默认 `disabled`。
- Celery 异步任务框架：
  - 新增 `backend_python/celery_app.py`。
  - 新增 `backend_python/tasks/health.py` 的 `ping_task`。
  - 本地/测试默认 `CELERY_TASK_ALWAYS_EAGER=true`，不需要真实 worker。
- AI/RAG 异步任务预留：
  - 新增 `backend_python/task_status.py`。
  - 新增 `backend_python/tasks/rag_evaluation.py`。
  - 新增 `POST /api/rag/evaluation/tasks` 和 `GET /api/rag/evaluation/tasks/{task_id}`。
  - 当前先用内存状态模型和 eager task 跑通 taskId/status/result 闭环，不重构 RAG 底层。
- 新增学习文档：`docs/learning/11-PostgreSQL Redis Celery如何让后端走向生产化.md`。

阶段性验证记录：

```text
python -m pytest tests/test_database_config.py tests/test_database_migrations.py -q
10 passed in 0.27s

python -m pytest tests/test_redis_client.py tests/test_core_flows.py -q
8 passed, 1 warning in 1.14s

python -m pytest tests/test_celery_app.py -q
2 passed in 1.84s

python -m pytest tests/test_async_tasks.py tests/test_rag_evaluation_management.py -q
6 passed, 1 warning in 1.12s
```

最终验证记录：

```text
python -m pytest -q
269 passed, 1 warning in 37.32s

Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
通过，无失败输出
```

浏览器烟测：

- `http://127.0.0.1:8000/` 可打开。
- 页面标题为 `AI 模拟面试系统 MVP`。
- 面试工作台 DOM 存在。
- 页面未出现 `undefined`。
- 控制台无 error。

## 面试体验增强 V3 + LangGraph 深化进度

当前阶段目标：通过 `Agent Policy` 把面试体验规则从 classic Agent 和 LangGraph 旁路中抽出来，避免两套规则分叉。

已完成阶段性内容：

- 新增 `backend_python/agent_policy.py`，把连续弱回答、重复追问、话题锁、coach/interview 模式差异、人机协同预留字段抽成可测试策略。
- classic Agent 的 fallback / normalize 决策已带上 `policy`，Agent 决策摘要会展示策略原因。
- `agent_orchestrator.py` 已新增 `apply_policy` nodeTrace，便于在 Agent 日志中观察策略层。
- LangGraph 旁路已新增 `apply_policy` 节点，节点顺序变为 `observe_state -> analyze_answer -> retrieve_context -> apply_policy -> select_action -> generate_question -> update_memory`。
- LangGraph checkpoint summary 已记录 `policyRecommendedAction`、`shouldAskUserChoice`、`requiresHumanReview`、`policyReasons` 和 `policyTriggerRules`。
- 前端“为什么这样问”面板已轻量展示策略原因和 coach 模式提示。
- 新增学习文档：`docs/learning/10-Agent Policy如何连接面试体验和LangGraph.md`。

阶段性验证记录：

```text
python -m pytest tests/test_agent_policy.py tests/test_interview_agent.py tests/test_agent_orchestrator.py -q
26 passed in 0.41s

python -m pytest tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_graph_v2.py tests/test_langgraph_agent_checkpoint.py tests/test_langgraph_agent_state.py -q
12 passed, 1 warning in 0.24s

node tests/frontend_interview_flow.test.mjs
通过，无失败输出
```

最终验证记录：

```text
python -m pytest -q
258 passed, 1 warning in 33.88s

Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
通过，无失败输出
```

浏览器验证：

- 桌面端 `http://127.0.0.1:8000/`：页面可打开，`agentDecisionPanel` 和面试工作台 DOM 存在，未出现 `undefined`，控制台无 error。
- 移动端 390px：`scrollWidth=375`、`innerWidth=390`，无横向溢出，未出现 `undefined`，控制台无 error。

## 当前目标

根据 `docs/superpowers/specs/2026-06-10-pre-deployment-engineering-roadmap-design.md` 推进上线部署前综合补强。

## 阶段状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 阶段 0：项目体检与执行基线 | 已完成 | 已记录模块地图、测试基线和风险。 |
| 阶段 1A：RAG seed 与 evaluation case | 已完成 | 已新增 predeploy RAG/Agent/后端/部署相关 seed、题库和 evaluation case。 |
| 阶段 1B：RAG 指标与命中解释 | 已完成 | 已新增指标中文解释和 case 级别 insight。 |
| 阶段 1C：RAG 可观测前端增强 | 已完成 | `/api/rag/debug` 已返回 explanations，前端已展示 RAG 命中解释面板。 |
| 阶段 2A：Agent V3 设计与第一步 | 已完成阶段性版本 | 已新增 Agent V3 设计 spec、Agent 学习文档，并完成 `analyze_answer`、`generate_question`、`update_memory` 显式 nodeTrace。 |
| 阶段 3：面试训练闭环增强 | 已完成阶段性版本 | 已新增训练闭环学习文档，完成弱点标签标准化、候选人画像聚合，并补充前端“一键重练薄弱点”入口。 |
| 阶段 4：上线前工程化准备文档 | 已完成文档版 | 已新增上线部署前置知识文档和 deployment preflight checklist；未做真实部署。 |

## 阶段性学习产出

- `docs/learning/09-AI模拟面试系统阶段性项目讲解.md`：已新增，用于把当前项目从产品目标、后端结构、数据库关系、三类 RAG、Agent 工程化、训练闭环、日志测试、项目边界和面试表达完整串起来。

## 下一阶段设计文档

- `docs/superpowers/specs/2026-06-10-productization-v2-training-admin-langgraph-reserve-design.md`：已新增，用于规划“训练中心 + 管理后台 MVP + LangGraph 预留”的产品化 V2 阶段；当前仅完成 spec，尚未进入 implementation plan 和代码实现。
- `docs/superpowers/plans/2026-06-10-productization-v2-training-admin-langgraph-reserve.md`：已新增，用于按 TDD 分阶段执行产品化 V2。

## 产品化 V2 进度

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 阶段 0：设计确认与现状体检 | 已完成阶段性版本 | 已阅读产品化 V2 spec，完成 implementation plan，并确认本阶段不做 Docker/Nginx/云服务器上线、不直接引入 LangGraph。 |
| 阶段 1：用户角色与后台权限基础 | 已完成阶段性版本 | 已新增 `User.role`、SQLite 旧库补列、`require_admin_user`、认证响应 role、`/api/admin/summary` 和 `/api/admin/config`。 |
| 阶段 2：训练任务后端 | 已完成阶段性版本 | 已新增 `TrainingTask`、SQLite 兼容建表、训练任务 service、训练任务 API、从报告 weakTags 生成任务、开始/完成/归档任务接口。 |
| 阶段 3：用户端训练中心 | 已完成阶段性版本 | 已新增训练任务列表、详情、开始/完成/归档交互，并让一键重练薄弱点生成训练任务。 |
| 阶段 4：管理员后台 MVP | 已完成阶段性版本 | 已新增后台只读列表接口、管理员入口、后台统计卡片和用户/RAG/Agent 日志只读视图。 |
| 阶段 5：Agent 读取训练任务 | 已完成阶段性版本 | `next-question` 已读取高优先级低掌握度训练任务，并写入 `candidateTrainingTasks` 与 `selectedTrainingTask`。 |
| 阶段 6：LangGraph 迁移预留 | 已完成文档版 | 已新增自研 Agent 到 LangGraph 的迁移映射、checkpoint 与 human-in-the-loop 预留设计；未引入运行时依赖。 |

### 产品化 V2 阶段 1 验证记录

- 管理员权限聚焦测试：`python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py -q`，结果：`5 passed in 3.27s`。
- 历史记录鉴权回归：`python -m pytest tests/test_history_auth.py -q`，结果：`3 passed in 2.07s`。
- 前端 token 刷新回归：`node tests/frontend_auth_refresh.test.mjs`，结果：通过，无失败输出。

### 产品化 V2 阶段 2 验证记录

- 训练任务后端聚焦测试：`python -m pytest tests/test_training_tasks.py tests/test_training_task_generation.py -q`，结果：`6 passed in 2.30s`。

### 产品化 V2 阶段 3 验证记录

- 训练中心前端渲染测试：`node tests/frontend_training_center.test.mjs`，结果：通过，无失败输出。
- 训练任务操作测试：`node tests/frontend_training_actions.test.mjs`，结果：通过，无失败输出。
- 训练中心事件绑定测试：`node tests/frontend_training_events.test.mjs`，结果：通过，无失败输出。
- 面试流程与一键重练回归：`node tests/frontend_interview_flow.test.mjs`，结果：通过，无失败输出。
- 本阶段学习文档：`docs/learning/12-训练中心前端页面如何拆分.md`。

### 产品化 V2 阶段 4 验证记录

- 管理员后台后端聚焦测试：`python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py -q`，结果：`7 passed in 4.42s`。
- 后台入口权限前端测试：`node tests/frontend_admin_permissions.test.mjs`，结果：通过，无失败输出。
- 后台仪表盘前端测试：`node tests/frontend_admin_dashboard.test.mjs`，结果：通过，无失败输出。
- 本阶段学习文档：`docs/learning/13-管理员后台MVP如何设计.md`。

### 产品化 V2 阶段 5 验证记录

- Agent 训练任务接入测试：`python -m pytest tests/test_agent_training_tasks.py -q`，结果：`1 passed in 0.92s`。
- next-question 路由回归：`python -m pytest tests/test_agent_training_tasks.py tests/test_interview_agent_route.py -q`，结果：`7 passed in 3.06s`。
- 训练任务后端回归：`python -m pytest tests/test_training_tasks.py tests/test_training_task_generation.py -q`，结果：`6 passed in 2.39s`。
- 本阶段学习文档：`docs/learning/14-训练任务如何影响Agent决策.md`。

### 产品化 V2 阶段 6 验证记录

- LangGraph 迁移预留文档：`docs/learning/15-自研Agent如何迁移到LangGraph.md`。
- 文档占位词检查：`rg -n "T[O]DO|T[B]D|待[定]|占[位]|F[IX]ME" docs/learning/15-自研Agent如何迁移到LangGraph.md`，结果：无匹配。
- 本阶段没有安装 LangGraph / LangChain，没有改运行时依赖。

## 测试基线

| 类型 | 命令 | 结果 |
| --- | --- | --- |
| 后端 pytest | `python -m pytest -q` | `163 passed in 25.21s` |
| 前端 .mjs | `Get-ChildItem tests -Filter "*.mjs" \| ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }` | 通过，无失败输出 |
| 当前后端全量 | `python -m pytest -q` | `171 passed in 21.88s` |
| 当前前端全量 | `Get-ChildItem tests -Filter "*.mjs" \| ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }` | 通过，无失败输出 |
| 当前最终后端全量 | `python -m pytest -q` | `175 passed in 22.34s` |
| 当前最终前端全量 | `Get-ChildItem tests -Filter "*.mjs" \| ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }` | 通过，无失败输出 |
| 产品化 V2 后端全量 | `python -m pytest -q` | `203 passed in 28.06s` |
| 产品化 V2 前端全量 | `Get-ChildItem tests -Filter "*.mjs" \| ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }` | 通过，无失败输出 |

## 产品化 V2 浏览器验证

- 本轮启动本地 FastAPI 服务：`http://127.0.0.1:8000/`。
- 桌面端 Chrome headless 验证：`innerWidth=1258`，`scrollWidth=1243`，无横向溢出；训练中心和后台面板 DOM 存在；页面文本不包含 `undefined`。
- 移动端 Chrome headless 验证：`innerWidth=478`，`scrollWidth=463`，无横向溢出；训练中心和后台面板 DOM 存在；页面文本不包含 `undefined`。
- Codex 内置浏览器插件本轮连接时出现本地资源写入失败，因此使用本机 Chrome headless 完成等价页面渲染验证。

## 风险记录

- 当前工作区存在大量未跟踪和已修改文件，本轮不自动 commit。
- 本轮不做 Docker、Nginx、云服务器真实上线。
- 本轮不引入 LangGraph、LangChain、React、Vue 或 Next.js。
- 每个代码阶段必须先跑对应测试，再进入下一阶段。

## 下一步

阶段 1C 已完成，阶段 2A 已完成文档设计、`analyze_answer` 显式 nodeTrace、`generate_question` 显式 nodeTrace、`update_memory` deferred nodeTrace，并确认前端 Agent 日志可以展示 `nodeTrace` / `toolCalls`。阶段 3 已完成阶段性训练闭环增强：弱点标签标准化、候选人画像聚合和前端“一键重练薄弱点”入口均已落地。阶段 4 已完成文档版。下一步可以继续让 `next-question` 更明确地读取 `candidateProfile.frequentWeakTags`，或为不同 weakTags 配置固定训练模板。

阶段 1A 已补充一小批可验证的上线前工程化知识样例，覆盖：

- RAG query rewrite。
- chunk metadata。
- RAG 质量面板。
- Agent 与三类 RAG 协作。
- FastAPI 错误日志。
- 上线前工程化准备。

阶段 1A 验证命令：

```text
python -m pytest tests/test_pre_deployment_rag_v2.py tests/test_rag_knowledge_curriculum_v2.py tests/test_rag_evaluation_seed.py -q
```

结果：

```text
8 passed in 0.56s
```

阶段 1B 验证命令：

```text
python -m pytest tests/test_rag_evaluation_explanations.py tests/test_rag_evaluation.py -q
```

结果：

```text
13 passed in 0.04s
```

阶段 1C 后端验证命令：

```text
python -m pytest tests/test_rag_debug_quality.py tests/test_rag_explain.py tests/test_rag_quality.py -q
```

结果：

```text
11 passed in 1.68s
```

阶段 1C 前端验证命令：

```text
node tests/frontend_rag_quality.test.mjs
node tests/frontend_workbench_layout.test.mjs
```

结果：通过，无失败输出。

阶段 1C 浏览器验证：

- `http://127.0.0.1:8000/` 桌面端 1280px：页面可打开，无 `undefined`，无横向溢出，控制台无 error。
- 登录本地临时测试账号后点击“查看当前检索上下文”：RAG 命中解释面板可显示，包含质量摘要、命中标题和命中词。
- 移动端 390px：RAG 命中解释可显示，无 `undefined`，无横向溢出，控制台无 error。

阶段 1C 额外修复：

- 给 RAG 解释卡片、RAG 调试明细和统计卡片增加长文本断行保护，避免英文指标名、长邮箱、长用户名在移动端撑破页面。

阶段 2A 文档产出：

- `docs/superpowers/specs/2026-06-10-agent-engineering-v3-design.md`
- `docs/learning/04-Agent状态决策工具日志完整讲解.md`

阶段 2A 当前结论：

- 项目已具备 Agent V2 基础：`agent_state.py`、`agent_tools.py`、`agent_trace.py`、`agent_orchestrator.py`、`interview_agent.py`。
- 当前不急着引入 LangGraph，而是先补齐自研 Agent 的节点 trace。
- 已完成第一轮代码增强：`run_next_question_agent()` 的 `nodeTrace` 现在包含 `observe_state -> analyze_answer -> retrieve_context -> select_action`。
- 已补充前端测试：Agent 日志面板能展示 `analyze_answer`、`nodeTrace` 和 `toolCalls`。
- 已完成第二轮代码增强：`/api/interview/next-question` 生成最终问题后，会向 `nodeTrace` 追加 `generate_question` 节点，记录 stage、focus、stability 和 promptLength。
- 已完成第三轮代码增强：`/api/interview/next-question` 会向 `nodeTrace` 追加 `update_memory` 节点，当前状态为 `deferred`，表示只记录记忆更新意图，不在下一题接口直接写长期画像。

阶段 2A 第一轮验证命令：

```text
python -m pytest tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
23 passed in 0.06s
```

阶段 2A 后端全量验证：

```text
python -m pytest -q
```

结果：

```text
171 passed in 22.41s
```

阶段 2A 前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 2A Agent 日志前端验证：

```text
node tests/frontend_agent_logs.test.mjs
```

结果：通过，无失败输出。

阶段 2A 第二轮 Agent 节点验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
28 passed in 2.19s
```

阶段 2A 第二轮后端全量验证：

```text
python -m pytest -q
```

结果：

```text
171 passed in 22.11s
```

阶段 2A 第二轮前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 2A 第三轮 Agent 节点验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_agent_trace.py tests/test_agent_state.py tests/test_interview_agent.py -q
```

结果：

```text
28 passed in 2.17s
```

阶段 2A 第三轮后端全量验证：

```text
python -m pytest -q
```

结果：

```text
171 passed in 21.97s
```

阶段 2A 第三轮前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 3 文档产出：

- `docs/learning/05-AI模拟面试训练闭环怎么设计.md`

阶段 3 当前结论：

- 当前项目已经有训练闭环雏形：`questionReviews` 做逐题复盘，`trainingPlan` 做下一轮训练计划，历史记录和候选人画像 RAG 支撑长期训练记忆。
- 已完成弱点标签标准化：新增 `backend_python/training_tags.py`，报告返回的 `questionReviews[*].weakTags` 和 `trainingPlan.weakTopics[*].weakTags` 会携带稳定标签。
- 已完成候选人画像聚合：历史报告里的 `weakTags` 会进入 `memories[*].weakTags` 和 `candidateProfile.frequentWeakTags`。
- 已完成前端“一键重练薄弱点”入口：报告中的 `trainingPlan` 可以一键切换到学习辅导模式、快速训练强度，并把薄弱点写入下一轮 profile 上下文。
- 还没有完成训练计划直接影响下一轮问题优先级、不同 weakTags 固定训练模板等增强。
- 推荐下一步让 `next-question` 更明确地读取 `frequentWeakTags`，或补充 weakTags 到训练题模板的映射。

阶段 3 第一轮验证：

```text
python -m pytest tests/test_training_tags.py tests/test_question_reviews.py tests/test_history_auth.py tests/test_candidate_memory.py -q
```

结果：

```text
14 passed in 2.88s
```

阶段 3 第一轮后端全量验证：

```text
python -m pytest -q
```

结果：

```text
174 passed in 22.09s
```

阶段 3 第一轮前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 3 第二轮验证：

```text
python -m pytest tests/test_candidate_memory.py tests/test_training_tags.py tests/test_question_reviews.py tests/test_rag_debug_quality.py -q
```

结果：

```text
15 passed in 2.54s
```

阶段 3 第二轮后端全量验证：

```text
python -m pytest -q
```

结果：

```text
175 passed in 22.04s
```

阶段 3 第二轮前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 3 第三轮前端“一键重练薄弱点”验证：

```text
node tests/frontend_interview_flow.test.mjs
```

结果：通过，无失败输出。

阶段 3 第三轮前端全量验证：

```text
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：通过，无失败输出。

阶段 3 第三轮后端全量验证：

```text
python -m pytest -q
```

结果：

```text
175 passed in 22.57s
```

阶段 3 第三轮浏览器验证：

- `http://127.0.0.1:8000/` 桌面端 1280px：页面可打开，无 `undefined`，无横向溢出，控制台无 error。
- `http://127.0.0.1:8000/` 移动端 390px：页面可打开，无 `undefined`，无横向溢出，控制台无 error。
- 当前浏览器自动化工具的文本输入路径被虚拟剪贴板限制拦截，因此动态报告按钮点击由 `frontend_interview_flow.test.mjs` 覆盖。

阶段 4 文档产出：

- `docs/learning/06-上线部署前置知识与准备清单.md`
- `docs/deployment-preflight-checklist.md`

阶段 4 当前结论：

- 本阶段只做上线前准备文档，不进行真实 Docker / Nginx / 云服务器部署。
- 当前项目已具备 FastAPI、SQLAlchemy、Alembic、用户认证、RAG/Agent 日志和测试基础。
- 真正上线前仍需准备生产数据库、Nginx、HTTPS、日志轮转、备份、CORS 白名单、上传限制和监控。

最终浏览器验证：

- `http://127.0.0.1:8000/` 桌面端 1280px：页面可打开，无 `undefined`，无横向溢出，控制台无 error。
- `http://127.0.0.1:8000/` 移动端 390px：页面可打开，无 `undefined`，无横向溢出，控制台无 error。

## 阶段 5：候选人画像弱点驱动 Agent 决策 V1

状态：已完成阶段性版本。

本阶段目标是让 `candidateProfile.frequentWeakTags` 不只停留在候选人画像里，而是进入 Agent State，并通过 `weaknessStrategy` 影响 coach / interview 两种模式下的下一题策略。

已完成内容：

- 新增 `backend_python/weakness_strategy.py`，集中处理弱点标签标准化、弱点策略选择、coach / interview 模式差异和防死磕规则。
- `build_agent_state()` 已把 `candidateProfile.frequentWeakTags` 和 `weaknessStrategy` 写入 Agent State。
- `build_fallback_decision()` 和 `normalize_agent_decision()` 已保留并使用 `weaknessStrategy`。
- `nodeTrace` 已增加 `select_weakness_strategy` 节点，方便观察弱点策略的输入、输出和保护规则。
- `/api/interview/next-question` 的问题生成 payload 已把 `weaknessStrategy` 摘要写入 `questionStrategy`，同时保持接口兼容。
- `AgentDecisionLog.state_json` 能看到 `candidateProfile.frequentWeakTags`。
- `AgentDecisionLog.decision_json` 能看到 `weaknessStrategy` 和完整 `nodeTrace`。
- 新增学习文档：`docs/learning/07-候选人画像如何驱动Agent决策.md`。

局部验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_interview_agent.py tests/test_weakness_strategy.py -q
```

结果：

```text
28 passed in 2.50s
```

后端全量验证：

```text
python -m pytest -q
```

结果：

```text
183 passed in 21.48s
```

本阶段未改前端文件，因此未运行前端 `.mjs` 测试。

当前风险：

- `weaknessStrategy` 目前仍是轻量规则策略，没有引入真实的学习路径规划系统。
- `weakTags` 到固定训练题模板的映射尚未完成，后续可以做成更稳定的训练题库。
- 防死磕规则已经具备，但真实体验还需要通过多轮人工试用继续调参。

下一步建议：

- 继续做 weakTag 到训练模板 / 题库样例的映射，让系统能针对 `rag_quality`、`agent_state`、`backend_fastapi` 等薄弱点生成更稳定的问题。
- 或者先做一次阶段性项目讲解，把 Agent State、ToolCalls、RAG、weaknessStrategy、nodeTrace 和日志链路串成面试表达。

## 阶段 6：weakTag 训练模板系统 V1

状态：已完成阶段性版本。

本阶段新增 weakTag 到训练模板的映射，让 `weaknessStrategy.primaryWeakTag` 能生成 `trainingTemplateHint`，并进入 Agent Decision、questionStrategy、Agent 日志和 nodeTrace。

已完成内容：

- 新增 `backend_python/weakness_training_templates.py`，集中维护 6 个核心 weakTag 的训练模板。
- 已覆盖 `rag_quality`、`rag_retrieval`、`agent_state`、`backend_fastapi`、`database_modeling`、`project_storytelling`。
- 每个模板包含 coach / interview 问题、难度阶梯、答题要点、常见错误和 1 分钟表达模板。
- 新增 `get_training_template()` 和 `select_training_template_hint()`。
- Agent Decision 已包含 `trainingTemplateHint`。
- `nodeTrace` 已增加 `select_training_template` 节点。
- `/api/interview/next-question` 的 `questionStrategy` 已包含 `trainingTemplateHint`。
- AgentDecisionLog 的 `decision_json` 能保存 `trainingTemplateHint` 和完整 nodeTrace。
- 新增学习文档：`docs/learning/08-weakTag训练模板如何让Agent更会训练.md`。

局部验证：

```text
python -m pytest tests/test_interview_agent_route.py tests/test_agent_orchestrator.py tests/test_interview_agent.py tests/test_weakness_training_templates.py -q
```

结果：

```text
30 passed in 2.54s
```

后端全量验证：

```text
python -m pytest -q
```

结果：

```text
189 passed in 20.80s
```

本阶段未改前端文件，因此未运行前端 `.mjs` 测试。

当前风险：

- 训练模板仍是静态规则，没有做掌握度评分和训练路径持久化。
- 前端暂未做模板摘要的专项可视化，只能通过 Agent 调试 JSON 看到。
- 模板问题池还可以继续扩充，避免长期训练时问题重复。

下一步建议：

- 进入阶段性项目讲解 B，把 FastAPI、三类 RAG、Agent State、weaknessStrategy、trainingTemplateHint、nodeTrace、日志和测试串成一套可面试表达。
- 后续再考虑 weakTag 掌握度评分、专项训练页面和训练任务表。

## 阶段 7：生产级 RAG 工程化升级 - 文档生命周期与权限边界

状态：已完成阶段性版本。

本阶段开始执行生产级 RAG 工程化升级，优先补齐知识库文档的生命周期和权限边界。目标不是一次性接入 Qdrant、Celery、OCR 等重组件，而是先让当前 RAG 的资料边界可控、可解释、可测试。

已完成内容：

- `RagDocument` 增加 `status` 字段，支持 `enabled / disabled / archived`。
- `RagDocument` 增加 `visibility` 字段，支持 `private / public`。
- SQLite 兼容迁移已补充 `rag_documents.status` 和 `rag_documents.visibility`，并增加索引。
- RAG 文档创建接口支持传入 `visibility`，默认 `private`。
- RAG 文档序列化结果返回 `status` 和 `visibility`。
- 新增 `PATCH /api/rag/documents/{document_id}/status`，owner 可以停用或恢复自己的文档。
- BM25、vector、hybrid、hybrid_rerank 检索路径统一过滤：
  - 只召回 `enabled` 文档；
  - 当前用户可以召回自己的 private/public 文档；
  - 当前用户也可以召回其他用户的 public 文档；
  - 不能召回其他用户的 private 文档。
- RAG hit 结果增加 `documentStatus` 和 `documentVisibility`，方便后续日志和调试。
- 新增学习文档：`docs/learning/17-RAG文档生命周期和权限边界.md`。

局部验证：

```text
python -m pytest tests/test_rag_document_lifecycle.py tests/test_rag_documents.py tests/test_retrieval_service.py tests/test_rag_vector_retrieval.py tests/test_rag_hybrid_retrieval.py tests/test_rag_rerank_retrieval.py tests/test_interview_agent_route.py -q
```

结果：

```text
33 passed in 12.26s
```

本阶段暂未改前端页面，因此没有运行前端 `.mjs` 测试。

当前风险：

- `archived` 当前和 `disabled` 一样都是“不参与检索”，还没有独立的归档列表页面。
- 公共知识库目前是轻量实现，只有 `public` 可见性，没有引入组织、租户、角色级 ACL。
- 状态更新接口目前只做 owner 更新，管理员统一治理入口后续可以放到后台管理模块。

下一步建议：

- 继续做生产级 RAG 阶段 2：metadata filter，让检索可以按岗位、题目分类、难度、面试阶段过滤候选 chunk。
- 之后再做文档去重、chunk 去重、query rewrite、multi-query、hybrid 权重、rerank 解释和 RAG evaluation case 管理。

## 阶段 8：生产级 RAG 工程化升级 - metadata filter

状态：已完成阶段性版本。

本阶段补齐 metadata filter，让 RAG 不再只依赖文本相似度，而是可以先按业务字段过滤候选 chunk，再进行 BM25、vector、hybrid 或 rerank 排序。

已完成内容：

- 新增 `normalize_metadata_filter()`，统一处理 metadata filter 的字段名和空值。
- 新增 `chunk_matches_metadata_filter()`，支持按 chunk metadata 判断是否通过过滤。
- 支持的第一版过滤字段：
  - `positionTag`
  - `category`
  - `difficulty`
  - `interviewStage`
  - `source`
- `retrieve_chunks()` 增加 `metadata_filter` 参数。
- `retrieve_vector_chunks()` 增加 `metadata_filter` 参数。
- `retrieve_hybrid_chunks()` 和 `retrieve_hybrid_rerank_chunks()` 透传 `metadata_filter`。
- RAG hit 结果增加：
  - `metadataFilter`
  - `metadataMatch`
- `retrieve_role_context()` 会根据 `profile.positionTag` 传入岗位过滤条件。
- `retrieve_questions()` 会根据 `profile.positionTag` 和可选 `profile.difficulty` 传入题库过滤条件。
- 面试主流程中由 profile 推导出来的 filter 采用软过滤策略：优先过滤，若数据库空命中则回退到未过滤检索，以兼容早期未维护 metadata 的用户自建文档。
- 新增学习文档：`docs/learning/18-RAG元数据过滤与业务召回边界.md`。

局部验证：

```text
python -m pytest tests/test_rag_metadata_filter.py tests/test_rag_database_retrieval.py -q
```

结果：

```text
10 passed in 0.55s
```

当前风险：

- metadata filter 当前在 Python 层过滤，数据量大时应下推到数据库查询或向量库 filter。
- `interviewStage` 目前只支持底层显式传入，上层面试阶段到标准枚举的映射还可以继续增强。
- 当前还没有前端筛选控件，主要服务于面试主流程和后端检索质量。

下一步建议：

- 继续生产级 RAG 阶段 3：文档去重、chunk 去重和 chunk 统计。
- 后续结合 metadata filter 做低质量召回分析，例如“有 filter 但 hit_count=0”的场景。

## 阶段 9：生产级 RAG 工程化升级 - 文档去重和 chunk 统计

状态：已完成阶段性版本。

本阶段给 RAG 文档管理增加轻量去重能力。当前策略是“识别重复，不强行拦截上传”，为后续后台治理、低质量召回分析和知识库清理打基础。

已完成内容：

- `RagDocument` 增加 `content_hash` 字段，用于记录文档正文 hash。
- `RagDocument` 增加 `duplicate_chunk_count` 字段，用于记录当前文档内部重复 chunk 数量。
- `RagChunk` 增加 `chunk_hash` 字段，用于记录 chunk 内容 hash。
- `RagChunk` 增加 `is_duplicate` 字段，用于标记当前 chunk 是否是同文档内重复 chunk。
- SQLite 兼容迁移已补充以上字段和索引。
- RAG store 新增：
  - `normalize_hash_text()`
  - `compute_text_hash()`
  - `build_chunk_hash_records()`
- 创建文档时会计算 `contentHash`、`chunkHash` 和 `duplicateChunkCount`。
- 文档创建、列表、详情接口会返回 `contentHash` 和 `duplicateChunkCount`。
- chunk 详情接口会返回 `chunkHash` 和 `isDuplicate`。
- 新增学习文档：`docs/learning/19-RAG文档去重和chunk统计.md`。

局部验证：

```text
python -m pytest tests/test_rag_document_dedup.py tests/test_rag_documents.py tests/test_rag_document_lifecycle.py tests/test_rag_metadata_filter.py tests/test_rag_database_retrieval.py tests/test_interview_agent_route.py -q
```

结果：

```text
28 passed in 12.71s
```

当前风险：

- 当前只统计同一文档内部重复 chunk，跨文档重复治理还没有做成后台面板。
- 目前不阻止重复上传，后续需要结合管理员后台做“发现、确认、归档”的治理流程。
- content hash 使用文本规范化后的 SHA-256，能识别完全重复，但不能识别语义重复。

下一步建议：

- 继续生产级 RAG 阶段 4：query rewrite / multi-query，让系统不只用用户原始 query 检索，而是结合岗位、阶段、简历和弱点生成多路 query。
- 后续把重复文档统计接入后台质量面板，帮助管理员发现知识库污染。

## 阶段 10：生产级 RAG 工程化升级 - query rewrite / multi-query

状态：已完成阶段性版本。

本阶段新增规则版 query rewrite 和 multi-query 检索，让系统不再只用单条原始 query 召回资料，而是结合岗位、阶段、JD 和薄弱点生成多条 query variant。

已完成内容：

- 新增 `backend_python/query_rewrite.py`。
- 新增 `build_query_variants()`，支持生成：
  - `base`
  - `role`
  - `stage`
  - `weakness`
- 新增 `retrieve_multi_query_chunks()`：
  - 每条 query variant 单独检索；
  - 按 `chunkId` 合并结果；
  - 同一 chunk 多次命中时保留更高分；
  - hit 写入 `matchedQueryVariant` 和 `queryVariants`。
- 岗位知识库 RAG `retrieve_role_context()` 接入 multi-query。
- 题库 RAG `retrieve_questions()` 接入 multi-query。
- 保留 metadata filter 的软过滤回退策略。
- 新增学习文档：`docs/learning/20-query-rewrite和multi-query检索.md`。

局部验证：

```text
python -m pytest tests/test_rag_query_rewrite.py tests/test_rag_database_retrieval.py tests/test_rag_metadata_filter.py tests/test_rag_retrieval_logs.py tests/test_interview_agent_route.py -q
```

结果：

```text
28 passed in 6.77s
```

当前风险：

- 当前 query rewrite 是规则版，不调用大模型，因此表达扩展能力有限。
- `weakness` variant 目前需要调用方传入 weakTags，面试主流程里的弱点标签还可以进一步接入。
- 多路 query 会增加检索次数，后续数据量变大时需要控制 variant 数量和召回上限。

下一步建议：

- 继续生产级 RAG 阶段 5：hybrid search 权重配置和 rerank 解释。
- 后续可把 query rewrite 抽象成 Agent / LangGraph 的独立节点，支持 LLM rewrite、人审和 checkpoint。

## 阶段 11：生产级 RAG 工程化升级 - hybrid 权重和 rerank 解释

状态：已完成阶段性版本。

本阶段增强 hybrid search 和 rerank 的可配置性、可解释性，让 RAG 排序不再只是返回一个最终列表，而是能说明权重、重排前后排名和重排原因。

已完成内容：

- 新增 `normalize_hybrid_weights()`，支持 BM25 / vector 权重归一化。
- `merge_hybrid_hits()` 返回 `hybridWeights`。
- `retrieve_hybrid_chunks()` 支持 `hybrid_weights` 参数。
- `retrieve_hybrid_rerank_chunks()` 支持 `hybrid_weights` 参数。
- `retrieve_chunks()` 透传 `hybrid_weights`。
- `retrieve_multi_query_chunks()` 透传 `hybrid_weights`。
- `apply_rerank_results()` 新增：
  - `postRerankRank`
  - `rankChange`
  - `rerankExplanation`
- 新增学习文档：`docs/learning/21-hybrid权重和rerank解释.md`。

局部验证：

```text
python -m pytest tests/test_rag_hybrid_rerank_explain.py tests/test_rag_hybrid_retrieval.py tests/test_rag_rerank_retrieval.py tests/test_rag_query_rewrite.py tests/test_rag_retrieval_logs.py tests/test_interview_agent_route.py -q
```

结果：

```text
31 passed in 6.73s
```

当前风险：

- hybrid 权重目前通过函数参数传入，还没有做成后台可配置项。
- rerankExplanation 当前是规则解释，不是 rerank 模型自己生成的自然语言解释。
- 不同面试阶段应该使用什么权重还没有策略化，后续可以结合 Agent decision 动态选择。

下一步建议：

- 继续生产级 RAG 阶段 6：RAG evaluation case 管理，把 Hit@K、MRR、关键词覆盖率等评估能力产品化。
- 后续可以让 Agent 根据场景选择 hybrid 权重，例如技术题偏 BM25，项目复盘偏 vector。

## 阶段 12：生产级 RAG 工程化升级 - evaluation case 管理

状态：已完成阶段性版本。

本阶段把已有 RAG 评估指标进一步整理成 case 管理和评估报告能力，方便后续做检索质量回归、后台质量面板和简历项目表达。

已完成内容：

- 新增 `normalize_evaluation_case()`：
  - 规范化 case 字段；
  - 自动补齐 `expectedKnowledgeBase`；
  - 支持把单个 `expectedKeywords` 转成列表。
- 新增 `filter_evaluation_cases()`：
  - 支持按 `knowledgeBase` 筛选；
  - 支持按 `expectedPositionTag` 筛选。
- 新增 `run_evaluation_suite()`：
  - 复用 `evaluate_modes()`；
  - 返回 `caseCount`；
  - 返回 `metricDefinitions`；
  - 为每个 case 生成 `caseInsights`。
- 继续保留并复用原有指标：
  - Hit@K；
  - MRR；
  - keywordCoverage；
  - metadataMatch；
  - emptyRecall。
- 新增学习文档：`docs/learning/22-RAG评测case和质量指标.md`。

局部验证：

```text
python -m pytest tests/test_rag_evaluation_management.py tests/test_rag_evaluation.py tests/test_rag_evaluation_explanations.py tests/test_rag_evaluation_script.py tests/test_rag_evaluation_seed.py -q
```

结果：

```text
23 passed in 0.73s
```

当前风险：

- evaluation cases 目前主要来自本地 JSON / seed 数据，还没有做成数据库表和后台增删改查。
- 指标运行目前是同步函数，case 规模增大后可以改为异步任务或后台定时评估。
- case insight 是规则解释，不是模型自动诊断。

下一步建议：

- 继续生产级 RAG 阶段 7：低质量召回日志和后台质量面板。
- 后续把 evaluation suite 结果接入管理员后台，让用户能看到空召回、metadata miss、弱关键词覆盖等问题。

## 阶段 13：生产级 RAG 工程化升级 - 低质量召回日志和后台质量面板

状态：已完成阶段性版本。

本阶段把 RAG 日志进一步产品化为管理员可见的低质量召回面板，用于发现空召回、弱召回和未进入 prompt 的召回记录。

已完成内容：

- 后端新增 `GET /api/admin/rag/quality`。
- 新增 `classify_rag_quality_issue()`：
  - `empty_recall`
  - `weak_recall`
  - `unused_in_prompt`
- 新增 `build_rag_quality_payload()`：
  - 汇总 `totalLogCount`
  - 汇总 `lowQualityCount`
  - 汇总 `emptyRecallCount`
  - 汇总 `weakRecallCount`
  - 汇总 `unusedInPromptCount`
  - 返回低质量召回样例和 recommendation。
- 前端管理员后台新增“低质量召回”只读面板。
- `loadAdminDashboard()` 增加 `/api/admin/rag/quality` 请求。
- 新增学习文档：`docs/learning/23-低质量召回日志和后台质量面板.md`。

局部验证：

```text
python -m pytest tests/test_admin_rag_quality.py tests/test_admin_routes.py tests/test_rag_retrieval_logs.py -q
node tests/frontend_admin_dashboard.test.mjs
```

结果：

```text
14 passed in 7.30s
```

当前风险：

- 当前低质量分类仍是规则版，没有接入 evaluation suite 的 case 级指标。
- 前端只是只读摘要面板，还没有筛选、分页、跳转详情和导出。
- recommendation 是固定规则文案，还不是模型诊断。

下一步建议：

- 继续生产级 RAG 阶段 8：向量库持久化迁移抽象，保留 SQLite 实现，同时抽出可迁移到 Qdrant / pgvector 的接口。
- 后续再把 metadata miss、keywordCoverage 低、duplicate chunk 污染纳入低质量召回面板。

## 阶段 14：生产级 RAG 工程化升级 - 向量库迁移抽象

状态：已完成阶段性版本。

本阶段在不直接引入 Qdrant / pgvector 的前提下，抽象出 VectorStore 协议和 SQLite 实现，让当前项目具备后续迁移生产级向量库的工程基础。

已完成内容：

- 新增 `backend_python/vector_store.py`。
- 新增 `VectorStore` Protocol。
- 新增 `VectorSearchResult` 数据结构。
- 新增 `SQLiteVectorStore`：
  - `upsert_embedding()`
  - `search()`
- `SQLiteVectorStore.search()` 支持：
  - 向量相似度检索；
  - 文档生命周期过滤；
  - private / public 权限边界；
  - metadata filter；
  - 同分时优先当前用户自己的文档。
- `retrieve_vector_chunks()` 已切换为通过 `SQLiteVectorStore` 检索，保持上层返回结构兼容。
- 新增学习文档：`docs/learning/24-向量库持久化迁移抽象设计.md`。

局部验证：

```text
python -m pytest tests/test_vector_store_contract.py tests/test_rag_vector_retrieval.py tests/test_rag_hybrid_retrieval.py tests/test_rag_rerank_retrieval.py tests/test_rag_hybrid_rerank_explain.py -q
```

结果：

```text
19 passed in 0.69s
```

当前风险：

- 当前仍然是 SQLite JSON embedding，不适合大规模向量检索。
- VectorStore 目前只抽象了 upsert 和 search，没有覆盖批量删除、集合管理、索引参数等生产向量库能力。
- 还没有真实接入 Qdrant / pgvector，后续上线前可作为独立阶段推进。

下一步建议：

- 生产级 RAG 本轮主线已经完成一轮闭环，可以先做一次阶段性项目讲解和简历表达整理。
- 后续如果继续工程化，可以进入部署前准备：Docker、Nginx、云服务器、MySQL/PostgreSQL、对象存储和日志轮转。

## 阶段 15：前端产品化重构 V2 - 信息架构和导航基线

状态：已启动，完成阶段 0 基线验证和阶段 1 导航骨架。

本阶段目标不是重复开发 RAG / Agent 后端链路，而是把已经落地的账号、面试、训练、知识库、RAG 调试、Agent 日志和管理员后台能力整理成更清晰的面试训练工作台。

已完成内容：

- 新增 active spec：`docs/specs/active/frontend-productization-v2-design.md`。
- 新增 active plan：`docs/plans/active/frontend-productization-v2.md`。
- 新增前端测试：`tests/frontend_product_navigation.test.mjs`。
- `index.html` 新增产品级导航：
  - 账号与档案；
  - 面试工作台；
  - 训练中心；
  - 知识库与 RAG；
  - 管理员后台。
- `index.html` 为现有主要区块增加 `data-product-section` 标记。
- `styles.css` 新增 `.product-nav`、`.product-section` 和移动端导航样式。
- `app.js` 新增 `switchProductSection()` 和 `bindProductNavigation()`。
- 管理员原有“后台”按钮已接入新产品导航，点击后切换到管理员后台分区。
- 测试 VM 环境补齐/兼容产品导航需要的 DOM 查询能力。

全量验证：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
230 passed in 33.27s
全部前端 .mjs 测试通过，无失败输出。
```

当前风险：

- 当前只是信息架构第一步，导航已经把功能分层，但每个分区内部的说明卡片、RAG 可解释信息和 Agent 可解释信息还需要继续产品化。
- 管理员后台仍然依赖管理员角色可见，普通用户点击产品导航里的“管理员后台”时仍会看到权限隐藏后的空态问题，后续需要补一个更清楚的权限提示。
- 移动端视觉已经有基础响应式样式，但还需要用浏览器做桌面端和移动端实测。

下一步建议：

- 继续阶段 2：面试训练工作台产品化。
- 重点优化“为什么问这一题”的 Agent 决策摘要，让普通用户默认看到中文解释，开发调试细节再放到折叠区。
- 继续阶段 3：知识库与 RAG 面板产品化，把 queryVariants、matchedQueryVariant、rerankExplanation 等字段转成更容易读懂的中文说明。

## 阶段 16：前端产品化重构 V2 - Agent 决策摘要产品化

状态：已完成阶段性版本。

本阶段把面试工作台里的 Agent 决策面板从“技术字段直接展示”升级为“普通用户可读 + 开发者可展开调试”的双层结构。

已完成内容：

- `tests/frontend_interview_flow.test.mjs` 增加 Agent 产品解释断言：
  - “为什么这样问”；
  - 中文动作标签；
  - 推荐训练任务；
  - 工具调用中文名；
  - “开发者调试”折叠入口。
- `app.js` 新增：
  - `agentActionProductLabel()`；
  - `agentDifficultyProductLabel()`；
  - `agentToolReadableName()`；
  - `renderToolCallChips()`；
  - `renderSelectedTrainingTask()`。
- `renderAgentDecision()` 改为双层结构：
  - 默认层：解释为什么这样问、下一步动作、考察点、难度、参考工具和推荐训练；
  - 调试层：通过 `details` 展开原有 Agent 调试面板、触发规则、保护规则、话题迁移等信息。
- `styles.css` 新增 Agent 产品解释卡片样式：
  - `.agent-product-explain`；
  - `.agent-product-head`；
  - `.agent-product-meta`；
  - `.agent-tool-chip-row`；
  - `.agent-tool-chip`；
  - `.agent-training-hint`；
  - `.agent-debug-details`。

全量验证：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
230 passed in 33.22s
全部前端 .mjs 测试通过，无失败输出。
```

当前风险：

- 当前 Agent 解释仍依赖后端已有字段，前端不会重新推理 Agent 决策原因。
- 如果后端某些模型响应缺少 `toolCalls` 或 `selectedTrainingTask`，前端会显示“暂无工具调用摘要”，不会强造信息。
- 真实面试流程里还需要继续观察卡片文案是否足够自然，避免用户觉得像调试日志。

下一步建议：

- 继续阶段 3：知识库与 RAG 面板产品化。
- 把 RAG 文档状态、可见性、chunk 数、重复 chunk 数，以及 queryVariants、matchedQueryVariant、rerankExplanation 转成更容易读懂的中文信息。
- 后续再继续阶段 4：训练中心和历史复盘优化，让“面试报告 -> 薄弱点 -> 训练任务”闭环更明显。

## 阶段 17：前端产品化重构 V2 - 知识库与 RAG 面板产品化

状态：已完成阶段性版本。

本阶段把 RAG 文档管理和 RAG 调试命中从“工程字段裸展示”升级为更可读的产品化信息：用户能看懂知识库文档是否可用、谁能看到、切片质量如何；开发调试时也能看懂多路 query 和 rerank 重排信息。

已完成内容：

- `tests/frontend_rag_documents.test.mjs` 增加文档生命周期断言：
  - `status` 显示为“启用 / 停用 / 归档”；
  - `visibility` 显示为“私有 / 公开”；
  - 展示 `chunkCount`；
  - 展示 `duplicateChunkCount`；
  - 展示 metadata 预览。
- `tests/frontend_rag_quality.test.mjs` 增加 RAG 命中解释断言：
  - 多路 query；
  - 命中 query；
  - rerank 重排解释；
  - 不出现 `undefined`。
- `app.js` 新增：
  - `ragStatusLabel()`；
  - `ragVisibilityLabel()`；
  - `renderMetadataPreview()`；
  - `renderRagLifecycleBadges()`；
  - `renderRagHitDiagnostics()`。
- `renderRagDocumentList()` 展示文档生命周期、权限、chunk 数、重复 chunk 数和 metadata。
- `loadRagDocumentDetail()` 的详情卡片展示同样的生命周期与 metadata 信息。
- RAG debug 命中项新增诊断块：
  - `多路 query`；
  - `命中 query`；
  - `重排`。
- `styles.css` 新增：
  - `.rag-lifecycle-row`；
  - `.rag-meta-chip-row`；
  - `.rag-meta-chip`；
  - `.rag-hit-diagnostics`。

全量验证：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
230 passed in 33.24s
全部前端 .mjs 测试通过，无失败输出。
```

当前风险：

- 当前只是把已有后端字段产品化展示，前端不重新计算 RAG 质量。
- 如果后端没有返回 queryVariants、matchedQueryVariant 或 rerankExplanation，前端会自动隐藏诊断块，不会强造解释。
- 管理员低质量召回面板后续仍可继续优化筛选、分页和问题类型聚合。

下一步建议：

- 继续阶段 4：训练中心和历史复盘优化。
- 重点让“面试报告 -> 薄弱点 -> 训练任务 -> 再练一轮”这条训练闭环在界面上更清楚。
- 后续阶段 5 再优化管理员后台里的低质量召回面板和 Agent 决策日志可读性。

## 阶段 18：前端产品化重构 V2 - 训练中心行动计划

状态：已完成阶段性版本。

本阶段把训练中心从“训练任务列表”升级为“下一步训练行动计划”，让用户能直接看懂某个薄弱点接下来该练什么、为什么优先练、当前掌握度是多少。

已完成内容：

- `tests/frontend_training_center.test.mjs` 增加训练行动计划断言：
  - “下一步训练”；
  - “掌握度”；
  - “高优先级”；
  - 推荐练习题。
- `app.js` 新增 `renderTrainingActionPlan()`。
- `renderTrainingCenter()` 的详情区域新增行动计划卡片：
  - 训练标题；
  - 训练说明；
  - 掌握度；
  - 优先级；
  - 当前状态；
  - 推荐练习题。
- 保留原有训练操作：
  - 开始训练；
  - 标记完成；
  - 归档。
- `styles.css` 新增训练行动计划样式：
  - `.training-action-plan`；
  - `.training-plan-metrics`；
  - `.training-recommended-question`。

全量验证：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
230 passed in 33.10s
全部前端 .mjs 测试通过，无失败输出。
```

当前风险：

- 当前训练任务来源仍依赖后端已有报告生成和训练任务接口，前端不重新生成薄弱点。
- 推荐练习题需要后端返回 `recommendedQuestion` 才会显示；没有该字段时不会强行展示。
- 历史复盘区域后续仍可继续强化“从某次面试跳转到对应训练任务”的联动。

下一步建议：

- 继续阶段 5：管理员后台产品化。
- 优化管理员后台里的低质量召回面板，让管理员更容易看到空召回、弱召回、未进入 prompt 等问题。
- 再优化 Agent 决策日志的后台可读性，便于排查 Agent 是否频繁 fallback、重复追问或话题迁移异常。

## 阶段 19：前端产品化重构 V2 - 管理员 RAG 质量诊断面板

状态：已完成阶段性版本。

本阶段把管理员后台的“低质量召回”从普通列表升级为质量诊断面板，让管理员能快速看到 RAG 召回问题分布和对应建议动作。

已完成内容：

- `tests/frontend_admin_dashboard.test.mjs` 增加后台质量诊断断言：
  - “质量问题分布”；
  - “空召回”；
  - “弱召回”；
  - “未进入 Prompt”；
  - “建议动作”。
- `renderAdminRagQuality()` 改为诊断面板结构：
  - 总低质量记录数；
  - 空召回数量和说明；
  - 弱召回数量和说明；
  - 未进入 Prompt 数量和说明；
  - 低质量召回样例；
  - 每条样例的建议动作。
- `styles.css` 新增后台质量面板样式：
  - `.admin-quality-grid`；
  - `.admin-quality-sample-list`；
  - `.admin-quality-sample`。
- 保持现有管理员接口不变，继续消费 `/api/admin/rag/quality` 的已有返回结构。

全量验证：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
230 passed in 32.98s
全部前端 .mjs 测试通过，无失败输出。
```

当前风险：

- 当前后台质量诊断仍是只读面板，没有筛选、分页、导出和跳转到日志详情。
- 建议动作来自后端已有 recommendation 或质量原因，前端不做额外模型诊断。
- 管理员后台仍是 MVP 级别，不做复杂 RBAC、用户封禁或内容删除。

下一步建议：

- 进入阶段 6：文档、学习总结和整体验收。
- 补一篇精简学习文档：`docs/learning/06-前端产品化重构如何承接RAG和Agent能力.md`。
- 做一次完整桌面端和移动端浏览器检查，确认面试工作台、RAG 分区、训练中心、管理员后台都可达且无横向溢出。

## 阶段 20：前端产品化重构 V2 - 文档与整体验收

状态：已完成。

本阶段对前端产品化重构 V2 做收口：补充精简学习文档，记录本阶段完成范围，并执行后端测试、前端测试、桌面端和移动端浏览器验证。

已完成内容：

- 新增学习文档：`docs/learning/06-前端产品化重构如何承接RAG和Agent能力.md`。
- 本轮前端产品化 V2 已完成：
  - 信息架构和产品导航；
  - 面试工作台 Agent 决策解释层；
  - RAG 文档生命周期和命中解释；
  - 训练中心行动计划；
  - 管理员 RAG 质量诊断面板。

验证命令：

```text
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

浏览器验证范围：

```text
http://127.0.0.1:8000/

桌面端：
- 账号与档案
- 面试工作台
- 训练中心
- 知识库与 RAG
- 管理员后台

移动端：
- 导航正常换行
- 无 undefined
- 无横向溢出
```

最终验证结果：

```text
后端：python -m pytest -q
结果：230 passed in 32.97s

前端：Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
结果：全部前端 .mjs 测试通过，无失败输出。
```

浏览器验证结果：

```text
桌面端和移动端均已检查：
- 账号与档案
- 面试工作台
- 训练中心
- 知识库与 RAG
- 管理员后台

结果：
- 分区切换正常。
- 页面无 undefined。
- 无横向溢出。
- 移动端导航可正常换行。

本轮复核补充：

```text
桌面端：1280x720，导航 display=flex，scrollWidth=clientWidth=1280，无 undefined。
移动端：390x844，导航 display=grid，scrollWidth=clientWidth=390，无 undefined。
五个分区按钮均存在且可切换 active 状态。
管理员后台在未登录管理员状态下保持隐藏，符合权限设计。
```
```

## 阶段 21：部署工程化 V1 - Spec 设计

状态：已完成 spec，等待 implementation plan。

本阶段根据当前项目进度，将下一条主线从“前端产品化 V2”切换到“部署工程化 V1”。这一步不重复执行已经完成的 RAG / Agent / 前端产品化内容，而是规划 Docker、docker-compose、PostgreSQL、Nginx、日志、排错和上线验收。

已完成内容：

- 将已执行完的前端产品化 V2 文档从 active 移到 completed：
  - `docs/specs/completed/frontend-productization-v2-design.md`
  - `docs/plans/completed/frontend-productization-v2.md`
- 新增 active spec：
  - `docs/specs/active/deployment-engineering-v1-design.md`
- 更新路线入口：
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`

下一步：

```text
根据 docs/specs/active/deployment-engineering-v1-design.md
编写 docs/plans/active/deployment-engineering-v1.md
然后按 plan 分阶段实现。
```

当前边界：

- 不重构 RAG。
- 不重构 Agent。
- 不引入 LangGraph / LangChain。
- 不做 Kubernetes / CI/CD。
- 不做 Redis / Celery / 对象存储正式接入。

## 阶段 22：LangGraph Agent POC - Spec 设计

状态：已完成 spec，等待 implementation plan。

用户明确表示暂时不为上线部署做准备，希望继续打磨项目核心竞争力，并提到两个方向：Vue3 前端重构和 LangGraph。结合当前项目目标岗位是 AI 应用开发岗，且项目已经有自研 Interview Orchestrator Agent，本阶段将下一条主线调整为 LangGraph Agent POC。

已完成内容：

- 将部署工程化 V1 spec 暂时移到 archive：
  - `docs/specs/archive/2026-06-11-deployment-engineering-v1-design.md`
- 新增 active spec：
  - `docs/specs/active/langgraph-agent-poc-design.md`
- 更新路线入口：
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`

本阶段设计结论：

```text
不替换现有 /api/interview/next-question 主流程。
不删除自研 Agent。
新增旁路 LangGraph POC，用来验证 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory 可以映射为 StateGraph 节点。
第一版优先跑通 StateGraph 基础节点链路，checkpoint 和 human-in-the-loop 先做文档预留。
```

下一步：

```text
根据 docs/specs/active/langgraph-agent-poc-design.md
编写 docs/plans/active/langgraph-agent-poc.md
然后按 TDD 执行：
State 测试 -> Node 测试 -> Graph 测试 -> Route 测试 -> 学习文档 -> 全量验证。
```

POC 解释：

```text
POC 是 Proof of Concept，中文叫概念验证。它不是完整产品，而是用一个小而完整的实验版本证明技术路线可行。
本项目里的 LangGraph POC 用于证明自研 Agent 的 state、tool、decision、trace 可以迁移到 LangGraph 工作流。
```

## 阶段 23：LangGraph Agent POC - 第一版实现

状态：已完成阶段性版本。

本阶段新增旁路 LangGraph POC，不替换现有 `/api/interview/next-question` 主流程。

已完成内容：

- 新增 `langgraph==0.2.76` 依赖。
- 新增 `backend_python/langgraph_agent/` 包。
- 新增 `InterviewGraphState` 和初始 state 构造。
- 新增 6 个 LangGraph 节点：
  - `observe_state`
  - `analyze_answer`
  - `retrieve_context`
  - `select_action`
  - `generate_question`
  - `update_memory`
- 新增 `StateGraph` 编排。
- 新增实验接口：`POST /api/langgraph-agent/next-question-poc`。
- 新增学习文档：`docs/learning/08-LangGraph如何承接自研Agent.md`。
- 新增 implementation plan：`docs/plans/active/langgraph-agent-poc.md`。

局部验证：

```text
python -m pytest tests/test_langgraph_agent_state.py -q
结果：2 passed in 0.02s

python -m pytest tests/test_langgraph_agent_nodes.py -q
结果：3 passed in 0.03s

python -m pytest tests/test_langgraph_agent_graph.py -q
结果：2 passed, 1 warning in 1.52s

python -m pytest tests/test_langgraph_agent_route.py -q
结果：2 passed, 1 warning in 0.60s
```

当前边界：

- POC 使用独立路由，不影响主面试接口。
- checkpoint 和 human-in-the-loop 只做文档预留。
- 第一版 `generate_question` 使用 stub 文案，不直接调用真实模型。
- `retrieve_context` 使用 POC 样例数据，不重构三类 RAG 底层。

依赖风险记录：

```text
安装 langgraph==0.2.76 时，pip 将本机已有 langchain-core 调整为 0.3.86。
pip 提示当前用户环境中的 langchain-classic、langchain-community、langchain-text-splitters 与该版本存在依赖约束不一致。
本项目当前代码不依赖这些包，但后续建议使用虚拟环境隔离 AI 框架依赖，避免全局 Python 环境互相影响。
```

全量验证：

```text
python -m pytest tests/test_langgraph_agent_state.py tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_route.py -q
结果：9 passed, 1 warning in 0.67s

python -m pytest -q
结果：239 passed, 1 warning in 32.33s

Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
结果：全部前端 .mjs 测试通过，无失败输出。
```

本阶段未做内容：

- 未替换现有 `/api/interview/next-question` 主流程。
- 未删除自研 Agent。
- 未重构 RAG。
- 未改现有前端主流程。
- 未做 checkpoint / human-in-the-loop 运行时能力。
- 未做 Docker / Nginx / 云服务器上线。

## 阶段 24：LangGraph Agent V2 - Spec 设计

状态：已完成 spec，等待 implementation plan。

阶段 23 已经跑通 LangGraph V1 POC，但 V1 仍然使用样例 RAG 数据和 stub 问题生成，只能证明 StateGraph 节点链路可行。用户希望继续把 LangGraph 这条路线跑通并开发完善，因此本阶段不进入上线部署，也不做 Vue3 重构，而是把下一条主线调整为 LangGraph Agent V2。

已完成内容：

- 将已完成的 LangGraph V1 POC 文档移动到 completed：
  - `docs/specs/completed/langgraph-agent-poc-design.md`
  - `docs/plans/completed/langgraph-agent-poc.md`
- 新增 active spec：
  - `docs/specs/active/langgraph-agent-v2-real-rag-checkpoint-design.md`
- 更新路线入口：
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`

归档更新：

- 阶段 24 实现与验证完成后，V2 spec / plan 已从 active 移动到 completed：
  - `docs/specs/completed/langgraph-agent-v2-real-rag-checkpoint-design.md`
  - `docs/plans/completed/langgraph-agent-v2-real-rag-checkpoint.md`

本阶段设计结论：

```text
不替换现有 /api/interview/next-question 主流程。
不删除自研 Agent。
保留 /api/langgraph-agent/next-question-poc 作为 V1 POC 证明。
新增旁路 LangGraph V2 实验接口，用 adapter 复用现有三类 RAG 和 Agent 决策。
引入 threadId、MemorySaver checkpoint 和 checkpoint 摘要查询。
human-in-the-loop 和生产级 checkpoint 持久化继续预留，不在本阶段实现。
```

V2 目标范围：

- 接入真实岗位知识库 RAG、题库 RAG、候选人画像 RAG。
- 复用现有 `decide_next_action`、fallback、normalize / guardrail。
- 新增 `POST /api/langgraph-agent/next-question-v2`。
- 新增 `GET /api/langgraph-agent/checkpoint/{thread_id}`。
- 返回 `nodeTrace`、`toolCalls`、`decision`、`checkpointSummary`。
- 新增学习文档解释 checkpoint、thread state、普通数据库记录之间的区别。

下一步：

```text
根据 docs/specs/active/langgraph-agent-v2-real-rag-checkpoint-design.md
编写 docs/plans/active/langgraph-agent-v2-real-rag-checkpoint.md
然后按 TDD 执行：
Checkpoint 测试 -> Adapter 测试 -> Decision 测试 -> Route 测试 -> 学习文档 -> 全量验证。
```

阶段 24 实现进度：

- 已完成 checkpoint 基础：
  - `backend_python/langgraph_agent/checkpoint.py`
  - `threadId` graph config。
  - in-process checkpoint summary。
- 已扩展 LangGraph state：
  - `threadId`
  - `applicationProfileId`
  - `roundCount`
  - `remainingRounds`
  - `useRealRag`
  - `useRealDecision`
  - `checkpointSummary`
- 已完成真实/fake RAG adapter：
  - `backend_python/langgraph_agent/adapters.py`
  - 复用 `retrieve_role_knowledge_tool`
  - 复用 `retrieve_question_bank_tool`
  - 复用 `retrieve_candidate_memory_tool`
  - 复用 `evaluate_retrieval_quality`
- 已完成真实/fake Agent decision adapter：
  - 复用 `build_agent_state`
  - 复用 `decide_next_action`
  - 保留 fallback / normalize / guardrail。
- 已完成 V2 实验接口：
  - `POST /api/langgraph-agent/next-question-v2`
  - `GET /api/langgraph-agent/checkpoint/{thread_id}`
  - 保留 `POST /api/langgraph-agent/next-question-poc`
- 已新增学习文档：
  - `docs/learning/09-LangGraph checkpoint和thread state怎么理解.md`

局部验证：

```text
python -m pytest tests/test_langgraph_agent_state.py tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_checkpoint.py tests/test_langgraph_agent_adapters.py tests/test_langgraph_agent_graph.py tests/test_langgraph_agent_graph_v2.py tests/test_langgraph_agent_route.py -q
结果：19 passed, 1 warning in 0.75s
```

当前边界：

- V2 仍然是旁路实验接口，没有替换 `/api/interview/next-question`。
- V2 路由默认使用 fake RAG / fake decision，保证测试稳定。
- `useRealRag=true` 时接入现有 RAG adapter。
- `useRealDecision=true` 时接入现有 Agent decision adapter 和 `call_model`。
- checkpoint 使用 `MemorySaver` + 进程内 summary，尚不是生产级持久化。

## 阶段 25：Docker + Nginx + VPS 上线 V1 - Spec 设计

状态：已完成 spec，等待 implementation plan。

本阶段用户希望先不继续大范围重构 RAG / Agent / Vue3，而是把项目推向“可以上线展示”的工程化闭环。项目已经推送到 GitHub 私有仓库：

```text
https://github.com/davidluulc/ai-interview.git
```

已完成内容：

- 新增 active spec：
  - `docs/specs/active/docker-nginx-vps-deployment-v1-design.md`
- 更新路线入口：
  - `docs/specs/README.md`
  - `docs/roadmap/current-state.md`
  - `docs/roadmap/project-progress.md`

本阶段设计结论：

```text
采用香港或海外 VPS + Cloudflare DNS/SSL 的轻量上线展示路线。
本地开发继续保留 SQLite。
上线 V1 推荐用 Docker Compose 编排 app、PostgreSQL、Redis、Celery worker、Nginx。
Nginx 作为公网统一入口和反向代理。
本阶段不做 Vue3、不重构 RAG/Agent、不做 Kubernetes、不做复杂 CI/CD、不做大陆服务器备案。
```

下一步：

```text
根据 docs/specs/active/docker-nginx-vps-deployment-v1-design.md
编写 docs/plans/active/docker-nginx-vps-deployment-v1.md
然后按 TDD/文档驱动执行：
部署配置测试 -> Dockerfile/.dockerignore -> compose -> Nginx -> 部署文档 -> 学习文档 -> 全量验证。
```

阶段 25 实现进度：

- 已新增 active plan：
  - `docs/plans/active/docker-nginx-vps-deployment-v1.md`
- 已新增部署配置测试：
  - `tests/test_deployment_config.py`
- 已新增部署配置骨架：
  - `.env.production.example`
  - `.dockerignore`
  - `Dockerfile`
  - `docker-compose.yml`
  - `deploy/README.md`
  - `deploy/nginx/ai-interview.conf`
- 已新增部署文档：
  - `docs/deployment/README.md`
  - `docs/deployment/vps-deploy-v1.md`
  - `docs/deployment/nginx-cloudflare-https.md`
  - `docs/deployment/troubleshooting.md`
  - `docs/deployment/backup-and-rollback.md`
- 已新增学习文档：
  - `docs/learning/12-Docker-Nginx-VPS上线链路怎么理解.md`

局部验证：

```text
python -m pytest tests/test_deployment_config.py -q
结果：5 passed in 0.03s
```

待验证：

- `python -m pytest -q`
- 全部前端 `.mjs` 测试
- `docker --version`
- `docker compose version`
- `docker build -t ai-interview-app:local .`
- `docker compose --env-file .env.production.example config`

阶段 25 当前验证结果：

```text
python -m pytest tests/test_deployment_config.py -q
结果：5 passed in 0.03s

python -m pytest -q
结果：274 passed, 1 warning in 34.07s

Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
结果：全部前端 .mjs 测试通过，无失败输出。

docker --version
结果：Docker version 29.3.1

docker compose version
结果：Docker Compose version v5.1.1

docker compose -p ai-interview --env-file .env.production.example config
结果：通过，Compose 配置可解析。

docker build -t ai-interview-app:local .
结果：通过。第一次失败原因是 Docker Desktop Linux engine 未启动；第二次失败原因是 Debian apt 镜像临时 502。移除 Dockerfile 中非必要的 apt 安装后，镜像构建成功。

docker compose -p ai-interview --env-file .env.production.example up -d --no-build
结果：通过。app、db、redis、worker、nginx 均启动。

docker compose -p ai-interview --env-file .env.production.example exec app alembic upgrade head
结果：通过。干净 PostgreSQL 数据卷从空库迁移到 20260606_0008 head。

Invoke-WebRequest http://127.0.0.1:8080/api/health
结果：通过，Redis 状态为 ok。

Invoke-WebRequest http://127.0.0.1:8080/docs
结果：HTTP 200。

docker compose -p ai-interview exec worker celery -A backend_python.celery_app.celery_app inspect registered
结果：通过，已注册：
- backend_python.tasks.health.ping_task
- backend_python.tasks.rag_evaluation.run_rag_evaluation_task
```

补充结论：

```text
由于项目目录名包含中文，直接执行 docker compose --env-file .env.production.example config 会触发 project name must not be empty。
已将文档中的 compose 命令统一改为显式指定项目名：docker compose -p ai-interview ...

由于 Windows 中文路径下 docker compose up --build 可能触发 BuildKit gRPC 异常，本地验证采用：
docker build -t ai-interview-app:local .
docker compose -p ai-interview --env-file .env.production.example up -d --no-build

由于生产环境不能让 FastAPI 自动 create_all 建表，已新增 AUTO_INIT_DB 开关：
本地 SQLite 默认 AUTO_INIT_DB=true。
生产 PostgreSQL 模板和 Compose 使用 AUTO_INIT_DB=false，并通过 Alembic upgrade head 管理表结构。
```
