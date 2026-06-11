# 面试训练工作台 UI 重构 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前模拟面试页面从“表单 + 大问题卡片”升级为更像真实 AI 面试产品的训练工作台。

**Architecture:** 不引入新前端框架，继续使用现有 `index.html`、`styles.css`、`app.js` 和 Node `.mjs` 前端测试。先用测试锁定关键 DOM 结构和文案，再调整 HTML 结构、渲染函数和 CSS，使面试主区域呈现聊天流、轻量进度线、Agent Insight Bar 和回答 composer。

**Tech Stack:** Vanilla HTML、CSS、JavaScript、Node `.mjs` tests、FastAPI 静态文件服务。

---

## File Structure

- Modify: `index.html`
  - 给右侧面试区域增加工作台语义 class。
  - 将回答输入区外层命名为 `answer-composer`。
  - 保留所有现有 id，避免破坏 JS 查询。

- Modify: `app.js`
  - 调整 `renderStageStepper()` 输出轻量进度线结构。
  - 调整 `renderConversation()` 输出 AI / 用户聊天消息结构。
  - 调整 `renderAgentDecision()` 输出 Agent Insight Bar 结构。
  - 不改后端 API 请求字段。

- Modify: `styles.css`
  - 重写面试工作台、进度线、聊天流、Agent Insight Bar、回答 composer 的视觉样式。
  - 压缩左侧档案区视觉重量。
  - 增加移动端布局约束，避免文本和按钮溢出。

- Modify: `tests/frontend_interview_flow.test.mjs`
  - 更新断言，覆盖聊天流、紧凑进度、Agent Insight Bar。

- Create: `tests/frontend_workbench_layout.test.mjs`
  - 只检查静态 HTML/CSS/JS 关键结构，不启动浏览器。
  - 作为 UI 重构的结构回归测试。

---

### Task 1: 增加工作台结构测试

**Files:**
- Create: `tests/frontend_workbench_layout.test.mjs`
- Modify: `tests/frontend_interview_flow.test.mjs`

- [ ] **Step 1: Write the failing static layout test**

Create `tests/frontend_workbench_layout.test.mjs` with:

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("index.html", "utf8");
const css = fs.readFileSync("styles.css", "utf8");
const app = fs.readFileSync("app.js", "utf8");

assert.match(html, /class="interview-panel workbench-panel"/);
assert.match(html, /class="interview-header workbench-header"/);
assert.match(html, /class="answer-box answer-composer"/);

