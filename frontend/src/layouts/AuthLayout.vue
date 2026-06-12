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
