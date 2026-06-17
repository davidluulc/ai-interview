# Interview Workbench Experience V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Vue3 面试页和报告页升级成清晰的面试训练闭环：面试前配置、面试中进度反馈、结束复盘、报告训练、再来一场。

**Architecture:** 保持现有 FastAPI interview API、RAG、Agent、LangGraph 逻辑不变。本阶段主要在 Vue3 前端新增小组件，并扩展 Pinia interview store 的 session state。

**Tech Stack:** Vue3, Vite, TypeScript, Pinia, Vitest, Vue Test Utils, existing FastAPI APIs.

---

## 0. 执行边界

本 plan 只允许修改前端体验和配套学习文档，优先文件：

```text
frontend/src/stores/interview.ts
frontend/src/stores/interview.test.ts
frontend/src/pages/app/InterviewPage.vue
frontend/src/pages/app/interview-page.test.ts
frontend/src/pages/app/ReportPage.vue
frontend/src/pages/app/report-page.test.ts
frontend/src/components/interview/
docs/learning/
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

禁止事项：

- 不改 `/api/interview/next-question`。
- 不改 RAG、Agent、LangGraph 后端逻辑。
- 不安装 LangChain / LangGraph 新依赖。
- 不做 Docker / Nginx / VPS 上线。
- 不把本阶段扩展成全站 UI 重构。

每轮开发前先用中文解释本轮要学的前端 / AI 产品工程知识点。

---

## 1. File Map

- Modify: `frontend/src/stores/interview.ts`
  - 增加 sessionConfig、轮次进度 computed、reset/update actions，并暴露 answeredHistory。
- Modify: `frontend/src/stores/interview.test.ts`
  - 覆盖 session config、currentRound、isSessionComplete、canFinish、resetSession。
- Create: `frontend/src/components/interview/InterviewSessionSetup.vue`
  - 展示当前档案摘要和本次面试配置控件。
- Create: `frontend/src/components/interview/InterviewSessionSetup.test.ts`
  - 覆盖渲染、轮数/难度/重点方向更新事件。
- Create: `frontend/src/components/interview/InterviewProgressStrip.vue`
  - 展示当前轮次、总轮数、模式、难度、重点方向。
- Create: `frontend/src/components/interview/InterviewProgressStrip.test.ts`
  - 覆盖普通状态和完成状态。
- Create: `frontend/src/components/interview/InterviewFinishPanel.vue`
  - 展示结束复盘入口。
- Create: `frontend/src/components/interview/InterviewFinishPanel.test.ts`
  - 覆盖未回答不可复盘、已回答可复盘、达到轮数建议复盘。
- Modify: `frontend/src/pages/app/InterviewPage.vue`
  - 组合配置区、进度条、聊天区、解释区和结束复盘入口。
- Modify: `frontend/src/pages/app/interview-page.test.ts`
  - 验证页面组合、配置更新和提交 payload。
- Modify: `frontend/src/pages/app/ReportPage.vue`
  - 增强“建议优先训练”和“再来一场”入口。
- Modify: `frontend/src/pages/app/report-page.test.ts`
  - 验证报告页训练闭环和跳转。
- Create: `docs/learning/21-AI面试训练工作台如何形成产品闭环.md`
  - 中文学习文档。
- Modify: `docs/roadmap/current-state.md`
  - 更新 V4 进度。
- Modify: `docs/specs/README.md`
  - 保持 active spec 指向 V4。
- Modify: `docs/plans/README.md`
  - 保持 active plan 指向 V4。

---

## Task 1: Interview Store Session State

**Files:**

- Modify: `frontend/src/stores/interview.test.ts`
- Modify: `frontend/src/stores/interview.ts`

- [ ] **Step 1: 写 failing tests**

在 `frontend/src/stores/interview.test.ts` 增加测试：

```ts
it("tracks interview session config and progress", () => {
  const store = useInterviewStore();

  store.updateSessionConfig({
    totalRounds: 8,
    difficulty: "standard",
    focusArea: "rag_agent"
  });

  expect(store.sessionConfig.totalRounds).toBe(8);
  expect(store.sessionConfig.difficulty).toBe("standard");
  expect(store.sessionConfig.focusArea).toBe("rag_agent");
  expect(store.currentRound).toBe(1);
  expect(store.isSessionComplete).toBe(false);
  expect(store.canFinish).toBe(false);
});

