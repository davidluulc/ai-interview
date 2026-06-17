# Vue3 Frontend Rebuild V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new Vue3 + Vite + TypeScript frontend beside the existing legacy frontend, with a minimal Apple-like product shell, auth flow, API client, profile entry, and interview workspace skeleton.

**Architecture:** Keep the legacy frontend at `/` and build the new Vue3 app under `frontend/` first. During development, run FastAPI on `http://localhost:8000` and Vite on `http://localhost:5173`; Vite proxies `/api` to FastAPI. Do not change existing backend APIs, RAG, Agent, LangGraph, Docker, or the legacy `index.html` / `styles.css` / `app.js`.

**Tech Stack:** Vue3, Vite, TypeScript, Vue Router, Pinia, Vitest, CSS variables, existing FastAPI APIs.

---

## File Structure

Create:

- `docs/plans/active/vue3-frontend-rebuild-v1.md`: this implementation plan.
- `docs/frontend/vue3-rebuild-v1-quickstart.md`: Chinese quickstart for running old and new frontends.
- `frontend/package.json`: frontend scripts and dependencies.
- `frontend/index.html`: Vite HTML entry.
- `frontend/vite.config.ts`: Vite config with `/api` proxy and `/vue/` base.
- `frontend/tsconfig.json`, `frontend/tsconfig.node.json`: TypeScript config.
- `frontend/src/main.ts`: Vue app bootstrap.
- `frontend/src/App.vue`: root router outlet.
- `frontend/src/router/index.ts`: Vue Router routes and auth guard.
- `frontend/src/api/client.ts`: fetch wrapper, token injection, refresh handling.
- `frontend/src/api/auth.ts`: auth API calls.
- `frontend/src/api/profiles.ts`: application profile API calls.
- `frontend/src/api/interview.ts`: interview API calls.
- `frontend/src/stores/auth.ts`: auth state, login/register/logout/restore.
- `frontend/src/stores/profiles.ts`: profile list and current profile state.
- `frontend/src/stores/interview.ts`: interview draft and chat skeleton state.
- `frontend/src/layouts/AuthLayout.vue`: centered minimal auth layout.
- `frontend/src/layouts/AppLayout.vue`: product shell with top nav, side nav, content, right context slot.
- `frontend/src/pages/auth/LoginPage.vue`: login page.
- `frontend/src/pages/auth/RegisterPage.vue`: register page.
- `frontend/src/pages/app/InterviewPage.vue`: interview workspace skeleton.
- `frontend/src/pages/app/ProfilesPage.vue`: profile list and create/edit entry skeleton.
- `frontend/src/pages/app/KnowledgePage.vue`: V1 placeholder with knowledge module entry.
- `frontend/src/pages/app/HistoryPage.vue`: V1 placeholder with history entry.
- `frontend/src/pages/app/TrainingPage.vue`: V1 placeholder with training entry.
- `frontend/src/pages/app/AdminPage.vue`: V1 placeholder with admin entry.
- `frontend/src/pages/app/SettingsPage.vue`: V1 placeholder with settings entry.
- `frontend/src/components/common/PrimaryButton.vue`: minimal button component.
- `frontend/src/components/common/TextField.vue`: minimal input component.
- `frontend/src/components/interview/InterviewChatPanel.vue`: chat area skeleton.
- `frontend/src/components/interview/InterviewContextPanel.vue`: Agent/RAG explanation skeleton.
- `frontend/src/styles/tokens.css`: visual tokens.
- `frontend/src/styles/base.css`: global base styles.
- `frontend/src/test/setup.ts`: Vitest setup.
- `frontend/src/api/client.test.ts`: API client tests.
- `frontend/src/stores/auth.test.ts`: auth store tests.
- `frontend/src/router/router.test.ts`: route guard tests.

Modify:

- `.gitignore`: ignore `frontend/node_modules/`, `frontend/dist/`, and frontend coverage output if needed.
- `docs/specs/README.md`, `docs/plans/README.md`, `docs/roadmap/current-state.md`: only if plan status changes after implementation.

Do not modify:

- `index.html`
- `styles.css`
- `app.js`
- `backend_python/routes/*`
- `backend_python/langgraph_agent/*`
- `docker-compose.yml`
- `Dockerfile`
- `deploy/nginx/*`

