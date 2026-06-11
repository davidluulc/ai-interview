# Agent Debug Panel UI V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有面试训练工作台中增加 Agent 调试面板，让用户和开发者能看懂本轮 Agent 为什么降难度、换话题或触发保护规则。

**Architecture:** 不改后端 API，只消费 `agentDecision` 和最近 Agent 日志中已有的 `debugSignals`、`guardrailApplied`、`topicShift`、`triggerRules` 字段。前端继续使用原生 HTML/CSS/JS，通过小型格式化函数把工程字段渲染成可读 UI。

**Tech Stack:** 原生 HTML、CSS、JavaScript、Node `.mjs` 前端测试、FastAPI 现有后端测试。

---

## File Structure

- Modify: `tests/frontend_interview_flow.test.mjs`
  - 验证当前轮 `agentDecisionPanel` 能显示保护规则、连续弱回答次数、话题迁移、触发规则，并且缺字段不出现 `undefined`。
- Modify: `tests/frontend_agent_logs.test.mjs`
  - 验证最近 Agent 日志卡片能显示顶层 `debugSignals`、`guardrailApplied`、`topicShift`。
- Modify: `tests/frontend_workbench_layout.test.mjs`
  - 验证前端存在 Agent Debug Panel 相关 class，防止样式结构被误删。
- Modify: `app.js`
  - 新增 Agent 调试摘要格式化函数。
  - 增强 `renderAgentDecision(question)`。
  - 增强 `renderAgentLogItem(item)`。
- Modify: `styles.css`
  - 新增调试面板、信号网格、规则标签、话题迁移状态样式。
- Optional Modify: `index.html`
  - 如现有 `#agentDecisionPanel` 容器够用，则不新增 DOM；如测试需要明确语义，可补充 class 或 aria 文案。

---

### Task 1: 当前轮 Agent 调试面板测试

**Files:**
- Modify: `tests/frontend_interview_flow.test.mjs`

- [ ] **Step 1: Write the failing test**

在模拟的 `/api/interview/next-question` 返回体里，把 `agentDecision` 扩展为：

```js
agentDecision: {
  nextAction: "switch_topic",
  agentMode: "coach",
  difficulty: "basic",
  focus: "rag_basic",
  triggerRules: ["weak_answer_streak", "topic_shift"],
  guardrailApplied: true,
  topicShift: { from: "rag_log_json", to: "rag_basic" },
  debugSignals: {
    weakAnswerStreak: 2,
    repeatedQuestionCount: 1,
    topicLocked: false,
    guardrailApplied: true,
    topicShifted: true,
    triggerRules: ["weak_answer_streak", "topic_shift"]
  }
}
```

在断言区增加：

```js
assert.match(context.__result.agentDecisionHtml, /Agent 调试面板/);
assert.match(context.__result.agentDecisionHtml, /保护规则/);
assert.match(context.__result.agentDecisionHtml, /已介入/);
assert.match(context.__result.agentDecisionHtml, /连续弱回答/);
assert.match(context.__result.agentDecisionHtml, /2/);
assert.match(context.__result.agentDecisionHtml, /重复问题/);
assert.match(context.__result.agentDecisionHtml, /话题迁移/);
assert.match(context.__result.agentDecisionHtml, /rag_log_json/);
assert.match(context.__result.agentDecisionHtml, /rag_basic/);
assert.match(context.__result.agentDecisionHtml, /weak_answer_streak/);
assert.doesNotMatch(context.__result.agentDecisionHtml, /undefined/);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected: FAIL because current UI only renders the lightweight insight bar, not the full Agent 调试面板 fields.

---

### Task 2: 实现当前轮 Agent 调试面板

**Files:**
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add formatting helpers in `app.js`**

Add helper functions near existing Agent rendering helpers:

```js
function yesNoLabel(value) {
  return value ? "是" : "否";
}

function guardrailLabel(value) {
  return value ? "已介入" : "未介入";
}

function getAgentDebugSignals(source = {}) {
  return source.debugSignals && typeof source.debugSignals === "object" ? source.debugSignals : {};
}

function getAgentTriggerRules(decision = {}) {
  const signals = getAgentDebugSignals(decision);
  if (Array.isArray(signals.triggerRules) && signals.triggerRules.length) {
    return signals.triggerRules;
  }
  return Array.isArray(decision.triggerRules) ? decision.triggerRules : [];
}

