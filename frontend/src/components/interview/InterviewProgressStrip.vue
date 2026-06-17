<template>
  <section class="progress-strip" :class="{ complete }">
    <div class="round-block">
      <span>{{ complete ? "已完成" : "进行中" }}</span>
      <strong>第 {{ currentRound }} / {{ totalRounds }} 题</strong>
    </div>
    <div class="meta-list">
      <span>模式：{{ modeLabel }}</span>
      <span>难度：{{ difficultyLabel }}</span>
      <span>重点：{{ focusLabel }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { InterviewDifficulty, InterviewFocusArea } from "@/stores/interview";
import type { AgentMode } from "@/api/interview";

const props = defineProps<{
  currentRound: number;
  totalRounds: number;
  mode: AgentMode;
  difficulty: InterviewDifficulty;
  focusArea: InterviewFocusArea;
  complete: boolean;
}>();

const modeLabel = computed(() => (props.mode === "interview" ? "真实面试" : "学习辅导"));

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
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: #ffffff;
  margin-bottom: 14px;
  padding: 14px 16px;
}

.progress-strip.complete {
  border-color: #9ae6b4;
  background: #f0fdf4;
}

.round-block {
  display: grid;
  gap: 2px;
}

.round-block span {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
}

.round-block strong {
  font-size: 18px;
}

.meta-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.meta-list span {
  border-radius: 999px;
  background: #f1f5f9;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 9px;
}

@media (max-width: 760px) {
  .progress-strip {
    align-items: stretch;
    flex-direction: column;
  }

  .meta-list {
    justify-content: flex-start;
  }
}
</style>
