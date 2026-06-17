# Vue3 用户工作台 V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Vue3 前端上，把用户端“投递档案 -> 模拟面试 -> 复盘报告 -> 专项训练”主流程产品化，让面试、档案和训练成为普通用户工作台，而不是管理员后台功能。

**Architecture:** 保持后端 API、RAG、Agent、LangGraph 主流程不变，优先通过 Vue3 页面、Pinia store 和轻量组件增强用户体验。管理员后台继续只承载账号、RAG 质量、Agent 日志和系统配置观察能力，本计划不新增后台写操作。

**Tech Stack:** Vue3, Vite, TypeScript, Pinia, Vue Router, Vitest, existing FastAPI APIs.

---

## File Structure

Create:

- `frontend/src/components/profiles/ProfileCurrentCard.vue`: 展示当前投递档案摘要和“开始面试”入口。
- `frontend/src/components/profiles/ProfileList.vue`: 展示档案列表、当前标识、设为当前和开始面试动作。
- `frontend/src/components/interview/InterviewModeSwitch.vue`: 在 `coach` 与 `interview` 两种 Agent 模式之间切换。
- `frontend/src/components/interview/CurrentProfileBanner.vue`: 在面试页顶部展示当前档案摘要。
- `frontend/src/components/interview/InterviewEvidencePanel.vue`: 用用户能理解的中文展示 Agent 决策和 RAG 参考资料。
- `frontend/src/components/training/TrainingTaskList.vue`: 展示训练任务列表或空状态。
- `docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md`: 本阶段学习总结。

Modify:

- `frontend/src/pages/app/ProfilesPage.vue`: 从“表单 + 列表”升级为“当前档案 + 新建档案 + 档案列表”三段式页面。
- `frontend/src/pages/app/profiles-page.test.ts`: 覆盖当前档案、空状态、开始面试跳转。
- `frontend/src/stores/profiles.ts`: 增强当前档案选择、跳转前选择档案的可测试行为。
- `frontend/src/pages/app/InterviewPage.vue`: 增加未选档案引导、当前档案摘要、模式切换和产品化解释面板。
- `frontend/src/pages/app/interview-page.test.ts`: 覆盖未选档案、已选档案、模式切换、提交携带 agentMode。
- `frontend/src/stores/interview.ts`: 增加 `agentMode` 状态和 `setAgentMode()`。
- `frontend/src/stores/interview.test.ts`: 覆盖 agentMode 默认值、切换、提交请求。
- `frontend/src/pages/app/TrainingPage.vue`: 从占位页升级为训练入口页。
- `frontend/src/pages/app/training-page.test.ts`: 覆盖空状态和任务列表渲染。
- `frontend/src/layouts/AppLayout.vue`: 只在必要时轻量调整导航文案或移动端布局，不引入新后台入口。
- `docs/specs/README.md`, `docs/plans/README.md`, `docs/roadmap/current-state.md`: 阶段完成后更新状态。

Do not modify in this stage:

- `backend_python/langgraph_agent/*`
- `backend_python/agent_policy.py`
- `backend_python/retrieval_service.py`
- `backend_python/routes/admin.py`
- `docker-compose.yml`
- `Dockerfile`
- `deploy/nginx/*`
- legacy `index.html`, `styles.css`, `app.js`

No destructive actions:

- Do not delete user data.
- Do not delete database files.
- Do not add admin write operations.
- Do not push to GitHub without explicit user confirmation.
- Do not install React, Next.js, Element Plus, Ant Design Vue, or other heavy UI frameworks.

---

### Task 1: Profiles Workbench Components

**Learning focus:** Vue 组件拆分。页面负责“编排”，组件负责“一块明确的 UI”。这样面试时可以讲：我没有把所有逻辑堆在一个 `.vue` 文件里，而是按业务边界拆成当前档案卡片和档案列表。

**Files:**
- Create: `frontend/src/components/profiles/ProfileCurrentCard.vue`
- Create: `frontend/src/components/profiles/ProfileList.vue`
- Modify: `frontend/src/pages/app/profiles-page.test.ts`
- Modify: `frontend/src/pages/app/ProfilesPage.vue`

- [ ] **Step 1: Write failing tests for current profile and start interview**

Update `frontend/src/pages/app/profiles-page.test.ts` with these cases:

