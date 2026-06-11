# 阶段一验收记录：面试体验增强 V2

## 1. 验收结论

阶段一“面试体验增强 V2”当前已达到可收尾状态。

本阶段没有做 Docker、Nginx、云服务器上线，也没有直接引入 LangGraph。当前重点仍然是让模拟面试体验更自然、更可控、更可观察。

## 2. 验收项与证据

### 2.1 学习辅导模式和真实面试模式有差异

证据：
- 前端提供 `agentModeInput`，用户可选择“学习辅导模式”和“真实面试模式”。
- 后端 `build_mode_guidance` 会根据 `agentMode` 注入不同的问题生成策略。
- 测试 `test_question_strategy_payload_includes_mode_guidance` 覆盖两种模式的提示差异。
- 前端测试 `frontend_interview_flow.test.mjs` 覆盖 coach 模式会随请求发送到后端。

面试表达：
> 我把面试体验拆成学习辅导模式和真实面试模式。学习辅导模式更偏训练，会降低难度和拆小问题；真实面试模式保留压力，但不能无意义卡死。

### 2.2 连续答不上来时不再机械重复

证据：
- `interview_agent.py` 会根据连续弱回答触发 `weak_answer_streak` 和 `topic_shift`。
- `routes/interview.py` 在问题返回前做后端重复问题检测。
- 如果模型生成了历史里问过的问题，后端会触发 `repeated_prompt_guardrail`，切换相邻考察点。
- 测试 `test_next_question_rewrites_repeated_prompt_from_model` 覆盖重复问题改写、触发规则、日志记录。

面试表达：
> 我没有完全依赖大模型避免重复，而是在后端问题生成出口加了 guardrail。模型输出的问题会先和历史问题做标准化比较，重复时切换相邻考察点。

### 2.3 每道题能展示考察点或追问依据

证据：
- 前端会在面试问题区域显示问题 focus。
- `renderAgentDecision` 会展示 Agent 模式、下一步动作、决策摘要和触发规则。
- 前端测试 `frontend_interview_flow.test.mjs` 覆盖 Agent 决策面板和问题 focus 展示。

面试表达：
> 前端不只展示问题文本，还会展示 Agent 为什么这么问，包括当前模式、下一步动作、决策摘要和触发规则，避免黑箱体验。

### 2.4 Agent 决策日志能看到触发规则

证据：
- `create_agent_decision_log` 会保存 `state_json` 和 `decision_json`。
- 重复问题兜底会把 `repeated_prompt_guardrail` 写入 `agentDecision.triggerRules` 和日志。
- 测试覆盖日志中包含 `repeated_prompt_guardrail`。

面试表达：
> Agent 每轮决策都会落日志，里面包含状态、动作、原因、工具、触发规则和 fallback 状态，方便排查为什么降难度、深挖或切换话题。

### 2.5 面试报告能输出下一轮训练计划

证据：
- `ReportResponse` 包含 `trainingPlan`。
- 后端会生成或兜底补齐 `weakTopics`、`nextRoundPriority`、`practiceQuestions`、`oneMinuteTemplates`、`shouldRetry`。
- 测试 `test_question_reviews.py` 覆盖逐题复盘和训练计划。
- 前端当前报告和历史复盘都能展示“下一轮训练计划”。

面试表达：
> 报告不是只给分数，而是把每道题转成训练动作。用户能看到薄弱点、训练顺序、练习题和一分钟回答模板。

### 2.6 自动化测试

最新验证命令：

```powershell
python -m pytest -q
```

结果：

```text
122 passed
```

最新前端脚本验证：

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

结果：

```text
退出码 0
```

## 3. 当前阶段没有做的事情

本阶段明确没有做：
- Docker Compose。
- Nginx 反向代理。
- 云服务器部署。
- PostgreSQL 生产化切换。
- Redis 中间件接入。
- LangGraph 依赖接入。

这些内容应放到后续阶段处理。

## 4. 下一阶段建议

阶段一收尾后，建议进入阶段二：Agent 工程化增强。

优先事项：
- 把当前 Agent 流程拆成更清晰的节点概念：`observe_state`、`analyze_answer`、`retrieve_context`、`select_action`、`generate_question`、`update_memory`。
- 梳理轻量状态机设计：状态、事件、转移规则。
- 保留 LangGraph 迁移设计，但暂不引入依赖。
- 强化 Agent Trace，让每个节点的输入、输出和兜底原因更清晰。

阶段二的目标不是让功能堆更多，而是让你能在面试中讲清楚：Agent 的状态如何流转，决策如何产生，工具如何调用，日志如何排查。
