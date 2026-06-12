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
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
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