```ts
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfilesPage from "./ProfilesPage.vue";

const push = vi.fn();

const profilesStore = {
  profiles: [
    {
      id: 1,
      title: "后端实习投递",
      targetRole: "Python 后端开发实习生",
      company: "Example AI",
      jd: "负责 FastAPI 接口开发",
      resume: "有 AI 模拟面试系统项目经历"
    },
    {
      id: 2,
      title: "AI 应用开发投递",
      targetRole: "AI 应用开发实习生",
      company: "Future AI",
      jd: "熟悉 RAG 和 Agent",
      resume: "熟悉 Python 后端"
    }
  ],
  currentProfileId: 1,
  currentProfile: {
    id: 1,
    title: "后端实习投递",
    targetRole: "Python 后端开发实习生",
    company: "Example AI",
    jd: "负责 FastAPI 接口开发",
    resume: "有 AI 模拟面试系统项目经历"
  },
  loading: false,
  error: "",
  loadProfiles: vi.fn(),
  createProfile: vi.fn(),
  selectProfile: vi.fn()
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

describe("profiles page", () => {
  beforeEach(() => {
    push.mockReset();
    profilesStore.loadProfiles.mockReset();
    profilesStore.selectProfile.mockReset();
    profilesStore.createProfile.mockReset();
    profilesStore.currentProfileId = 1;
    profilesStore.currentProfile = profilesStore.profiles[0];
  });

  it("loads and displays the current application profile", () => {
    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(profilesStore.loadProfiles).toHaveBeenCalled();
    expect(wrapper.text()).toContain("当前档案");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("Example AI");
  });

  it("selects a profile before navigating to the interview page", async () => {
    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="start-profile-2"]').trigger("click");

    expect(profilesStore.selectProfile).toHaveBeenCalledWith(2);
    expect(push).toHaveBeenCalledWith("/vue/app/interview");
  });

  it("shows a clear empty state when there are no profiles", () => {
    profilesStore.profiles = [];
    profilesStore.currentProfile = null;
    profilesStore.currentProfileId = null;

    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("还没有投递档案");
    expect(wrapper.text()).toContain("先创建一个档案");
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- profiles-page.test.ts
```

Expected: FAIL because `ProfileCurrentCard.vue`, `ProfileList.vue`, and start interview behavior do not exist.

- [ ] **Step 3: Create `ProfileCurrentCard.vue`**

Create `frontend/src/components/profiles/ProfileCurrentCard.vue`:

```vue
<template>
  <section class="current-card">
    <div>
      <p class="eyebrow">当前档案</p>
      <h2>{{ profile.title }}</h2>
      <p class="meta">{{ roleText }} · {{ companyText }}</p>
    </div>

    <dl class="readiness">
      <div>
        <dt>岗位 JD</dt>
        <dd>{{ profile.jd ? "已填写" : "未填写" }}</dd>
      </div>
      <div>
        <dt>简历概况</dt>
        <dd>{{ profile.resume ? "已填写" : "未填写" }}</dd>
      </div>
    </dl>

    <button type="button" @click="$emit('start', profile.id)">开始面试</button>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ApplicationProfile } from "@/api/profiles";

const props = defineProps<{ profile: ApplicationProfile }>();
defineEmits<{ start: [id: number] }>();

const roleText = computed(() => props.profile.targetRole || props.profile.target_role || "未填写目标岗位");
const companyText = computed(() => props.profile.company || "未填写公司");
</script>

<style scoped>
.current-card {
  display: grid;
  gap: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h2,
p,
dl,
dd {
  margin: 0;
}

.meta,
dt {
  color: var(--color-text-muted);
}

.readiness {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.readiness div {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 12px;
}

dt {
  font-size: 13px;
}

dd {
  font-weight: 700;
  margin-top: 4px;
}

button {
  width: fit-content;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  font-weight: 700;
  padding: 11px 18px;
}
@media (max-width: 640px) {
  .readiness {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 4: Create `ProfileList.vue`**

Create `frontend/src/components/profiles/ProfileList.vue`:

```vue
<template>
  <section class="profile-list" aria-label="投递档案列表">
    <div class="list-head">
      <h2>已有档案</h2>
      <span>{{ profiles.length }} 个</span>
    </div>

    <p v-if="loading && profiles.length === 0" class="empty">正在加载档案...</p>
    <div v-else-if="profiles.length === 0" class="empty-state">
      <h3>还没有投递档案</h3>
      <p>先创建一个档案，AI 面试官会结合简历、岗位 JD 和公司信息生成问题。</p>
    </div>

    <article
      v-for="profile in profiles"
      :key="profile.id"
      :class="['profile-card', { active: currentProfileId === profile.id }]"
    >
      <div>
        <h3>{{ profile.title }}</h3>
        <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }}</p>
        <small>{{ profile.company || "未填写公司" }}</small>
      </div>
      <div class="actions">
        <button type="button" @click="$emit('select', profile.id)">
          {{ currentProfileId === profile.id ? "当前档案" : "设为当前" }}
        </button>
        <button
          class="primary"
          type="button"
          :data-testid="`start-profile-${profile.id}`"
          @click="$emit('start', profile.id)"
        >
          开始面试
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";

