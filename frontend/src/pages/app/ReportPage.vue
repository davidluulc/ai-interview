<template>
  <AppLayout>
    <section class="page-header">
      <div>
        <p class="eyebrow">Report</p>
        <h1>面试报告</h1>
        <p class="subtitle">把一次模拟面试沉淀成可复盘、可训练、可继续迭代的成长记录。</p>
      </div>
      <button type="button" @click="router.push('/vue/app/history')">返回历史</button>
    </section>

    <section v-if="reportStore.error" class="notice error">
      {{ reportStore.error }}
    </section>

    <section v-else-if="reportStore.loading" class="notice">
      正在加载面试报告...
    </section>

    <section v-else-if="!reportStore.record" class="notice">
      暂无报告内容
    </section>

    <div v-else class="report-grid">
      <section class="summary-card">
        <div class="score-block">
          <strong>{{ reportStore.score }}</strong>
          <span>{{ levelText }}</span>
        </div>
        <div class="summary-main">
          <p class="eyebrow">当前档案</p>
          <h2>{{ profileTitle }}</h2>
          <p>{{ roleTitle }}</p>
          <p class="summary-text">{{ summaryText }}</p>
        </div>
      </section>

      <section class="insight-card">
        <h2>建议优先训练</h2>
        <p>本次报告识别出的薄弱方向，建议先从高频短板开始补齐。</p>
        <div class="weak-tags">
          <button
            v-for="tag in weakTags"
            :key="tag"
            type="button"
            :data-testid="`go-training-${tag}`"
            @click="goTraining(tag)"
          >
            {{ tag }}
          </button>
        </div>
        <div v-if="weakTopics.length" class="topic-list">
          <article v-for="topic in weakTopics" :key="textField(topic, 'focus')" class="topic-item">
            <h3>{{ textField(topic, 'focus') }}</h3>
            <p>{{ textField(topic, 'reason') }}</p>
            <p>训练动作：{{ textField(topic, 'trainingAction') }}</p>
          </article>
        </div>
      </section>

      <section class="insight-card">
        <h2>优势与风险</h2>
        <div class="two-column">
          <div>
            <h3>优势</h3>
            <ul>
              <li v-for="item in listOf('strengths', 'advantages')" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div>
            <h3>风险</h3>
            <ul>
              <li v-for="item in listOf('risks')" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="insight-card">
        <h2>逐题复盘</h2>
        <article v-for="(review, index) in questionReviews" :key="index" class="review-item">
          <span>第 {{ index + 1 }} 题</span>
          <h3>{{ textField(review, 'question') }}</h3>
          <p>回答：{{ textField(review, 'answer') }}</p>
          <p>建议：{{ textField(review, 'feedback', 'evaluation', 'suggestion', 'referenceDirection', 'trainingAction') }}</p>
          <p>为什么问：{{ textField(review, 'whyAsked') }}</p>
          <p>缺失要点：{{ listField(review, 'missingPoints').join("、") }}</p>
          <p>回答方向：{{ textField(review, 'referenceDirection') }}</p>
          <p>训练动作：{{ textField(review, 'trainingAction') }}</p>
          <div class="weak-tags small">
            <span v-for="tag in tagsOf(review)" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </section>

      <section class="insight-card">
        <h2>为什么这样问</h2>
        <p>{{ evidenceText }}</p>
        <ul>
          <li v-for="reason in ragReasons" :key="reason">{{ reason }}</li>
        </ul>
      </section>

      <section class="insight-card">
        <h2>下一步训练</h2>
        <p>优先围绕下面的方向生成专项任务，练完后可以回到面试台再来一场。</p>
        <div class="priority-list">
          <span v-for="tag in priorityWeakTags" :key="tag">{{ tag }}</span>
        </div>
        <div class="practice-list">
          <article v-for="question in practiceQuestions" :key="question" class="practice-item">
            {{ question }}
          </article>
        </div>
        <div v-if="oneMinuteTemplates.length" class="template-list">
          <p v-for="template in oneMinuteTemplates" :key="template">{{ template }}</p>
        </div>
        <p v-if="reportStore.trainingGeneratedMessage" class="success-text">
          {{ reportStore.trainingGeneratedMessage }}
        </p>
        <div class="action-row">
          <button
            data-testid="generate-training-tasks"
            type="button"
            :disabled="reportStore.generatingTraining"
            @click="generateAndGoTraining"
          >
            {{ reportStore.generatingTraining ? "正在生成..." : "生成专项训练任务" }}
          </button>
          <button type="button" @click="router.push('/vue/app/training')">进入训练中心</button>
          <button data-testid="start-another-interview" type="button" @click="router.push('/vue/app/interview')">
            再来一场
          </button>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppLayout from "@/layouts/AppLayout.vue";
import { useReportStore } from "@/stores/report";

type ReviewLike = Record<string, unknown>;

const route = useRoute();
const router = useRouter();
const reportStore = useReportStore();

const recordId = computed(() => Number(route.params.recordId || 0));
const report = computed(() => reportStore.record?.report || {});

onMounted(() => {
  if (recordId.value) {
    void reportStore.loadReport(recordId.value);
  }
});

const profileTitle = computed(() => {
  return reportStore.record?.applicationProfile?.title || String(reportStore.record?.profile.title || "未命名面试");
});

const roleTitle = computed(() => {
  return reportStore.record?.applicationProfile?.targetRole || String(reportStore.record?.profile.targetRole || "未填写岗位");
});

const levelText = computed(() => {
  return typeof report.value.level === "string" && report.value.level ? report.value.level : "待复盘";
});