it("marks a session complete when answered history reaches total rounds", () => {
  const store = useInterviewStore();
  store.updateSessionConfig({ totalRounds: 2 });
  store.answeredHistory = [
    { question: "Q1", answer: "A1" },
    { question: "Q2", answer: "A2" }
  ];

  expect(store.currentRound).toBe(2);
  expect(store.isSessionComplete).toBe(true);
  expect(store.canFinish).toBe(true);
});

it("resets interview session state", () => {
  const store = useInterviewStore();
  store.updateSessionConfig({
    totalRounds: 10,
    difficulty: "pressure",
    focusArea: "project_deep_dive"
  });
  store.answeredHistory = [{ question: "Q1", answer: "A1" }];
  store.decisionSummary = "旧决策";
  store.ragReasons = ["旧资料"];

  store.resetSession();

  expect(store.answeredHistory).toEqual([]);
  expect(store.currentRound).toBe(1);
  expect(store.decisionSummary).toBe("");
  expect(store.ragReasons).toEqual([]);
});
```

- [ ] **Step 2: 运行 store 测试，确认失败**

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts
```

预期失败原因：

```text
sessionConfig / updateSessionConfig / currentRound / resetSession 还不存在。
```

- [ ] **Step 3: 实现最小 store 能力**

在 `frontend/src/stores/interview.ts` 增加类型：

```ts
import { computed, ref } from "vue";

export type InterviewDifficulty = "basic" | "standard" | "pressure";
export type InterviewFocusArea = "project_deep_dive" | "technical_basic" | "rag_agent" | "behavioral" | "mixed";

export interface InterviewSessionConfig {
  totalRounds: number;
  difficulty: InterviewDifficulty;
  focusArea: InterviewFocusArea;
}
```

在 store 内增加：

```ts
const sessionConfig = ref<InterviewSessionConfig>({
  totalRounds: 8,
  difficulty: "standard",
  focusArea: "mixed"
});

const currentRound = computed(() => {
  return Math.min(answeredHistory.value.length + 1, sessionConfig.value.totalRounds);
});

const isSessionComplete = computed(() => {
  return answeredHistory.value.length >= sessionConfig.value.totalRounds;
});

const canFinish = computed(() => answeredHistory.value.length > 0);

function updateSessionConfig(config: Partial<InterviewSessionConfig>): void {
  sessionConfig.value = {
    ...sessionConfig.value,
    ...config,
    totalRounds: Number(config.totalRounds || sessionConfig.value.totalRounds)
  };
}

function resetSession(): void {
  messages.value = [{ role: "interviewer", content: openingQuestion }];
  answeredHistory.value = [];
  draft.value = "";
  error.value = "";
  decisionSummary.value = "";
  ragReasons.value = [];
}
```

return 中暴露：

```ts
answeredHistory,
sessionConfig,
currentRound,
isSessionComplete,
canFinish,
updateSessionConfig,
resetSession
```