defineProps<{
  profiles: ApplicationProfile[];
  currentProfileId: number | null;
  loading: boolean;
}>();

defineEmits<{
  select: [id: number];
  start: [id: number];
}>();
</script>

<style scoped>
.profile-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.list-head,
.profile-card,
.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.list-head,
.profile-card {
  justify-content: space-between;
}

.list-head {
  margin-bottom: 16px;
}

h2,
h3,
p {
  margin: 0;
}

.list-head span,
.profile-card p,
.empty,
small {
  color: var(--color-text-muted);
}

.empty-state {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 22px;
}

.profile-card {
  border-top: 1px solid var(--color-border);
  padding: 16px 0;
}

.profile-card.active h3 {
  color: var(--color-accent);
}

button {
  white-space: nowrap;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  padding: 8px 12px;
}

button.primary {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: white;
}

@media (max-width: 720px) {
  .profile-card,
  .actions {
    align-items: stretch;
    flex-direction: column;
  }

  .actions,
  .actions button {
    width: 100%;
  }
}
</style>
```

- [ ] **Step 5: Refactor `ProfilesPage.vue` to use the new components**

Modify `frontend/src/pages/app/ProfilesPage.vue`:

```vue
<template>
  <AppLayout>
    <section class="page-header">
      <p class="eyebrow">Application Profiles</p>
      <h1>投递档案</h1>
      <p>先把简历、岗位 JD 和公司信息沉淀成档案，再进入模拟面试。</p>
    </section>

    <section v-if="profiles.currentProfile" class="current-section">
      <ProfileCurrentCard :profile="profiles.currentProfile" @start="startInterview" />
    </section>

    <section class="profile-workspace">
      <form class="profile-form" @submit.prevent="submit">
        <h2>新建档案</h2>
        <TextField v-model="form.title" label="档案名称" name="title" placeholder="后端实习投递" required />
        <TextField v-model="form.targetRole" label="目标岗位" name="targetRole" placeholder="Python 后端开发实习生" />
        <TextField v-model="form.company" label="目标公司" name="company" placeholder="可先留空" />
        <label class="area-field">
          <span>岗位 JD</span>
          <textarea v-model="form.jd" placeholder="粘贴岗位职责、任职要求、技术栈关键词" />
        </label>
        <label class="area-field">
          <span>简历概况</span>
          <textarea v-model="form.resume" placeholder="先用文本概括简历，后续再接入文件上传" />
        </label>
        <p v-if="profiles.error" class="error">{{ profiles.error }}</p>
        <PrimaryButton :disabled="profiles.loading">{{ profiles.loading ? "保存中" : "保存档案" }}</PrimaryButton>
      </form>

      <ProfileList
        :current-profile-id="profiles.currentProfileId"
        :loading="profiles.loading"
        :profiles="profiles.profiles"
        @select="profiles.selectProfile"
        @start="startInterview"
      />
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import PrimaryButton from "@/components/common/PrimaryButton.vue";
import TextField from "@/components/common/TextField.vue";
import ProfileCurrentCard from "@/components/profiles/ProfileCurrentCard.vue";
import ProfileList from "@/components/profiles/ProfileList.vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useProfilesStore } from "@/stores/profiles";

const router = useRouter();
const profiles = useProfilesStore();
const form = reactive({
  title: "",
  targetRole: "",
  company: "",
  jd: "",
  resume: ""
});

onMounted(() => {
  void profiles.loadProfiles();
});

async function submit(): Promise<void> {
  await profiles.createProfile({ ...form });
  form.title = "";
  form.targetRole = "";
  form.company = "";
  form.jd = "";
  form.resume = "";
}

async function startInterview(id: number): Promise<void> {
  profiles.selectProfile(id);
  await router.push("/vue/app/interview");
}
</script>
```

Keep the existing form CSS, and remove duplicated list/card CSS that moved into `ProfileList.vue`. Add:

```css
.current-section {
  margin-bottom: 22px;
}
```

- [ ] **Step 6: Run focused test**

Run:

```powershell
cd frontend
npm.cmd run test -- profiles-page.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit task changes**

Run:

```powershell
git add frontend/src/components/profiles frontend/src/pages/app/ProfilesPage.vue frontend/src/pages/app/profiles-page.test.ts
git commit -m "feat: productize vue profile workbench"
```

Skip commit if the user explicitly asked not to commit.

---

### Task 2: Interview Mode And Current Profile

