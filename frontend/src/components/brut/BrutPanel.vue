<template>
  <section class="brut-panel">
    <header class="brut-panel__head">
      <h3 class="brut-panel__title">{{ title }}</h3>
    </header>
    <div class="brut-panel__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>

<style scoped>
.brut-panel {
  display: flex;
  flex-direction: column;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  box-shadow: var(--shadow-4);
}

.brut-panel__head {
  background: var(--ink);
  color: var(--paper);
  padding: var(--s2) var(--s3);
}

.brut-panel__title {
  margin: 0;
  font-size: var(--text-label);
  font-weight: 900;
  line-height: 1.2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brut-panel__body {
  background: var(--panel);
  color: var(--ink);
  padding: var(--s4);
  flex: 1;
}
</style>
