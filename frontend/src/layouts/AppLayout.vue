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