**Learning focus:** 前端状态如何影响后端请求。`agentMode` 是用户在页面上选择的训练策略，Pinia store 保存这个状态，提交回答时把它带给 `/api/interview/next-question`。

**Files:**
- Create: `frontend/src/components/interview/InterviewModeSwitch.vue`
- Create: `frontend/src/components/interview/CurrentProfileBanner.vue`
- Modify: `frontend/src/stores/interview.ts`
- Modify: `frontend/src/stores/interview.test.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`
- Modify: `frontend/src/pages/app/interview-page.test.ts`

- [ ] **Step 1: Write failing store tests for `agentMode`**

Update `frontend/src/stores/interview.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as interviewApi from "@/api/interview";
import { useInterviewStore } from "./interview";

vi.mock("@/api/interview", () => ({
  nextQuestion: vi.fn()
}));

describe("interview store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(interviewApi.nextQuestion).mockReset();
  });

  it("uses coach mode by default and supports switching to interview mode", () => {
    const store = useInterviewStore();

    expect(store.agentMode).toBe("coach");

    store.setAgentMode("interview");

    expect(store.agentMode).toBe("interview");
  });

  it("submits answers with the selected agent mode", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "请继续讲项目里的 RAG 质量评估。"
    });

    const store = useInterviewStore();
    store.draft = "我做了 Hit@K 和 MRR";
    store.setAgentMode("interview");

    await store.submitAnswer({ applicationProfileId: 3, profile: { title: "AI 应用开发投递" } });

    expect(interviewApi.nextQuestion).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        agentMode: "interview"
      })
    );
  });
});
```

- [ ] **Step 2: Run focused store test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- interview.test.ts
```

Expected: FAIL because `agentMode` and `setAgentMode()` are not implemented.

- [ ] **Step 3: Implement `agentMode` in `interview.ts`**

Modify `frontend/src/stores/interview.ts`:

```ts
const agentMode = ref<interviewApi.AgentMode>("coach");

function setAgentMode(mode: interviewApi.AgentMode): void {
  agentMode.value = mode;
}
```

In `submitAnswer`, replace:

```ts
agentMode: options.agentMode || "coach",
```

with:

```ts
agentMode: options.agentMode || agentMode.value,
```

Return:

```ts
return { messages, draft, loading, error, decisionSummary, ragReasons, agentMode, setAgentMode, submitAnswer };
```

- [ ] **Step 4: Create `InterviewModeSwitch.vue`**

Create `frontend/src/components/interview/InterviewModeSwitch.vue`:

```vue
<template>
  <div class="mode-switch" role="group" aria-label="面试模式">
    <button :class="{ active: modelValue === 'coach' }" type="button" @click="$emit('update:modelValue', 'coach')">
      学习辅导
    </button>
    <button
      :class="{ active: modelValue === 'interview' }"
      type="button"
      @click="$emit('update:modelValue', 'interview')"
    >
      真实面试
    </button>
  </div>
</template>

<script setup lang="ts">
import type { AgentMode } from "@/api/interview";

defineProps<{ modelValue: AgentMode }>();
defineEmits<{ "update:modelValue": [mode: AgentMode] }>();
</script>

<style scoped>
.mode-switch {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(96px, 1fr));
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface-muted);
  padding: 4px;
}

button {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-weight: 700;
  padding: 9px 14px;
}

button.active {
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
}
</style>
```

- [ ] **Step 5: Create `CurrentProfileBanner.vue`**

Create `frontend/src/components/interview/CurrentProfileBanner.vue`:

```vue
<template>
  <section class="profile-banner">
    <div>
      <p class="eyebrow">当前面试档案</p>
      <h2>{{ profile.title }}</h2>
      <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }} · {{ profile.company || "未填写公司" }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";

defineProps<{ profile: ApplicationProfile }>();
</script>

<style scoped>
.profile-banner {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 18px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 6px;
}

h2,
p {
  margin: 0;
}

p:last-child {
  color: var(--color-text-muted);
  margin-top: 6px;
}
</style>
```

- [ ] **Step 6: Write failing page tests for profile guidance and mode switch**

Update `frontend/src/pages/app/interview-page.test.ts` with:

```ts
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import InterviewPage from "./InterviewPage.vue";

const push = vi.fn();

const interviewStore = {
  messages: [{ role: "interviewer", content: "请先做一个一分钟自我介绍。" }],
  draft: "",
  loading: false,
  error: "",
  decisionSummary: "当前处于学习辅导模式，会先确认基础概念。",
  ragReasons: ["命中岗位知识库：FastAPI"],
  agentMode: "coach",
  setAgentMode: vi.fn((mode: "coach" | "interview") => {
    interviewStore.agentMode = mode;
  }),
  submitAnswer: vi.fn()
};

const profilesStore = {
  currentProfileId: 3,
  currentProfile: {
    id: 3,
    title: "后端实习投递",
    targetRole: "Python 后端开发实习生",
    company: "Example AI"
  }
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/stores/interview", () => ({
  useInterviewStore: () => interviewStore
}));

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

