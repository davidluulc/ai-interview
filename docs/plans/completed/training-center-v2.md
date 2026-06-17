# Training Center V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Vue3 训练中心从任务列表升级成专项训练工作台，承接报告 weakTag、训练任务和再面试闭环。

**Architecture:** 不改训练后端 API，不动 RAG / Agent / LangGraph 主流程。通过扩展 Pinia training store 的 computed/filter 状态，并新增 Vue3 小组件来完成训练中心产品化。

**Tech Stack:** Vue3, Vite, TypeScript, Pinia, Vitest, Vue Test Utils, existing FastAPI training APIs.

---

## 0. 执行边界

优先修改：

```text
frontend/src/stores/training.ts
frontend/src/stores/training.test.ts
frontend/src/pages/app/TrainingPage.vue
frontend/src/pages/app/training-page.test.ts
frontend/src/components/training/
docs/learning/
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

禁止事项：

- 不新增或重写训练后端 API。
- 不改 `/api/interview/next-question`。
- 不改 RAG、Agent、LangGraph 主流程。
- 不做 Docker、Nginx、VPS、云服务器上线。
- 不把本阶段扩展成全站 UI 重构。

每轮开发前先用中文解释本轮要学的训练闭环或 Vue3 前端工程化知识点。

---

## Task 1: Training Store V2 State

**Files:**

- Modify: `frontend/src/stores/training.test.ts`
- Modify: `frontend/src/stores/training.ts`

- [ ] **Step 1: 写 failing store tests**

在 `frontend/src/stores/training.test.ts` 增加测试，覆盖：

```ts
it("computes training overview metrics", () => {
  const store = useTrainingStore();
  store.tasks = [
    { id: 1, weakTag: "agent_tool_calling", title: "A", description: "", status: "todo", priority: "high", masteryScore: 40 },
    { id: 2, weakTag: "rag_quality", title: "B", description: "", status: "in_progress", priority: "medium", masteryScore: 60 },
    { id: 3, weakTag: "rag_quality", title: "C", description: "", status: "done", priority: "low", masteryScore: 80 },
    { id: 4, weakTag: "behavioral", title: "D", description: "", status: "archived", priority: "low", masteryScore: 20 }
  ];

  expect(store.todoTasks).toHaveLength(1);
  expect(store.inProgressTasks).toHaveLength(1);
  expect(store.doneTasks).toHaveLength(1);
  expect(store.archivedTasks).toHaveLength(1);
  expect(store.averageMastery).toBe(50);
});

it("groups training tasks by weak tag", () => {
  const store = useTrainingStore();
  store.tasks = [
    { id: 1, weakTag: "rag_quality", weakLabel: "RAG 质量", title: "A", description: "", status: "todo", priority: "high", masteryScore: 40 },
    { id: 2, weakTag: "rag_quality", weakLabel: "RAG 质量", title: "B", description: "", status: "done", priority: "medium", masteryScore: 80 }
  ];

  expect(store.weakTagGroups).toEqual([
    expect.objectContaining({
      weakTag: "rag_quality",
      weakLabel: "RAG 质量",
      total: 2,
      averageMastery: 60,
      highestPriority: "high"
    })
  ]);
});

it("filters visible tasks by status and weak tag", () => {
  const store = useTrainingStore();
  store.tasks = [
    { id: 1, weakTag: "rag_quality", title: "A", description: "", status: "todo", priority: "high", masteryScore: 40 },
    { id: 2, weakTag: "agent_tool_calling", title: "B", description: "", status: "done", priority: "medium", masteryScore: 80 }
  ];

  store.setWeakTagFilter("rag_quality");
  store.setStatusFilter("todo");

  expect(store.visibleTasks.map((task) => task.id)).toEqual([1]);

  store.clearFilters();
  expect(store.visibleTasks).toHaveLength(2);
});
```

- [ ] **Step 2: 运行 store 测试并确认失败**

```powershell
cd frontend
npm.cmd run test -- src/stores/training.test.ts
```

- [ ] **Step 3: 实现 store V2 状态**

在 `frontend/src/stores/training.ts` 增加：

```ts
export type TrainingStatusFilter = "" | "todo" | "in_progress" | "done" | "archived";

