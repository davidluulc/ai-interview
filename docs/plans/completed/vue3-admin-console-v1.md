# Vue3 Admin Console V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vue3 administrator console that differentiates admin users from normal users and surfaces account management, RAG quality, Agent decision logs, and system configuration through existing `/api/admin/*` endpoints.

**Architecture:** Keep the backend admin API read-only for this stage and implement the new capability in the Vue3 frontend. Use `auth.user.role` as the frontend visibility signal, while relying on backend `require_admin_user` as the real security boundary. Add a focused `admin` API module, a Pinia `admin` store, and a productized `AdminPage.vue` with tests before implementation.

**Tech Stack:** Vue3, TypeScript, Pinia, Vue Router, Vitest, existing FastAPI `/api/admin/*` routes, existing `apiRequest` client.

---

## File Structure

Create:

- `frontend/src/api/admin.ts`: typed wrappers around existing read-only admin endpoints.
- `frontend/src/stores/admin.ts`: admin dashboard state, filtered users, and `loadDashboard()`.
- `frontend/src/stores/admin.test.ts`: store tests for dashboard loading, search, role filtering, and permission errors.
- `frontend/src/pages/app/admin-page.test.ts`: page tests for permission copy and dashboard rendering.
- `docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md`: Chinese learning note after implementation.

Modify:

- `frontend/src/stores/auth.ts`: expose `isAdmin` computed property.
- `frontend/src/stores/auth.test.ts`: assert admin role detection.
- `frontend/src/layouts/AppLayout.vue`: hide admin navigation for non-admin users.
- `frontend/src/layouts/app-layout.test.ts`: assert admin navigation visibility and keep logout behavior covered.
- `frontend/src/pages/app/AdminPage.vue`: replace placeholder with permission-aware admin console.
- `frontend/src/router/router.test.ts`: keep existing auth redirect tests green; add no route-level admin redirect unless implementation explicitly chooses it.
- `docs/plans/README.md`: mark this plan as active.
- `docs/roadmap/current-state.md`: mention this plan as the current admin-console execution plan.

Do not modify in this stage:

- `backend_python/routes/admin.py` unless a frontend requirement cannot be met by current response fields.
- `backend_python/db_models.py`.
- `backend_python/auth.py`.
- `docker-compose.yml`.
- `Dockerfile`.
- legacy `index.html`, `styles.css`, `app.js`.

No destructive actions:

- Do not delete users.
- Do not change roles.
- Do not reset passwords.
- Do not revoke other users' tokens.
- Do not add write admin endpoints.
- Do not push to GitHub without explicit user confirmation.

---

### Task 1: Admin Role Signal And Navigation

**Files:**
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/stores/auth.test.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`
- Modify: `frontend/src/layouts/app-layout.test.ts`

- [ ] **Step 1: Write failing auth store test for admin role**

Add this test to `frontend/src/stores/auth.test.ts`:

```ts
it("exposes whether the current user is an admin", async () => {
  vi.mocked(authApi.login).mockResolvedValue({
    access_token: "access-1",
    refresh_token: "refresh-1",
    user: {
      id: 1,
      email: "admin@ai-interview.com",
      username: "admin",
      role: "admin"
    }
  });

  const store = useAuthStore();
  await store.login("admin@ai-interview.com", "password123");

  expect(store.isAdmin).toBe(true);
});
```

- [ ] **Step 2: Run auth store test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- auth.test.ts
```

Expected: FAIL because `store.isAdmin` does not exist.

- [ ] **Step 3: Implement `isAdmin` in auth store**

Modify `frontend/src/stores/auth.ts`:

```ts
const isAdmin = computed(() => user.value?.role === "admin");
```

Return it from the store:

```ts
return { user, loading, error, isAuthenticated, isAdmin, login, register, restore, logout };
```

- [ ] **Step 4: Run auth store test and verify it passes**

Run:

```powershell
cd frontend
npm.cmd run test -- auth.test.ts
```

Expected: PASS.

- [ ] **Step 5: Update layout tests for admin navigation visibility**