describe("interview page", () => {
  beforeEach(() => {
    push.mockReset();
    interviewStore.submitAnswer.mockReset();
    interviewStore.setAgentMode.mockClear();
    interviewStore.agentMode = "coach";
    profilesStore.currentProfileId = 3;
    profilesStore.currentProfile = {
      id: 3,
      title: "后端实习投递",
      targetRole: "Python 后端开发实习生",
      company: "Example AI"
    };
  });

  it("shows the current profile and mode switch", () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("当前面试档案");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("学习辅导");
    expect(wrapper.text()).toContain("真实面试");
  });

  it("guides users to create a profile before interviewing", async () => {
    profilesStore.currentProfileId = null;
    profilesStore.currentProfile = null;

    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("请先选择或创建投递档案");
    await wrapper.get('[data-testid="go-profiles"]').trigger("click");
    expect(push).toHaveBeenCalledWith("/vue/app/profiles");
  });

  it("submits answers with the selected mode", async () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="mode-interview"]').trigger("click");
    await wrapper.get('[data-testid="interview-submit"]').trigger("submit");

    expect(interviewStore.setAgentMode).toHaveBeenCalledWith("interview");
    expect(interviewStore.submitAnswer).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        agentMode: "interview"
      })
    );
  });
});
```

- [ ] **Step 7: Refactor `InterviewPage.vue`**

Modify `frontend/src/pages/app/InterviewPage.vue` to:

```vue
<template>
  <AppLayout>
    <section v-if="!profiles.currentProfile" class="empty-profile">
      <p class="eyebrow">Interview Workspace</p>
      <h1>请先选择或创建投递档案</h1>
      <p>AI 面试官需要结合简历、岗位 JD 和公司信息，才能生成贴近真实场景的问题。</p>
      <button data-testid="go-profiles" type="button" @click="router.push('/vue/app/profiles')">去创建档案</button>
    </section>

    <div v-else class="interview-workbench">
      <section class="workbench-main">
        <div class="toolbar">
          <div>
            <p class="eyebrow">Interview Workspace</p>
            <h1>面试训练台</h1>
          </div>
          <InterviewModeSwitch :model-value="interview.agentMode" @update:model-value="interview.setAgentMode" />
        </div>
        <CurrentProfileBanner :profile="profiles.currentProfile" />
        <p class="subtitle">围绕当前投递档案，进行可解释的 AI 模拟面试。</p>
        <InterviewChatPanel
          v-model:draft="interview.draft"
          :error="interview.error"
          :loading="interview.loading"
          :messages="interview.messages"
          data-testid="interview-submit"
          @submit="submit"
        />
      </section>

      <InterviewEvidencePanel :decision-summary="interview.decisionSummary" :rag-reasons="interview.ragReasons" />
    </div>
  </AppLayout>
</template>
```

Script:

```ts
import { useRouter } from "vue-router";
import AppLayout from "@/layouts/AppLayout.vue";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import CurrentProfileBanner from "@/components/interview/CurrentProfileBanner.vue";
import InterviewEvidencePanel from "@/components/interview/InterviewEvidencePanel.vue";
import InterviewModeSwitch from "@/components/interview/InterviewModeSwitch.vue";
import { useInterviewStore } from "@/stores/interview";
import { useProfilesStore } from "@/stores/profiles";

const router = useRouter();
const interview = useInterviewStore();
const profiles = useProfilesStore();

function submit(): Promise<void> {
  return interview.submitAnswer({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: interview.agentMode,
    profile: (profiles.currentProfile || {}) as Record<string, unknown>
  });
}
```

Add CSS for `.empty-profile`, `.toolbar`, and responsive layout. Keep it restrained:

```css
.empty-profile {
  display: grid;
  gap: 14px;
  max-width: 720px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 28px;
}

.empty-profile button {
  width: fit-content;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  font-weight: 700;
  padding: 11px 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 760px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
```

- [ ] **Step 8: Rename or replace the context panel with product wording**

If `frontend/src/components/interview/InterviewContextPanel.vue` still exists, either keep it as an internal wrapper or replace its usage with `InterviewEvidencePanel.vue`.

Create `frontend/src/components/interview/InterviewEvidencePanel.vue`:

```vue
<template>
  <aside class="evidence-panel">
    <section>
      <p class="eyebrow">Why this question</p>
      <h2>为什么这样问</h2>
      <p>{{ decisionSummary || "开始面试后，这里会展示面试官的追问依据。" }}</p>
    </section>

    <section>
      <p class="eyebrow">References</p>
      <h2>本题参考资料</h2>
      <ul v-if="ragReasons.length > 0">
        <li v-for="reason in ragReasons" :key="reason">{{ reason }}</li>
      </ul>
      <p v-else>当前问题暂未命中可展示的参考资料。</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  decisionSummary: string;
  ragReasons: string[];
}>();
</script>

