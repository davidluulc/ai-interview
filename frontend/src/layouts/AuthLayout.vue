<template>
  <main class="auth-layout">
    <section class="auth-panel">
      <header class="auth-band">
        <span class="auth-band__mark">AI 面试</span>
        <span class="auth-band__tag">/ 进入工作台</span>
      </header>
      <div class="auth-body">
        <slot />
      </div>
    </section>
  </main>
</template>

<style scoped>
.auth-layout {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: var(--s6);
  background: var(--paper);
  font-family: var(--font-ui);
}

.auth-panel {
  width: min(440px, 100%);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-5);
}

.auth-band {
  display: flex;
  align-items: baseline;
  gap: var(--s2);
  background: var(--ink);
  padding: var(--s3) var(--s4);
}

.auth-band__mark {
  color: var(--warn);
  font-size: var(--text-strong);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.auth-band__tag {
  color: var(--paper);
  font-size: var(--text-label);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.auth-body {
  padding: var(--s6);
}
</style>
