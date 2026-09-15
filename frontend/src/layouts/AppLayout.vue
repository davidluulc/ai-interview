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
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-ui);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  border-right: var(--line);
  background: var(--panel);
  padding: var(--s6) var(--s4);
}

.brand {
  margin-bottom: var(--s5);
  border: var(--line);
  background: var(--action);
  color: var(--action-ink);
  box-shadow: var(--shadow-4);
  font-size: var(--text-strong);
  font-weight: 900;
  letter-spacing: 0.04em;
  padding: var(--s2) var(--s3);
  white-space: nowrap;
}

.sidebar a,
.logout-button {
  border-radius: 0;
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s3);
  white-space: nowrap;
}

.sidebar a {
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow-3);
  text-decoration: none;
}

.logout-button {
  margin-top: auto;
  border: 2px dashed var(--ink);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

@media (hover: hover) and (pointer: fine) {
  .sidebar a:hover,
  .logout-button:hover {
    background: var(--panel-warm);
  }
}

.sidebar a.router-link-active {
  background: var(--warn);
}

.workspace {
  min-width: 0;
  padding: var(--s6);
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
    padding: var(--s4);
  }

  .brand,
  .sidebar a,
  .logout-button {
    flex: 0 0 auto;
  }

  .brand {
    margin-bottom: 0;
  }

  .logout-button {
    margin-top: 0;
  }
}
</style>