Update `frontend/src/layouts/app-layout.test.ts` so the mocked auth store can switch roles:

```ts
const authStore = {
  user: { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin" },
  isAdmin: true,
  logout: vi.fn()
};
```

Add tests:

```ts
it("shows the admin navigation item for admin users", () => {
  authStore.isAdmin = true;
  const wrapper = mount(AppLayout, { global: globalConfig });

  expect(wrapper.text()).toContain("后台");
});

it("hides the admin navigation item for normal users", () => {
  authStore.isAdmin = false;
  const wrapper = mount(AppLayout, { global: globalConfig });

  expect(wrapper.text()).not.toContain("后台");
});
```

- [ ] **Step 6: Run layout tests and verify they fail**

Run:

```powershell
cd frontend
npm.cmd run test -- app-layout.test.ts
```

Expected: FAIL because the admin link is always visible.

- [ ] **Step 7: Hide admin link for non-admin users**

Modify `frontend/src/layouts/AppLayout.vue`:

```vue
<RouterLink v-if="auth.isAdmin" to="/vue/app/admin">后台</RouterLink>
```

Ensure the script has:

```ts
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
```

Keep the existing logout function unchanged.

- [ ] **Step 8: Run focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- auth.test.ts app-layout.test.ts
```

Expected: PASS.

- [ ] **Step 9: Commit task changes**

Run:

```powershell
git add frontend/src/stores/auth.ts frontend/src/stores/auth.test.ts frontend/src/layouts/AppLayout.vue frontend/src/layouts/app-layout.test.ts
git commit -m "feat: gate vue admin navigation by role"
```

If the working tree contains unrelated user changes, do not include them.

---

### Task 2: Admin API Client And Store

**Files:**
- Create: `frontend/src/api/admin.ts`
- Create: `frontend/src/stores/admin.ts`
- Create: `frontend/src/stores/admin.test.ts`

- [ ] **Step 1: Write failing admin store tests**

Create `frontend/src/stores/admin.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as adminApi from "@/api/admin";
import { useAdminStore } from "./admin";

vi.mock("@/api/admin", () => ({
  fetchAdminSummary: vi.fn(),
  fetchAdminUsers: vi.fn(),
  fetchAdminRagDocuments: vi.fn(),
  fetchAdminRagQuality: vi.fn(),
  fetchAdminAgentLogs: vi.fn(),
  fetchAdminConfig: vi.fn()
}));

describe("admin store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(adminApi.fetchAdminSummary).mockReset();
    vi.mocked(adminApi.fetchAdminUsers).mockReset();
    vi.mocked(adminApi.fetchAdminRagDocuments).mockReset();
    vi.mocked(adminApi.fetchAdminRagQuality).mockReset();
    vi.mocked(adminApi.fetchAdminAgentLogs).mockReset();
    vi.mocked(adminApi.fetchAdminConfig).mockReset();
  });

  it("loads the full admin dashboard through read-only endpoints", async () => {
    vi.mocked(adminApi.fetchAdminSummary).mockResolvedValue({
      userCount: 2,
      interviewRecordCount: 3,
      ragDocumentCount: 4,
      ragRetrievalLogCount: 5,
      agentDecisionLogCount: 6
    });
    vi.mocked(adminApi.fetchAdminUsers).mockResolvedValue({
      items: [
        { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin", createdAt: "2026-06-12T10:00:00" },
        { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "2026-06-12T11:00:00" }
      ]
    });
    vi.mocked(adminApi.fetchAdminRagDocuments).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagQuality).mockResolvedValue({
      summary: { totalLogCount: 2, lowQualityCount: 1, emptyRecallCount: 1, weakRecallCount: 0, unusedInPromptCount: 0 },
      items: []
    });
    vi.mocked(adminApi.fetchAdminAgentLogs).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminConfig).mockResolvedValue({
      modelName: "qwen-plus",
      embeddingModel: "text-embedding-v4",
      rerankModel: "gte-rerank",
      databaseUrl: "sqlite:///./data/app.db"
    });

    const store = useAdminStore();
    await store.loadDashboard();

    expect(store.summary?.userCount).toBe(2);
    expect(store.users).toHaveLength(2);
    expect(store.ragQuality?.summary.emptyRecallCount).toBe(1);
    expect(store.config?.modelName).toBe("qwen-plus");
  });

  it("filters users by search text and role", () => {
    const store = useAdminStore();
    store.users = [
      { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin", createdAt: "" },
      { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "" }
    ];

    store.userSearch = "demo";
    store.roleFilter = "user";

    expect(store.filteredUsers).toEqual([
      { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "" }
    ]);
  });

  it("maps 403 errors to a readable permission message", async () => {
    vi.mocked(adminApi.fetchAdminSummary).mockRejectedValue(new Error("Admin privileges required"));
    vi.mocked(adminApi.fetchAdminUsers).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagDocuments).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagQuality).mockResolvedValue({
      summary: { totalLogCount: 0, lowQualityCount: 0, emptyRecallCount: 0, weakRecallCount: 0, unusedInPromptCount: 0 },
      items: []
    });
    vi.mocked(adminApi.fetchAdminAgentLogs).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminConfig).mockResolvedValue({
      modelName: "",
      embeddingModel: "",
      rerankModel: "",
      databaseUrl: ""
    });

    const store = useAdminStore();
    await store.loadDashboard();

    expect(store.error).toBe("当前账号没有管理员权限");
  });
});
```

- [ ] **Step 2: Run admin store test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- admin.test.ts
```

