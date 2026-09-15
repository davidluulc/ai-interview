<template>
  <BrutPanel title="训练概览" aria-label="训练概览">
    <div class="overview-grid">
      <div v-for="item in overviewItems" :key="item.label" class="stat-tile" :class="{ 'stat-tile--hero': item.hero }">
        <span class="stat-tile__caption">{{ item.label }}</span>
        <strong class="stat-tile__value">{{ item.value }}</strong>
      </div>
    </div>
  </BrutPanel>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";

const props = defineProps<{
  todoCount: number;
  inProgressCount: number;
  doneCount: number;
  archivedCount: number;
  averageMastery: number | null;
}>();

const overviewItems = computed(() => [
  { label: "待训练", value: props.todoCount, hero: false },
  { label: "训练中", value: props.inProgressCount, hero: false },
  { label: "已完成", value: props.doneCount, hero: false },
  { label: "已归档", value: props.archivedCount, hero: false },
  { label: "平均掌握度", value: props.averageMastery ?? "--", hero: true }
]);
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--s3);
}

.stat-tile {
  display: grid;
  gap: var(--s2);
  align-content: start;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  padding: var(--s3);
}

.stat-tile--hero {
  background: var(--action);
  color: var(--action-ink);
}

.stat-tile__caption {
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
  text-transform: uppercase;
}

.stat-tile--hero .stat-tile__caption {
  color: var(--action-ink);
}

.stat-tile:not(.stat-tile--hero) .stat-tile__caption {
  color: var(--ink-soft);
}

.stat-tile__value {
  font-family: var(--font-mono);
  font-size: var(--text-page);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
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
}
</style>
