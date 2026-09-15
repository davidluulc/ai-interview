<template>
  <BrutPanel title="专项练习" aria-label="专项练习">
    <div class="practice-stack">
      <div class="panel-top">
        <span class="panel-top__eyebrow">Practice Session</span>
        <BrutButton variant="ghost" type="button" @click="$emit('reset')">重置</BrutButton>
      </div>

      <p v-if="loading" class="practice-note">正在加载专项练习...</p>
      <p v-else-if="error" class="practice-error">{{ error }}</p>

      <div v-else-if="!practice" class="empty-practice">
        <h3>选择一个训练任务开始专项练习</h3>
        <p>点击左侧任务的“开始训练”，这里会展示对应 weakTag 的练习题、回答要点和常见错误。</p>
      </div>

      <div v-else class="practice-body">
        <div class="question-block">
          <span class="tag">{{ practice.weakLabel || practice.weakTag }}</span>
          <h3>{{ practice.question }}</h3>
          <p class="practice-note">模式：{{ modeText(practice.mode) }} / 难度：{{ difficultyText(practice.difficulty) }}</p>
        </div>

        <div class="guidance-grid">
          <article class="guidance-card">
            <h4>回答要点</h4>
            <ul>
              <li v-for="point in practice.answerKeyPoints" :key="point">{{ point }}</li>
            </ul>
            <p v-if="practice.answerKeyPoints.length === 0" class="practice-note">暂无固定要点，优先讲清背景、做法和结果。</p>
          </article>

          <article class="guidance-card">
            <h4>常见错误</h4>
            <ul>
              <li v-for="mistake in practice.commonMistakes" :key="mistake">{{ mistake }}</li>
            </ul>
            <p v-if="practice.commonMistakes.length === 0" class="practice-note">暂无常见错误记录。</p>
          </article>
        </div>

        <article v-if="practice.oneMinuteTemplate" class="template-card">
          <h4>一分钟表达模板</h4>
          <p>{{ practice.oneMinuteTemplate }}</p>
        </article>

        <BrutField
          data-testid="practice-answer"
          label="我的练习回答"
          :model-value="answerText"
          placeholder="可以先写一个粗糙版本，再根据回答要点补齐。"
          @update:model-value="$emit('update:answerText', $event)"
        />

        <article v-if="practiceReview" class="review-card">
          <div class="review-head">
            <h4>AI 批改结果 · {{ practiceReview.qualityLabel }}</h4>
          </div>
          <section>
            <h5>参考答案</h5>
            <p>{{ practiceReview.referenceAnswer }}</p>
          </section>
          <section v-if="practiceReview.issues.length">
            <h5>需要纠正</h5>
            <ul>
              <li v-for="issue in practiceReview.issues" :key="issue">{{ issue }}</li>
            </ul>
          </section>
          <section>
            <h5>建议改写</h5>
            <p>{{ practiceReview.rewrittenAnswer }}</p>
          </section>
          <section>
            <h5>下一步练习</h5>
            <p>{{ practiceReview.nextPractice }}</p>
          </section>
        </article>

        <div class="panel-actions">
          <BrutButton
            variant="primary"
            type="button"
            data-testid="submit-practice"
            :disabled="practiceSubmitting || practiceSubmitted"
            @click="$emit('submit')"
          >
            {{ practiceSubmitting ? "批改中..." : practiceSubmitted ? "已批改" : "提交给 AI 批改" }}
          </BrutButton>
          <span v-if="result" class="practice-note">已练习 {{ result.attemptCount || 0 }} 次</span>
        </div>
      </div>
    </div>
  </BrutPanel>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type * as trainingApi from "@/api/training";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutField from "@/components/brut/BrutField.vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";

const props = defineProps<{
  practice: trainingApi.TrainingPractice | null;
  answerText: string;
  answerStatus: trainingApi.TrainingAnswerStatus;
  selfRating: number | null;
  loading: boolean;
  error: string;
  result: trainingApi.TrainingTask | null;
  practiceSubmitting: boolean;
  practiceSubmitted: boolean;
}>();

defineEmits<{
  "update:answerText": [value: string];
  "update:answerStatus": [value: trainingApi.TrainingAnswerStatus];
  "update:selfRating": [value: number | null];
  submit: [];
  reset: [];
}>();

const practiceReview = computed<trainingApi.TrainingPracticeReview | null>(() => {
  const metadata = props.result?.metadata as Record<string, unknown> | undefined;
  const lastPractice = metadata?.lastPractice as Record<string, unknown> | undefined;
  const review = lastPractice?.review as trainingApi.TrainingPracticeReview | undefined;
  return review || null;
});

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
.practice-stack {
  display: grid;
  gap: var(--s4);
}

.panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
}

.panel-top__eyebrow {
  color: var(--action);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

h3,
h4,
h5,
p {
  margin: 0;
}

.practice-note {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.practice-error {
  border: var(--line);
  background: var(--danger);
  color: var(--action-ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s3);
}

.empty-practice {
  display: grid;
  gap: var(--s2);
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s4);
}

.empty-practice h3 {
  font-size: var(--text-strong);
  font-weight: 900;
}

.empty-practice p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.practice-body {
  display: grid;
  gap: var(--s4);
}

.question-block {
  display: grid;
  gap: var(--s2);
}

.question-block h3 {
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.4;
}

.tag {
  display: inline-flex;
  width: fit-content;
  border: 1px solid var(--ink);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 800;
  padding: var(--s1) var(--s2);
}

.guidance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s3);
}

.guidance-card,
.template-card {
  display: grid;
  gap: var(--s2);
  align-content: start;
  border: 1px solid var(--line-hair);
  background: var(--panel);
  padding: var(--s3);
}

.review-card {
  display: grid;
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.guidance-card h4,
.template-card h4,
.review-card h4 {
  font-size: var(--text-strong);
  font-weight: 900;
}

.template-card p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

ul {
  display: grid;
  gap: var(--s2);
  margin: 0;
  padding-left: 18px;
}

.review-card section {
  display: grid;
  gap: var(--s1);
}

.review-card h5 {
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.review-card section p {
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.panel-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--s3);
}

@media (max-width: 720px) {
  .guidance-grid {
    grid-template-columns: 1fr;
  }

  .panel-top,
  .panel-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
