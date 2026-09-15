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
  display: inline-flex;
  align-items: stretch;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-2);
  font-family: var(--font-ui);
}

.mode-switch button {
  border: 0;
  border-right: 2px solid var(--ink);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.04em;
  line-height: 1.2;
  padding: var(--s2) var(--s3);
  white-space: nowrap;
}

.mode-switch button:last-child {
  border-right: 0;
}

.mode-switch button.active {
  background: var(--warn);
  color: var(--ink);
}

.mode-switch button:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
</style>