Expected: FAIL because `@/api/admin` and `useAdminStore` do not exist.

- [ ] **Step 3: Create admin API client**

Create `frontend/src/api/admin.ts`:

```ts
import { apiRequest } from "./client";

export interface AdminSummary {
  userCount: number;
  interviewRecordCount: number;
  ragDocumentCount: number;
  ragRetrievalLogCount: number;
  agentDecisionLogCount: number;
}

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  role: "admin" | "user" | string;
  createdAt: string | null;
}

export interface AdminListResponse<T> {
  items: T[];
}

export interface AdminRagDocument {
  id: number;
  title: string;
  knowledgeBase?: string;
  knowledge_base?: string;
  status?: string;
  visibility?: string;
  chunkCount?: number;
  chunk_count?: number;
  duplicateChunkCount?: number;
  duplicate_chunk_count?: number;
  userId?: number;
  userEmail?: string;
  updatedAt?: string | null;
  updated_at?: string | null;
}

export interface AdminRagQualitySummary {
  totalLogCount: number;
  lowQualityCount: number;
  emptyRecallCount: number;
  weakRecallCount: number;
  unusedInPromptCount: number;
}

export interface AdminRagQualityItem {
  id?: number;
  queryText?: string;
  query_text?: string;
  retrieverName?: string;
  retriever_name?: string;
  hitCount?: number;
  hit_count?: number;
  issueType?: string;
  recommendation?: string;
  createdAt?: string | null;
}

export interface AdminRagQuality {
  summary: AdminRagQualitySummary;
  items: AdminRagQualityItem[];
}

export interface AdminAgentLog {
  id?: number;
  nextAction?: string;
  next_action?: string;
  stage?: string;
  difficulty?: string;
  focus?: string;
  reason?: string;
  fallbackUsed?: boolean;
  fallback_used?: number | boolean;
  createdAt?: string | null;
}

export interface AdminConfig {
  modelName: string;
  embeddingModel: string;
  rerankModel: string;
  databaseUrl: string;
}

export function fetchAdminSummary(): Promise<AdminSummary> {
  return apiRequest<AdminSummary>("/api/admin/summary");
}

export function fetchAdminUsers(): Promise<AdminListResponse<AdminUser>> {
  return apiRequest<AdminListResponse<AdminUser>>("/api/admin/users");
}

export function fetchAdminRagDocuments(): Promise<AdminListResponse<AdminRagDocument>> {
  return apiRequest<AdminListResponse<AdminRagDocument>>("/api/admin/rag/documents");
}

export function fetchAdminRagQuality(): Promise<AdminRagQuality> {
  return apiRequest<AdminRagQuality>("/api/admin/rag/quality");
}

export function fetchAdminAgentLogs(): Promise<AdminListResponse<AdminAgentLog>> {
  return apiRequest<AdminListResponse<AdminAgentLog>>("/api/admin/agent/logs");
}

export function fetchAdminConfig(): Promise<AdminConfig> {
  return apiRequest<AdminConfig>("/api/admin/config");
}
```

