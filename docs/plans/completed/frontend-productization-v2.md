# Frontend Productization V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current feature-stacked single page into a clearer AI interview training workbench that productizes existing RAG and Agent engineering capabilities without changing backend contracts.

**Architecture:** Keep the current native frontend architecture: `index.html`, `styles.css`, `app.js`, and Node `.mjs` tests. Add product structure in small slices: first navigation and section hierarchy, then interview workbench explanations, then RAG, training, history, and admin panels. Existing FastAPI APIs stay compatible; RAG and Agent backend logic are only consumed and displayed, not rebuilt.

**Tech Stack:** Native HTML, CSS, JavaScript, FastAPI static serving, Node `.mjs` tests, pytest, browser verification.

---

## Scope Rules

Implement:

- Product-level section hierarchy for:
  - Account and profile.
  - Interview workbench.
  - Training center.
  - Knowledge base and RAG.
  - Admin dashboard.
- User-readable RAG and Agent explanation cards.
- Developer/debug expandable sections for `nodeTrace`, `toolCalls`, RAG query variants, and rerank details.
- Responsive layout and no-horizontal-overflow checks.
- Focused progress updates and one concise learning document.

Do not implement:

- React, Vue, Next.js, or any new frontend framework.
- LangGraph or LangChain runtime.
- Docker, Nginx, cloud deployment.
- RAG retrieval rewrites or Agent Orchestrator rewrites.
- Large backend API changes.
- Redis, Celery, Qdrant, pgvector.

## File Map

Primary files:

- `index.html`
  - Add product navigation and stable section anchors.
  - Keep existing DOM ids used by current `app.js` and tests.

- `styles.css`
  - Add layout system for product sections, tabs, explanation cards, responsive constraints, and overflow protection.

- `app.js`
  - Add lightweight section switching.
  - Improve rendering helpers for Agent explanations, RAG explanations, training tasks, and admin panels.
  - Keep existing API helpers and auth state.

Frontend tests:

- Create: `tests/frontend_product_navigation.test.mjs`
- Modify: `tests/frontend_workbench_layout.test.mjs`
- Modify: `tests/frontend_interview_flow.test.mjs`
- Modify: `tests/frontend_rag_documents.test.mjs`
- Modify: `tests/frontend_rag_quality.test.mjs`
- Modify: `tests/frontend_agent_logs.test.mjs`
- Modify: `tests/frontend_training_center.test.mjs`
- Modify: `tests/frontend_admin_dashboard.test.mjs`

Docs:

- Modify: `docs/roadmap/project-progress.md`
- Create if useful: `docs/learning/06-前端产品化重构如何承接RAG和Agent能力.md`

---

## Stage 0: Baseline And Current UI Audit

**Learning point before coding:** 前端产品化重构不是一上来改颜色，而是先建立基线：当前页面有哪些功能、哪些测试保护了它、哪些视觉问题不能在重构中变坏。先有基线，后面才知道改动有没有破坏核心流程。

### Task 0.1: Run Baseline Verification

**Files:**
- Read: `docs/roadmap/current-state.md`
- Read: `docs/specs/active/frontend-productization-v2-design.md`
- No code changes.

- [ ] **Step 1: Run backend baseline**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All backend tests pass.
```

- [ ] **Step 2: Run frontend baseline**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
All frontend tests pass with no failure output.
```

- [ ] **Step 3: Record baseline in progress doc**

Modify `docs/roadmap/project-progress.md` and add a short Frontend Productization V2 section with:

```text
## 前端产品化重构 V2

状态：已启动。

当前目标：
- 按 `docs/specs/active/frontend-productization-v2-design.md` 推进前端产品化重构。
- 不重复开发 RAG / Agent 底层链路。
- 先建立测试基线，再分阶段整理页面信息架构。

基线验证：
- 后端：运行 `python -m pytest -q` 后记录真实结果。
- 前端：运行全部 `.mjs` 测试后记录真实结果。
```

Only fill the command result after actually running the command.

---

## Stage 1: Product Navigation And Section Hierarchy

**Learning point before coding:** 信息架构是前端工程化的一部分。一个页面可以仍然是单页应用，但用户必须能分清“我现在在面试工作台、训练中心、知识库还是后台”。本阶段先建立导航和区域层级，不急着改业务逻辑。

### Task 1.1: Add Product Navigation Tests