- [ ] **Step 4: 运行 store 测试，确认通过**

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts
```

---

## Task 2: Session Setup Component

**Files:**

- Create: `frontend/src/components/interview/InterviewSessionSetup.vue`
- Create: `frontend/src/components/interview/InterviewSessionSetup.test.ts`

- [ ] **Step 1: 写 failing component test**

创建 `frontend/src/components/interview/InterviewSessionSetup.test.ts`：

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewSessionSetup from "./InterviewSessionSetup.vue";

describe("InterviewSessionSetup", () => {
  it("renders profile summary and emits session config updates", async () => {
    const wrapper = mount(InterviewSessionSetup, {
      props: {
        profile: {
          title: "后端实习投递",
          targetRole: "Python 后端开发实习生",
          company: "Example AI",
          jd: "熟悉 FastAPI、RAG 和 Agent"
        },
        config: {
          totalRounds: 8,
          difficulty: "standard",
          focusArea: "mixed"
        }
      }
    });

    expect(wrapper.text()).toContain("本次面试配置");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("Example AI");
    expect(wrapper.text()).toContain("FastAPI、RAG 和 Agent");

    await wrapper.get('[data-testid="session-total-rounds"]').setValue("10");
    await wrapper.get('[data-testid="session-difficulty"]').setValue("pressure");
    await wrapper.get('[data-testid="session-focus-area"]').setValue("rag_agent");

    expect(wrapper.emitted("update:config")?.at(-1)?.[0]).toEqual(
      expect.objectContaining({
        totalRounds: 10,
        difficulty: "pressure",
        focusArea: "rag_agent"
      })
    );
  });
});
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd frontend
npm.cmd run test -- src/components/interview/InterviewSessionSetup.test.ts
```

- [ ] **Step 3: 实现组件**

组件要求：

- props:
  - `profile`
  - `config`
- emit:
  - `update:config`
- 控件 data-testid:
  - `session-total-rounds`
  - `session-difficulty`
  - `session-focus-area`
- 文案使用中文。
- 视觉风格贴近当前 Vue3 页面：白底、细边框、轻阴影、克制圆角。
- 移动端控件单列展示。

- [ ] **Step 4: 运行组件测试**

```powershell
cd frontend
npm.cmd run test -- src/components/interview/InterviewSessionSetup.test.ts
```

---

## Task 3: Progress Strip And Finish Panel

**Files:**

- Create: `frontend/src/components/interview/InterviewProgressStrip.vue`
- Create: `frontend/src/components/interview/InterviewProgressStrip.test.ts`
- Create: `frontend/src/components/interview/InterviewFinishPanel.vue`
- Create: `frontend/src/components/interview/InterviewFinishPanel.test.ts`

- [ ] **Step 1: 写 failing tests**

创建 `InterviewProgressStrip.test.ts`：

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewProgressStrip from "./InterviewProgressStrip.vue";

describe("InterviewProgressStrip", () => {
  it("renders round progress and session labels", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 3,
        totalRounds: 8,
        mode: "coach",
        difficulty: "standard",
        focusArea: "rag_agent",
        complete: false
      }
    });

    expect(wrapper.text()).toContain("第 3 / 8 题");
    expect(wrapper.text()).toContain("学习辅导");
    expect(wrapper.text()).toContain("标准");
    expect(wrapper.text()).toContain("RAG & Agent");
  });

  it("marks the session as complete", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 8,
        totalRounds: 8,
        mode: "interview",
        difficulty: "pressure",
        focusArea: "project_deep_dive",
        complete: true
      }
    });

    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).toContain("真实面试");
  });
});
```

创建 `InterviewFinishPanel.test.ts`：

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewFinishPanel from "./InterviewFinishPanel.vue";

describe("InterviewFinishPanel", () => {
  it("keeps review disabled before the first answer", () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: false, complete: false, answeredCount: 0 }
    });

    expect(wrapper.text()).toContain("至少完成 1 轮问答后再复盘");
    expect(wrapper.find('[data-testid="finish-interview"]').attributes("disabled")).toBeDefined();
  });

  it("allows users to finish after at least one answer", async () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: true, complete: false, answeredCount: 2 }
    });

    await wrapper.get('[data-testid="finish-interview"]').trigger("click");
    expect(wrapper.emitted("finish")).toHaveLength(1);
  });

  it("recommends review after completing configured rounds", () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: true, complete: true, answeredCount: 8 }
    });

    expect(wrapper.text()).toContain("本轮面试可以复盘了");
  });
});
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd frontend
npm.cmd run test -- src/components/interview/InterviewProgressStrip.test.ts src/components/interview/InterviewFinishPanel.test.ts
```

