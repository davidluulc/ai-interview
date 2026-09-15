<template>
  <span class="chunk-chip" :class="`chunk-chip--tier-${tier}`">
    <span class="chunk-chip__label">{{ label }}</span>
    <span class="chunk-chip__score">{{ score }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: string;
  score: number;
}>();

const tier = computed(() => {
  if (props.score >= 0.8) return 5;
  if (props.score >= 0.7) return 4;
  if (props.score >= 0.6) return 3;
  if (props.score >= 0.5) return 2;
  return 1;
});
</script>

<style scoped>
.chunk-chip {
  display: inline-flex;
  align-items: baseline;
  gap: var(--s2);
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
}

.chunk-chip--tier-5 {
  background: var(--score-5);
  color: var(--action-ink);
}

.chunk-chip--tier-4 {
  background: var(--score-4);
  color: var(--ink);
}

.chunk-chip--tier-3 {
  background: var(--score-3);
  color: var(--ink);
}

.chunk-chip--tier-2 {
  background: var(--score-2);
  color: var(--ink);
}

.chunk-chip--tier-1 {
  background: var(--score-1);
  color: var(--ink);
}

.chunk-chip__score {
  font-family: var(--font-mono);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}
</style>
