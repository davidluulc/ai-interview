# LangGraph Agent POC Spec

## 1. POC 是什么

POC 是 `Proof of Concept`，中文叫“概念验证”。

它的重点不是一次性做完整产品，而是用一个小而完整的实验版本证明某条技术路线可行。

放到本项目里，LangGraph Agent POC 的含义是：

```text
不推翻现有自研 Interview Orchestrator Agent，
不替换当前稳定的 /api/interview/next-question 主流程，
而是在旁路新增一个实验性 LangGraph 工作流，
证明现有 Agent 的 state、tool、decision、trace 可以迁移到 LangGraph。
```

## 2. 文档目的

当前 AI 模拟面试系统已经完成了自研 Agent 工程化：

- Agent State。
- Tool Calls。
- Agent Decision。
- fallback decision。
- normalize / guardrail。
- coach / interview 双模式。
- nodeTrace。
- 三类 RAG 工具调用。
- 训练任务接入。
- Agent 日志。

本阶段目标不是继续堆功能，而是补齐 AI 应用开发岗很重要的一块表达能力：

```text
我不仅会自研 Agent 编排，也理解如何把 Agent 状态机和工具调用迁移到 LangGraph 这类工作流框架。
```

本 spec 用于规划一个可测试、可解释、风险可控的 LangGraph POC。

## 3. 官方能力参考

LangGraph 官方文档里的几个关键点和本项目高度匹配：

- Graph API 的基本过程是：先定义 State，再添加 nodes 和 edges，最后 compile graph。官方文档说明 compile 会检查图结构，并可以配置 checkpointer、breakpoints 等运行参数。
  - 参考：https://docs.langchain.com/oss/python/langgraph/graph-api
- Persistence / checkpoint 用于保存 graph state，可支持 human-in-the-loop、memory 和故障恢复。
  - 参考：https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph 的 overview 把它定位为低层级 agent orchestration 框架，关注 durable execution、streaming、human-in-the-loop 等能力。
  - 参考：https://docs.langchain.com/oss/python/langgraph/overview
- Interrupts 可以暂停 graph 执行，保存状态，并等待外部输入后恢复。
  - 参考：https://docs.langchain.com/oss/python/langgraph/interrupts
- 短期 memory 可以作为 agent state 的一部分，通过 thread-scoped checkpoints 持久化。
  - 参考：https://docs.langchain.com/oss/python/concepts/memory

本项目第一版 POC 不会一次性用完这些能力，但会按这些概念设计代码边界。

## 4. 当前项目基础

当前自研 Agent 的核心文件：

```text
backend_python/agent_state.py
backend_python/agent_tools.py
backend_python/agent_trace.py
backend_python/agent_orchestrator.py
backend_python/interview_agent.py
backend_python/routes/interview.py
backend_python/routes/agent.py
```

当前自研 Agent 已经具备的节点语义：

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

其中：

- `agent_state.py` 负责构造状态和分析回答质量。
- `agent_tools.py` 把三类 RAG 包装成工具调用。
- `agent_trace.py` 统一记录节点轨迹。
- `agent_orchestrator.py` 负责编排状态、工具和决策。
- `interview_agent.py` 负责 LLM 决策、fallback、normalize 和 guardrail。
- `routes/interview.py` 负责 HTTP 接口、数据库、历史记录和最终响应。

这意味着 LangGraph POC 不需要从零开始；它要做的是把现有节点映射成 `StateGraph` 的节点和边。

## 5. 总目标

本阶段完成后，项目应新增一个实验性 LangGraph 工作流，具备以下能力：

```text
输入 profile、history、nextStage、agentMode
-> 构造 graph state
-> 经过 observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question_stub 或 generate_question
-> update_memory_stub
-> 输出结构化结果
```

第一版 POC 可以使用 stub 模型生成，避免让 LangGraph 阶段一开始就受模型 API 稳定性影响。

后续第二轮再决定是否接入真实 LLM 调用和真实 `/api/interview/next-question`。

## 6. 非目标

本阶段明确不做：

- 不替换现有 `/api/interview/next-question`。
- 不删除自研 Agent。
- 不把所有 Agent 代码迁移到 LangGraph。
- 不改现有前端主流程。
- 不做 LangGraph 云部署。
- 不引入 LangSmith 平台依赖。
- 不做复杂 multi-agent。
- 不做完整 human-in-the-loop 产品页面。
- 不做 Docker / Nginx / 云服务器上线。
- 不重构 RAG 检索底层。
- 不改数据库主表结构，除非测试需要极小字段或文档记录。

## 7. 方案选择

### 方案 A：只写 LangGraph 设计文档，不安装依赖

优点：

- 风险最低。
- 不影响现有代码。
- 学习成本小。

缺点：

- 面试说服力较弱。
- 只能说“设计过”，不能说“跑通过”。

