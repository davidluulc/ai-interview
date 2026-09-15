<template>
  <div class="progress-strip" role="status">
    <span class="progress-strip__chip" :class="complete ? 'progress-strip__chip--done' : 'progress-strip__chip--live'">
      {{ complete ? "已完成" : "进行中" }}
    </span>
    <span class="progress-strip__chip">第 {{ currentRound }} / {{ totalRounds }} 题</span>
    <span class="progress-strip__chip">难度 {{ difficultyLabel }}</span>
    <span class="progress-strip__chip">重点 {{ focusLabel }}</span>
    <span v-if="runtimeLabel" class="progress-strip__chip progress-strip__chip--runtime">链路 {{ runtimeLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { InterviewDifficulty, InterviewFocusArea } from "@/stores/interview";

const props = withDefaults(
  defineProps<{
    currentRound: number;
    totalRounds: number;
    difficulty: InterviewDifficulty;
    focusArea: InterviewFocusArea;
    complete: boolean;
    runtimeLabel?: string;
  }>(),
  { runtimeLabel: "" }
);

const difficultyLabel = computed(() => {
  const labels: Record<InterviewDifficulty, string> = {
    basic: "基础",
    standard: "标准",
    pressure: "压力"
  };
  return labels[props.difficulty] || "标准";
});

const focusLabel = computed(() => {
  const labels: Record<InterviewFocusArea, string> = {
    project_deep_dive: "项目深挖",
    technical_basic: "技术基础",
    rag_agent: "RAG & Agent",
    behavioral: "行为面试",
    mixed: "综合"
  };
  return labels[props.focusArea] || "综合";
});
</script>

<style scoped>
.progress-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--s2);
  font-family: var(--font-ui);
}

.progress-strip__chip {
  border: 2px solid var(--ink);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  white-space: nowrap;
}

.progress-strip__chip--live {
  background: var(--warn);
}

.progress-strip__chip--done {
  background: var(--ok);
  color: var(--action-ink);
}

.progress-strip__chip--runtime {
  background: var(--panel-warm);
}

@media (max-width: 760px) {
  .progress-strip {
    justify-content: flex-start;
  }
}
</style>
