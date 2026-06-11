# Interview Experience V3 LangGraph Deepening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a shared Agent Policy layer so the classic Interview Orchestrator Agent and the LangGraph side-path use the same interview-experience rules for weak answers, topic switching, coaching, and human-in-the-loop readiness.

**Architecture:** Add `backend_python/agent_policy.py` as a pure, JSON-serializable policy module. The classic Agent calls it while building fallback and normalized decisions; the LangGraph V2/V3 side-path adds an `apply_policy` node before action selection, then checkpoint summaries and the frontend expose the policy result lightly.

**Tech Stack:** Python 3, FastAPI backend modules, LangGraph side-path, pytest, vanilla HTML/CSS/JavaScript, Node `.mjs` frontend tests.

---

## File Structure

- Create `backend_python/agent_policy.py`: pure policy functions and constants. No database, network, or LLM dependency.
- Modify `backend_python/interview_agent.py`: call Agent Policy from classic fallback/normalize path and include policy fields in `AgentDecision`.
- Modify `backend_python/agent_orchestrator.py`: add `apply_policy` node trace and keep `/api/interview/next-question` compatible.
- Modify `backend_python/langgraph_agent/state.py`: add optional state fields for `policy`, `policySummary`, and human-in-the-loop flags.
- Modify `backend_python/langgraph_agent/nodes.py`: add `apply_policy_node`, wire policy into V2 action selection, and keep fake path stable.
- Modify `backend_python/langgraph_agent/graph.py`: insert `apply_policy` between `retrieve_context` and `select_action`.
- Modify `backend_python/langgraph_agent/checkpoint.py`: record policy summary in checkpoint summary.
- Modify `app.js`: lightly render policy reasons and user-choice hints inside the existing Agent decision panel.
- Create `tests/test_agent_policy.py`: unit tests for policy behavior.
- Modify `tests/test_interview_agent.py` and/or `tests/test_agent_orchestrator.py`: prove classic Agent decisions expose policy without breaking existing decision shape.
- Modify `tests/test_langgraph_agent_graph_v2.py` and/or `tests/test_langgraph_agent_checkpoint.py`: prove LangGraph side-path returns policy and checkpoint summary includes policy fields.
- Modify `tests/frontend_interview_flow.test.mjs`: prove frontend renders policy reasons and coaching hints.
- Create `docs/learning/10-Agent Policy如何连接面试体验和LangGraph.md`: Chinese learning doc.
- Modify `docs/roadmap/project-progress.md`, `docs/roadmap/current-state.md`, `docs/specs/README.md`, and `docs/plans/README.md`: record completion and archive paths.

---

## Task 1: Agent Policy Unit Tests

**Files:**
- Create: `tests/test_agent_policy.py`
- Create later: `backend_python/agent_policy.py`

- [x] **Step 1: Write failing tests for weak-answer streak policy**

Add tests that call `apply_agent_policy()` with a coach-mode state containing `weakAnswerStreak=1`, `2`, and `3`.

Expected assertions:
- streak 1 returns `recommendedAction == "lower_difficulty"`.
- streak 2 returns `shouldExplainBeforeAsk is True` and `shouldAskUserChoice is True`.
- streak 3 returns `shouldSwitchTopic is True`.
- every result includes non-empty `policyReasons` and `triggerRules`.