**Files:**
- Create: `tests/frontend_product_navigation.test.mjs`
- Read: `index.html`
- Read: `styles.css`
- Read: `app.js`

- [ ] **Step 1: Write failing navigation structure test**

Create `tests/frontend_product_navigation.test.mjs`:

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("index.html", "utf8");
const css = fs.readFileSync("styles.css", "utf8");
const app = fs.readFileSync("app.js", "utf8");

assert.match(html, /id="productNav"/);
assert.match(html, /data-product-section="account-profile"/);
assert.match(html, /data-product-section="interview-workbench"/);
assert.match(html, /data-product-section="training-center"/);
assert.match(html, /data-product-section="rag-knowledge"/);
assert.match(html, /data-product-section="admin-dashboard"/);

assert.match(html, /data-section-target="account-profile"/);
assert.match(html, /data-section-target="interview-workbench"/);
assert.match(html, /data-section-target="training-center"/);
assert.match(html, /data-section-target="rag-knowledge"/);
assert.match(html, /data-section-target="admin-dashboard"/);

assert.match(css, /\.product-nav/);
assert.match(css, /\.product-section/);
assert.match(css, /\.product-section\.is-active/);

assert.match(app, /function switchProductSection/);
assert.match(app, /function bindProductNavigation/);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node tests/frontend_product_navigation.test.mjs
```

Expected:

```text
FAIL because productNav and product section markers do not exist yet.
```

### Task 1.2: Implement Product Navigation Markup And Styles

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add product navigation in `index.html`**

Add a nav near the topbar/workspace boundary:

```html
<nav id="productNav" class="product-nav" aria-label="产品功能导航">
  <button class="product-nav-item is-active" type="button" data-section-target="interview-workbench">面试工作台</button>
  <button class="product-nav-item" type="button" data-section-target="account-profile">账号与档案</button>
  <button class="product-nav-item" type="button" data-section-target="training-center">训练中心</button>
  <button class="product-nav-item" type="button" data-section-target="rag-knowledge">知识库与 RAG</button>
  <button class="product-nav-item" type="button" data-section-target="admin-dashboard">管理员后台</button>
</nav>
```

Wrap or mark existing major panels with `data-product-section`:

```html
<section class="workspace product-section is-active" data-product-section="interview-workbench">
```

```html
<section class="user-center-panel product-section" data-product-section="account-profile">
```

```html
<section class="training-center-panel product-section" data-product-section="training-center">
```

```html
<section class="rag-doc-panel product-section" data-product-section="rag-knowledge">
```

For RAG debug panels, keep them inside the RAG section if moving is low risk; otherwise mark them as:

```html
<section class="debug-panel product-section" data-product-section="rag-knowledge">
<section class="agent-debug-panel product-section" data-product-section="rag-knowledge">
```

For admin:

```html
<section id="adminDashboardPanel" class="admin-dashboard-panel product-section hidden" data-product-section="admin-dashboard">
```

Keep all existing ids unchanged.

- [ ] **Step 2: Add navigation styles in `styles.css`**

Add:

```css
.product-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px 0;
}

.product-nav-item {
  border: 1px solid var(--border-color, #d9e2ec);
  background: #fff;
  color: var(--text-color, #172033);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 14px;
  cursor: pointer;
}

.product-nav-item.is-active {
  background: #172033;
  color: #fff;
  border-color: #172033;
}

.product-section {
  scroll-margin-top: 16px;
}

.product-section:not(.is-active).is-section-collapsed {
  display: none;
}

@media (max-width: 720px) {
  .product-nav {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .product-nav-item {
    width: 100%;
    min-width: 0;
  }
}
```

Use existing CSS variables if available; otherwise keep these values stable and readable.

### Task 1.3: Implement Product Section Switching

**Files:**
- Modify: `app.js`
- Test: `tests/frontend_product_navigation.test.mjs`

- [ ] **Step 1: Add section switching helpers**

Add near other DOM constants:

```javascript
const productNav = document.querySelector("#productNav");
const productNavItems = Array.from(document.querySelectorAll("[data-section-target]"));
const productSections = Array.from(document.querySelectorAll("[data-product-section]"));
```

Add helper functions near other render helpers:

```javascript
function switchProductSection(sectionName) {
  const targetName = sectionName || "interview-workbench";
  productSections.forEach((section) => {
    const isActive = section.dataset.productSection === targetName;
    section.classList.toggle("is-active", isActive);
    section.classList.toggle("is-section-collapsed", !isActive);
  });
  productNavItems.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.sectionTarget === targetName);
  });
}