function renderRuleTags(rules = []) {
  if (!rules.length) {
    return `<span class="agent-rule-tag muted">暂无触发规则</span>`;
  }
  return rules.map((rule) => `<span class="agent-rule-tag">${rule}</span>`).join("");
}
```

- [ ] **Step 2: Enhance `renderAgentDecision(question)`**

Inside `renderAgentDecision`, compute:

```js
const debugSignals = getAgentDebugSignals(decision);
const triggerRules = getAgentTriggerRules(decision);
const topicShift = decision.topicShift && typeof decision.topicShift === "object" ? decision.topicShift : {};
const guardrailApplied = Boolean(decision.guardrailApplied || debugSignals.guardrailApplied);
const topicShiftText = topicShift.from || topicShift.to ? `${topicShift.from || "未知"} -> ${topicShift.to || "未知"}` : "未发生";
```

Then render a `.agent-debug-panel-inline` block containing:

```html
<section class="agent-debug-panel-inline" aria-label="Agent 调试面板">
  <div class="agent-debug-title">
    <span>Agent 调试面板</span>
    <strong>可观测性</strong>
  </div>
  <div class="agent-debug-grid">
    ...
  </div>
  <div class="agent-rule-list">...</div>
</section>
```

- [ ] **Step 3: Add CSS**

Add styles:

```css
.agent-debug-panel-inline { ... }
.agent-debug-title { ... }
.agent-debug-grid { ... }
.agent-debug-signal { ... }
.agent-rule-list { ... }
.agent-rule-tag { ... }
.agent-rule-tag.muted { ... }
.agent-topic-shift { ... }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected: PASS.

---

### Task 3: 最近 Agent 日志卡片测试与实现

**Files:**
- Modify: `tests/frontend_agent_logs.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Write the failing test**

In the mocked log item, add top-level fields:

```js
debugSignals: {
  weakAnswerStreak: 2,
  repeatedQuestionCount: 1,
  topicLocked: false,
  guardrailApplied: true,
  topicShifted: true,
  triggerRules: ["weak_answer_streak", "topic_shift"]
},
guardrailApplied: true,
topicShift: { from: "rag_log_json", to: "rag_basic" },
```

Add assertions:

```js
assert.match(getElement("#agentLogContent").innerHTML, /调试摘要/);
assert.match(getElement("#agentLogContent").innerHTML, /已介入/);
assert.match(getElement("#agentLogContent").innerHTML, /连续弱回答/);
assert.match(getElement("#agentLogContent").innerHTML, /rag_log_json/);
assert.match(getElement("#agentLogContent").innerHTML, /topic_shift/);
assert.doesNotMatch(getElement("#agentLogContent").innerHTML, /undefined/);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node tests/frontend_agent_logs.test.mjs
```

Expected: FAIL because current log card hides these fields inside details or does not render top-level debug summary.

- [ ] **Step 3: Implement log debug summary**

In `renderAgentLogItem(item)`, compute top-level first, fallback to `decision`:

```js
const debugSignals = getAgentDebugSignals(item.debugSignals ? item : decision);
const guardrailApplied = Boolean(item.guardrailApplied ?? decision.guardrailApplied ?? debugSignals.guardrailApplied);
const topicShift = item.topicShift || decision.topicShift || {};
const triggerRules = Array.isArray(debugSignals.triggerRules) && debugSignals.triggerRules.length
  ? debugSignals.triggerRules
  : Array.isArray(decision.triggerRules) ? decision.triggerRules : [];
```

Render a `.agent-log-debug-summary` block before `<details>`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
node tests/frontend_agent_logs.test.mjs
```

Expected: PASS.

---

### Task 4: 布局存在性测试与样式收口

**Files:**
- Modify: `tests/frontend_workbench_layout.test.mjs`
- Modify: `styles.css`

- [ ] **Step 1: Write layout assertions**

Add:

```js
assert.match(app, /class="agent-debug-panel-inline"/);
assert.match(css, /\.agent-debug-panel-inline/);
assert.match(css, /\.agent-debug-grid/);
assert.match(css, /\.agent-log-debug-summary/);
```

- [ ] **Step 2: Run layout test**

Run:

```powershell
node tests/frontend_workbench_layout.test.mjs
```

Expected: PASS after Task 2 and Task 3.

---

### Task 5: Full Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run all frontend `.mjs` tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend tests pass.

- [ ] **Step 3: Browser verification**

Open:

```text
http://localhost:8000/
```

Check desktop and mobile:
- 页面能打开。
- 面试问题下方能看到 Agent 调试面板。
- 最近 Agent 日志能显示调试摘要。
- 不出现 `undefined`。
- 页面排版没有明显重叠。

---

## Self-Review

- Spec coverage:
  - 当前轮 Agent 调试面板: Task 1, Task 2.
  - 最近 Agent 日志增强: Task 3.
  - 布局和样式: Task 4.
  - 不改后端 API、不中断现有前端调用: 所有任务只修改前端文件和前端测试。
  - 验证桌面和移动端: Task 5.
- Placeholder scan:
  - 无 `TBD`、无 `TODO`、无未定义任务。
- Type consistency:
  - 统一使用 `debugSignals`、`guardrailApplied`、`topicShift`、`triggerRules`。
  - 顶层日志字段优先，`decision` 字段兜底。
