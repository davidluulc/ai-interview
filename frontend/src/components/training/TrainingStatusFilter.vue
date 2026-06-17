<template>
  <section class="status-filter" aria-label="训练任务状态筛选">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :class="{ active: modelValue === option.value }"
      :data-testid="`status-filter-${option.value || 'all'}`"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </section>
</template>

<script setup lang="ts">
import type { TrainingStatusFilter } from "@/stores/training";

defineProps<{
  modelValue: TrainingStatusFilter;
}>();

defineEmits<{
  "update:modelValue": [status: TrainingStatusFilter];
}>();

const options: Array<{ label: string; value: TrainingStatusFilter }> = [
  { label: "全部", value: "" },
  { label: "待训练", value: "todo" },
  { label: "训练中", value: "in_progress" },
  { label: "已完成", value: "done" },
  { label: "已归档", value: "archived" }
];
</script>

<style scoped>
.status-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

button {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: pointer;
  font-weight: 800;
  min-height: 38px;
  padding: 8px 14px;
  white-space: nowrap;
}

button:hover,
button.active {
  border-color: var(--color-accent);
  background: #eef4ff;
  color: var(--color-accent);
}
</style>
