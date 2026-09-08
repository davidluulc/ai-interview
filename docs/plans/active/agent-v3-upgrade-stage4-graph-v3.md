# Agent v3 Stage 4：LangGraph 真图化 + 模型驱动工具选择 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把直线图升级为「plan ⇄ tools 条件路由循环」的真 Agent 图：模型自主选择检索工具与查询词，规则 policy 降级为 guardrail（覆盖模型建议并留 overrideReason），注册 `langgraph_agent_v3` runtime 走既有灰度（quality gate / shadow / fallback classic）。

**Architecture:** 新模块 `langgraph_agent/graph_v3.py` 自带图构建与路由函数（不动 v2）；`plan` 节点用 S1 的 `call_model_structured` + 新 `AgentPlanModel`（selectedTools/queries/readyToAsk/nextAction…）；`tools` 节点只执行被选中的工具（复用 agent_tools 包装）；条件边由 `route_after_plan()` 返回 `tools | generate | end`；双保险步数上限（state.planningSteps + `recursion_limit`）。`agent_runtime.py` 的 allowed 集合与分派处注册 v3（默认仍 langgraph_mainline，v3 先 shadow）。

**Tech Stack:** langgraph 0.2.76（已验证 `add_conditional_edges` / `ToolNode` 可用；本阶段不用 ToolNode——工具选择走 PlanModel 结构化输出，与 S1 链路一致且可测）。零新依赖。

**上游 spec:** `docs/specs/active/agent-v3-upgrade-design.md` §4-S4。**执行前修订点：** Task 6 的 runtime 注册锚点以 `rg -n "langgraph_mainline" backend_python/` 的实际分派代码为准；v2 图与既有 runtime 零改动。

## Global Constraints

- 不改 `graph.py`（v2）、`agent_policy.py` 既有函数、既有测试；新测试进 `tests/test_langgraph_agent_v3.py`。
- 所有新节点函数为纯函数或可注入依赖（plan 的 LLM 调用经参数注入，测试用 fake）。
- 步数上限：`MAX_PLANNING_STEPS = 2`（plan→tools 循环至多 2 轮，第 2 轮后强制 readyToAsk）；`recursion_limit=25` 兜底。
- 分支 `feat/agent-v3-s4-graph`；不 push。

## 预先完成的事实（已验证）

- v2 图七节点线性（graph.py:20-59）；`InterviewGraphState` 已有 remainingRounds/nodeTrace/toolCalls 等键（state.py:5-29），v3 复用并新增 `planningSteps`/`planDecision`/`selectedToolResults`（total=False，向后兼容）。
- `decide_next_action` 已支持 `structured_call_fn`（S1）；`apply_agent_policy` 返回 recommendedAction/difficulty/shouldSwitchTopic 等（agent_policy.py:47+）。
- 工具包装：`agent_tools.py` 三个 `retrieve_*_tool(profile, ..., retrieve_fn)` 返回 `{"result", "toolCall"}`。
- 追问/换方向/结束的动作词：`deep_follow_up | lower_difficulty | switch_topic`（agent_policy）+ `end_interview`（policy 的收尾分支，见 agent_policy.py 后半；执行时确认枚举并保持一致）。

## File Map

- Create: `backend_python/langgraph_agent/graph_v3.py` — 图、节点、路由、AgentPlanModel
- Create: `tests/test_langgraph_agent_v3.py`
- Modify: `backend_python/agent_runtime.py` — allowed 集合 + v3 分派
- Modify: `docs/roadmap/current-state.md`

---

### Task 1: AgentPlanModel + plan 节点（TDD）

**Files:**
- Create: `backend_python/langgraph_agent/graph_v3.py`
- Create: `tests/test_langgraph_agent_v3.py`

**Interfaces:**
- Consumes: `call_model_structured`（S1）、`apply_agent_policy`、`build_node_trace`。
- Produces:

```python
class AgentPlanModel(BaseModel):  # graph_v3.py 内定义（或从 structured_output 导入——本任务就地定义，S5 复用导出名）
    readyToAsk: bool
    selectedTools: list[str]        # ⊆ {retrieve_role_knowledge, retrieve_question_bank, retrieve_candidate_memory}
    toolQuery: str                  # 本轮检索统一查询词（替代 v2 的硬编码拼接）
    nextAction: str                 # deep_follow_up | lower_difficulty | switch_topic | end_interview
    difficulty: str                 # basic | medium | hard
    focus: str
    reason: str

def build_plan_messages(state) -> list[dict]        # 纯函数
def apply_policy_guardrail(plan: dict, policy: dict) -> dict  # 纯函数：policy 触发时覆盖 + overrideReason
async def make_plan_node(structured_call_fn):       # 返回节点函数，写 planDecision/planningSteps/nodeTrace
```

- [ ] **Step 1: 失败测试**（5 个，全 fake structured_call_fn）：
  1. `apply_policy_guardrail`：policy.recommendedAction=switch_topic 且 weak_streak≥3 → plan.nextAction 被覆盖、`overrideReason` 非空、decision 来源标 `guardrail`；
  2. guardrail 不触发 → plan 原样通过、无 overrideReason；
  3. `make_plan_node` 正常路径写 state 键（planDecision/decision/planningSteps+1/nodeTrace 追加）；
  4. structured 耗尽 → fallback 到 policy 推荐动作（decision.fallbackUsed=True）；
  5. `planningSteps ≥ MAX_PLANNING_STEPS` 时节点强制 readyToAsk=True（不再循环）。