function bindProductNavigation() {
  if (!productNav) {
    return;
  }
  productNav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-section-target]");
    if (!button) {
      return;
    }
    switchProductSection(button.dataset.sectionTarget);
  });
}
```

Call during initialization near existing event binding:

```javascript
bindProductNavigation();
switchProductSection("interview-workbench");
```

- [ ] **Step 2: Run focused navigation test**

Run:

```powershell
node tests/frontend_product_navigation.test.mjs
```

Expected:

```text
PASS
```

- [ ] **Step 3: Run current frontend layout test**

Run:

```powershell
node tests/frontend_workbench_layout.test.mjs
```

Expected:

```text
PASS
```

---

## Stage 2: Interview Workbench Explanation Layer

**Learning point before coding:** RAG 和 Agent 的调试字段不能直接丢给普通用户。产品化做法是把技术字段转译成“为什么这么问、参考了什么、下一步怎么练”，同时保留开发者展开调试的入口。

### Task 2.1: Test User-Readable Agent Decision Summary

**Files:**
- Modify: `tests/frontend_interview_flow.test.mjs`
- Modify: `tests/frontend_agent_logs.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add assertions for productized decision summary**

In `tests/frontend_interview_flow.test.mjs`, extend the mocked next-question response to include:

```javascript
agentDecision: {
  nextAction: "lower_difficulty",
  difficulty: "basic",
  focus: "RAG 质量评估",
  reason: "上一轮回答较弱，先拆小概念。",
  guardrailApplied: true,
  fallbackUsed: false,
  selectedTrainingTask: {
    weakTag: "rag_quality",
    title: "RAG 质量评估专项训练",
    masteryScore: 35
  },
  trainingTemplateHint: {
    enabled: true,
    weakTag: "rag_quality",
    label: "RAG 质量评估",
    recommendedQuestion: "Hit@K、MRR 和关键词覆盖率分别解决什么问题？"
  },
  toolCalls: [
    { toolName: "retrieve_role_knowledge", success: true, hitCount: 2, elapsedMs: 12 },
    { toolName: "retrieve_question_bank", success: true, hitCount: 1, elapsedMs: 8 }
  ],
  nodeTrace: [
    { nodeName: "observe_state", fallbackUsed: false, elapsedMs: 1, inputSummary: {}, outputSummary: {} },
    { nodeName: "select_action", fallbackUsed: false, elapsedMs: 3, inputSummary: {}, outputSummary: { nextAction: "lower_difficulty" } }
  ]
}
```

Assert rendered HTML contains:

```javascript
assert.match(getElement("#agentDecisionPanel").innerHTML, /为什么这样问/);
assert.match(getElement("#agentDecisionPanel").innerHTML, /降低难度/);
assert.match(getElement("#agentDecisionPanel").innerHTML, /RAG 质量评估专项训练/);
assert.match(getElement("#agentDecisionPanel").innerHTML, /岗位知识库/);
assert.match(getElement("#agentDecisionPanel").innerHTML, /开发者调试/);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected:

```text
FAIL because the current decision panel does not yet render the new productized labels.
```

### Task 2.2: Implement Productized Agent Decision Panel

**Files:**
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add Chinese action labels**

Extend or add helper:

```javascript
function agentActionProductLabel(action) {
  return {
    deepen: "继续深挖",
    lower_difficulty: "降低难度",
    switch_topic: "切换话题",
    finish: "结束面试",
    coach_explain: "学习辅导",
    select_action: "选择下一步"
  }[action] || action || "选择下一步";
}
```

- [ ] **Step 2: Add tool call readable summary**

Add:

```javascript
function agentToolReadableName(toolName = "") {
  if (toolName.includes("role")) return "岗位知识库";
  if (toolName.includes("question")) return "题库 RAG";
  if (toolName.includes("memory")) return "候选人画像";
  return toolName || "工具调用";
}

