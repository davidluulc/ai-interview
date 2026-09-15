<template>
  <span class="brut-stamp" :class="`brut-stamp--${verdict}`">{{ text }}</span>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
  verdict: "pass" | "warn" | "fail";
}>();
</script>

<style scoped>
.brut-stamp {
  display: inline-block;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.2;
  padding: var(--s2) var(--s3);
  transform: rotate(2deg);
  box-shadow: var(--shadow-2);
}

.brut-stamp--pass {
  background: var(--ok);
  color: var(--action-ink);
}

.brut-stamp--warn {
  background: var(--warn);
  color: var(--ink);
}

.brut-stamp--fail {
  background: var(--danger);
  color: var(--action-ink);
}
</style>