export interface TrainingWeakTagGroup {
  weakTag: string;
  weakLabel: string;
  total: number;
  todo: number;
  inProgress: number;
  done: number;
  averageMastery: number;
  highestPriority: trainingApi.TrainingTaskPriority;
}
```

新增 computed：

```ts
todoTasks
inProgressTasks
doneTasks
averageMastery
weakTagGroups
```

扩展 `visibleTasks`，叠加 `statusFilter`。

新增 actions：

```ts
setStatusFilter(status: TrainingStatusFilter): void
setWeakTagFilter(tag: string): void
clearFilters(): void
```

- [ ] **Step 4: 运行 store 测试**

```powershell
cd frontend
npm.cmd run test -- src/stores/training.test.ts
```

---

## Task 2: Training Overview Cards

**Files:**

- Create: `frontend/src/components/training/TrainingOverviewCards.vue`
- Create: `frontend/src/components/training/TrainingOverviewCards.test.ts`

- [ ] **Step 1: 写 failing component test**

测试要求：

```ts
expect(wrapper.text()).toContain("待训练");
expect(wrapper.text()).toContain("训练中");
expect(wrapper.text()).toContain("已完成");
expect(wrapper.text()).toContain("平均掌握度");
```

- [ ] **Step 2: 运行测试确认组件不存在**

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingOverviewCards.test.ts
```

- [ ] **Step 3: 实现组件**

props：

```ts
todoCount: number;
inProgressCount: number;
doneCount: number;
archivedCount: number;
averageMastery: number | null;
```

要求：

- 卡片式展示。
- 移动端自动换行。
- 平均掌握度为空时显示 `--`。

- [ ] **Step 4: 跑组件测试**

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingOverviewCards.test.ts
```

---

## Task 3: WeakTag Map And Status Filter

**Files:**

- Create: `frontend/src/components/training/TrainingWeakTagMap.vue`
- Create: `frontend/src/components/training/TrainingWeakTagMap.test.ts`
- Create: `frontend/src/components/training/TrainingStatusFilter.vue`
- Create: `frontend/src/components/training/TrainingStatusFilter.test.ts`

- [ ] **Step 1: 写 failing tests**

`TrainingWeakTagMap` 测试：

```ts
expect(wrapper.text()).toContain("RAG 质量");
expect(wrapper.text()).toContain("2 个任务");
await wrapper.get('[data-testid="weak-tag-rag_quality"]').trigger("click");
expect(wrapper.emitted("select")?.[0]).toEqual(["rag_quality"]);
```

`TrainingStatusFilter` 测试：

```ts
expect(wrapper.text()).toContain("全部");
expect(wrapper.text()).toContain("待训练");
await wrapper.get('[data-testid="status-filter-done"]').trigger("click");
expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["done"]);
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingWeakTagMap.test.ts src/components/training/TrainingStatusFilter.test.ts
```

- [ ] **Step 3: 实现两个组件**

`TrainingWeakTagMap.vue`：

- props: `groups`, `activeWeakTag`
- emits: `select`
- 空状态提示“还没有可聚合的薄弱点”

`TrainingStatusFilter.vue`：

- props: `modelValue`
- emits: `update:modelValue`
- 选项：全部 / 待训练 / 训练中 / 已完成 / 已归档

- [ ] **Step 4: 跑组件测试**

```powershell
cd frontend
npm.cmd run test -- src/components/training/TrainingWeakTagMap.test.ts src/components/training/TrainingStatusFilter.test.ts
```

---

## Task 4: Compose Training Page V2

**Files:**

- Modify: `frontend/src/pages/app/training-page.test.ts`
- Modify: `frontend/src/pages/app/TrainingPage.vue`

- [ ] **Step 1: 更新 page test**

mock training store 增加：

```ts
todoTasks
inProgressTasks
doneTasks
averageMastery
weakTagGroups
statusFilter
setStatusFilter
setWeakTagFilter
clearFilters
```

新增断言：

```ts
expect(wrapper.text()).toContain("训练概览");
expect(wrapper.text()).toContain("薄弱点训练地图");
expect(wrapper.text()).toContain("平均掌握度");
```

新增交互：

```ts
await wrapper.get('[data-testid="status-filter-done"]').trigger("click");
expect(trainingStore.setStatusFilter).toHaveBeenCalledWith("done");

