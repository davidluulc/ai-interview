<template>
  <div class="score-block">
    <div class="score-block__caption">{{ caption }}</div>
    <div class="score-block__value">{{ score }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  score: number;
  caption: string;
}>();
</script>

<style scoped>
.score-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  background: var(--action);
  color: var(--action-ink);
  padding: var(--s3) var(--s4);
  box-shadow: var(--shadow-4);
}

.score-block__caption {
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: 0.08em;
}

.score-block__value {
  font-family: var(--font-mono);
  font-size: 36px;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
</style>