function renderToolCallChips(toolCalls = []) {
  if (!Array.isArray(toolCalls) || toolCalls.length === 0) {
    return `<span class="agent-tool-chip muted">暂无工具调用摘要</span>`;
  }
  return toolCalls
    .slice(0, 3)
    .map((tool) => {
      const name = agentToolReadableName(String(tool.toolName || ""));
      const hitCount = Number(tool.hitCount ?? tool.outputSummary?.hitCount ?? 0);
      return `<span class="agent-tool-chip">${name} · 命中 ${hitCount} 条</span>`;
    })
    .join("");
}
```

- [ ] **Step 3: Update `renderAgentDecision()`**

Make the top-level panel include:

```html
<div class="agent-product-explain">
  <div class="agent-product-head">
    <span>为什么这样问</span>
    <strong>${agentActionProductLabel(decision.nextAction)}</strong>
  </div>
  <p>${summary}</p>
  <div class="agent-tool-chip-row">${renderToolCallChips(decision.toolCalls || [])}</div>
  <details class="agent-debug-details">
    <summary>开发者调试</summary>
    ${renderAgentDebugPanel(decision)}
  </details>
</div>
```

Keep existing `agent-insight-bar` fields if current tests depend on them, but wrap or augment them instead of deleting.

- [ ] **Step 4: Add CSS**

Add:

```css
.agent-product-explain {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #f8fbff;
}

.agent-product-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.agent-tool-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.agent-tool-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid #c9d7e5;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  background: #fff;
  overflow-wrap: anywhere;
}

.agent-tool-chip.muted {
  color: #667085;
}

.agent-debug-details summary {
  cursor: pointer;
  font-weight: 700;
}
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
node tests/frontend_agent_logs.test.mjs
```

Expected:

```text
PASS
```

---

## Stage 3: Knowledge Base And RAG Productization

**Learning point before coding:** RAG 工程化已经有生命周期、权限、query rewrite、rerank 和质量指标。前端产品化要做的是把这些信息变成“知识库是否可用、为什么命中、哪里质量差”的可读界面。

### Task 3.1: Extend RAG Document Frontend Test

**Files:**
- Modify: `tests/frontend_rag_documents.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Update RAG document mock payload**

In `tests/frontend_rag_documents.test.mjs`, update mock document list item:

```javascript
{
  id: 1,
  title: "FastAPI 岗位知识",
  knowledgeBase: "role_knowledge",
  status: "enabled",
  visibility: "private",
  chunkCount: 2,
  duplicateChunkCount: 1,
  metadata: { positionTag: "python_backend_intern", category: "technical" },
  createdAt: "2026-06-04T12:00:00"
}
```

Update detail mock:

```javascript
document: {
  id: 2,
  title: "RAG 日志题库",
  knowledgeBase: "question_bank",
  status: "enabled",
  visibility: "public",
  chunkCount: 1,
  duplicateChunkCount: 0,
  metadata: { positionTag: "ai_app_intern" }
}
```

Add assertions:

```javascript
assert.match(getElement("#ragDocumentList").innerHTML, /启用/);
assert.match(getElement("#ragDocumentList").innerHTML, /私有/);
assert.match(getElement("#ragDocumentList").innerHTML, /重复 chunk 1/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /公开/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /positionTag/);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node tests/frontend_rag_documents.test.mjs
```

Expected:

```text
FAIL because current RAG document cards do not render all lifecycle and metadata labels.
```

### Task 3.2: Render RAG Lifecycle And Metadata

**Files:**
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add label helpers**

Add near RAG render helpers:

```javascript
function ragStatusLabel(status) {
  return {
    enabled: "启用",
    disabled: "停用",
    archived: "归档"
  }[status] || "未知状态";
}

function ragVisibilityLabel(visibility) {
  return {
    private: "私有",
    public: "公开"
  }[visibility] || "未知权限";
}

function renderMetadataPreview(metadata = {}) {
  const entries = Object.entries(metadata || {}).slice(0, 4);
  if (!entries.length) {
    return `<span class="rag-meta-chip muted">无 metadata</span>`;
  }
  return entries
    .map(([key, value]) => `<span class="rag-meta-chip">${key}: ${String(value)}</span>`)
    .join("");
}
```

- [ ] **Step 2: Update `renderRagDocumentList()` and detail renderer**

Ensure each document card includes:

```html
<div class="rag-doc-meta-row">
  <span>${ragStatusLabel(document.status)}</span>
  <span>${ragVisibilityLabel(document.visibility)}</span>
  <span>chunk ${document.chunkCount ?? 0}</span>
  <span>重复 chunk ${document.duplicateChunkCount ?? 0}</span>
</div>
<div class="rag-meta-chip-row">${renderMetadataPreview(document.metadata || {})}</div>
```