---

### Task 1: Plan And Docs Baseline

**Files:**
- Create: `docs/plans/active/vue3-frontend-rebuild-v1.md`
- Create: `docs/frontend/vue3-rebuild-v1-quickstart.md`

- [ ] **Step 1: Create the implementation plan**

Write this file at `docs/plans/active/vue3-frontend-rebuild-v1.md`.

- [ ] **Step 2: Create the Chinese quickstart document**

Create `docs/frontend/vue3-rebuild-v1-quickstart.md` with:

```markdown
# Vue3 前端重构 V1 快速启动

## 1. 前端并行策略

旧前端继续保留：

```text
http://localhost:8000/
```

新 Vue3 前端开发期使用：

```text
http://localhost:5173/vue/
```

这样做的原因是：Vue3 重构期间不直接覆盖旧页面，旧页面仍然可以作为兜底入口。

## 2. 启动后端

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. 启动 Vue3 前端

```powershell
cd frontend
npm install
npm run dev
```

## 4. 验证入口

```text
旧页面：http://localhost:8000/
新页面：http://localhost:5173/vue/
登录页：http://localhost:5173/vue/auth/login
面试训练台：http://localhost:5173/vue/app/interview
```

## 5. 面试表达

这次前端重构采用新旧前端并行策略。旧原生页面继续保留，新 Vue3 页面使用 `/vue` 前缀独立运行。这样可以逐步迁移登录、档案、面试训练台、历史复盘和知识库页面，降低一次性替换带来的回归风险。
```

- [ ] **Step 3: Run a docs path check**

Run:

```powershell
Test-Path docs/plans/active/vue3-frontend-rebuild-v1.md
Test-Path docs/frontend/vue3-rebuild-v1-quickstart.md
```

Expected:

```text
True
True
```

- [ ] **Step 4: Commit**

```powershell
git add docs/plans/active/vue3-frontend-rebuild-v1.md docs/frontend/vue3-rebuild-v1-quickstart.md
git commit -m "docs: add vue3 frontend rebuild plan"
```

---

### Task 2: Scaffold Vue3 Vite Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/base.css`
- Modify: `.gitignore`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "ai-interview-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 5173",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1 --port 4173",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "pinia": "^3.0.0",
    "vue": "^3.5.0",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@types/node": "^24.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^27.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0",
    "vitest": "^3.2.0",
    "vue-tsc": "^3.0.0"
  }
}
```

- [ ] **Step 2: Create Vite and TypeScript config**

`frontend/vite.config.ts`:

```ts
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/vue/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true
  }
});
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals", "node"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create HTML and Vue bootstrap**

`frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI 模拟面试系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

`frontend/src/main.ts`:

```ts
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import "./styles/tokens.css";
import "./styles/base.css";

createApp(App).use(createPinia()).mount("#app");
```

`frontend/src/App.vue`:

```vue
<template>
  <main class="boot-page">
    <p>AI Interview</p>
    <h1>Vue3 前端已初始化</h1>
  </main>
</template>

<style scoped>
.boot-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  text-align: center;
}

.boot-page p {
  color: var(--color-accent);
  font-weight: 700;
  margin: 0;
}

.boot-page h1 {
  font-size: 40px;
  margin: 12px 0 0;
}
</style>
```

- [ ] **Step 4: Create visual tokens and base styles**

`frontend/src/styles/tokens.css`:

```css
:root {
  color-scheme: light;
  --color-bg: #f5f5f7;
  --color-surface: #ffffff;
  --color-surface-muted: #fbfbfd;
  --color-text: #1d1d1f;
  --color-text-muted: #6e6e73;
  --color-border: rgba(0, 0, 0, 0.1);
  --color-accent: #0071e3;
  --color-accent-hover: #0077ed;
  --shadow-soft: 0 18px 45px rgba(0, 0, 0, 0.08);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
}
```

`frontend/src/styles/base.css`:

```css
* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  letter-spacing: 0;
}

button,
input,
textarea,
select {
  font: inherit;
}