- [x] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_agent_policy.py -q
```

Expected: fail because `backend_python.agent_policy` does not exist yet.

- [x] **Step 3: Write minimal policy implementation**

Create `backend_python/agent_policy.py` with:
- `normalize_agent_mode(value: str) -> str`
- `normalize_policy_input(state: dict[str, Any]) -> dict[str, Any]`
- `apply_agent_policy(state: dict[str, Any]) -> dict[str, Any]`

The output must include:
- `recommendedAction`
- `difficulty`
- `shouldExplainBeforeAsk`
- `shouldSwitchTopic`
- `shouldAskUserChoice`
- `requiresHumanReview`
- `policyReasons`
- `triggerRules`

- [x] **Step 4: Run green test**

Run:

```powershell
python -m pytest tests/test_agent_policy.py -q
```

Expected: pass.

---

## Task 2: Coach / Interview and Topic-Lock Policy

**Files:**
- Modify: `tests/test_agent_policy.py`
- Modify: `backend_python/agent_policy.py`

- [x] **Step 1: Add failing tests for mode differences**

Add tests proving the same weak state behaves differently:
- coach mode sets `shouldExplainBeforeAsk is True`.
- interview mode keeps `shouldExplainBeforeAsk is False`.
- interview mode can still set `shouldSwitchTopic is True` after repeated weak answers.

- [x] **Step 2: Add failing tests for topic lock and repeated focus**

Add tests with:

```python
"answerAnalysis": {
    "weakAnswerStreak": 2,
    "repeatedQuestionCount": 2,
    "topicLock": {"locked": True, "topic": "RAG 日志 JSON", "count": 3}
}
```

Expected:
- `shouldSwitchTopic is True`
- `requiresHumanReview is True` only when lock count is high or weak streak is high.
- `triggerRules` includes `topic_lock_guardrail`.

- [x] **Step 3: Run red tests**

Run:

```powershell
python -m pytest tests/test_agent_policy.py -q
```

Expected: fail on missing mode/topic behavior.

- [x] **Step 4: Implement policy branching**

Update `apply_agent_policy()`:
- coach weak streak 2: explain before asking and ask user choice.
- coach weak streak 3+: switch topic, explain first, require human review if topic lock is also present.
- interview weak streak 2+: switch topic but do not feed answer.
- repeated question count 2+ or topic lock: switch topic and record guardrail trigger.

- [x] **Step 5: Run green tests**

Run:

```powershell
python -m pytest tests/test_agent_policy.py -q
```

Expected: pass.

---

## Task 3: Classic Agent Reuses Agent Policy

**Files:**
- Modify: `tests/test_interview_agent.py`
- Modify: `tests/test_agent_orchestrator.py`
- Modify: `backend_python/interview_agent.py`
- Modify: `backend_python/agent_orchestrator.py`

- [x] **Step 1: Add failing tests for policy fields in classic decisions**

Add tests proving:
- `build_fallback_decision(state)` includes `policy`.
- normalized model decisions preserve `policy` and `policyReasons`.
- a pressure decision is corrected when Agent Policy says to switch topic.

- [x] **Step 2: Add failing orchestrator trace test**

Add or update an orchestrator test asserting `nodeTrace` includes an `apply_policy` node and `agentDecision["policy"]` exists.

- [x] **Step 3: Run red tests**

Run:

```powershell
python -m pytest tests/test_interview_agent.py tests/test_agent_orchestrator.py -q
```

Expected: fail because classic Agent does not attach policy yet.

- [x] **Step 4: Integrate policy in classic Agent**

Update `interview_agent.py`:
- import `apply_agent_policy`.
- call it inside `build_fallback_decision(state)`.
- use policy output to adjust `action`, `difficulty`, `triggerRules`, and `reason` without removing existing weakness strategy logic.
- attach `policy` to every fallback and normalized decision.
- extend `build_decision_summary()` to mention `policyReasons` briefly.

Update `agent_orchestrator.py`:
- add an `apply_policy` node trace after `select_weakness_strategy`.
- include policy summary in trace output.

- [x] **Step 5: Run green tests**

Run:

```powershell
python -m pytest tests/test_interview_agent.py tests/test_agent_orchestrator.py -q
```

Expected: pass.

---

## Task 4: LangGraph Side-Path Reuses Agent Policy

**Files:**
- Modify: `tests/test_langgraph_agent_graph_v2.py`
- Modify: `tests/test_langgraph_agent_nodes.py`
- Modify: `backend_python/langgraph_agent/state.py`
- Modify: `backend_python/langgraph_agent/nodes.py`
- Modify: `backend_python/langgraph_agent/graph.py`

- [x] **Step 1: Add failing node tests**

Add tests for `apply_policy_node(state)`:
- input has `agentMode`, `answerAnalysis`, `retrievalQuality`, `history`.
- output has `policy`.
- output `nodeTrace` contains `apply_policy`.

- [x] **Step 2: Add failing graph V2 test**

Update graph V2 test to assert:
- result includes `policy`.
- result `decision` includes policy summary or policy fields.
- node trace order contains `apply_policy` before `select_action`.

- [x] **Step 3: Run red tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph_v2.py -q
```

Expected: fail because LangGraph has no `apply_policy` node yet.

- [x] **Step 4: Implement LangGraph policy node**

Update `nodes.py`:
- import `apply_agent_policy`.
- add `apply_policy_node(state)`.
- in `make_select_action_v2_node()`, merge state policy into decision.
- in fake `select_action_node()`, also use state policy when present.

Update `graph.py`:
- add node `apply_policy`.
- wire `retrieve_context -> apply_policy -> select_action`.

Update `state.py`:
- add optional policy-related keys to `InterviewGraphState`.

- [x] **Step 5: Run green tests**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_nodes.py tests/test_langgraph_agent_graph_v2.py -q
```

Expected: pass.

---

## Task 5: Checkpoint Summary and Human-in-the-loop Fields

**Files:**
- Modify: `tests/test_langgraph_agent_checkpoint.py`
- Modify: `backend_python/langgraph_agent/checkpoint.py`

- [x] **Step 1: Add failing checkpoint summary test**

Create a state containing:

```python
"policy": {
    "recommendedAction": "switch_topic",
    "shouldAskUserChoice": True,
    "requiresHumanReview": True,
    "policyReasons": ["连续弱回答，建议用户选择继续面试或先学习。"],
    "triggerRules": ["weak_answer_streak", "human_review_precheck"]
}
```

Expected summary fields:
- `policyRecommendedAction == "switch_topic"`
- `shouldAskUserChoice is True`
- `requiresHumanReview is True`
- `policyReasons` includes the Chinese reason.

- [x] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_checkpoint.py -q
```