const summaryText = computed(() => {
  return typeof report.value.summary === "string" && report.value.summary
    ? report.value.summary
    : "本场报告暂未提供文字总结，请优先查看逐题复盘和薄弱点。";
});

const trainingPlan = computed(() => {
  const value = report.value.trainingPlan;
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
});

const weakTopics = computed<ReviewLike[]>(() => {
  const topics = trainingPlan.value.weakTopics;
  return Array.isArray(topics) ? topics.filter((item): item is ReviewLike => Boolean(item) && typeof item === "object") : [];
});

const practiceQuestions = computed(() => {
  const questions = trainingPlan.value.practiceQuestions;
  return Array.isArray(questions) ? questions.map(String).filter(Boolean) : [];
});

const oneMinuteTemplates = computed(() => {
  const templates = trainingPlan.value.oneMinuteTemplates;
  return Array.isArray(templates) ? templates.map(String).filter(Boolean) : [];
});

const weakTags = computed(() => {
  if (reportStore.weakTags.length) {
    return reportStore.weakTags;
  }
  const tags = weakTopics.value.flatMap((topic) => tagsOf(topic));
  if (tags.length) {
    return Array.from(new Set(tags));
  }
  const focuses = weakTopics.value.map((topic) => textField(topic, "focus")).filter((value) => value !== "暂无");
  return focuses.length ? focuses : ["待训练"];
});

const priorityWeakTags = computed(() => {
  const priorities = trainingPlan.value.nextRoundPriority;
  if (Array.isArray(priorities) && priorities.length > 0) {
    return priorities.map(String).filter(Boolean).slice(0, 3);
  }
  return weakTags.value.slice(0, 3);
});

const questionReviews = computed<ReviewLike[]>(() => {
  const reviews = report.value.questionReviews;
  if (Array.isArray(reviews) && reviews.length > 0) {
    const answers = reportStore.record?.answers || [];
    return reviews
      .filter((item): item is ReviewLike => Boolean(item) && typeof item === "object")
      .map((review, reviewIndex) => {
        const answerIndex = typeof review.index === "number" ? review.index - 1 : reviewIndex;
        const answer = answers[answerIndex] || answers[reviewIndex];
        return {
          ...review,
          question: textField(review, "question") !== "暂无" ? review.question : answer?.question,
          answer: textField(review, "answer") !== "暂无" ? review.answer : answer?.answer
        };
      });
  }
  return (reportStore.record?.answers || []).map((item) => ({
    question: item.question,
    answer: item.answer,
    feedback: "报告暂未提供逐题建议，请结合总评继续复盘。"
  }));
});

const evidenceText = computed(() => {
  return typeof report.value.decisionSummary === "string" && report.value.decisionSummary
    ? report.value.decisionSummary
    : "本题由当前档案、历史回答和检索上下文共同驱动。";
});

const ragReasons = computed(() => {
  const reasons = report.value.ragReasons;
  return Array.isArray(reasons) ? reasons.map(String).filter(Boolean) : [];
});

function listOf(...keys: string[]): string[] {
  for (const key of keys) {
    const value = report.value[key];
    if (Array.isArray(value) && value.length > 0) {
      return value.map(String).filter(Boolean);
    }
  }
  return ["报告暂未提供该项明细"];
}

function textField(source: ReviewLike, ...keys: string[]): string {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "暂无";
}

function listField(source: ReviewLike, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) && value.length > 0 ? value.map(String).filter(Boolean) : ["暂无"];
}

function tagsOf(source: ReviewLike): string[] {
  const value = source.weakTags;
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function goTraining(tag: string): void {
  void router.push({
    path: "/vue/app/training",
    query: {
      recordId: String(recordId.value),
      weakTag: tag
    }
  });
}

async function generateAndGoTraining(): Promise<void> {
  await reportStore.generateTrainingTasks();
  goTraining(weakTags.value[0] || "待训练");
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h1,
h2,
h3,
p,
ul {
  margin: 0;
}

h1 {
  font-size: 40px;
}

.subtitle,
.summary-main p,
.insight-card p,
.review-item p,
li {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.page-header button,
.insight-card button,
.weak-tags button {
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  font-weight: 700;
  padding: 10px 16px;
  white-space: nowrap;
}

.report-grid {
  display: grid;
  gap: 18px;
}

.summary-card,
.insight-card,
.notice {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.summary-card {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 20px;
}

.score-block {
  display: grid;
  place-items: center;
  border-radius: var(--radius-lg);
  background: #111827;
  color: #fff;
  padding: 24px;
}

.score-block strong {
  font-size: 44px;
}

.summary-main,
.insight-card,
.review-item,
.topic-list,
.topic-item,
.practice-list,
.template-list {
  display: grid;
  gap: 12px;
}

.summary-text {
  margin-top: 6px;
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.priority-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.success-text {
  color: #067647;
  font-weight: 700;
}

.weak-tags span,
.weak-tags button,
.priority-list span {
  background: #eef4ff;
  border-radius: 999px;
  color: #175cd3;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
}

.two-column {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

ul {
  display: grid;
  gap: 6px;
  padding-left: 18px;
}

.review-item {
  border-top: 1px solid var(--color-border);
  padding-top: 16px;
}

.topic-item,
.practice-item,
.template-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f8fafc;
  padding: 12px;
}

.review-item span {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
}

.small span {
  border-radius: 999px;
  padding: 5px 9px;
}

.error {
  color: #b42318;
}

@media (max-width: 760px) {
  .page-header,
  .summary-card {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .two-column {
    grid-template-columns: 1fr;
  }
}
</style>