a {
  color: inherit;
  text-decoration: none;
}
```

- [ ] **Step 5: Update `.gitignore`**

Append these lines if absent:

```gitignore
frontend/node_modules/
frontend/dist/
frontend/coverage/
```

- [ ] **Step 6: Install dependencies**

Run:

```powershell
cd frontend
npm install
```

Expected: `package-lock.json` is created and dependencies install successfully.

- [ ] **Step 7: Run initial build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds and generates `frontend/dist/`.

- [ ] **Step 8: Commit**

```powershell
git add .gitignore frontend
git commit -m "feat: scaffold vue3 frontend"
```

---

### Task 3: Router, Layouts, And Placeholder Pages

**Files:**
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AuthLayout.vue`
- Create: `frontend/src/layouts/AppLayout.vue`
- Create: `frontend/src/pages/auth/LoginPage.vue`
- Create: `frontend/src/pages/auth/RegisterPage.vue`
- Create: `frontend/src/pages/app/InterviewPage.vue`
- Create: `frontend/src/pages/app/ProfilesPage.vue`
- Create: `frontend/src/pages/app/KnowledgePage.vue`
- Create: `frontend/src/pages/app/HistoryPage.vue`
- Create: `frontend/src/pages/app/TrainingPage.vue`
- Create: `frontend/src/pages/app/AdminPage.vue`
- Create: `frontend/src/pages/app/SettingsPage.vue`
- Test: `frontend/src/router/router.test.ts`

- [ ] **Step 1: Write route guard test**

Create `frontend/src/router/router.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { routes, requiresAuth } from "./index";

describe("vue router config", () => {
  it("keeps auth pages public and app pages protected", () => {
    expect(requiresAuth("/vue/auth/login")).toBe(false);
    expect(requiresAuth("/vue/auth/register")).toBe(false);
    expect(requiresAuth("/vue/app/interview")).toBe(true);
  });

  it("defines the main V1 pages", () => {
    const paths = routes.map((route) => route.path);
    expect(paths).toContain("/vue/auth/login");
    expect(paths).toContain("/vue/auth/register");
    expect(paths).toContain("/vue/app/interview");
    expect(paths).toContain("/vue/app/profiles");
  });
});
```

- [ ] **Step 2: Run router test and verify it fails**

Run:

```powershell
cd frontend
npm run test -- router.test.ts
```

Expected: FAIL because `frontend/src/router/index.ts` does not exist.

- [ ] **Step 3: Implement router**

Create `frontend/src/router/index.ts`:

```ts
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  { path: "/vue", redirect: "/vue/app/interview" },
  {
    path: "/vue/auth/login",
    component: () => import("@/pages/auth/LoginPage.vue"),
    meta: { public: true }
  },
  {
    path: "/vue/auth/register",
    component: () => import("@/pages/auth/RegisterPage.vue"),
    meta: { public: true }
  },
  {
    path: "/vue/app/interview",
    component: () => import("@/pages/app/InterviewPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/profiles",
    component: () => import("@/pages/app/ProfilesPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/knowledge",
    component: () => import("@/pages/app/KnowledgePage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/history",
    component: () => import("@/pages/app/HistoryPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/training",
    component: () => import("@/pages/app/TrainingPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/admin",
    component: () => import("@/pages/app/AdminPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/settings",
    component: () => import("@/pages/app/SettingsPage.vue"),
    meta: { requiresAuth: true }
  },
  { path: "/:pathMatch(.*)*", redirect: "/vue/app/interview" }
];

export function requiresAuth(path: string): boolean {
  const matched = routes.find((route) => route.path === path);
  return Boolean(matched?.meta?.requiresAuth);
}

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  const isPublic = Boolean(to.meta.public);
  const hasToken = Boolean(localStorage.getItem("ai_interview_access_token"));
  if (!isPublic && !hasToken) {
    return "/vue/auth/login";
  }
  return true;
});

export default router;
```

- [ ] **Step 4: Connect router to the Vue app**

Modify `frontend/src/main.ts`:

```ts
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/tokens.css";
import "./styles/base.css";

createApp(App).use(createPinia()).use(router).mount("#app");
```

Modify `frontend/src/App.vue`:

```vue
<template>
  <RouterView />
</template>
```

- [ ] **Step 5: Create layouts and placeholder pages**

Use minimal page content that clearly shows the route is working.

`frontend/src/layouts/AuthLayout.vue`:

```vue
<template>
  <main class="auth-layout">
    <section class="auth-panel">
      <slot />
    </section>
  </main>
</template>

<style scoped>
.auth-layout {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 32px;
}

.auth-panel {
  width: min(440px, 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: var(--shadow-soft);
  padding: 36px;
}
</style>
```

`frontend/src/layouts/AppLayout.vue`:

```vue
<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand">AI Interview</div>
      <RouterLink to="/vue/app/interview">面试</RouterLink>
      <RouterLink to="/vue/app/profiles">档案</RouterLink>
      <RouterLink to="/vue/app/knowledge">知识库</RouterLink>
      <RouterLink to="/vue/app/history">复盘</RouterLink>
      <RouterLink to="/vue/app/training">训练</RouterLink>
      <RouterLink to="/vue/app/admin">后台</RouterLink>
    </aside>
    <main class="workspace">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 232px minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-right: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.78);
  padding: 24px 18px;
}

.brand {
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 700;
}

.sidebar a {
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  padding: 10px 12px;
}

.sidebar a.router-link-active {
  background: var(--color-surface);
  color: var(--color-text);
}

.workspace {
  min-width: 0;
  padding: 28px;
}

@media (max-width: 760px) {
  .app-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: sticky;
    top: 0;
    z-index: 2;
    flex-direction: row;
    overflow-x: auto;
  }
}
</style>
```

Create each placeholder page with a visible heading. Example `frontend/src/pages/app/KnowledgePage.vue`:

```vue
<template>
  <AppLayout>
    <section class="page">
      <p class="eyebrow">Knowledge Base</p>
      <h1>知识库</h1>
      <p>Vue3 V1 先保留知识库入口，完整文档管理在 V2 迁移。</p>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
</script>
```

- [ ] **Step 6: Run router test**

```powershell
cd frontend
npm run test -- router.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src
git commit -m "feat: add vue routes and layouts"
```

---

### Task 4: API Client And Auth Store

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/stores/auth.ts`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/stores/auth.test.ts`

- [ ] **Step 1: Write API client tests**

`frontend/src/api/client.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, setApiTokens } from "./client";

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("injects the access token into requests", async () => {
    setApiTokens({ accessToken: "access-1", refreshToken: "refresh-1" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await apiRequest("/api/example");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/example",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer access-1"
        })
      })
    );
  });

  it("throws a readable error when the response is not ok", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "登录已过期" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(apiRequest("/api/example")).rejects.toThrow("登录已过期");
  });
});
```

- [ ] **Step 2: Run API client test and verify it fails**

```powershell
cd frontend
npm run test -- client.test.ts
```

Expected: FAIL because `apiRequest` is not implemented.

- [ ] **Step 3: Implement API client**

`frontend/src/api/client.ts`:

```ts
export const ACCESS_TOKEN_KEY = "ai_interview_access_token";
export const REFRESH_TOKEN_KEY = "ai_interview_refresh_token";

export interface ApiTokens {
  accessToken: string;
  refreshToken: string;
}

export function setApiTokens(tokens: ApiTokens): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
}

export function clearApiTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_TOKEN_KEY) || "";
}

export async function apiRequest<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...init, headers });
  const contentType = response.headers.get("Content-Type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof body === "object" && body && "detail" in body ? String(body.detail) : "请求失败";
    throw new Error(message);
  }

  return body as T;
}
```

- [ ] **Step 4: Implement auth API and store**

`frontend/src/api/auth.ts`:

```ts
import { apiRequest } from "./client";

export interface AuthResponse {
  accessToken?: string;
  refreshToken?: string;
  access_token?: string;
  refresh_token?: string;
  tokenType?: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  username: string;
  role?: string;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function register(email: string, username: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password })
  });
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/api/auth/me");
}
```

`frontend/src/stores/auth.ts`:

```ts
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as authApi from "@/api/auth";
import { clearApiTokens, getAccessToken, setApiTokens } from "@/api/client";

function normalizeToken(value: authApi.AuthResponse): { accessToken: string; refreshToken: string } {
  return {
    accessToken: value.accessToken || value.access_token || "",
    refreshToken: value.refreshToken || value.refresh_token || ""
  };
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<authApi.CurrentUser | null>(null);
  const loading = ref(false);
  const error = ref("");
  const isAuthenticated = computed(() => Boolean(getAccessToken()));

  async function login(email: string, password: string): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const tokens = normalizeToken(await authApi.login(email, password));
      setApiTokens(tokens);
      user.value = await authApi.fetchCurrentUser();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "登录失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function register(email: string, username: string, password: string): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const tokens = normalizeToken(await authApi.register(email, username, password));
      setApiTokens(tokens);
      user.value = await authApi.fetchCurrentUser();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "注册失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function restore(): Promise<void> {
    if (!getAccessToken()) {
      return;
    }
    user.value = await authApi.fetchCurrentUser();
  }

  function logout(): void {
    clearApiTokens();
    user.value = null;
  }

  return { user, loading, error, isAuthenticated, login, register, restore, logout };
});
```

- [ ] **Step 5: Run auth tests**

Create `frontend/src/stores/auth.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "@/api/auth";
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from "@/api/client";
import { useAuthStore } from "./auth";

vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  fetchCurrentUser: vi.fn()
}));

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
    vi.mocked(authApi.login).mockReset();
    vi.mocked(authApi.register).mockReset();
    vi.mocked(authApi.fetchCurrentUser).mockReset();
  });

  it("stores tokens and current user after login", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "access-1",
      refresh_token: "refresh-1"
    });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: 1,
      email: "student@example.com",
      username: "student"
    });

    const store = useAuthStore();
    await store.login("student@example.com", "password");

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("access-1");
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-1");
    expect(store.user?.email).toBe("student@example.com");
  });

  it("clears tokens and user on logout", () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "access-1");
    localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-1");

    const store = useAuthStore();
    store.logout();

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(store.user).toBeNull();
  });
});
```

Run:

```powershell
cd frontend
npm run test -- client.test.ts auth.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/api frontend/src/stores
git commit -m "feat: add vue auth api client"
```

---

### Task 5: Login And Register Pages

**Files:**
- Modify: `frontend/src/pages/auth/LoginPage.vue`
- Modify: `frontend/src/pages/auth/RegisterPage.vue`
- Create: `frontend/src/components/common/PrimaryButton.vue`
- Create: `frontend/src/components/common/TextField.vue`

- [ ] **Step 1: Create common components**

`frontend/src/components/common/PrimaryButton.vue`:

```vue
<template>
  <button class="primary-button" :disabled="disabled">
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ disabled?: boolean }>();
</script>

<style scoped>
.primary-button {
  width: 100%;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  font-weight: 600;
  padding: 13px 18px;
  transition: background 160ms ease, transform 160ms ease;
}

.primary-button:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.primary-button:active:not(:disabled) {
  transform: scale(0.99);
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
```

`frontend/src/components/common/TextField.vue`:

```vue
<template>
  <label class="field">
    <span>{{ label }}</span>
    <input :type="type || 'text'" :value="modelValue" @input="onInput" />
  </label>
</template>

<script setup lang="ts">
defineProps<{ label: string; modelValue: string; type?: string }>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.field input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  outline: none;
  padding: 13px 14px;
}

.field input:focus {
  border-color: rgba(0, 113, 227, 0.55);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
}
</style>
```

- [ ] **Step 2: Implement login page**

`frontend/src/pages/auth/LoginPage.vue`:

```vue
<template>
  <AuthLayout>
    <div class="auth-copy">
      <p class="eyebrow">AI Interview</p>
      <h1>欢迎回来</h1>
      <p>进入你的面试训练工作台。</p>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <TextField v-model="email" label="邮箱" type="email" />
      <TextField v-model="password" label="密码" type="password" />
      <p v-if="auth.error" class="error">{{ auth.error }}</p>
      <PrimaryButton :disabled="auth.loading">{{ auth.loading ? "登录中" : "登录" }}</PrimaryButton>
    </form>

    <RouterLink class="switch-link" to="/vue/auth/register">还没有账号？去注册</RouterLink>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import PrimaryButton from "@/components/common/PrimaryButton.vue";
import TextField from "@/components/common/TextField.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const email = ref("");
const password = ref("");

async function submit(): Promise<void> {
  await auth.login(email.value, password.value);
  await router.push("/vue/app/interview");
}
</script>

<style scoped>
.auth-copy {
  display: grid;
  gap: 8px;
  margin-bottom: 28px;
  text-align: center;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1 {
  font-size: 34px;
  margin: 0;
}

p {
  color: var(--color-text-muted);
  margin: 0;
}

.auth-form {
  display: grid;
  gap: 16px;
}

.error {
  color: #b42318;
  font-size: 14px;
}

.switch-link {
  display: block;
  margin-top: 18px;
  text-align: center;
  color: var(--color-accent);
  font-size: 14px;
}
</style>
```

