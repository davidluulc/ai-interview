<template>
  <BrutPanel title="薄弱点训练地图" aria-label="薄弱点训练地图">
    <div v-if="groups.length === 0" class="weak-empty">
      <strong>还没有可聚合的薄弱点</strong>
      <p>完成一次模拟面试并生成报告后，这里会按 weakTag 汇总专项训练任务。</p>
    </div>

    <div v-else class="weak-list">
      <button
        type="button"
        class="weak-row"
        :class="{ 'weak-row--active': !activeWeakTag }"
        data-testid="weak-tag-all"
        @click="$emit('select', '')"
      >
        <span class="weak-row__title">全部训练任务</span>
        <span class="weak-row__meta">查看所有薄弱点任务</span>
      </button>
      <button
        v-for="group in groups"
        :key="group.weakTag"
        type="button"
        class="weak-row"
        :class="{ 'weak-row--active': activeWeakTag === group.weakTag }"
        :data-testid="`weak-tag-${group.weakTag}`"
        @click="$emit('select', group.weakTag)"
      >
        <span class="weak-row__head">
          <HeatChip :label="group.weakLabel" :count="group.total" />
        </span>
        <span class="weak-row__meta">
          {{ group.total }} 个任务
          <span aria-hidden="true">/</span>
          {{ priorityText(group.highestPriority) }}
        </span>
        <span class="weak-row__progress">
          <span>待训练 {{ group.todo }}</span>
          <span>训练中 {{ group.inProgress }}</span>
          <span>已完成 {{ group.done }}</span>
        </span>
        <strong class="weak-row__mastery">平均掌握度 {{ group.averageMastery }}</strong>
      </button>
    </div>
  </BrutPanel>
</template>

<script setup lang="ts">
import BrutPanel from "@/components/brut/BrutPanel.vue";
import HeatChip from "@/components/brut/HeatChip.vue";
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
.weak-list {
  display: grid;
  gap: var(--s2);
}

.weak-row {
  display: grid;
  gap: var(--s2);
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-family: var(--font-ui);
  padding: var(--s3);
  text-align: left;
  box-shadow: var(--shadow-2);
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

@media (hover: hover) and (pointer: fine) {
  .weak-row:hover {
    transform: translateY(-1px);
  }
}

.weak-row:active {
  transform: scale(0.99);
}

.weak-row--active {
  background: var(--panel-warm);
  box-shadow: var(--shadow-3);
}

.weak-row__head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
}

.weak-row__title {
  font-size: var(--text-strong);
  font-weight: 900;
}

.weak-row__meta {
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.4;
}

.weak-row__progress {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
  border-top: 1px solid var(--line-hair);
  padding-top: var(--s2);
}

.weak-row__progress span {
  border: 1px solid var(--line-hair);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: var(--text-data);
  font-weight: 800;
  padding: var(--s1) var(--s2);
}

.weak-row__mastery {
  font-family: var(--font-mono);
  font-size: var(--text-body);
  font-variant-numeric: tabular-nums;
}

.weak-empty {
  display: grid;
  gap: var(--s2);
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s4);
}

.weak-empty strong {
  font-size: var(--text-strong);
  font-weight: 900;
}

.weak-empty p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}
</style>