Expected: fail because summary does not record policy fields.

- [x] **Step 3: Implement checkpoint policy summary**

Update `record_checkpoint_summary()` and empty `summarize_checkpoint()` shape to include:
- `policyRecommendedAction`
- `shouldAskUserChoice`
- `requiresHumanReview`
- `policyReasons`
- `policyTriggerRules`

- [x] **Step 4: Run green test**

Run:

```powershell
python -m pytest tests/test_langgraph_agent_checkpoint.py -q
```

Expected: pass.

---

## Task 6: Frontend Light Policy Display

**Files:**
- Modify: `tests/frontend_interview_flow.test.mjs`
- Modify: `app.js`

- [x] **Step 1: Add failing frontend test**

Extend existing Agent decision rendering test with a question object containing:

```javascript
agentDecision: {
  policy: {
    policyReasons: ["连续两轮答不上来，coach 模式先解释再追问。"],
    shouldExplainBeforeAsk: true,
    shouldAskUserChoice: true,
    requiresHumanReview: false
  }
}
```

Expected rendered HTML includes:
- `策略原因`
- `先解释再追问`
- `建议让用户选择`

- [x] **Step 2: Run red frontend test**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected: fail because policy display is not rendered.

- [x] **Step 3: Implement light frontend display**

Update `renderAgentDecision(question = {})` in `app.js`:
- read `decision.policy`.
- show at most three `policyReasons`.
- show compact flags for `shouldExplainBeforeAsk`, `shouldAskUserChoice`, `requiresHumanReview`.
- keep current layout and existing strings stable.

- [x] **Step 4: Run green frontend test**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected: pass.

---

## Task 7: Chinese Learning Doc and Roadmap Updates

**Files:**
- Create: `docs/learning/10-Agent Policy如何连接面试体验和LangGraph.md`
- Modify: `docs/roadmap/project-progress.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [x] **Step 1: Add learning doc**

Write a Chinese learning doc explaining:
- Agent Policy 是什么。
- 它和普通 prompt 规则有什么区别。
- classic Agent 如何调用 policy。
- LangGraph 如何把 policy 变成节点。
- checkpoint summary 为什么要记录 policy。
- human-in-the-loop 当前为什么只做字段预留。
- 面试时怎么讲。

- [x] **Step 2: Update roadmap docs**

Update progress/current-state docs to say V3 is implemented when code verification passes.

- [x] **Step 3: Run doc link sanity scan**

Run:

```powershell
rg -n "interview-experience-v3-langgraph-deepening|Agent Policy|LangGraph" docs/roadmap docs/specs/README.md docs/plans/README.md docs/learning
```

Expected: relevant entries appear.

---

## Task 8: Archive Completed Spec and Plan

**Files:**
- Move: `docs/specs/active/interview-experience-v3-langgraph-deepening-design.md` to `docs/specs/completed/interview-experience-v3-langgraph-deepening-design.md`
- Move: `docs/plans/active/interview-experience-v3-langgraph-deepening.md` to `docs/plans/completed/interview-experience-v3-langgraph-deepening.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [x] **Step 1: Move files only after tests pass**

Use PowerShell `Move-Item` after full verification is green.

- [x] **Step 2: Update indexes**

Make README entries reflect that the V3 spec and plan are completed, not active.

- [x] **Step 3: Verify active folders**

Run:

```powershell
Get-ChildItem docs/specs/active, docs/plans/active
```

Expected: V3 files no longer appear in active after completion.

---

## Task 9: Full Verification

**Files:**
- No new files.

- [x] **Step 1: Run backend test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [x] **Step 2: Run all frontend `.mjs` tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend tests pass.

- [x] **Step 3: Browser validation if frontend changed**

Open `http://127.0.0.1:8000/` in the in-app browser and verify:
- desktop layout still renders.
- mobile viewport still renders.
- Agent decision panel can display policy reasons without breaking layout.

---

## Completion Notes

Do not mark this stage complete until:
- Agent Policy has independent tests.
- Classic Agent decisions include policy data.
- LangGraph V2 side-path includes policy data and checkpoint summary fields.
- Human-in-the-loop precheck fields are visible in policy/checkpoint data.
- Frontend renders policy reasons lightly.
- Required docs are updated.
- Backend and frontend tests pass.

