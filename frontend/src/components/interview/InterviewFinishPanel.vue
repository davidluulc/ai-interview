<template>
  <section class="finish-panel" :class="{ complete }">
    <div class="finish-panel__copy">
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <BrutButton
      type="button"
      variant="primary"
      data-testid="finish-interview"
      :disabled="!canFinish || submitting"
      @click="emit('finish')"
    >
      {{ submitting ? "生成中" : "结束并复盘" }}
    </BrutButton>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BrutButton from "@/components/brut/BrutButton.vue";

const props = withDefaults(
  defineProps<{
    canFinish: boolean;
    complete: boolean;
    answeredCount: number;
    submitting?: boolean;
  }>(),
  { submitting: false }
);

const emit = defineEmits<{
  finish: [];
}>();

const title = computed(() => {
  if (props.submitting) {
    return "正在生成复盘报告";
  }
  if (!props.canFinish) {
    return "至少完成 1 轮问答后再复盘";
  }
  if (props.complete) {
    return "本轮面试可以复盘了";
  }
  return "可以先阶段性复盘";
});

const description = computed(() => {
  if (props.submitting) {
    return "系统正在生成报告、保存历史记录并创建专项训练任务。";
  }
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
  gap: var(--s4);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-4);
  font-family: var(--font-ui);
  padding: var(--s4);
}

.finish-panel.complete {
  border: 2px solid var(--ok);
  box-shadow: var(--shadow-4);
}

.finish-panel__copy {
  min-width: 0;
}

h2,
p {
  margin: 0;
}

h2 {
  color: var(--ink);
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.3;
}

.finish-panel__copy p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  margin-top: var(--s1);
}

.finish-panel .brut-button {
  flex: 0 0 auto;
}

@media (max-width: 760px) {
  .finish-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .finish-panel .brut-button {
    width: 100%;
  }
}
</style>