- [ ] **Step 2: 红灯 → 实现（plan 消息含：档案摘要/历史最近 3 轮/policy 建议/工具清单及各自用途说明）→ 绿灯**
- [ ] **Step 3: commit** `feat: add v3 plan node with model-driven tool selection and guardrail`

### Task 2: tools 节点 + 条件路由 + 图组装（TDD）

**Files:**
- Modify: `backend_python/langgraph_agent/graph_v3.py`
- Modify: `tests/test_langgraph_agent_v3.py`

**Interfaces:**
- Produces:

```python
def route_after_plan(state) -> str            # "tools" | "generate" | "end"（纯函数）
def make_tools_node(tool_fns: dict[str, Callable]) -> Callable  # 只执行 selectedTools 命中的工具
def build_interview_graph_v3(*, structured_call_fn, tool_fns) -> CompiledGraph
```

路由规则（测试钉死）：`planDecision.readyToAsk` 或 planningSteps 超限 → `generate`；`nextAction == end_interview` → `end`；否则 `tools`。`tools` 节点把各工具 result 并入 `selectedToolResults`（role/question/memory 三键，未选中为空列表），nodeTrace 记录每个工具的 toolCall 摘要与**未选中的工具列表**（可观测性卖点）。图结构：

```python
graph.add_node("observe_state", observe_state_node)      # 复用 v2 nodes
graph.add_node("analyze_answer", analyze_answer_node)
graph.add_node("plan", make_plan_node(structured_call_fn))
graph.add_node("tools", make_tools_node(tool_fns))
graph.add_node("generate_question", generate_question_node)
graph.add_node("update_memory", update_memory_node)
graph.add_edge(START, "observe_state")
graph.add_edge("observe_state", "analyze_answer")
graph.add_edge("analyze_answer", "plan")
graph.add_conditional_edges("plan", route_after_plan, {"tools": "tools", "generate": "generate_question", "end": END})
graph.add_edge("tools", "plan")
graph.add_edge("generate_question", "update_memory")
graph.add_edge("update_memory", END)
```

- [ ] **Step 1: 失败测试**（4 个）：路由三分支各一（含 end 直接收束，state 保留 decision）；tools 只执行选中工具（fake tool_fns 计数）；图级集成——fake plan 第一轮 readyToAsk=False+选中 1 个工具、第二轮 readyToAsk=True → `graph.ainvoke` 完成，nodeTrace 顺序 = observe/analyze/plan/tools/plan/generate/memory，`planningSteps == 2`。
- [ ] **Step 2: 红灯 → 实现 → 绿灯 → 全量回归 → commit** `feat: add v3 graph with conditional routing loop`

### Task 3: 死循环双保险测试

- [ ] 测试：fake plan 永远 readyToAsk=False → invoke 在 planningSteps=MAX 后走 generate 正常结束（不是超时/异常）；再加 `config={"recursion_limit": 25}` 传参断言（build_interview_graph_v3 的 runner 封装 `run_interview_graph_v3(...)` 内传入，对齐 v2 的 `build_graph_config` 模式，thread_id/checkpoint 摘要同 v2 处理）。
- [ ] commit `test: pin v3 loop bounds`

### Task 4: runtime 注册 + shadow 分派

**Files:**
- Modify: `backend_python/agent_runtime.py`

- [ ] **Step 1:** allowed 集合加 `"langgraph_agent_v3"`（agent_runtime.py:15 附近）；
- [ ] **Step 2:** 按 `rg -n "langgraph_mainline|build_interview_graph_v2|run_interview_graph_v2" backend_python/` 定位分派处，为 `langgraph_agent_v3` 增加分支：调用 `run_interview_graph_v3`，结果过 `_runtime_response` 同构包装；v3 抛错走 `_failed_langgraph_result` → quality gate → fallback classic（复用既有机制，与 mainline 同路径）；
- [ ] **Step 3:** 测试（追加到 test 文件）：`normalize_agent_runtime("langgraph_agent_v3")` 合法；v3 失败时 runtime 响应带 fallbackRuntime=classic 的路径与 mainline 一致（复用 test_agent_runtime_switching.py 的 fake 模式——只读参照，不改旧文件）。
- [ ] commit `feat: register langgraph agent v3 runtime`

### Task 5: 阶段收尾

- [ ] 全量回归（基线 + 新增 ~12 测试）；`current-state.md` 记录（默认 runtime 不变，v3 待 shadow 观察后切 mainline——**切默认不在本阶段**，公网部署窗口后人工决策）。
- [ ] commit `docs: record stage4 graph v3 completion`；合并门按流水线总控。

## Self-Review（写作时已执行）

- Spec §4-S4 验收四条：三路径集成测试（Task 2）、循环上限（Task 3）、override 规则（Task 1）、灰度注册 + quality gate（Task 4）逐一对应。
- 已知执行时确认点：end_interview 动作词枚举、runtime 分派代码锚点——均为事实型，非设计缺口。
- 红线核对：v2/policy/既有测试零改动 ✅；零新依赖 ✅；LLM 调用全部可注入 fake ✅。