await wrapper.get('[data-testid="weak-tag-agent_tool_calling"]').trigger("click");
expect(trainingStore.setWeakTagFilter).toHaveBeenCalledWith("agent_tool_calling");
```

- [ ] **Step 2: 跑页面测试确认失败**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/training-page.test.ts
```

- [ ] **Step 3: 组合页面**

更新 `TrainingPage.vue`：

- 引入 `TrainingOverviewCards`
- 引入 `TrainingWeakTagMap`
- 引入 `TrainingStatusFilter`
- 保留 `TrainingTaskList`
- 增加“回到面试台”按钮，跳转 `/vue/app/interview`
- 空状态提供去面试和去历史复盘入口

- [ ] **Step 4: 跑页面测试**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/training-page.test.ts
```

---

## Task 5: Learning Doc And Roadmap

**Files:**

- Create: `docs/learning/22-训练中心如何承接AI面试报告闭环.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: 新增学习文档**

文档至少包含：

```markdown
# 22 训练中心如何承接 AI 面试报告闭环

## 1. 为什么报告不是终点
## 2. weakTag 如何变成训练任务
## 3. 训练中心为什么要按薄弱点组织
## 4. 本项目的训练闭环链路
## 5. 面试时怎么讲
```

- [ ] **Step 2: 更新路线文档**

将当前 active 阶段指向：

```text
docs/specs/active/training-center-v2-design.md
docs/plans/active/training-center-v2.md
```

- [ ] **Step 3: 文档 sanity check**

```powershell
Test-Path 'docs\learning\22-训练中心如何承接AI面试报告闭环.md'
Test-Path 'docs\specs\active\training-center-v2-design.md'
Test-Path 'docs\plans\active\training-center-v2.md'
```

---

## Task 6: Verification And Browser Check

- [ ] **Step 1: 运行聚焦测试**

```powershell
cd frontend
npm.cmd run test -- src/stores/training.test.ts src/components/training/TrainingOverviewCards.test.ts src/components/training/TrainingWeakTagMap.test.ts src/components/training/TrainingStatusFilter.test.ts src/pages/app/training-page.test.ts
```

- [ ] **Step 2: 运行全量前端测试**

```powershell
cd frontend
npm.cmd run test
```

- [ ] **Step 3: 运行 build**

```powershell
cd frontend
npm.cmd run build
```

- [ ] **Step 4: 浏览器验证**

打开：

```text
http://127.0.0.1:5173/vue/app/training
http://127.0.0.1:5173/vue/app/training?recordId=262&weakTag=agent_tool_calling
```

验证：

- 顶部训练概览可见。
- weakTag 训练地图可见。
- 状态筛选可用。
- 任务列表能响应筛选。
- 来源报告跳转可用。
- 回到面试台入口可用。
- 桌面端和移动端无横向溢出。
- 页面无 `undefined`。

- [ ] **Step 5: 完成后归档**

测试、build、浏览器验证全部通过后：

```powershell
Move-Item -LiteralPath 'docs\specs\active\training-center-v2-design.md' -Destination 'docs\specs\completed\training-center-v2-design.md'
Move-Item -LiteralPath 'docs\plans\active\training-center-v2.md' -Destination 'docs\plans\completed\training-center-v2.md'
```

更新 README/current-state，说明 Training Center V2 已完成，active 等待下一阶段规划。