适合：

```text
完全不想引入新依赖时。
```

### 方案 B：新增旁路 LangGraph POC，不替换主流程

优点：

- 能真实跑通 LangGraph。
- 不破坏现有稳定功能。
- 面试表达最稳：既有自研 Agent，又有框架迁移验证。
- 失败时可以独立回滚。

缺点：

- 需要新增依赖和测试。
- 需要理解 StateGraph、node、edge、compile。

适合：

```text
当前阶段推荐。
```

### 方案 C：直接把主流程迁移到 LangGraph

优点：

- 技术含量最高。
- 主流程完全框架化。

缺点：

- 风险大。
- 影响现有面试功能。
- 调试成本高。
- 你现在还在学习 Agent，直接重构容易失控。

适合：

```text
POC 跑通并理解以后，再作为后续大版本考虑。
```

本阶段选择：方案 B。

## 8. 目标架构

新增模块建议：

```text
backend_python/langgraph_agent/
  __init__.py
  state.py
  nodes.py
  graph.py
  adapters.py

backend_python/routes/langgraph_agent.py
tests/test_langgraph_agent_state.py
tests/test_langgraph_agent_nodes.py
tests/test_langgraph_agent_graph.py
tests/test_langgraph_agent_route.py
docs/learning/08-LangGraph如何承接自研Agent.md
```

### 8.1 state.py

职责：

- 定义 `InterviewGraphState`。
- 保持 JSON 可序列化。
- 不保存数据库 Session。
- 不保存模型 client。

推荐字段：

```python
class InterviewGraphState(TypedDict, total=False):
    profile: dict[str, Any]
    history: list[dict[str, Any]]
    nextStage: str
    agentMode: str
    answerAnalysis: dict[str, Any]
    retrievalQuality: dict[str, Any]
    roleHits: list[dict[str, Any]]
    questionHits: list[dict[str, Any]]
    memoryHits: list[dict[str, Any]]
    toolCalls: list[dict[str, Any]]
    decision: dict[str, Any]
    nextQuestion: dict[str, Any]
    memoryUpdate: dict[str, Any]
    nodeTrace: list[dict[str, Any]]
```

### 8.2 nodes.py

职责：

- 把当前自研 Agent 的节点拆成 LangGraph node 函数。

第一版节点：

```text
observe_state_node
analyze_answer_node
retrieve_context_node
select_action_node
generate_question_node
update_memory_node
```

节点规则：

- 每个 node 输入 graph state。
- 每个 node 返回 state update。
- 每个 node 追加 nodeTrace。
- 每个 node 不直接读写数据库。
- 需要外部依赖时通过 adapter 注入。

### 8.3 adapters.py

职责：

- 复用现有自研 Agent 能力。
- 让 LangGraph POC 不重复造轮子。

建议封装：

```text
build_state_from_existing_agent()
run_existing_rag_tools()
select_action_with_existing_decider()
```

第一版可以使用假检索函数和假模型函数，先证明图结构可运行。

### 8.4 graph.py

职责：

- 创建 `StateGraph`。
- 注册 nodes。
- 注册 edges。
- compile graph。

第一版图结构：

```text
START
-> observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
-> END
```

第二版可以增加条件边：

```text
select_action
  if nextAction == "finish_interview" -> END
  else -> generate_question
```

### 8.5 route

新增实验接口：

```text
POST /api/langgraph-agent/next-question-poc
```

用途：

- 只用于开发验证。
- 不被当前前端主流程调用。
- 返回 graphState、nodeTrace、decision、nextQuestion。

## 9. 依赖策略

第一版需要新增依赖：

```text
langgraph
```

是否需要 `langchain`：

```text
第一版不强制需要。
LangGraph 可以作为底层编排框架使用，模型调用仍然复用当前 llm_client 或 stub。
```

如果安装后发现 LangGraph 依赖链自动引入 LangChain 相关包，记录在进度文档中，不把它作为业务代码直接依赖。

## 10. 测试策略

测试必须先于实现。

### 10.1 State 测试

验证：

- state 是 dict / TypedDict 语义。
- 必要字段存在。
- state 可 JSON 序列化。
- 不包含数据库 Session、模型 client 等运行时对象。

### 10.2 Node 测试

验证：

- `observe_state_node` 能写入 session / round 信息。
- `analyze_answer_node` 能识别弱回答。
- `retrieve_context_node` 能返回三类 hits 和 toolCalls。
- `select_action_node` 能输出 decision。
- `generate_question_node` 能输出 nextQuestion。
- `update_memory_node` 能输出 memoryUpdate。
- 每个节点都追加 nodeTrace。

### 10.3 Graph 测试

验证：

- graph 可以 compile。
- graph 可以 invoke。
- graph 输出包含 decision、nextQuestion、nodeTrace。
- 节点顺序符合预期。