<style scoped>
.evidence-panel {
  display: grid;
  gap: 16px;
}

section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 18px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h2,
p {
  margin: 0;
}

p,
li {
  color: var(--color-text-muted);
  line-height: 1.7;
}

ul {
  margin: 0;
  padding-left: 18px;
}
</style>
```

- [ ] **Step 9: Run focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- interview.test.ts interview-page.test.ts
```

Expected: PASS.

- [ ] **Step 10: Commit task changes**

Run:

```powershell
git add frontend/src/components/interview frontend/src/pages/app/InterviewPage.vue frontend/src/pages/app/interview-page.test.ts frontend/src/stores/interview.ts frontend/src/stores/interview.test.ts
git commit -m "feat: productize vue interview workspace"
```

Skip commit if the user explicitly asked not to commit.

---

### Task 3: Training Entry Productization

**Learning focus:** 空状态不是“没做功能”，而是产品流程的一部分。训练页暂时不强行重构后端，只把“完成面试后生成训练任务”的闭环表达清楚。

**Files:**
- Create: `frontend/src/components/training/TrainingTaskList.vue`
- Create: `frontend/src/pages/app/training-page.test.ts`
- Modify: `frontend/src/pages/app/TrainingPage.vue`

- [ ] **Step 1: Write failing tests for training empty state and task list**

Create `frontend/src/pages/app/training-page.test.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TrainingPage from "./TrainingPage.vue";

describe("training page", () => {
  it("shows an empty state when there are no training tasks", () => {
    const wrapper = mount(TrainingPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("暂无训练任务");
    expect(wrapper.text()).toContain("先完成一次模拟面试");
  });

  it("renders local task examples as a productized training entry", () => {
    const wrapper = mount(TrainingPage, {
      props: {
        demoTasks: [
          {
            id: 1,
            weakTag: "rag_quality",
            title: "RAG 质量评估表达训练",
            status: "not_started",
            source: "最近一次 AI 应用岗模拟面试"
          }
        ]
      },
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("RAG 质量评估表达训练");
    expect(wrapper.text()).toContain("未开始");
    expect(wrapper.text()).toContain("最近一次 AI 应用岗模拟面试");
  });
});
```

- [ ] **Step 2: Run focused test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- training-page.test.ts
```

Expected: FAIL because `TrainingPage.vue` has only placeholder content and no `demoTasks` prop.

- [ ] **Step 3: Create `TrainingTaskList.vue`**

Create `frontend/src/components/training/TrainingTaskList.vue`:

```vue
<template>
  <section class="task-list">
    <div class="list-head">
      <h2>训练任务</h2>
      <span>{{ tasks.length }} 个</span>
    </div>

    <div v-if="tasks.length === 0" class="empty-state">
      <h3>暂无训练任务</h3>
      <p>先完成一次模拟面试，系统会根据复盘里的薄弱点生成专项训练建议。</p>
    </div>

    <article v-for="task in tasks" :key="task.id" class="task-card">
      <div>
        <span class="tag">{{ task.weakTag }}</span>
        <h3>{{ task.title }}</h3>
        <p>{{ task.source }}</p>
      </div>
      <strong>{{ statusText(task.status) }}</strong>
    </article>
  </section>
</template>

<script setup lang="ts">
export interface TrainingTaskView {
  id: number;
  weakTag: string;
  title: string;
  status: "not_started" | "in_progress" | "completed" | "archived";
  source: string;
}

defineProps<{ tasks: TrainingTaskView[] }>();

function statusText(status: TrainingTaskView["status"]): string {
  const map = {
    not_started: "未开始",
    in_progress: "进行中",
    completed: "已完成",
    archived: "已归档"
  };
  return map[status];
}
</script>