- [ ] **Step 3: Implement register page**

`frontend/src/pages/auth/RegisterPage.vue`:

```vue
<template>
  <AuthLayout>
    <div class="auth-copy">
      <p class="eyebrow">AI Interview</p>
      <h1>创建账号</h1>
      <p>建立你的面试训练档案。</p>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <TextField v-model="email" label="邮箱" type="email" />
      <TextField v-model="username" label="用户名" />
      <TextField v-model="password" label="密码" type="password" />
      <p v-if="auth.error" class="error">{{ auth.error }}</p>
      <PrimaryButton :disabled="auth.loading">{{ auth.loading ? "注册中" : "注册" }}</PrimaryButton>
    </form>

    <RouterLink class="switch-link" to="/vue/auth/login">已有账号？去登录</RouterLink>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import PrimaryButton from "@/components/common/PrimaryButton.vue";
import TextField from "@/components/common/TextField.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const email = ref("");
const username = ref("");
const password = ref("");

async function submit(): Promise<void> {
  await auth.register(email.value, username.value, password.value);
  await router.push("/vue/app/interview");
}
</script>

<style scoped>
.auth-copy {
  display: grid;
  gap: 8px;
  margin-bottom: 28px;
  text-align: center;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1 {
  font-size: 34px;
  margin: 0;
}

p {
  color: var(--color-text-muted);
  margin: 0;
}

.auth-form {
  display: grid;
  gap: 16px;
}

.error {
  color: #b42318;
  font-size: 14px;
}

.switch-link {
  display: block;
  margin-top: 18px;
  text-align: center;
  color: var(--color-accent);
  font-size: 14px;
}
</style>
```

- [ ] **Step 4: Run frontend tests and build**

```powershell
cd frontend
npm run test
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components frontend/src/pages/auth
git commit -m "feat: add vue auth pages"
```

---

### Task 6: Profiles Store And Profiles Page Skeleton

**Files:**
- Create: `frontend/src/api/profiles.ts`
- Create: `frontend/src/stores/profiles.ts`
- Modify: `frontend/src/pages/app/ProfilesPage.vue`

- [ ] **Step 1: Implement profiles API**

`frontend/src/api/profiles.ts`:

```ts
import { apiRequest } from "./client";

export interface ApplicationProfile {
  id: number;
  title: string;
  targetRole?: string;
  target_role?: string;
  company?: string;
  jd?: string;
  resume?: string;
  createdAt?: string;
  created_at?: string;
}

export interface CreateApplicationProfilePayload {
  title: string;
  targetRole: string;
  company: string;
  jd: string;
  resume: string;
}

export async function listProfiles(): Promise<ApplicationProfile[]> {
  return apiRequest<ApplicationProfile[]>("/api/application-profiles");
}

export async function createProfile(payload: CreateApplicationProfilePayload): Promise<ApplicationProfile> {
  return apiRequest<ApplicationProfile>("/api/application-profiles", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
```

- [ ] **Step 2: Implement profiles store**

`frontend/src/stores/profiles.ts`:

```ts
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as profileApi from "@/api/profiles";

export const useProfilesStore = defineStore("profiles", () => {
  const profiles = ref<profileApi.ApplicationProfile[]>([]);
  const currentProfileId = ref<number | null>(null);
  const loading = ref(false);
  const error = ref("");
  const currentProfile = computed(() => profiles.value.find((item) => item.id === currentProfileId.value) || null);

  async function loadProfiles(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      profiles.value = await profileApi.listProfiles();
      if (!currentProfileId.value && profiles.value.length > 0) {
        currentProfileId.value = profiles.value[0].id;
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案加载失败";
    } finally {
      loading.value = false;
    }
  }

  function selectProfile(id: number): void {
    currentProfileId.value = id;
  }

  return { profiles, currentProfileId, currentProfile, loading, error, loadProfiles, selectProfile };
});
```

- [ ] **Step 3: Implement profiles page skeleton**

`frontend/src/pages/app/ProfilesPage.vue`:

```vue
<template>
  <AppLayout>
    <section class="page-header">
      <p class="eyebrow">Application Profiles</p>
      <h1>投递档案</h1>
      <p>先把简历、岗位 JD 和公司信息沉淀成档案，再进入模拟面试。</p>
    </section>

    <section class="profile-grid">
      <article v-for="profile in profiles.profiles" :key="profile.id" class="profile-card">
        <h2>{{ profile.title }}</h2>
        <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }}</p>
        <button @click="profiles.selectProfile(profile.id)">设为当前档案</button>
      </article>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useProfilesStore } from "@/stores/profiles";

const profiles = useProfilesStore();
onMounted(() => profiles.loadProfiles());
</script>
```

- [ ] **Step 4: Run build**

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/api/profiles.ts frontend/src/stores/profiles.ts frontend/src/pages/app/ProfilesPage.vue
git commit -m "feat: add vue profile entry"
```

---

### Task 7: Interview Workspace Skeleton

**Files:**
- Create: `frontend/src/api/interview.ts`
- Create: `frontend/src/stores/interview.ts`
- Create: `frontend/src/components/interview/InterviewChatPanel.vue`
- Create: `frontend/src/components/interview/InterviewContextPanel.vue`
- Modify: `frontend/src/pages/app/InterviewPage.vue`

- [ ] **Step 1: Implement interview API types**

`frontend/src/api/interview.ts`:

```ts
import { apiRequest } from "./client";

export interface NextQuestionPayload {
  answer: string;
  applicationProfileId?: number;
  agentMode?: "coach" | "interview";
}

export interface NextQuestionResponse {
  question?: string;
  nextQuestion?: string;
  decisionSummary?: string;
  agentDecision?: unknown;
}