### 10.4 Route 测试

验证：

- 实验接口可调用。
- 不影响 `/api/interview/next-question`。
- 非法输入返回可解释错误。

## 11. 前端策略

第一版不改当前主前端。

可选第二轮再增加：

```text
管理员后台或调试面板里新增“LangGraph POC 调试”折叠区。
```

当前不做原因：

- 先把后端 POC 跑通。
- 避免前端和 LangGraph 同时变化导致调试困难。

## 12. 日志和可观测性

第一版 POC 需要返回：

```text
nodeTrace
toolCalls
decision
nextQuestion
memoryUpdate
```

暂不要求写入数据库。

第二版可以考虑：

```text
把 LangGraph POC 的执行结果写入 AgentDecisionLog 的 state_json / decision_json。
```

## 13. 和现有自研 Agent 的关系

本阶段不是“自研 Agent 被 LangGraph 取代”，而是形成双轨结构：

```text
主流程：自研 Agent，继续服务真实面试功能。
旁路：LangGraph POC，用来验证迁移方向和学习框架。
```

面试表达：

```text
我先自研 Agent，是为了理解状态、工具、决策、兜底和日志这些底层机制。
在此基础上，我做了 LangGraph POC，把 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory 映射成 StateGraph 节点。
这样既能保证主流程稳定，又能证明项目具备向 LangGraph 工作流迁移的能力。
```

## 14. 阶段拆分

### 阶段 1：文档和依赖确认

目标：

- 确认 LangGraph 官方概念。
- 添加依赖。
- 写学习文档开头。

验收：

- `requirements.txt` 包含 LangGraph。
- 能在本地 import LangGraph。

### 阶段 2：State 和 Node 单测

目标：

- 先写 state/node 测试。
- 实现最小节点函数。

验收：

- state/node 测试通过。
- 节点输出 nodeTrace。

### 阶段 3：Graph 编排

目标：

- 创建 StateGraph。
- 注册节点和边。
- compile 并 invoke。

验收：

- graph 测试通过。
- 输出包含 decision、nextQuestion、nodeTrace。

### 阶段 4：实验接口

目标：

- 新增 `/api/langgraph-agent/next-question-poc`。
- 不影响现有主接口。

验收：

- route 测试通过。
- 现有 `/api/interview/next-question` 测试通过。

### 阶段 5：学习文档和项目进度

目标：

- 新增精简学习文档。
- 更新进度文档。

验收：

- 文档能讲清 LangGraph 和自研 Agent 的关系。
- 全量测试通过。

## 15. 验收标准

本阶段完成后必须满足：

- LangGraph POC 可运行。
- 现有主面试流程不受影响。
- 不替换自研 Agent。
- POC 有独立测试。
- POC 输出 nodeTrace。
- POC 能解释每个节点做了什么。
- 文档能讲清 POC 的意义。
- `python -m pytest -q` 通过。
- 前端 `.mjs` 测试通过。

## 16. 风险和控制

### 16.1 新依赖风险

风险：

```text
LangGraph 依赖链可能引入较多包。
```

控制：

- 只在 POC 模块中使用。
- 不让主流程强依赖 POC。
- 如果依赖安装失败，记录原因，不强行改主流程。

### 16.2 学习成本风险

风险：

```text
StateGraph、checkpoint、interrupt 一次性学太多会混乱。
```

控制：

- 第一版只做 StateGraph 基础节点链路。
- checkpoint 和 interrupt 先写文档预留。
- 第二版再做 checkpoint / human-in-the-loop。

### 16.3 主流程稳定性风险

风险：

```text
LangGraph POC 影响现有模拟面试功能。
```

控制：

- POC 使用独立模块和独立路由。
- 不改 `/api/interview/next-question` 合约。
- 所有旧测试必须继续通过。

## 17. 下一步执行建议

下一步不要直接改代码，应先写 implementation plan：

```text
docs/plans/active/langgraph-agent-poc.md
```

plan 应按 TDD 拆分：

```text
State 测试
-> Node 测试
-> Graph 测试
-> Route 测试
-> 学习文档
-> 全量验证
```

## 18. 面试表达目标

完成后可以这样讲：

```text
我这个项目里有两条 Agent 路线。主流程是自研 Interview Orchestrator Agent，它维护面试状态，调用岗位知识库 RAG、题库 RAG 和候选人画像 RAG，再根据回答质量、剩余轮次、训练任务和 guardrail 做下一步决策。为了证明这个自研 Agent 具备迁移到标准工作流框架的能力，我又做了 LangGraph POC，把 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory 映射成 StateGraph 节点。第一版 POC 不替换主流程，只验证状态、节点、边和 trace 能跑通；后续可以继续接 checkpoint 和 human-in-the-loop。
```
