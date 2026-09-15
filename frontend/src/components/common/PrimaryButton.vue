<template>
  <button class="primary-button" :disabled="disabled" :type="type || 'submit'">
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ disabled?: boolean; type?: "button" | "submit" | "reset" }>();
</script>

<style scoped>
.primary-button {
  width: 100%;
  min-height: 46px;
  border: var(--line);
  border-radius: 0;
  background: var(--action);
  color: var(--action-ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-weight: 800;
  padding: 13px 18px;
  box-shadow: var(--shadow-3);
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

.primary-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-4);
}

.primary-button:active:not(:disabled) {
  transform: scale(0.99);
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
