<template>
  <section class="overview-panel" aria-labelledby="training-overview-title">
    <div class="panel-head">
      <p class="eyebrow">Overview</p>
      <h2 id="training-overview-title">训练概览</h2>
    </div>

    <div class="overview-grid">
      <article v-for="item in overviewItems" :key="item.label" class="overview-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  todoCount: number;
  inProgressCount: number;
  doneCount: number;
  archivedCount: number;
  averageMastery: number | null;
}>();

const overviewItems = computed(() => [
  { label: "待训练", value: props.todoCount },
  { label: "训练中", value: props.inProgressCount },
  { label: "已完成", value: props.doneCount },
  { label: "已归档", value: props.archivedCount },
  { label: "平均掌握度", value: props.averageMastery ?? "--" }
]);
</script>

<style scoped>
.overview-panel {
  display: grid;
  gap: 14px;
}

.panel-head {
  display: grid;
  gap: 4px;
}

.eyebrow,
h2 {
  margin: 0;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

h2 {
  font-size: 22px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 12px;
}

.overview-card {
  display: grid;
  gap: 8px;
  min-height: 92px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 16px;
}

.overview-card span {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 700;
}

.overview-card strong {
  color: var(--color-text);
  font-size: 30px;
  line-height: 1;
}

@media (max-width: 1080px) {
  .overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-card {
    min-height: 84px;
    padding: 14px;
  }
}
</style>