- [ ] **Step 4: Create admin store**

Create `frontend/src/stores/admin.ts`:

```ts
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as adminApi from "@/api/admin";

export const useAdminStore = defineStore("admin", () => {
  const summary = ref<adminApi.AdminSummary | null>(null);
  const users = ref<adminApi.AdminUser[]>([]);
  const ragDocuments = ref<adminApi.AdminRagDocument[]>([]);
  const ragQuality = ref<adminApi.AdminRagQuality | null>(null);
  const agentLogs = ref<adminApi.AdminAgentLog[]>([]);
  const config = ref<adminApi.AdminConfig | null>(null);
  const loading = ref(false);
  const error = ref("");
  const userSearch = ref("");
  const roleFilter = ref<"all" | "admin" | "user">("all");

  const filteredUsers = computed(() => {
    const search = userSearch.value.trim().toLowerCase();
    return users.value.filter((user) => {
      const matchesRole = roleFilter.value === "all" || user.role === roleFilter.value;
      const matchesSearch =
        !search ||
        user.email.toLowerCase().includes(search) ||
        user.username.toLowerCase().includes(search);
      return matchesRole && matchesSearch;
    });
  });

  async function loadDashboard(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const [summaryResult, usersResult, documentsResult, qualityResult, logsResult, configResult] =
        await Promise.all([
          adminApi.fetchAdminSummary(),
          adminApi.fetchAdminUsers(),
          adminApi.fetchAdminRagDocuments(),
          adminApi.fetchAdminRagQuality(),
          adminApi.fetchAdminAgentLogs(),
          adminApi.fetchAdminConfig()
        ]);

      summary.value = summaryResult;
      users.value = usersResult.items;
      ragDocuments.value = documentsResult.items;
      ragQuality.value = qualityResult;
      agentLogs.value = logsResult.items;
      config.value = configResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : "管理员后台加载失败";
      error.value = message.includes("Admin privileges") || message.includes("403")
        ? "当前账号没有管理员权限"
        : message;
    } finally {
      loading.value = false;
    }
  }

  return {
    summary,
    users,
    ragDocuments,
    ragQuality,
    agentLogs,
    config,
    loading,
    error,
    userSearch,
    roleFilter,
    filteredUsers,
    loadDashboard
  };
});
```

- [ ] **Step 5: Run admin store test**

Run:

```powershell
cd frontend
npm.cmd run test -- admin.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit task changes**

Run:

```powershell
git add frontend/src/api/admin.ts frontend/src/stores/admin.ts frontend/src/stores/admin.test.ts
git commit -m "feat: add vue admin dashboard store"
```

---

### Task 3: Admin Page Rendering

**Files:**
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Create: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing admin page tests**

Create `frontend/src/pages/app/admin-page.test.ts`:

```ts
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminPage from "./AdminPage.vue";

const authStore = {
  isAdmin: true
};

