<template>
  <span class="heat-chip" :class="`heat-chip--tier-${tier}`">{{ label }}<span v-if="count > 1" class="heat-chip__count"> ×{{ count }}</span></span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: string;
  count: number;
}>();

const tier = computed(() => {
  if (props.count >= 3) return 3;
  if (props.count === 2) return 2;
  return 1;
});
</script>

<style scoped>
.heat-chip {
  display: inline-flex;
  align-items: center;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
}

.heat-chip--tier-3 {
  background: var(--heat-3);
  color: var(--action-ink);
}

.heat-chip--tier-2 {
  background: var(--heat-2);
  color: var(--ink);
}

.heat-chip--tier-1 {
  background: var(--heat-1);
  color: var(--ink);
}

.heat-chip__count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
</style>
