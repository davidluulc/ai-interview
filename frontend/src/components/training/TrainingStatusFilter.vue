<template>
  <section class="status-filter" aria-label="训练任务状态筛选">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="status-filter__btn"
      :class="{ 'status-filter__btn--active': modelValue === option.value }"
      :data-testid="`status-filter-${option.value || 'all'}`"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </section>
</template>

<script setup lang="ts">
import type { TrainingStatusFilter as TrainingStatusFilterValue } from "@/stores/training";

defineProps<{
  modelValue: TrainingStatusFilterValue;
}>();

defineEmits<{
  "update:modelValue": [status: TrainingStatusFilterValue];
}>();

const options: Array<{ label: string; value: TrainingStatusFilterValue }> = [
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
  gap: var(--s2);
}

.status-filter__btn {
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.2;
  padding: var(--s2) var(--s3);
  box-shadow: var(--shadow-2);
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

.status-filter__btn:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

@media (hover: hover) and (pointer: fine) {
  .status-filter__btn:hover {
    transform: translateY(-1px);
  }
}

.status-filter__btn:active {
  transform: scale(0.97);
}

.status-filter__btn--active {
  background: var(--action);
  color: var(--action-ink);
}
</style>