const adminStore = {
  summary: {
    userCount: 2,
    interviewRecordCount: 3,
    ragDocumentCount: 4,
    ragRetrievalLogCount: 5,
    agentDecisionLogCount: 6
  },
  filteredUsers: [
    { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin", createdAt: "2026-06-12T10:00:00" },
    { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "2026-06-12T11:00:00" }
  ],
  ragDocuments: [
    { id: 1, title: "RAG 日志知识", knowledgeBase: "role_knowledge", status: "enabled", visibility: "public", chunkCount: 8, duplicateChunkCount: 1, userEmail: "admin@ai-interview.com" }
  ],
  ragQuality: {
    summary: { totalLogCount: 3, lowQualityCount: 1, emptyRecallCount: 1, weakRecallCount: 0, unusedInPromptCount: 0 },
    items: [
      { id: 1, queryText: "RAG 日志怎么写", retrieverName: "role_knowledge", hitCount: 0, issueType: "empty_recall", recommendation: "补充知识库内容" }
    ]
  },
  agentLogs: [
    { id: 1, nextAction: "switch_topic", stage: "技术追问", difficulty: "basic", focus: "RAG", reason: "连续弱回答", fallbackUsed: true }
  ],
  config: {
    modelName: "qwen-plus",
    embeddingModel: "text-embedding-v4",
    rerankModel: "gte-rerank",
    databaseUrl: "sqlite:///./data/app.db"
  },
  loading: false,
  error: "",
  userSearch: "",
  roleFilter: "all",
  loadDashboard: vi.fn()
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

vi.mock("@/stores/admin", () => ({
  useAdminStore: () => adminStore
}));

const globalConfig = {
  stubs: {
    AppLayout: { template: "<main><slot /></main>" }
  }
};

describe("admin page", () => {
  beforeEach(() => {
    authStore.isAdmin = true;
    adminStore.loadDashboard.mockReset();
    adminStore.error = "";
  });

  it("shows a permission message for normal users", () => {
    authStore.isAdmin = false;

    const wrapper = mount(AdminPage, { global: globalConfig });

    expect(wrapper.text()).toContain("当前账号没有管理员权限");
    expect(adminStore.loadDashboard).not.toHaveBeenCalled();
  });

  it("loads and renders the admin dashboard for admin users", () => {
    const wrapper = mount(AdminPage, { global: globalConfig });

    expect(adminStore.loadDashboard).toHaveBeenCalled();
    expect(wrapper.text()).toContain("平台概览");
    expect(wrapper.text()).toContain("用户数");
    expect(wrapper.text()).toContain("admin@ai-interview.com");
    expect(wrapper.text()).toContain("RAG 质量诊断");
    expect(wrapper.text()).toContain("补充知识库内容");
    expect(wrapper.text()).toContain("Agent 决策日志");
    expect(wrapper.text()).toContain("连续弱回答");
  });
});
```

- [ ] **Step 2: Run admin page test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- admin-page.test.ts
```

Expected: FAIL because `AdminPage.vue` still contains placeholder content.

- [ ] **Step 3: Replace AdminPage placeholder**

Modify `frontend/src/pages/app/AdminPage.vue` with this structure:

```vue
<template>
  <AppLayout>
    <section v-if="!auth.isAdmin" class="permission-panel">
      <p class="eyebrow">Admin</p>
      <h1>当前账号没有管理员权限</h1>
      <p>后台入口只对管理员开放。前端隐藏入口只是体验控制，真正权限仍由后端 /api/admin/* 接口校验。</p>
    </section>

    <section v-else class="admin-page">
      <header class="page-header">
        <p class="eyebrow">Admin Console</p>
        <h1>管理员后台</h1>
        <p>观察账号、RAG 召回质量、Agent 决策和系统配置。</p>
      </header>

      <p v-if="admin.error" class="error">{{ admin.error }}</p>
      <p v-if="admin.loading" class="muted">后台数据加载中...</p>

      <section v-if="admin.summary" class="section">
        <h2>平台概览</h2>
        <div class="metrics-grid">
          <article class="metric"><span>用户数</span><strong>{{ admin.summary.userCount }}</strong></article>
          <article class="metric"><span>面试记录</span><strong>{{ admin.summary.interviewRecordCount }}</strong></article>
          <article class="metric"><span>RAG 文档</span><strong>{{ admin.summary.ragDocumentCount }}</strong></article>
          <article class="metric"><span>RAG 日志</span><strong>{{ admin.summary.ragRetrievalLogCount }}</strong></article>
          <article class="metric"><span>Agent 日志</span><strong>{{ admin.summary.agentDecisionLogCount }}</strong></article>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <h2>账号管理</h2>
          <span>{{ admin.filteredUsers.length }} 个结果</span>
        </div>
        <div class="filters">
          <input v-model="admin.userSearch" placeholder="搜索邮箱或用户名" />
          <select v-model="admin.roleFilter">
            <option value="all">全部角色</option>
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th><th>邮箱</th><th>用户名</th><th>角色</th><th>注册时间</th></tr>
            </thead>
            <tbody>
              <tr v-for="user in admin.filteredUsers" :key="user.id">
                <td>{{ user.id }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.username }}</td>
                <td><span class="pill">{{ user.role === "admin" ? "管理员" : "普通用户" }}</span></td>
                <td>{{ formatDate(user.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="admin.ragQuality" class="section">
        <h2>RAG 质量诊断</h2>
        <div class="quality-grid">
          <article><span>低质量召回</span><strong>{{ admin.ragQuality.summary.lowQualityCount }}</strong></article>
          <article><span>空召回</span><strong>{{ admin.ragQuality.summary.emptyRecallCount }}</strong></article>
          <article><span>弱召回</span><strong>{{ admin.ragQuality.summary.weakRecallCount }}</strong></article>
          <article><span>未进入 Prompt</span><strong>{{ admin.ragQuality.summary.unusedInPromptCount }}</strong></article>
        </div>
        <article v-for="item in admin.ragQuality.items" :key="item.id || item.queryText" class="log-item">
          <strong>{{ item.queryText || item.query_text || "未知 query" }}</strong>
          <p>{{ item.retrieverName || item.retriever_name }} · 命中 {{ item.hitCount ?? item.hit_count ?? 0 }} 条 · {{ item.issueType }}</p>
          <p>{{ item.recommendation }}</p>
        </article>
      </section>

      <section class="section">
        <h2>RAG 文档概览</h2>
        <article v-for="document in admin.ragDocuments" :key="document.id" class="log-item">
          <strong>{{ document.title }}</strong>
          <p>{{ document.knowledgeBase || document.knowledge_base }} · {{ document.status }} · {{ document.visibility }}</p>
          <p>chunk {{ document.chunkCount ?? document.chunk_count ?? 0 }}，重复 {{ document.duplicateChunkCount ?? document.duplicate_chunk_count ?? 0 }}，所属 {{ document.userEmail || "未知用户" }}</p>
        </article>
      </section>

      <section class="section">
        <h2>Agent 决策日志</h2>
        <article v-for="log in admin.agentLogs" :key="log.id || log.createdAt" class="log-item">
          <strong>{{ normalizeAction(log.nextAction || log.next_action) }}</strong>
          <p>{{ log.stage }} · {{ log.difficulty }} · {{ log.focus }}</p>
          <p>{{ log.reason }}</p>
          <span v-if="log.fallbackUsed || log.fallback_used" class="warning-pill">fallback</span>
        </article>
      </section>

      <section v-if="admin.config" class="section">
        <h2>系统配置</h2>
        <div class="config-grid">
          <p><span>LLM</span><strong>{{ admin.config.modelName }}</strong></p>
          <p><span>Embedding</span><strong>{{ admin.config.embeddingModel }}</strong></p>
          <p><span>Rerank</span><strong>{{ admin.config.rerankModel }}</strong></p>
          <p><span>Database</span><strong>{{ maskDatabaseUrl(admin.config.databaseUrl) }}</strong></p>
        </div>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useAdminStore } from "@/stores/admin";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const admin = useAdminStore();

onMounted(() => {
  if (auth.isAdmin) {
    void admin.loadDashboard();
  }
});

function formatDate(value: string | null): string {
  if (!value) return "未知";
  return value.slice(0, 10);
}

function normalizeAction(action = ""): string {
  const map: Record<string, string> = {
    deep_follow_up: "继续深挖",
    lower_difficulty: "降低难度",
    switch_topic: "切换话题",
    finish_interview: "结束面试",
    practice_weakness: "专项训练"
  };
  return map[action] || action || "未知动作";
}

function maskDatabaseUrl(value: string): string {
  if (!value) return "未配置";
  if (value.includes("@")) return value.replace(/\/\/.*@/, "//***@");
  return value;
}
</script>
```

Add scoped CSS that keeps layout readable:

```css
.admin-page,
.permission-panel {
  display: grid;
  gap: 24px;
  max-width: 1180px;
}

.page-header,
.section,
.permission-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h1,
h2,
p {
  margin: 0;
}

.page-header p,
.muted {
  color: var(--color-text-muted);
}

.metrics-grid,
.quality-grid,
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.metric,
.quality-grid article,
.config-grid p,
.log-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 14px;
}

.metric span,
.quality-grid span,
.config-grid span {
  color: var(--color-text-muted);
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
}

.metric strong,
.quality-grid strong {
  font-size: 26px;
}

.section-title,
.filters {
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.filters {
  margin: 16px 0;
}

.filters input,
.filters select {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  min-width: 720px;
  width: 100%;
}

th,
td {
  border-bottom: 1px solid var(--color-border);
  padding: 12px;
  text-align: left;
  vertical-align: top;
}

.pill,
.warning-pill {
  border-radius: 999px;
  display: inline-flex;
  font-size: 12px;
  padding: 4px 8px;
}

.pill {
  background: #eef4ff;
  color: #175cd3;
}

.warning-pill {
  background: #fff3cd;
  color: #7a4d00;
  margin-top: 8px;
}

.error {
  color: #b42318;
}

@media (max-width: 760px) {
  .section-title,
  .filters {
    align-items: stretch;
    flex-direction: column;
  }
}
```

- [ ] **Step 4: Run admin page test**

Run:

```powershell
cd frontend
npm.cmd run test -- admin-page.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit task changes**

Run:

```powershell
git add frontend/src/pages/app/AdminPage.vue frontend/src/pages/app/admin-page.test.ts
git commit -m "feat: render vue admin console"
```

---

### Task 4: Integration Verification

**Files:**
- Possibly modify: `frontend/src/router/router.test.ts`
- Possibly modify: `frontend/src/pages/app/AdminPage.vue`
- Possibly modify: `frontend/src/layouts/AppLayout.vue`

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

- [ ] **Step 3: Run admin backend tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_admin_rag_quality.py -q
```

Expected: all selected backend tests pass.

- [ ] **Step 4: Run full backend regression if admin backend files changed**

Only if `backend_python/` was modified, run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 5: Browser verification**

Start or reuse backend:

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

Start or reuse Vue dev server:

```powershell
cd frontend
npm.cmd run dev
```

Verify with localhost:

```text
http://localhost:5173/vue/auth/login
http://localhost:5173/vue/app/admin
```

Checks:

```text
普通用户登录后：侧边栏不显示“后台”。
普通用户手动访问 /vue/app/admin：页面显示“当前账号没有管理员权限”。
管理员登录后：侧边栏显示“后台”。
管理员进入 /vue/app/admin：能看到“平台概览”“账号管理”“RAG 质量诊断”“Agent 决策日志”“系统配置”。
页面不出现 undefined。
移动端宽度下后台表格不挤压主布局。
```

- [ ] **Step 6: Fix only issues found by verification**

If verification reveals text overflow, add scoped CSS only in `AdminPage.vue` or `AppLayout.vue`.

If verification reveals a missing field from an existing backend response, normalize camelCase and snake_case in the frontend before changing backend code.

- [ ] **Step 7: Commit verification fixes**

Run:

```powershell
git add frontend/src
git commit -m "fix: polish vue admin console verification issues"
```

Skip this commit if there were no fixes.

---

### Task 5: Learning Document And Route State Update

**Files:**
- Create: `docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/roadmap/current-state.md`

- [ ] **Step 1: Create learning document**

Create `docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md`:

```markdown
# 13. Vue3 管理员后台如何承接权限和 AI 可观测性

## 1. 为什么管理员后台不是摆设

AI 模拟面试系统不是只有用户端对话页面。

当系统有用户、RAG、Agent、训练任务和历史记录后，管理员需要观察系统运行情况：

- 当前有多少用户。
- RAG 文档是否足够。
- RAG 是否经常空召回或弱召回。
- Agent 是否频繁 fallback。
- 系统当前用的模型和数据库配置是什么。

## 2. 前端权限和后端权限的区别

前端根据 `auth.user.role` 决定是否显示后台入口。

这只是用户体验控制。

真正的安全边界在后端：

```text
/api/admin/* -> require_admin_user
```

如果普通用户绕过前端，直接请求 admin 接口，后端仍然会返回 403。

## 3. 为什么 V1 只做只读后台

删除用户、禁用账号、重置密码、修改角色都属于高风险写操作。

这些能力需要：

- 操作审计日志。
- 最后一个管理员保护。
- 管理员不能禁用自己。
- 二次确认和回滚策略。

所以 V1 先做低风险只读能力：用户列表、平台统计、RAG 质量诊断、Agent 决策日志和系统配置。

## 4. RAG 质量诊断怎么讲

后台会展示：

- 空召回。
- 弱召回。
- 未进入 prompt。
- 建议动作。

这说明项目不是只会调用模型，而是关注 RAG 的召回质量和可观测性。

## 5. Agent 决策日志怎么讲

后台会展示：

- nextAction。
- stage。
- difficulty。
- focus。
- reason。
- fallbackUsed。

这能用来观察 Agent 是否一直卡在同一话题，是否根据用户回答调整难度，是否频繁走兜底逻辑。

## 6. 面试表达

可以这样说：

```text
我在 Vue3 前端中补了管理员后台。普通用户默认看不到后台入口，管理员可以看到平台统计、用户列表、RAG 质量诊断、Agent 决策日志和系统配置。前端的 role 判断只负责体验层显示，真正的权限控制在后端 /api/admin/*，通过 require_admin_user 保证普通用户无法访问后台接口。第一版后台只做只读能力，避免误删用户或引入复杂 RBAC，但已经能体现 AI 应用工程化里的可观测性。
```
```

- [ ] **Step 2: Update plan README**

Modify `docs/plans/README.md` current state to mention:

```text
docs/plans/active/vue3-frontend-rebuild-v1.md
docs/plans/active/vue3-admin-console-v1.md
```

- [ ] **Step 3: Update current state**

In `docs/roadmap/current-state.md`, update the active plan section to mention:

```text
docs/plans/active/vue3-admin-console-v1.md
```

and note that Vue3 admin console implementation is now planned.

- [ ] **Step 4: Run documentation sanity checks**

Run:

```powershell
rg -n "T[B]D|T[O]DO|F[I]XME|待[定]|待[补]充" docs/plans/active/vue3-admin-console-v1.md docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md
```

Expected: no matches.

- [ ] **Step 5: Commit documentation**

Run:

```powershell
git add docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md docs/plans/README.md docs/roadmap/current-state.md
git commit -m "docs: explain vue admin console architecture"
```

---

## Final Verification

Run these commands before claiming completion:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
cd ..
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_admin_rag_quality.py -q
```

If backend code was modified, also run:

```powershell
python -m pytest -q
```

Browser verification must cover:

```text
普通用户：无后台入口，手动进入后台显示无权限。
管理员：有后台入口，后台数据可渲染。
登出：清理登录态后无法继续访问后台。
移动端：后台页面无明显文字重叠和横向撑破。
```

## Plan Self-Review

Spec coverage:

- 管理员和普通用户体验差异：Task 1 and Task 3.
- 后端权限边界不变：File boundaries and Task 4 backend admin tests.
- 用户列表、搜索和角色筛选：Task 2 and Task 3.
- 平台统计：Task 2 and Task 3.
- RAG 质量诊断：Task 2 and Task 3.
- RAG 文档概览：Task 2 and Task 3.
- Agent 决策日志：Task 2 and Task 3.
- 系统配置只读和数据库 URL 脱敏：Task 3.
- 不做高风险写操作：File boundaries and no destructive actions section.
- 追求目标少打断：Plan avoids external submission, GitHub push, destructive file commands, and new dependency installation.

Implementation order:

```text
role signal and navigation
-> admin API and store
-> admin page rendering
-> integration verification
-> learning docs and route state update
```

Risk control:

- No admin write endpoints.
- No database schema changes.
- No legacy frontend edits.
- Backend admin API remains the security boundary.
- Each implementation task starts with failing tests.