For detail, include the same labels plus chunk list.

- [ ] **Step 3: Add CSS**

Add:

```css
.rag-doc-meta-row,
.rag-meta-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.rag-doc-meta-row span,
.rag-meta-chip {
  border: 1px solid #d9e2ec;
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 12px;
  background: #fff;
  overflow-wrap: anywhere;
}

.rag-meta-chip.muted {
  color: #667085;
}
```

- [ ] **Step 4: Run focused RAG document test**

Run:

```powershell
node tests/frontend_rag_documents.test.mjs
```

Expected:

```text
PASS
```

### Task 3.3: Improve RAG Explanation Cards

**Files:**
- Modify: `tests/frontend_rag_quality.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add assertions for query and rerank explanation**

Extend mocked RAG debug payload to include:

```javascript
hits: [
  {
    title: "RAG 质量评估与可观测面板",
    matchedQueryVariant: "stage",
    queryVariants: [{ name: "base" }, { name: "role" }, { name: "stage" }],
    rerankScore: 0.95,
    rankChange: 1,
    rerankExplanation: "rerankScore=0.95, rank 2 -> 1"
  }
]
```

Assert:

```javascript
assert.match(getElement("#ragDebugContent").innerHTML, /多路 query/);
assert.match(getElement("#ragDebugContent").innerHTML, /stage/);
assert.match(getElement("#ragDebugContent").innerHTML, /重排/);
assert.match(getElement("#ragDebugContent").innerHTML, /rerankScore=0.95/);
```

- [ ] **Step 2: Update RAG explanation rendering**

In `renderRagExplanationPanel()` or related RAG debug renderer, add compact fields:

```html
<p>多路 query：${variantNames}</p>
<p>命中 query：${matchedQueryVariant}</p>
<p>重排：${rerankExplanation}</p>
```

Guard every optional field:

```javascript
const variantNames = Array.isArray(hit.queryVariants)
  ? hit.queryVariants.map((item) => item.name || item.query || "").filter(Boolean).join(" / ")
  : "";
```

Do not render `undefined`.

- [ ] **Step 3: Run RAG quality test**

Run:

```powershell
node tests/frontend_rag_quality.test.mjs
```

Expected:

```text
PASS
```

---

## Stage 4: Training Center And History Productization

**Learning point before coding:** 训练闭环的产品意义是“面试后知道下一步练什么”。训练任务不应该只是列表，而应该像行动计划：薄弱点、推荐问题、掌握度、下一步动作。

### Task 4.1: Strengthen Training Center Tests

**Files:**
- Modify: `tests/frontend_training_center.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add assertions for action-plan wording**

Ensure test task includes:

```javascript
{
  weakTag: "rag_quality",
  title: "RAG 质量评估专项训练",
  description: "练习 Hit@K、MRR 和关键词覆盖率。",
  masteryScore: 35,
  priority: "high",
  recommendedQuestion: "Hit@K、MRR 和关键词覆盖率分别解决什么问题？"
}
```

Assert detail panel contains:

```javascript
assert.match(getElement("#trainingTaskDetail").innerHTML, /下一步训练/);
assert.match(getElement("#trainingTaskDetail").innerHTML, /掌握度/);
assert.match(getElement("#trainingTaskDetail").innerHTML, /Hit@K/);
assert.match(getElement("#trainingTaskDetail").innerHTML, /高优先级/);
```

- [ ] **Step 2: Update training detail renderer**

In `renderTrainingCenter()`, make selected task detail include:

```html
<div class="training-action-plan">
  <span>下一步训练</span>
  <strong>${task.title}</strong>
  <p>${task.description || "围绕该薄弱点完成一次结构化回答练习。"}</p>
  <p>掌握度：${task.masteryScore ?? 0}</p>
  <p>优先级：${priorityLabel(task.priority)}</p>
</div>
```

Add `priorityLabel()` if missing:

```javascript
function priorityLabel(priority) {
  return {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级"
  }[priority] || "中优先级";
}
```

- [ ] **Step 3: Run training tests**

Run:

```powershell
node tests/frontend_training_center.test.mjs
node tests/frontend_training_actions.test.mjs
node tests/frontend_training_events.test.mjs
```

