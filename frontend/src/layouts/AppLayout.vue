<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand">AI Interview</div>
      <RouterLink to="/vue/app/interview">面试</RouterLink>
      <RouterLink to="/vue/app/profiles">档案</RouterLink>
      <RouterLink to="/vue/app/knowledge">知识库</RouterLink>
      <RouterLink to="/vue/app/history">复盘</RouterLink>
      <RouterLink to="/vue/app/training">训练</RouterLink>
      <RouterLink v-if="auth.isAdmin" to="/vue/app/admin">后台</RouterLink>
      <button class="logout-button" type="button" @click="logout">退出登录</button>
    </aside>
    <main class="workspace">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

async function logout(): Promise<void> {
  await auth.logout();
  await router.replace("/vue/auth/login");
}
</script>

<style scoped>
.app-layout {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 232px minmax(0, 1fr);
  overflow-x: hidden;
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
  white-space: nowrap;
}

.sidebar a,
.logout-button {
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  padding: 10px 12px;
  white-space: nowrap;
}

.logout-button {
  margin-top: auto;
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.sidebar a.router-link-active {
  background: var(--color-surface);
  color: var(--color-text);
}

.logout-button:hover {
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
    align-items: center;
    max-width: 100vw;
    overflow-x: auto;
    padding: 16px 18px;
  }

  .brand {
    margin-bottom: 0;
  }

  .logout-button {
    margin-top: 0;
  }
}
</style>