- [ ] **Step 3: 实现两个组件**

`InterviewProgressStrip.vue` props:

```ts
currentRound: number;
totalRounds: number;
mode: "coach" | "interview";
difficulty: "basic" | "standard" | "pressure";
focusArea: "project_deep_dive" | "technical_basic" | "rag_agent" | "behavioral" | "mixed";
complete: boolean;
```

`InterviewFinishPanel.vue` props:

```ts
canFinish: boolean;
complete: boolean;
answeredCount: number;
```

`InterviewFinishPanel.vue` emit:

```ts
finish
```

- [ ] **Step 4: 运行组件测试**

```powershell
cd frontend
npm.cmd run test -- src/components/interview/InterviewProgressStrip.test.ts src/components/interview/InterviewFinishPanel.test.ts
```

---

## Task 4: Compose Interview Page

**Files:**

- Modify: `frontend/src/pages/app/interview-page.test.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`

- [ ] **Step 1: 更新 page tests**

在页面测试的 interview store mock 中补充：

```ts
sessionConfig: { totalRounds: 8, difficulty: "standard", focusArea: "mixed" },
currentRound: 1,
isSessionComplete: false,
canFinish: false,
answeredHistory: [],
updateSessionConfig: vi.fn(),
resetSession: vi.fn()
```

新增测试：

```ts
it("shows setup progress and finish guidance in the interview workbench", () => {
  const wrapper = mountPage();

  expect(wrapper.text()).toContain("本次面试配置");
  expect(wrapper.text()).toContain("第 1 / 8 题");
  expect(wrapper.text()).toContain("至少完成 1 轮问答后再复盘");
});
```

新增配置更新测试：

```ts
it("updates interview session config from setup controls", async () => {
  const wrapper = mountPage();

  await wrapper.get('[data-testid="session-total-rounds"]').setValue("10");

  expect(interviewStore.updateSessionConfig).toHaveBeenCalledWith(
    expect.objectContaining({ totalRounds: 10 })
  );
});
```

新增提交 payload 测试或更新已有提交测试，确认 `sessionConfig` 放进 profile：

```ts
expect(interviewStore.submitAnswer).toHaveBeenCalledWith(
  expect.objectContaining({
    profile: expect.objectContaining({
      sessionConfig: interviewStore.sessionConfig
    })
  })
);
```

- [ ] **Step 2: 运行页面测试，确认失败**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/interview-page.test.ts
```

- [ ] **Step 3: 组合页面**

更新 `InterviewPage.vue`：

- import 新组件。
- `CurrentProfileBanner` 下方渲染 `InterviewSessionSetup`。
- 聊天区上方渲染 `InterviewProgressStrip`。
- 聊天区下方渲染 `InterviewFinishPanel`。
- `finishInterview()` 暂时跳转 `/vue/app/history`。
- `submit()` 保持接口兼容，把 sessionConfig 放进 profile：

```ts
function submit(): Promise<void> {
  return interview.submitAnswer({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: interview.agentMode,
    profile: {
      ...((profiles.currentProfile || {}) as Record<string, unknown>),
      sessionConfig: interview.sessionConfig
    }
  });
}
```

- [ ] **Step 4: 运行页面测试**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/interview-page.test.ts
```

---

## Task 5: Report Page Training Loop Polish

**Files:**

- Modify: `frontend/src/pages/app/report-page.test.ts`
- Modify: `frontend/src/pages/app/ReportPage.vue`

- [ ] **Step 1: 写 failing report tests**

在 `report-page.test.ts` 增加断言：

```ts
expect(wrapper.text()).toContain("建议优先训练");
expect(wrapper.text()).toContain("再来一场");
```

触发新按钮：

```ts
await wrapper.get('[data-testid="start-another-interview"]').trigger("click");
expect(push).toHaveBeenCalledWith("/vue/app/interview");
```

