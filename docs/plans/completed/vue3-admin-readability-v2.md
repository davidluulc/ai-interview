# Vue3 管理员后台可读性 V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把管理员后台的 RAG 质量、RAG 文档和 Agent 日志从原始工程字段升级为可读诊断视图。

**Architecture:** 保持后端接口不变，只在 `AdminPage.vue` 做展示层映射和说明文案。测试通过 `admin-page.test.ts` 验证页面能把原始字段翻译成中文诊断。

**Tech Stack:** Vue 3、Pinia mock、Vitest、Vue Test Utils。

---

### Task 1: 前端测试先行

**Files:**
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: 增加可读性断言**

新增测试断言页面包含：

```ts
expect(text).toContain("用于判断 RAG 是不是找到了合适资料");
expect(text).toContain("空召回：没有找到资料");
expect(text).toContain("岗位知识库");
expect(text).toContain("建议动作：补充岗位知识库或题库内容");
expect(text).toContain("启用中");
expect(text).toContain("公共资料");
expect(text).toContain("可能存在重复切片");
expect(text).toContain("兜底规则已启用");
expect(text).toContain("下一步动作：切换话题");
expect(text).not.toContain("undefined");
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: 测试失败，原因是页面尚未展示新增中文诊断文案。

### Task 2: 实现展示层翻译

**Files:**
- Modify: `frontend/src/pages/app/AdminPage.vue`

- [ ] **Step 1: 增加 helper 函数**

新增用于展示映射的函数：

```ts
function issueLabel(issueType?: string): string
function issueAdvice(item: AdminRagQualityItem): string
function retrieverLabel(value?: string): string
function documentStatusLabel(value?: string): string
function documentVisibilityLabel(value?: string): string
function documentRiskHint(document: AdminRagDocument): string
function actionExplanation(action?: string): string
function fallbackLabel(log: AdminAgentLog): string
```

- [ ] **Step 2: 修改 RAG 质量诊断 UI**

把原始 issue type 改成中文诊断标签，并展示建议动作。

- [ ] **Step 3: 修改 RAG 文档概览 UI**

把知识库类型、状态、可见性翻译成中文，并在重复 chunk 大于 0 时展示风险提示。

- [ ] **Step 4: 修改 Agent 决策日志 UI**

把 action 和 fallback 展示成可读决策轨迹。

### Task 3: 验证

**Files:**
- Test: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: 运行单测**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: PASS。

- [ ] **Step 2: 运行前端测试**

```powershell
cd frontend
npm.cmd run test
```

Expected: PASS。

- [ ] **Step 3: 运行前端构建**

```powershell
cd frontend
npm.cmd run build
```

Expected: PASS。

- [ ] **Step 4: 浏览器验证**

打开：

```text
http://127.0.0.1:5173/vue/app/admin
```

验证桌面端和移动端没有明显错位，三个后台诊断板块比原来更容易理解。