<style scoped>
.task-list {
  display: grid;
  gap: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.list-head,
.task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

h2,
h3,
p {
  margin: 0;
}

.list-head span,
p {
  color: var(--color-text-muted);
}

.empty-state {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 22px;
}

.task-card {
  border-top: 1px solid var(--color-border);
  padding-top: 16px;
}

.tag {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  background: #eef4ff;
  color: #175cd3;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
  padding: 4px 8px;
}

@media (max-width: 640px) {
  .task-card {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
```

- [ ] **Step 4: Replace `TrainingPage.vue` placeholder**

Modify `frontend/src/pages/app/TrainingPage.vue`:

```vue
<template>
  <AppLayout>
    <section class="page-header">
      <p class="eyebrow">Training</p>
      <h1>训练中心</h1>
      <p>这里承接面试复盘里的薄弱点，把“答不上来”变成下一轮可以练习的任务。</p>
    </section>

    <section class="training-grid">
      <article class="explain-card">
        <h2>训练从哪里来</h2>
        <p>完成一次模拟面试后，系统会从报告中提取 weakTag，并生成专项训练任务。</p>
      </article>
      <TrainingTaskList :tasks="demoTasks" />
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
import TrainingTaskList, { type TrainingTaskView } from "@/components/training/TrainingTaskList.vue";

withDefaults(defineProps<{ demoTasks?: TrainingTaskView[] }>(), {
  demoTasks: () => []
});
</script>
```

Add scoped CSS:

```css
.page-header {
  display: grid;
  gap: 8px;
  max-width: 900px;
  margin-bottom: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 40px;
}

.page-header p,
.explain-card p {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.training-grid {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.explain-card {
  display: grid;
  gap: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: 22px;
}

@media (max-width: 900px) {
  .training-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 5: Run focused test**

Run:

```powershell
cd frontend
npm.cmd run test -- training-page.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit task changes**

Run:

```powershell
git add frontend/src/components/training frontend/src/pages/app/TrainingPage.vue frontend/src/pages/app/training-page.test.ts
git commit -m "feat: productize vue training entry"
```

Skip commit if the user explicitly asked not to commit.

---

### Task 4: Integration Verification And Browser Check

**Learning focus:** 前端工程不是“页面看起来能点”就结束，必须跑测试、build，并用浏览器验证桌面端和移动端。

**Files:**
- Possibly modify only files changed in Tasks 1-3 if verification reveals layout defects.

- [ ] **Step 1: Run all Vue tests**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected: all Vitest files pass.

- [ ] **Step 2: Run Vue build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds with exit code 0.

- [ ] **Step 3: Run backend tests only if backend files changed**

If any `backend_python/` file changed, run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

If no backend files changed, do not run full backend tests for this frontend-only stage.

- [ ] **Step 4: Start local services**

Start or reuse backend:

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

Start or reuse Vue dev server:

```powershell
cd frontend
npm.cmd run dev
```

- [ ] **Step 5: Browser verify desktop and mobile**

Use the in-app browser or local browser to verify:

```text
http://127.0.0.1:5173/vue/app/profiles
http://127.0.0.1:5173/vue/app/interview
http://127.0.0.1:5173/vue/app/training
```

Desktop checks:

```text
档案页显示当前档案、新建表单、档案列表。
档案页“开始面试”会进入面试页。
面试页未选档案时显示引导。
面试页已选档案时显示档案摘要和 coach/interview 模式。
训练页显示训练来源说明和空状态。
页面不出现 undefined。
```

Mobile checks:

```text
宽度 390px 左右无明显横向溢出。
按钮文字不挤压。
档案卡片、面试工具栏、训练任务卡片能正常换行。
```

- [ ] **Step 6: Fix only verification issues**

If browser verification reveals overflow, fix scoped CSS in the affected component only:

```text
ProfileCurrentCard.vue
ProfileList.vue
InterviewPage.vue
InterviewModeSwitch.vue
TrainingTaskList.vue
TrainingPage.vue
```

Do not use this step to add new features.

- [ ] **Step 7: Commit verification fixes**

Run:

```powershell
git add frontend/src
git commit -m "fix: polish vue user workbench layout"
```

Skip this commit if there were no fixes.

---

### Task 5: Learning Document And Route State Update

**Learning focus:** 项目开发完成后要沉淀可讲解材料。面试官问“你做了什么”时，回答应该围绕产品边界、组件拆分、状态流和测试验证。

**Files:**
- Create: `docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Create learning document**

Create `docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md`:

```markdown
# 14. Vue3 用户工作台如何串起档案、面试和训练闭环

## 1. 为什么面试和档案不放在管理员后台

面试和档案是普通用户自己的核心业务流程。

管理员后台负责观察系统运行情况，例如账号列表、RAG 质量、Agent 日志和系统配置。

用户端工作台负责用户怎么训练，例如投递档案、模拟面试、复盘报告和专项训练。

## 2. 档案页的作用

档案页是面试训练的准备入口。

一份档案包含：

- 简历概况。
- 岗位 JD。
- 目标岗位。
- 目标公司。

AI 面试官后续会基于这些信息生成更贴合场景的问题。

## 3. 面试页的作用

面试页是用户主工作台。

它需要展示：

- 当前使用哪份档案。
- 当前是学习辅导模式还是模拟面试模式。
- AI 面试官的问题。
- 用户回答输入框。
- Agent 为什么这样问。
- 本题参考了哪些 RAG 资料。

## 4. 训练页的作用

训练页承接面试复盘中的 weakTag。

完整闭环是：

```text
完成面试 -> 生成复盘 -> 提取薄弱点 -> 生成训练任务 -> 继续专项训练
```

## 5. Vue3 工程化怎么讲

这轮没有把所有代码继续堆在页面里，而是拆成：

- `ProfilesPage.vue`：档案页编排。
- `ProfileCurrentCard.vue`：当前档案摘要。
- `ProfileList.vue`：档案列表。
- `InterviewPage.vue`：面试工作台编排。
- `InterviewModeSwitch.vue`：面试模式切换。
- `CurrentProfileBanner.vue`：当前档案横幅。
- `InterviewEvidencePanel.vue`：Agent / RAG 解释。
- `TrainingPage.vue`：训练入口页。
- `TrainingTaskList.vue`：训练任务列表。

页面负责组合组件，store 负责跨页面状态，API client 负责请求后端。

## 6. 面试表达

可以这样讲：

```text
我把 Vue3 用户端继续产品化，重点打磨投递档案、面试训练台和训练中心。档案页负责沉淀简历、岗位 JD 和公司信息；面试页绑定当前档案，并支持学习辅导和真实面试两种 Agent 模式；训练页承接复盘里的 weakTag，把薄弱点转成后续训练任务。

同时我把用户端和管理员后台的边界分开：用户端回答“我怎么训练”，管理员后台回答“系统运行得怎么样”。这样设计能体现我对产品边界、权限边界和 AI 应用可观测性的理解。
```
```

- [ ] **Step 2: Update status docs**

After implementation and verification pass, update:

```text
docs/specs/README.md
docs/plans/README.md
docs/roadmap/current-state.md
```

Required changes:

```text
Move docs/specs/active/vue3-user-workbench-v2-design.md to docs/specs/completed/vue3-user-workbench-v2-design.md.
Move docs/plans/active/vue3-user-workbench-v2.md to docs/plans/completed/vue3-user-workbench-v2.md.
Set docs/specs/active/ and docs/plans/active/ to empty unless a new stage has been discussed.
Record that Vue3 用户工作台 V2 has completed a staged implementation.
```

- [ ] **Step 3: Run documentation sanity check**

Run:

```powershell
rg -n "T[O]DO|T[B]D|F[I]XME|待[定]|待[补]充" docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md docs/specs/README.md docs/plans/README.md docs/roadmap/current-state.md
```

Expected: no matches.

- [ ] **Step 4: Commit docs**

Run:

```powershell
git add docs/learning/14-Vue3用户工作台如何串起档案面试和训练闭环.md docs/specs/README.md docs/plans/README.md docs/roadmap/current-state.md
git commit -m "docs: explain vue user workbench flow"
```

Skip commit if the user explicitly asked not to commit.

---

## Final Verification

Run before claiming completion:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

If any backend file changed, also run:

```powershell
python -m pytest -q
```

Browser verification must cover:

```text
http://127.0.0.1:5173/vue/app/profiles
http://127.0.0.1:5173/vue/app/interview
http://127.0.0.1:5173/vue/app/training
```

Completion criteria:

- 档案页有当前档案、新建档案、档案列表和开始面试入口。
- 面试页未选择档案时有明确引导。
- 面试页选择档案后有档案摘要、模式切换、聊天区和解释面板。
- 训练页有训练闭环说明和空状态 / 任务列表能力。
- 普通用户主流程不混入管理员后台功能。
- Vue tests pass.
- Vue build passes.
- Browser desktop and mobile checks pass.

## Plan Self-Review

Spec coverage:

- 档案页产品化：Task 1.
- 面试页产品化：Task 2.
- 训练页产品化：Task 3.
- 前端测试优先：Tasks 1-3 each begin with failing tests.
- 浏览器验证：Task 4.
- 学习文档：Task 5.
- 不改后端 API、RAG、Agent、LangGraph：file boundaries and do-not-modify list.
- 不做管理员后台 V2：file boundaries and product boundary.

Implementation order:

```text
profiles
-> interview
-> training
-> verification
-> learning docs and route state
```

Risk control:

- Existing backend APIs stay unchanged.
- Existing admin console stays read-only and separate.
- Each UI area is componentized.
- Vue tests and build gate completion.
