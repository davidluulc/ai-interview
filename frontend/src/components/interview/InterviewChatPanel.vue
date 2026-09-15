<template>
  <section class="chat-panel">
    <QuestionStage v-if="currentQuestion" :tag="stageTag" :text="currentQuestion" :meta="stageMeta" />

    <article v-if="loading" class="thinking" data-testid="interviewer-thinking" aria-live="polite">
      <span class="thinking__label">AI 面试官</span>
      <p class="thinking__text">
        <i data-testid="thinking-spinner" aria-hidden="true"></i>
        {{ loadingText }}
      </p>
    </article>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="composer">
      <AnswerBox
        v-model="draftProxy"
        data-testid="draft-input"
        placeholder="输入你的回答..."
        hint="Enter 提交 · Shift+Enter 换行"
      />
      <BrutButton
        type="button"
        variant="primary"
        data-testid="submit-answer"
        :disabled="loading || canSubmit === false"
        @click="$emit('submit')"
      >
        {{ loading ? "生成中" : "提交回答" }}
      </BrutButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import AnswerBox from "@/components/brut/AnswerBox.vue";
import BrutButton from "@/components/brut/BrutButton.vue";
import QuestionStage from "@/components/brut/QuestionStage.vue";
import type { AgentMode } from "@/api/interview";
import type { ChatMessage, InterviewDifficulty, InterviewFocusArea } from "@/stores/interview";

const props = defineProps<{
  messages: ChatMessage[];
  draft: string;
  loading: boolean;
  error?: string;
  canSubmit?: boolean;
  sessionStatus?: "idle" | "starting" | "ready" | "answering" | "reporting" | "completed";
  currentRound: number;
  totalRounds: number;
  difficulty: InterviewDifficulty;
  focusArea: InterviewFocusArea;
  mode: AgentMode;
}>();
const emit = defineEmits<{ "update:draft": [value: string]; submit: [] }>();

const draftProxy = computed({
  get: () => props.draft,
  set: (value: string) => emit("update:draft", value)
});

const currentQuestion = computed(() => {
  return [...props.messages].reverse().find((message) => message.role === "interviewer")?.content || "";
});

const loadingText = computed(() =>
  props.sessionStatus === "starting"
    ? "AI 面试官正在生成第一题，检索岗位知识库和题库..."
    : "AI 面试官正在分析你的回答，检索岗位知识库和题库..."
);

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

const difficultyLabel = computed(() => {
  const labels: Record<InterviewDifficulty, string> = {
    basic: "基础",
    standard: "标准",
    pressure: "压力"
  };
  return labels[props.difficulty] || "标准";
});

const modeLabel = computed(() => (props.mode === "interview" ? "真实面试" : "学习辅导"));

const stageTag = computed(() => `第 ${props.currentRound} / ${props.totalRounds} 题 · ${focusLabel.value}`);

const stageMeta = computed(() => [`难度 ${difficultyLabel.value}`, `模式 ${modeLabel.value}`]);
</script>

<style scoped>
.chat-panel {
  display: grid;
  gap: var(--s5);
  font-family: var(--font-ui);
}

.thinking {
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-3);
  padding: var(--s4);
}

.thinking__label {
  display: block;
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 800;
  letter-spacing: 0.06em;
  margin-bottom: var(--s2);
  text-transform: uppercase;
}

.thinking__text {
  display: flex;
  align-items: center;
  gap: var(--s2);
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 800;
  line-height: 1.6;
  margin: 0;
}

.thinking__text i {
  width: 12px;
  height: 12px;
  border: 2px solid var(--ink);
  border-radius: 0;
  background: var(--warn);
  flex: 0 0 auto;
  animation: thinking-pulse 0.8s var(--ease-out) infinite alternate;
}

@keyframes thinking-pulse {
  from {
    transform: scale(0.6);
  }

  to {
    transform: scale(1.15);
  }
}

.error {
  border: var(--line);
  border-radius: 0;
  background: var(--danger);
  color: var(--action-ink);
  font-size: var(--text-body);
  font-weight: 800;
  line-height: 1.5;
  margin: 0;
  padding: var(--s2) var(--s3);
}

.composer {
  display: grid;
  gap: var(--s3);
}

.composer .brut-button {
  justify-self: end;
  min-width: 132px;
}

@media (max-width: 680px) {
  .composer .brut-button {
    justify-self: stretch;
  }
}
</style>
