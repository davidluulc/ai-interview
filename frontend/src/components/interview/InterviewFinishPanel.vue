<template>
  <section class="finish-panel" :class="{ complete }">
    <div>
      <p class="eyebrow">Review</p>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <button data-testid="finish-interview" type="button" :disabled="!canFinish" @click="emit('finish')">
      结束并复盘
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  canFinish: boolean;
  complete: boolean;
  answeredCount: number;
}>();

const emit = defineEmits<{
  finish: [];
}>();

const title = computed(() => {
  if (!props.canFinish) {
    return "至少完成 1 轮问答后再复盘";
  }
  if (props.complete) {
    return "本轮面试可以复盘了";
  }
  return "可以先阶段性复盘";
});

const description = computed(() => {
  if (!props.canFinish) {
    return "先完成一次回答，系统才能根据你的表现生成有效复盘。";
  }
  if (props.complete) {
    return `你已经完成 ${props.answeredCount} 轮回答，建议进入报告页整理薄弱点和训练任务。`;
  }
  return `当前已完成 ${props.answeredCount} 轮回答，如果今天只想练一个小片段，也可以先结束复盘。`;
});
</script>

<style scoped>
.finish-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  margin-top: 14px;
  padding: 18px;
}

.finish-panel.complete {
  border-color: #9ae6b4;
  background: #f0fdf4;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
  margin: 0 0 6px;
}

h2,
p {
  margin: 0;
}

h2 {
  font-size: 20px;
}

p {
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: 6px;
}

button {
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  flex: 0 0 auto;
  font-weight: 700;
  padding: 11px 17px;
}

button:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

@media (max-width: 760px) {
  .finish-panel {
    align-items: stretch;
    flex-direction: column;
  }

  button {
    width: 100%;
  }
}
</style>
