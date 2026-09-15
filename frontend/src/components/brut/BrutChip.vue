<template>
  <span class="brut-chip" :class="`brut-chip--${tone}`">{{ label }}</span>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  tone: "ok" | "warn" | "danger" | "info" | "neutral";
}>();
</script>

<style scoped>
.brut-chip {
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

.brut-chip--ok {
  background: var(--ok);
  color: var(--action-ink);
}

.brut-chip--warn {
  background: var(--warn);
  color: var(--ink);
}

.brut-chip--danger {
  background: var(--danger);
  color: var(--action-ink);
}

.brut-chip--info {
  background: var(--info);
  color: var(--action-ink);
}

.brut-chip--neutral {
  background: var(--panel);
  color: var(--ink);
}
</style>