assert.match(app, /class="progress-dot/);
assert.match(app, /class="conversation-message interviewer-message/);
assert.match(app, /class="conversation-message candidate-message/);
assert.match(app, /class="agent-insight-grid"/);

assert.match(css, /\.workbench-panel/);
assert.match(css, /\.compact-progress/);
assert.match(css, /\.conversation-message/);
assert.match(css, /\.agent-insight-bar/);
assert.match(css, /\.answer-composer/);
```

- [ ] **Step 2: Run the failing static layout test**

Run:

```powershell
node tests/frontend_workbench_layout.test.mjs
```

Expected:

```text
AssertionError
```

The failure should come from missing new workbench class names or render structures.

- [ ] **Step 3: Update frontend flow test assertions**

In `tests/frontend_interview_flow.test.mjs`, extend the final assertions:

```javascript
assert.match(context.__result.agentDecisionHtml, /agent-insight-grid/);
assert.match(context.__result.agentDecisionHtml, /考察点/);
assert.match(context.__result.agentDecisionHtml, /触发规则/);
assert.match(context.__result.conversationHtml, /conversation-message interviewer-message/);
assert.match(context.__result.conversationHtml, /message-bubble/);
assert.match(context.__result.stageStepperHtml, /compact-progress/);
assert.match(context.__result.stageStepperHtml, /progress-dot/);
```

- [ ] **Step 4: Run the focused frontend flow test**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected:

```text
AssertionError
```

The failure should confirm current render functions do not yet output workbench structures.

---

### Task 2: Update HTML and JS structure

**Files:**
- Modify: `index.html`
- Modify: `app.js`

- [ ] **Step 1: Update static HTML class names**

In `index.html`, change:

```html
<section class="interview-panel" aria-label="模拟面试">
```

to:

```html
<section class="interview-panel workbench-panel" aria-label="模拟面试">
```

Change:

```html
<header class="interview-header">
```

to:

```html
<header class="interview-header workbench-header">
```

Change:

```html
<label class="answer-box">
```

to:

```html
<label class="answer-box answer-composer">
```

- [ ] **Step 2: Update progress renderer**

In `app.js`, update `renderStageStepper()` so `stageStepper.innerHTML` wraps progress items in:

```javascript
<div class="compact-progress">
  ...
</div>
```

Each item should include:

```javascript
<span class="progress-dot">${index + 1}</span>
<span class="progress-state">${status === "active" ? "当前" : status === "done" ? "完成" : "待进行"}</span>
```

Keep `aria-label` with the full stage title.

- [ ] **Step 3: Update conversation renderer**

In `app.js`, update `renderConversation()` so AI messages use:

```javascript
<article class="conversation-message interviewer-message">
  <div class="message-avatar">AI</div>
  <div class="message-bubble">
    <span class="message-role">AI 面试官 · ${question.focus || question.stage}</span>
    <p>${question.prompt}</p>
  </div>
</article>
```

Candidate messages use:

```javascript
<article class="conversation-message candidate-message">
  <div class="message-avatar">你</div>
  <div class="message-bubble">
    <span class="message-role">候选人回答</span>
    <p>${answer.answer || "未作答"}</p>
  </div>
</article>
```

- [ ] **Step 4: Update Agent decision renderer**

In `app.js`, update `renderAgentDecision()` so it renders:

```javascript
<div class="agent-insight-bar">
  <div class="agent-insight-head">
    <span>${agentModeLabel(decision.agentMode || agentModeInput?.value || "interview")}</span>
    <strong>${decision.nextAction || "select_action"}</strong>
  </div>
  <div class="agent-insight-grid">
    <span>考察点：${question.focus || decision.focus || "综合追问"}</span>
    <span>难度：${decision.difficulty || question.stability || "动态"}</span>
    <span>触发规则：${rules || "未记录"}</span>
  </div>
  <p>${summary}</p>
</div>
```

- [ ] **Step 5: Run focused frontend tests**

Run:

```powershell
node tests/frontend_workbench_layout.test.mjs
node tests/frontend_interview_flow.test.mjs
```

Expected:

```text
exit code 0
```

---

### Task 3: Update workbench visual styling

**Files:**
- Modify: `styles.css`

- [ ] **Step 1: Add workbench panel styles**

Add CSS rules for:

```css
.workbench-panel {}
.workbench-header {}
.compact-progress {}
.progress-step {}
.progress-dot {}
.progress-state {}
.conversation-message {}
.interviewer-message {}
.candidate-message {}
.message-avatar {}
.message-bubble {}
.message-role {}
.agent-insight-bar {}
.agent-insight-head {}
.agent-insight-grid {}
.answer-composer {}
```

Rules must keep cards at `8px` border radius or less, avoid decorative orbs, and keep text from overflowing buttons or bubbles.

- [ ] **Step 2: Reduce old bulky stepper styling**

Adjust existing `.stage-stepper` and related rules so the progress area is compact:

```css
.stage-stepper {
  overflow-x: auto;
  padding-bottom: 4px;
}
```

Avoid large vertical pill shapes.

- [ ] **Step 3: Add responsive rules**

Inside existing media queries, ensure:

```css
.workspace {
  grid-template-columns: 1fr;
}

.conversation-message,
.message-bubble {
  max-width: 100%;
}

.agent-insight-grid {
  grid-template-columns: 1fr;
}
```

- [ ] **Step 4: Run frontend scripts**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
exit code 0
```

---

### Task 4: Browser verification

**Files:**
- No source changes unless browser verification reveals layout defects.

- [ ] **Step 1: Ensure local server is running**

Run:

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

If another server is already running at `http://localhost:8000/`, reuse it.

- [ ] **Step 2: Open desktop viewport**

Use Codex in-app browser to open:

```text
http://localhost:8000/
```

Check:

- Right side looks like a workbench.
- Progress line is compact.
- Chat messages are visually separated.
- Agent Insight Bar is readable.
- Input composer is not too tall.

- [ ] **Step 3: Open mobile/narrow viewport**

Use browser screenshot or viewport adjustment.

Check:

- Left and right panels do not overlap.
- Buttons do not overflow.
- Progress line remains usable.
- Long Chinese text wraps cleanly.

- [ ] **Step 4: Run full verification**

Run:

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
backend tests pass
frontend scripts exit code 0
```

---

## Self-Review

- Spec coverage: This plan covers workbench header, compact progress, chat stream, Agent Insight Bar, answer composer, responsive behavior, frontend tests, backend regression tests, and browser verification.
- Placeholder scan: No task uses TBD/TODO or unspecified “add tests” wording.
- Type consistency: Existing ids remain unchanged. New class names are `workbench-panel`, `workbench-header`, `compact-progress`, `conversation-message`, `message-bubble`, `agent-insight-bar`, `agent-insight-grid`, and `answer-composer`.
