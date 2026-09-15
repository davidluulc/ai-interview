<template>
  <BrutPanel title="轮次台账">
    <ol class="round-ledger">
      <li
        v-for="round in rounds"
        :key="round.index"
        class="round-ledger__row"
        :class="`round-ledger__row--${round.status}`"
      >
        <span class="round-ledger__index">{{ round.index }}</span>
        <span class="round-ledger__label">{{ round.label }}</span>
        <span
          class="round-ledger__badge"
          :class="`round-ledger__badge--${round.status}`"
        >{{ STATUS_TEXT[round.status] }}</span>
      </li>
    </ol>
  </BrutPanel>
</template>

<script setup lang="ts">
import BrutPanel from "./BrutPanel.vue";

defineProps<{
  rounds: Array<{
    index: number;
    label: string;
    status: "pass" | "fail" | "done" | "current" | "todo";
  }>;
}>();

const STATUS_TEXT = {
  pass: "✓",
  fail: "✕",
  done: "已答",
  current: "回答中",
  todo: "—"
} as const;
</script>

<style scoped>
.round-ledger {
  list-style: none;
  margin: 0;
  padding: 0;
  font-family: var(--font-ui);
}

.round-ledger__row {
  display: flex;
  align-items: center;
  gap: var(--s2);
  padding: var(--s2) var(--s1);
}

.round-ledger__row + .round-ledger__row {
  border-top: var(--line);
}

.round-ledger__row--current {
  background: var(--warn);
}

.round-ledger__row--done {
  background: var(--panel);
}

.round-ledger__index {
  flex: none;
  min-width: 2em;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
}

.round-ledger__label {
  flex: 1;
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.3;
}

.round-ledger__badge {
  flex: none;
  border: var(--line);
  border-radius: 0;
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  margin-left: auto;
}

.round-ledger__badge--pass {
  background: var(--ok);
  color: var(--action-ink);
}

.round-ledger__badge--fail {
  background: var(--danger);
  color: var(--action-ink);
}

.round-ledger__badge--done {
  background: var(--line-hair);
  color: var(--ink-soft);
}

.round-ledger__badge--current {
  background: var(--warn);
  color: var(--ink);
}

.round-ledger__badge--todo {
  background: var(--line-hair);
  color: var(--ink-soft);
}
</style>
