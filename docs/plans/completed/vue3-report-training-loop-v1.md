# Vue3 面试报告与训练闭环 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Vue3 用户端的历史记录、报告详情和训练任务串成“面试 -> 复盘 -> 训练”的可用闭环。

**Architecture:** 优先只改 Vue3 前端，复用现有 FastAPI `/api/history` 和 `/api/training/tasks` 接口。新增 API client 和 Pinia store 承接数据请求，页面组件只负责渲染与跳转。

**Tech Stack:** Vue3, Vite, TypeScript, Pinia, Vue Router, Vitest, @vue/test-utils, FastAPI existing APIs.

---

## File Structure

- Create: `frontend/src/api/history.ts`
  - 封装 `/api/history` 的历史列表请求和类型。
- Create: `frontend/src/api/training.ts`
  - 封装 `/api/training/tasks` 列表、生成、开始、完成、归档请求和类型。
- Create: `frontend/src/stores/history.ts`
  - 管理历史记录列表、加载状态、错误信息。
- Create: `frontend/src/stores/report.ts`
  - 管理当前报告详情、recordId、加载状态、从报告生成训练任务。
- Create or modify: `frontend/src/stores/training.ts`
  - 管理真实训练任务列表、状态分组、开始/完成/归档动作。
- Modify: `frontend/src/router/index.ts`
  - 新增 `/vue/app/reports/:recordId` 报告详情路由。
- Modify: `frontend/src/pages/app/HistoryPage.vue`
  - 从静态占位页升级为历史复盘列表页。
- Create: `frontend/src/pages/app/ReportPage.vue`
  - 新增单场面试报告详情页。
- Modify: `frontend/src/pages/app/TrainingPage.vue`
  - 从 demoTasks 升级为真实任务数据页。
- Modify: `frontend/src/components/training/TrainingTaskList.vue`
  - 增加开始、完成、归档、查看来源报告动作。
- Create/Modify tests:
  - `frontend/src/stores/history.test.ts`
  - `frontend/src/stores/report.test.ts`
  - `frontend/src/stores/training.test.ts`
  - `frontend/src/pages/app/history-page.test.ts`
  - `frontend/src/pages/app/report-page.test.ts`
  - `frontend/src/pages/app/training-page.test.ts`
- Create: `docs/learning/15-Vue3面试报告历史复盘和训练闭环怎么串起来.md`
  - 解释本阶段的产品闭环和工程拆分。

## Task 1: History API And Store

**Files:**
- Create: `frontend/src/api/history.ts`
- Create: `frontend/src/stores/history.ts`
- Test: `frontend/src/stores/history.test.ts`

- [ ] **Step 1: Write the failing store test**

Create `frontend/src/stores/history.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as historyApi from "@/api/history";
import { useHistoryStore } from "./history";

vi.mock("@/api/history", () => ({
  listHistory: vi.fn()
}));

describe("history store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(historyApi.listHistory).mockReset();
  });

  it("loads interview history records for the current user", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([
      {
        id: 1,
        createdAt: "2026-06-12T10:00:00",
        applicationProfile: {
          id: 2,
          title: "AI 应用开发投递",
          targetRole: "AI 应用开发实习生"
        },
        profile: { targetRole: "AI 应用开发实习生" },
        answers: [{ question: "什么是 RAG？", answer: "检索增强生成。" }],
        report: { score: 82, level: "良好", weakTags: ["rag_quality"] }
      }
    ]);

    const store = useHistoryStore();
    await store.loadHistory();

    expect(store.items).toHaveLength(1);
    expect(store.items[0].applicationProfile?.title).toBe("AI 应用开发投递");
    expect(store.loading).toBe(false);
    expect(store.error).toBe("");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/history.test.ts
```

Expected: FAIL because `@/api/history` or `./history` does not exist.

- [ ] **Step 3: Implement minimal API and store**

Create `frontend/src/api/history.ts` with:

```ts
import { apiRequest } from "./client";

export interface HistoryApplicationProfile {
  id: number;
  title: string;
  targetRole?: string;
  applicationType?: string;
  positionTag?: string;
}

export interface HistoryAnswer {
  question: string;
  answer: string;
}

export interface HistoryRecord {
  id: number;
  createdAt: string;
  applicationProfile?: HistoryApplicationProfile | null;
  profile: Record<string, unknown>;
  answers: HistoryAnswer[];
  report: Record<string, unknown>;
}

export async function listHistory(): Promise<HistoryRecord[]> {
  return apiRequest<HistoryRecord[]>("/api/history");
}
```

Create `frontend/src/stores/history.ts` with:

```ts
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as historyApi from "@/api/history";

export const useHistoryStore = defineStore("history", () => {
  const items = ref<historyApi.HistoryRecord[]>([]);
  const loading = ref(false);
  const error = ref("");

  const latestItems = computed(() => items.value.slice(0, 20));

  async function loadHistory(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      items.value = await historyApi.listHistory();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "历史记录加载失败";
    } finally {
      loading.value = false;
    }
  }

  function findById(id: number): historyApi.HistoryRecord | null {
    return items.value.find((item) => item.id === id) || null;
  }

  return { items, latestItems, loading, error, loadHistory, findById };
});
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/history.test.ts
```

Expected: PASS.

## Task 2: History Page

**Files:**
- Modify: `frontend/src/pages/app/HistoryPage.vue`
- Create: `frontend/src/pages/app/history-page.test.ts`

- [ ] **Step 1: Write failing page test**

Create `frontend/src/pages/app/history-page.test.ts`:

```ts
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPage from "./HistoryPage.vue";

const push = vi.fn();
const historyStore = {
  items: [
    {
      id: 8,
      createdAt: "2026-06-12T10:00:00",
      applicationProfile: { id: 1, title: "后端实习投递", targetRole: "Python 后端开发实习生" },
      profile: { targetRole: "Python 后端开发实习生" },
      answers: [{ question: "请介绍 FastAPI Depends", answer: "它是依赖注入。" }],
      report: { score: 76, level: "可提升", weakTags: ["backend_architecture"] }
    }
  ],
  loading: false,
  error: "",
  loadHistory: vi.fn()
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/stores/history", () => ({
  useHistoryStore: () => historyStore
}));

describe("history page", () => {
  beforeEach(() => {
    push.mockReset();
    historyStore.loadHistory.mockReset();
  });

  it("renders history records and opens the report page", async () => {
    const wrapper = mount(HistoryPage, {
      global: {
        stubs: { AppLayout: { template: "<main><slot /></main>" } }
      }
    });

    expect(historyStore.loadHistory).toHaveBeenCalled();
    expect(wrapper.text()).toContain("历史复盘");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("76");

    await wrapper.get('[data-testid="open-report-8"]').trigger("click");
    expect(push).toHaveBeenCalledWith("/vue/app/reports/8");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/history-page.test.ts
```

Expected: FAIL because `HistoryPage.vue` is still a placeholder and has no report navigation.

- [ ] **Step 3: Implement page**

Update `HistoryPage.vue` to load store data on mount, render list cards, show empty state, and navigate to `/vue/app/reports/:id`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/history-page.test.ts
```

Expected: PASS.

## Task 3: Report Store And Route

**Files:**
- Create: `frontend/src/stores/report.ts`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/report.test.ts`

- [ ] **Step 1: Write failing report store test**

Create `frontend/src/stores/report.test.ts` to verify the store can find or load a report by record id from history data.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/report.test.ts
```

Expected: FAIL because report store does not exist.

- [ ] **Step 3: Implement report store and route**

Implement `useReportStore()` and add:

```ts
{
  path: "/vue/app/reports/:recordId",
  component: () => import("@/pages/app/ReportPage.vue"),
  meta: { requiresAuth: true }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/report.test.ts src/router/router.test.ts
```

Expected: PASS.

## Task 4: Report Page

**Files:**
- Create: `frontend/src/pages/app/ReportPage.vue`
- Create: `frontend/src/pages/app/report-page.test.ts`

- [ ] **Step 1: Write failing report page test**

Verify the report page displays summary, question reviews, weak tags, and a training CTA.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: FAIL because page does not exist.

- [ ] **Step 3: Implement page**

Render report header, score summary, question reviews, evidence summary, and route links back to history/training.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

Expected: PASS.

## Task 5: Training API, Store, And Page Integration

**Files:**
- Create: `frontend/src/api/training.ts`
- Create: `frontend/src/stores/training.ts`
- Modify: `frontend/src/pages/app/TrainingPage.vue`
- Modify: `frontend/src/components/training/TrainingTaskList.vue`
- Modify: `frontend/src/components/training/types.ts`
- Create: `frontend/src/stores/training.test.ts`
- Modify: `frontend/src/pages/app/training-page.test.ts`

- [ ] **Step 1: Write failing training store test**

Verify `loadTasks()`, `startTask()`, `completeTask()`, and `archiveTask()` call the API and update local state.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/training.test.ts
```

Expected: FAIL because training API/store do not exist.

- [ ] **Step 3: Implement API/store**

Create API wrappers around:

```text
GET /api/training/tasks
POST /api/training/tasks/generate-from-report
POST /api/training/tasks/{task_id}/start
POST /api/training/tasks/{task_id}/complete
POST /api/training/tasks/{task_id}/archive
```

- [ ] **Step 4: Update page and component tests first**

Update `training-page.test.ts` so it expects real store-driven tasks and action buttons.

- [ ] **Step 5: Implement page/component**

Make TrainingPage call `training.loadTasks()` and pass action handlers into `TrainingTaskList`.

- [ ] **Step 6: Run tests**

Run:

```bash
cd frontend
npm.cmd run test -- src/stores/training.test.ts src/pages/app/training-page.test.ts
```

Expected: PASS.

## Task 6: Learning Doc And Verification

**Files:**
- Create: `docs/learning/15-Vue3面试报告历史复盘和训练闭环怎么串起来.md`

- [ ] **Step 1: Write learning doc**

Explain:

- Vue Router 如何串页面。
- API client 如何隔离后端请求。
- Pinia store 如何保存列表、详情、加载状态和错误状态。
- 报告 weakTags 如何驱动训练任务。
- 面试时如何讲“产品闭环”。

- [ ] **Step 2: Run full frontend verification**

Run:

```bash
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: all tests pass and build exits 0.

- [ ] **Step 3: Browser verification**

Open:

```text
http://127.0.0.1:5173/vue/app/history
http://127.0.0.1:5173/vue/app/reports/<recordId>
http://127.0.0.1:5173/vue/app/training
```

Verify desktop and mobile layouts, no obvious overflow, no `undefined`, and history/report/training navigation works.

## Self-Review

- Spec coverage: covers history page, report page, training task real loop, API/store split, tests, browser verification, learning doc.
- Scope check: does not include RAG, Agent, LangGraph, Docker/Nginx/VPS, or admin V2.
- Placeholder scan: no TBD/TODO. Later tasks intentionally describe behavior rather than full final code because implementation must inspect exact current types and keep TDD red/green evidence.
- Backend boundary: first pass should be frontend-only; backend changes are only allowed if tests prove a missing compatible field.
