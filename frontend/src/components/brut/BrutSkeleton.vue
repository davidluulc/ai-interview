<template>
  <div v-if="variant === 'panel'" class="brut-skeleton brut-skeleton--panel">
    <div class="brut-skeleton__head" />
    <div class="brut-skeleton__block" />
  </div>
  <div v-else class="brut-skeleton brut-skeleton--rows">
    <div v-for="row in rows" :key="row" class="brut-skeleton__row" />
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number;
    variant: "panel" | "rows";
  }>(),
  { rows: 3 }
);
</script>

<style scoped>
.brut-skeleton {
  display: flex;
  flex-direction: column;
  border-radius: 0;
  font-family: var(--font-ui);
}

.brut-skeleton--panel {
  border: var(--line);
}

.brut-skeleton__head {
  background: var(--ink);
  height: 28px;
}

.brut-skeleton__block {
  background: var(--line-hair);
  height: 96px;
}

.brut-skeleton--rows {
  gap: var(--s2);
}

.brut-skeleton__row {
  background: var(--line-hair);
  height: 10px;
}
</style>
