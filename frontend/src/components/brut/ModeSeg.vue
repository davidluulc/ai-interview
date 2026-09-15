<template>
  <div class="mode-seg" role="group">
    <button
      v-for="option in options"
      :key="option.value"
      class="mode-seg__btn"
      :class="{ 'mode-seg__btn--active': modelValue === option.value }"
      type="button"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  options: Array<{ value: string; label: string }>;
  modelValue: string;
}>();

defineEmits<{
  "update:modelValue": [value: string];
}>();
</script>

<style scoped>
.mode-seg {
  display: inline-flex;
  align-items: stretch;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  box-shadow: var(--shadow-2);
}

.mode-seg__btn {
  border: 0;
  border-right: 2px solid var(--ink);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: 0.04em;
  padding: var(--s2) var(--s3);
  cursor: pointer;
}

.mode-seg__btn:last-child {
  border-right: 0;
}

.mode-seg__btn--active {
  background: var(--action);
  color: var(--action-ink);
}

.mode-seg__btn:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
</style>
