<template>
  <section class="weak-map" aria-labelledby="weak-tag-map-title">
    <div class="panel-head">
      <p class="eyebrow">Weak Tags</p>
      <h2 id="weak-tag-map-title">薄弱点训练地图</h2>
    </div>

    <div v-if="groups.length === 0" class="empty-state">
      <strong>还没有可聚合的薄弱点</strong>
      <p>完成一次模拟面试并生成报告后，这里会按 weakTag 汇总专项训练任务。</p>
    </div>

    <div v-else class="weak-list">
      <button
        v-for="group in groups"
        :key="group.weakTag"
        type="button"
        class="weak-card"
        :class="{ active: activeWeakTag === group.weakTag }"
        :data-testid="`weak-tag-${group.weakTag}`"
        @click="$emit('select', group.weakTag)"
      >
        <span class="weak-title">{{ group.weakLabel }}</span>
        <span class="weak-meta">
          {{ group.total }} 个任务
          <span aria-hidden="true">/</span>
          {{ priorityText(group.highestPriority) }}
        </span>
        <span class="weak-progress">
          <span>待训练 {{ group.todo }}</span>
          <span>训练中 {{ group.inProgress }}</span>
          <span>已完成 {{ group.done }}</span>
        </span>
        <strong>平均掌握度 {{ group.averageMastery }}</strong>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TrainingWeakTagGroup } from "@/stores/training";

defineProps<{
  activeWeakTag: string;
  groups: TrainingWeakTagGroup[];
}>();

defineEmits<{
  select: [weakTag: string];
}>();

function priorityText(priority: TrainingWeakTagGroup["highestPriority"]): string {
  const map = {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级"
  };
  return map[priority];
}
</script>

<style scoped>
.weak-map {
  display: grid;
  gap: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.panel-head {
  display: grid;
  gap: 4px;
}

.eyebrow,
h2,
p {
  margin: 0;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

h2 {
  font-size: 20px;
}

.weak-list {
  display: grid;
  gap: 10px;
}

.weak-card {
  display: grid;
  gap: 8px;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  color: var(--color-text);
  cursor: pointer;
  padding: 14px;
  text-align: left;
}

.weak-card:hover,
.weak-card.active {
  border-color: var(--color-accent);
  background: #eef4ff;
}

.weak-title {
  font-weight: 900;
}

.weak-meta,
.weak-progress,
.empty-state p {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.weak-progress {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-state {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 18px;
}
</style>
