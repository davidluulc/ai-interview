<template>
  <div class="progress-blocks" role="group">
    <span
      v-for="block in total"
      :key="block"
      class="progress-blocks__block"
      :class="blockClass(block)"
      aria-hidden="true"
    ></span>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  total: number;
  current: number;
  prior: Array<"pass" | "fail">;
}>();

function blockClass(block: number): string {
  if (block <= props.prior.length) {
    return `progress-blocks__block--${props.prior[block - 1]}`;
  }
  if (block === props.current) {
    return "progress-blocks__block--current";
  }
  return "progress-blocks__block--todo";
}
</script>

<style scoped>
.progress-blocks {
  display: flex;
  align-items: center;
  gap: var(--s2);
  font-family: var(--font-ui);
}

.progress-blocks__block {
  flex: none;
  width: 26px;
  height: 18px;
  border: var(--line);
  border-radius: 0;
  box-shadow: var(--shadow-2);
}

.progress-blocks__block--pass {
  background: var(--ok);
}

.progress-blocks__block--fail {
  background: var(--danger);
}

.progress-blocks__block--current {
  background: var(--hazard);
}

.progress-blocks__block--todo {
  background: var(--panel);
}
</style>