Expected:

```text
PASS
```

---

## Stage 5: Admin Dashboard Productization

**Learning point before coding:** 管理员后台的价值不是“能看到一堆 JSON”，而是帮助排查系统质量。RAG 低质量召回和 Agent 决策日志应该用问题类型、原因和建议动作组织起来。

### Task 5.1: Improve Admin Quality Panel Tests

**Files:**
- Modify: `tests/frontend_admin_dashboard.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`

- [ ] **Step 1: Add assertions for quality issue explanations**

Assert admin dashboard contains:

```javascript
assert.match(getElement("#adminDashboardContent").innerHTML, /质量问题分布/);
assert.match(getElement("#adminDashboardContent").innerHTML, /空召回/);
assert.match(getElement("#adminDashboardContent").innerHTML, /弱召回/);
assert.match(getElement("#adminDashboardContent").innerHTML, /未进入 Prompt/);
assert.match(getElement("#adminDashboardContent").innerHTML, /建议动作/);
```

- [ ] **Step 2: Update `renderAdminRagQuality()`**

Render:

```html
<section class="admin-rag-quality-section">
  <h3>质量问题分布</h3>
  <div class="admin-quality-grid">
    ...
  </div>
  <h4>建议动作</h4>
  ...
</section>
```

Use existing `formatRagQualityIssue()` and recommendation data.

- [ ] **Step 3: Run admin tests**

Run:

```powershell
node tests/frontend_admin_dashboard.test.mjs
node tests/frontend_admin_permissions.test.mjs
```

Expected:

```text
PASS
```

---

## Stage 6: Documentation, Progress, And Browser Verification

**Learning point before coding:** 工程项目不是改完页面就结束，还要留下可追溯的进度、测试证据和学习总结。这样后面继续开发或面试复盘时不会再出现路线混乱。

### Task 6.1: Add One Concise Learning Document

**Files:**
- Create: `docs/learning/06-前端产品化重构如何承接RAG和Agent能力.md`

- [ ] **Step 1: Create concise learning doc**

Write sections:

```markdown
# 前端产品化重构如何承接 RAG 和 Agent 能力

## 1. 为什么不是重写 RAG / Agent

## 2. 信息架构怎么拆

## 3. RAG 可解释怎么展示

## 4. Agent 可观测怎么展示

## 5. 面试时怎么讲
```

Keep it concise. Do not duplicate all old learning docs.

### Task 6.2: Update Progress Record

**Files:**
- Modify: `docs/roadmap/project-progress.md`

- [ ] **Step 1: Add completion summary**

Append or update the Frontend Productization V2 section:

```text
状态：已完成阶段性版本。

已完成内容：
- 信息架构和导航整理。
- 面试训练工作台解释层优化。
- RAG 文档和命中解释产品化。
- 训练中心行动计划展示。
- 管理员质量面板优化。

验证命令：
- python -m pytest -q
- Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
- 浏览器桌面端和移动端验证 http://127.0.0.1:8000/
```

Only mark a line complete after the command or browser verification has actually run.

### Task 6.3: Full Verification

**Files:**
- No code changes unless verification finds issues.

- [ ] **Step 1: Run backend full suite**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Run frontend full suite**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
PASS
```

- [ ] **Step 3: Browser verify desktop and mobile**

Start server if needed:

```powershell
python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify:

```text
http://127.0.0.1:8000/
```

Desktop checks:

- Page opens.
- Product navigation visible.
- No `undefined`.
- No horizontal overflow.
- Interview workbench, RAG section, training center, and admin section are reachable.

Mobile checks:

- Product navigation wraps cleanly.
- No horizontal overflow.
- Cards do not overlap.
- Buttons remain readable.

---

## Final Completion Criteria

The stage is complete only when all are true:

- `docs/plans/active/frontend-productization-v2.md` exists and tracks the work.
- Product navigation and section hierarchy are implemented.
- RAG and Agent existing capabilities are displayed in user-readable and debug-friendly layers.
- Training center and admin dashboard are more action-oriented and readable.
- Backend full test suite passes.
- Frontend full `.mjs` suite passes.
- Browser desktop and mobile checks pass.
- `docs/roadmap/project-progress.md` records actual verification results.
- No backend API contract was broken.
- No React / Vue / Next.js / LangGraph / Docker / Nginx / Redis / Celery was introduced.
