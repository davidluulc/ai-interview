<template>
  <div class="mode-switch" role="group" aria-label="面试模式">
    <button
      :class="{ active: modelValue === 'coach' }"
      data-testid="mode-coach"
      type="button"
      @click="$emit('update:modelValue', 'coach')"
    >
      学习辅导
    </button>
    <button
      :class="{ active: modelValue === 'interview' }"
      data-testid="mode-interview"
      type="button"
      @click="$emit('update:modelValue', 'interview')"
    >
      真实面试
    </button>
  </div>
</template>

<script setup lang="ts">
import type { AgentMode } from "@/api/interview";

defineProps<{ modelValue: AgentMode }>();
defineEmits<{ "update:modelValue": [mode: AgentMode] }>();
</script>

<style scoped>
.mode-switch {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(96px, 1fr));
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface-muted);
  padding: 4px;
}

button {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-weight: 700;
  padding: 9px 14px;
}

button.active {
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
}
</style>
