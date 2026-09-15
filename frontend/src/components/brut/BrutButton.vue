<template>
  <button
    class="brut-button"
    :class="`brut-button--${variant}`"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="brut-button__loading">处理中…</span>
    <slot v-else />
  </button>
</template>

<script setup lang="ts">
defineProps<{
  disabled?: boolean;
  loading?: boolean;
  variant: "primary" | "ghost" | "danger";
}>();
</script>

<style scoped>
.brut-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--s2);
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  font-size: var(--text-strong);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s3) var(--s4);
  cursor: pointer;
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

.brut-button--primary {
  background: var(--ink);
  color: var(--warn);
  box-shadow: var(--shadow-4);
}

.brut-button--ghost {
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow-3);
}

.brut-button--danger {
  background: var(--danger);
  color: var(--action-ink);
  box-shadow: var(--shadow-4);
}

.brut-button:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

@media (hover: hover) and (pointer: fine) {
  .brut-button:hover:not(:disabled) {
    transform: translateY(-1px);
  }
}

.brut-button:active:not(:disabled) {
  transform: scale(0.97);
}

.brut-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  box-shadow: none;
}
</style>