export async function nextQuestion(payload: NextQuestionPayload): Promise<NextQuestionResponse> {
  return apiRequest<NextQuestionResponse>("/api/interview/next-question", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
```

- [ ] **Step 2: Implement interview store**

`frontend/src/stores/interview.ts`:

```ts
import { defineStore } from "pinia";
import { ref } from "vue";
import * as interviewApi from "@/api/interview";

export interface ChatMessage {
  role: "interviewer" | "candidate";
  content: string;
}

export const useInterviewStore = defineStore("interview", () => {
  const messages = ref<ChatMessage[]>([
    { role: "interviewer", content: "请选择投递档案，然后开始一次模拟面试。" }
  ]);
  const draft = ref("");
  const loading = ref(false);
  const error = ref("");
  const decisionSummary = ref("");

  async function submitAnswer(applicationProfileId?: number): Promise<void> {
    const answer = draft.value.trim();
    if (!answer) {
      return;
    }
    messages.value.push({ role: "candidate", content: answer });
    draft.value = "";
    loading.value = true;
    error.value = "";
    try {
      const response = await interviewApi.nextQuestion({ answer, applicationProfileId, agentMode: "coach" });
      messages.value.push({
        role: "interviewer",
        content: response.nextQuestion || response.question || "我会基于你的回答继续追问。"
      });
      decisionSummary.value = response.decisionSummary || "";
    } catch (err) {
      error.value = err instanceof Error ? err.message : "生成下一题失败";
    } finally {
      loading.value = false;
    }
  }

  return { messages, draft, loading, error, decisionSummary, submitAnswer };
});
```

- [ ] **Step 3: Create chat panel**

`frontend/src/components/interview/InterviewChatPanel.vue`:

```vue
<template>
  <section class="chat-panel">
    <div class="message-list">
      <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
        <span>{{ message.role === "interviewer" ? "AI 面试官" : "我" }}</span>
        <p>{{ message.content }}</p>
      </article>
    </div>
    <form class="composer" @submit.prevent="$emit('submit')">
      <textarea v-model="draftProxy" placeholder="输入你的回答..." />
      <button :disabled="loading">{{ loading ? "生成中" : "提交回答" }}</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChatMessage } from "@/stores/interview";

const props = defineProps<{ messages: ChatMessage[]; draft: string; loading: boolean }>();
const emit = defineEmits<{ "update:draft": [value: string]; submit: [] }>();

const draftProxy = computed({
  get: () => props.draft,
  set: (value: string) => emit("update:draft", value)
});
</script>
```

- [ ] **Step 4: Create context panel**

`frontend/src/components/interview/InterviewContextPanel.vue`:

```vue
<template>
  <aside class="context-panel">
    <section>
      <p class="eyebrow">Agent Decision</p>
      <h2>为什么这样问</h2>
      <p>{{ decisionSummary || "开始面试后，这里会展示 Agent 决策摘要。" }}</p>
    </section>
    <section>
      <p class="eyebrow">RAG Context</p>
      <h2>检索上下文</h2>
      <p>Vue3 V1 先展示入口，完整 RAG 命中解释在后续迁移。</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
defineProps<{ decisionSummary: string }>();
</script>
```

- [ ] **Step 5: Implement interview page**

`frontend/src/pages/app/InterviewPage.vue`:

```vue
<template>
  <AppLayout>
    <div class="interview-workbench">
      <section class="workbench-main">
        <p class="eyebrow">Interview Workspace</p>
        <h1>面试训练台</h1>
        <p class="subtitle">围绕当前投递档案，进行可解释的 AI 模拟面试。</p>
        <InterviewChatPanel
          v-model:draft="interview.draft"
          :messages="interview.messages"
          :loading="interview.loading"
          @submit="interview.submitAnswer(profiles.currentProfileId || undefined)"
        />
      </section>
      <InterviewContextPanel :decision-summary="interview.decisionSummary" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import InterviewContextPanel from "@/components/interview/InterviewContextPanel.vue";
import { useInterviewStore } from "@/stores/interview";
import { useProfilesStore } from "@/stores/profiles";

const interview = useInterviewStore();
const profiles = useProfilesStore();
</script>
```

- [ ] **Step 6: Run build**

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/api/interview.ts frontend/src/stores/interview.ts frontend/src/components/interview frontend/src/pages/app/InterviewPage.vue
git commit -m "feat: add vue interview workspace"
```

---

### Task 8: Legacy Safety And Verification

**Files:**
- Modify: `docs/frontend/vue3-rebuild-v1-quickstart.md`
- Test existing backend and frontend suites.

- [ ] **Step 1: Verify old page still exists**

Run:

```powershell
Test-Path index.html
Test-Path styles.css
Test-Path app.js
```

Expected:

```text
True
True
True
```

- [ ] **Step 2: Run backend tests**

```powershell
python -m pytest -q
```

Expected: exit code 0, with no failed tests or errors.

- [ ] **Step 3: Run legacy frontend `.mjs` tests**

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: exit code 0.

- [ ] **Step 4: Run Vue tests and build**

```powershell
cd frontend
npm run test
npm run build
```

Expected: both commands pass.

- [ ] **Step 5: Browser verification**

Start backend:

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

Start frontend:

```powershell
cd frontend
npm run dev
```

Verify:

```text
http://localhost:8000/
http://localhost:5173/vue/auth/login
http://localhost:5173/vue/app/interview
```

Check desktop and mobile widths:

- Login page has centered minimal panel.
- Interview page has app shell, side nav, chat panel, and context panel.
- Mobile width stacks or scrolls without overlapping text.

- [ ] **Step 6: Commit verification docs if changed**

```powershell
git add docs/frontend/vue3-rebuild-v1-quickstart.md
git commit -m "docs: update vue frontend verification guide"
```

Skip this commit if the doc did not change.

---

## Plan Self-Review

Spec coverage:

- Vue3 + Vite + TypeScript: Task 2.
- Vue Router: Task 3.
- Pinia: Tasks 2, 4, 6, 7.
- API client: Task 4.
- Login/register: Task 5.
- Profile entry: Task 6.
- Interview workspace skeleton: Task 7.
- Old frontend retained: Task 8.
- No backend/RAG/Agent/LangGraph/Docker changes: file boundaries and do-not-modify list.
- Tests and browser verification: Tasks 3, 4, 8.
- Minimal Apple-like visual style: Tasks 2, 3, 5, 7.

Implementation order:

```text
docs
-> scaffold
-> router/layout
-> API/auth
-> auth pages
-> profiles
-> interview workspace
-> verification
```

Risk control:

- The old frontend remains untouched.
- Vue3 uses `/vue` and Vite dev server first.
- Backend APIs remain unchanged.
- Each substantial step has tests or build verification before commit.