- [ ] **Step 2: 运行报告页测试，确认失败**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

- [ ] **Step 3: 实现报告页增强**

更新 `ReportPage.vue`：

- 把“薄弱点”区域标题或描述增强为“建议优先训练”。
- 在“下一步训练”区域展示前三个 weakTag。
- 增加 `data-testid="start-another-interview"` 的“再来一场”按钮。
- 点击后执行：

```ts
router.push("/vue/app/interview");
```

- [ ] **Step 4: 运行报告页测试**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
```

---

## Task 6: Learning Doc And Roadmap

**Files:**

- Create: `docs/learning/21-AI面试训练工作台如何形成产品闭环.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: 新增学习文档**

创建 `docs/learning/21-AI面试训练工作台如何形成产品闭环.md`，至少包含：

```markdown
# 21 AI 面试训练工作台如何形成产品闭环

## 1. 什么是产品闭环

## 2. 为什么 AI 应用不能只讲 RAG 和 Agent

## 3. 面试前、面试中、面试后的状态流转

## 4. 本项目如何把 RAG、Agent、报告和训练串起来

## 5. 面试时怎么讲
```

- [ ] **Step 2: 更新路线文档**

更新：

```text
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

确保它们指向：

```text
docs/specs/active/interview-workbench-experience-v4-design.md
docs/plans/active/interview-workbench-experience-v4.md
```

- [ ] **Step 3: 文档 sanity check**

```powershell
Test-Path 'docs\learning\21-AI面试训练工作台如何形成产品闭环.md'
Test-Path 'docs\specs\active\interview-workbench-experience-v4-design.md'
Test-Path 'docs\plans\active\interview-workbench-experience-v4.md'
```

---

## Task 7: Verification And Browser Check

**Files:**

- Move after implementation:
  - `docs/specs/active/interview-workbench-experience-v4-design.md`
  - `docs/plans/active/interview-workbench-experience-v4.md`
- To:
  - `docs/specs/completed/interview-workbench-experience-v4-design.md`
  - `docs/plans/completed/interview-workbench-experience-v4.md`

- [ ] **Step 1: 运行聚焦前端测试**

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts src/components/interview/InterviewSessionSetup.test.ts src/components/interview/InterviewProgressStrip.test.ts src/components/interview/InterviewFinishPanel.test.ts src/pages/app/interview-page.test.ts src/pages/app/report-page.test.ts
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

- [ ] **Step 4: 启动或确认 Vue dev server**

如果 `http://127.0.0.1:5173/` 不可访问，启动：

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

- [ ] **Step 5: 浏览器验证面试页**

打开：

```text
http://127.0.0.1:5173/vue/app/interview
```

检查：

- 未选择档案时仍然引导去档案页。
- 已选择档案时配置区可见。
- 进度条可见。
- 聊天区可提交。
- 解释区仍然可见。
- 结束复盘入口可见。
- 页面无 `undefined`。
- 桌面端无横向溢出。
- 移动端 390px 无横向溢出。

- [ ] **Step 6: 浏览器验证报告页**

打开一个已有报告页：

```text
http://127.0.0.1:5173/vue/app/reports/<recordId>
```

检查：

- “建议优先训练”可见。
- “再来一场”可见。
- 点击“再来一场”能回到面试页。
- 页面无 `undefined`。
- 桌面端和移动端无横向溢出。

- [ ] **Step 7: 完成后归档 active 文档**

仅在测试、build、浏览器验证全部通过后执行：

```powershell
Move-Item -LiteralPath 'docs\specs\active\interview-workbench-experience-v4-design.md' -Destination 'docs\specs\completed\interview-workbench-experience-v4-design.md'
Move-Item -LiteralPath 'docs\plans\active\interview-workbench-experience-v4.md' -Destination 'docs\plans\completed\interview-workbench-experience-v4.md'
```

随后更新：

```text
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

说明 Interview Workbench Experience V4 已完成，active 目录等待下一阶段规划。
