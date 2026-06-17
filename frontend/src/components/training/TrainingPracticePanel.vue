<template>
  <section class="practice-panel">
    <div class="panel-head">
      <div>
        <p class="eyebrow">Practice Session</p>
        <h2>专项练习</h2>
      </div>
      <button type="button" class="ghost-action" @click="$emit('reset')">重置</button>
    </div>

    <p v-if="loading" class="muted">正在加载专项练习...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else-if="!practice" class="empty-practice">
      <h3>选择一个训练任务开始专项练习</h3>
      <p>点击左侧任务的“开始训练”，这里会展示对应 weakTag 的练习题、回答要点和常见错误。</p>
    </div>

    <div v-else class="practice-body">
      <div class="question-block">
        <span class="tag">{{ practice.weakLabel || practice.weakTag }}</span>
        <h3>{{ practice.question }}</h3>
        <p class="muted">模式：{{ modeText(practice.mode) }} / 难度：{{ difficultyText(practice.difficulty) }}</p>
      </div>

      <div class="guidance-grid">
        <article class="guidance-card">
          <h4>回答要点</h4>
          <ul>
            <li v-for="point in practice.answerKeyPoints" :key="point">{{ point }}</li>
          </ul>
          <p v-if="practice.answerKeyPoints.length === 0" class="muted">暂无固定要点，优先讲清背景、做法和结果。</p>
        </article>

        <article class="guidance-card">
          <h4>常见错误</h4>
          <ul>
            <li v-for="mistake in practice.commonMistakes" :key="mistake">{{ mistake }}</li>
          </ul>
          <p v-if="practice.commonMistakes.length === 0" class="muted">暂无常见错误记录。</p>
        </article>
      </div>

      <article v-if="practice.oneMinuteTemplate" class="template-card">
        <h4>一分钟表达模板</h4>
        <p>{{ practice.oneMinuteTemplate }}</p>
      </article>

      <label class="answer-field">
        <span>我的练习回答</span>
        <textarea
          data-testid="practice-answer"
          :value="answerText"
          placeholder="可以先写一个粗糙版本，再根据回答要点补齐。"
          @input="$emit('update:answerText', ($event.target as HTMLTextAreaElement).value)"
        />
      </label>

      <div class="choice-row">
        <span>回答状态</span>
        <button
          v-for="option in answerStatusOptions"
          :key="option.value"
          type="button"
          :class="{ active: answerStatus === option.value }"
          :data-testid="option.testId"
          @click="$emit('update:answerStatus', option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <div class="choice-row">
        <span>自评分</span>
        <button
          v-for="rating in [1, 2, 3, 4, 5]"
          :key="rating"
          type="button"
          :class="{ active: selfRating === rating }"
          :data-testid="`self-rating-${rating}`"
          @click="$emit('update:selfRating', rating)"
        >
          {{ rating }}
        </button>
      </div>

      <div v-if="result" class="result-card">
        <strong>最新掌握度 {{ result.masteryScore }}</strong>
        <span>累计练习 {{ result.attemptCount || 0 }} 次</span>
      </div>

      <div class="panel-actions">
        <button type="button" class="primary-action" data-testid="submit-practice" @click="$emit('submit')">
          提交练习
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type * as trainingApi from "@/api/training";

defineProps<{
  practice: trainingApi.TrainingPractice | null;
  answerText: string;
  answerStatus: trainingApi.TrainingAnswerStatus;
  selfRating: number | null;
  loading: boolean;
  error: string;
  result: trainingApi.TrainingTask | null;
}>();

defineEmits<{
  "update:answerText": [value: string];
  "update:answerStatus": [value: trainingApi.TrainingAnswerStatus];
  "update:selfRating": [value: number | null];
  submit: [];
  reset: [];
}>();

const answerStatusOptions: Array<{
  label: string;
  value: trainingApi.TrainingAnswerStatus;
  testId: string;
}> = [
  { label: "不会", value: "不会", testId: "answer-status-unknown" },
  { label: "模糊", value: "模糊", testId: "answer-status-fuzzy" },
  { label: "完整", value: "完整", testId: "answer-status-complete" }
];

function modeText(mode: trainingApi.TrainingPractice["mode"]): string {
  return mode === "interview" ? "真实面试" : "学习辅导";
}

function difficultyText(difficulty: trainingApi.TrainingPractice["difficulty"]): string {
  const map = {
    basic: "基础",
    medium: "标准",
    hard: "进阶"
  };
  return map[difficulty];
}
</script>

<style scoped>
.practice-panel,
.empty-practice,
.guidance-card,
.template-card,
.result-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
}

.practice-panel {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.panel-head,
.choice-row,
.panel-actions,
.result-card {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-head,
.panel-actions {
  justify-content: space-between;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
}

h2,
h3,
h4,
p {
  margin: 0;
}

.practice-body {
  display: grid;
  gap: 16px;
}

.question-block {
  display: grid;
  gap: 8px;
}

.tag {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  background: #eef4ff;
  color: #175cd3;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 8px;
}

.muted,
.empty-practice p,
.template-card p {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.error {
  color: #b42318;
}

.empty-practice,
.guidance-card,
.template-card,
.result-card {
  display: grid;
  gap: 10px;
  padding: 18px;
}

.guidance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.answer-field {
  display: grid;
  gap: 8px;
  font-weight: 800;
}

textarea {
  min-height: 128px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font: inherit;
  line-height: 1.6;
  padding: 12px;
}

button {
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 800;
  min-height: 38px;
  padding: 9px 14px;
  white-space: nowrap;
}

.primary-action {
  background: var(--color-accent);
  color: #fff;
}

.ghost-action,
.choice-row button {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

.choice-row {
  flex-wrap: wrap;
}

.choice-row span {
  color: var(--color-text-muted);
  font-weight: 800;
}

.choice-row button.active {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.result-card {
  grid-template-columns: repeat(2, minmax(0, auto));
  justify-content: start;
  background: var(--color-surface-muted);
}

@media (max-width: 720px) {
  .guidance-grid {
    grid-template-columns: 1fr;
  }

  .panel-head,
  .panel-actions,
  .result-card {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-action,
  .ghost-action {
    width: 100%;
  }
}
</style>
