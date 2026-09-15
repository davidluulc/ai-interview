<template>
  <AppLayout>
    <div class="report-page">
      <section class="page-head">
        <div>
          <h1>面试报告</h1>
          <p class="subtitle">把一次模拟面试沉淀成可复盘、可训练、可继续迭代的成长记录。</p>
        </div>
        <BrutButton type="button" variant="ghost" @click="router.push('/vue/app/history')">返回历史</BrutButton>
      </section>

      <section v-if="reportStore.error" class="notice notice--error">
        {{ reportStore.error }}
      </section>

      <section v-else-if="reportStore.loading" class="notice">
        正在加载面试报告...
      </section>

      <section v-else-if="!reportStore.record" class="notice">
        暂无报告内容
      </section>

      <div v-else class="report-body">
        <section class="report-hero">
          <div class="report-hero__profile">
            <p class="eyebrow">当前档案</p>
            <h2>{{ profileTitle }}</h2>
            <p class="report-hero__role">{{ roleTitle }}</p>
            <p class="report-hero__summary">{{ summaryText }}</p>
          </div>
          <div class="report-hero__score">
            <ScoreBlock :score="scoreValue" :caption="scoreCaption" />
            <BrutChip v-if="fallbackActive" tone="warn" label="模型复盘降级" />
          </div>
        </section>

        <div class="panel-duo">
          <BrutPanel title="优势">
            <ul class="mark-rows">
              <li v-for="item in listOf('strengths', 'advantages')" :key="item" class="mark-row">
                <span class="mark-row__mark mark-row__mark--ok" aria-hidden="true"></span>
                <span class="mark-row__text">{{ item }}</span>
              </li>
            </ul>
          </BrutPanel>
          <BrutPanel title="风险">
            <ul class="mark-rows">
              <li v-for="item in listOf('risks')" :key="item" class="mark-row">
                <span class="mark-row__mark mark-row__mark--warn" aria-hidden="true"></span>
                <span class="mark-row__text">{{ item }}</span>
              </li>
            </ul>
          </BrutPanel>
        </div>

        <section class="review-section">
          <h2 class="section-title">逐题复盘</h2>
          <BrutPanel v-for="(review, index) in questionReviews" :key="index" :title="reviewTitle(review, index)">
            <div class="review-meta">
              <BrutStamp
                v-if="reviewStamp(review)"
                :verdict="reviewStamp(review)!.verdict"
                :text="reviewStamp(review)!.text"
              />
              <BrutChip v-else-if="answerStatusText(review)" tone="neutral" :label="answerStatusText(review)" />
              <span v-for="tag in tagsOf(review)" :key="tag" class="review-tag">{{ tag }}</span>
            </div>
            <h4 class="review-question">{{ textField(review, "question") }}</h4>
            <p class="review-line"><strong>回答：</strong>{{ textField(review, "answer") }}</p>
            <p class="review-line"><strong>建议：</strong>{{ textField(review, "feedback", "evaluation", "suggestion", "referenceDirection", "trainingAction") }}</p>
            <p class="review-line"><strong>为什么问：</strong>{{ textField(review, "whyAsked") }}</p>
            <div class="point-group">
              <p class="group-label">缺失要点</p>
              <ul class="point-rows">
                <li v-for="point in listField(review, 'missingPoints')" :key="point" class="point-row">
                  <span class="point-row__mark" aria-hidden="true"></span>
                  <span class="point-row__text">{{ point }}</span>
                </li>
              </ul>
            </div>
            <p class="review-line"><strong>回答方向：</strong>{{ textField(review, "referenceDirection") }}</p>
            <p class="review-line"><strong>训练动作：</strong>{{ textField(review, "trainingAction") }}</p>
          </BrutPanel>
        </section>

        <BrutPanel v-if="shouldShowEvidence" title="出题依据">
          <p class="panel-copy">{{ humanizedEvidenceText }}</p>
          <div v-if="evidenceSources.length" class="group">
            <p class="group-label">参考来源</p>
            <ul class="plain-rows">
              <li v-for="source in evidenceSources" :key="`${source.label}-${source.title}`" class="plain-row">
                {{ source.label }}：{{ source.title }}
              </li>
            </ul>
          </div>
        </BrutPanel>

        <BrutPanel title="建议优先训练">
          <p class="panel-copy">本次报告识别出的薄弱方向，建议先从高频短板开始补齐。</p>
          <div class="tag-actions">
            <button
              v-for="tag in weakTags"
              :key="tag"
              type="button"
              class="tag-button"
              :data-testid="`go-training-${tag}`"
              @click="goTraining(tag)"
            >
              {{ tag }}
            </button>
          </div>
        </BrutPanel>

        <BrutPanel
          v-if="weakTopics.length || practiceQuestions.length || oneMinuteTemplates.length"
          title="训练处方"
        >
          <div v-if="weakTopics.length" class="topic-rows">
            <article v-for="topic in weakTopics" :key="textField(topic, 'focus')" class="topic-row">
              <h4>{{ textField(topic, "focus") }}</h4>
              <p>{{ textField(topic, "reason") }}</p>
              <p><strong>训练动作：</strong>{{ textField(topic, "trainingAction") }}</p>
            </article>
          </div>
          <div v-if="practiceQuestions.length" class="group">
            <p class="group-label">练习题</p>
            <ul class="plain-rows">
              <li v-for="question in practiceQuestions" :key="question" class="plain-row">{{ question }}</li>
            </ul>
          </div>
          <div v-if="oneMinuteTemplates.length" class="group">
            <p class="group-label">一分钟模板</p>
            <ul class="plain-rows">
              <li v-for="template in oneMinuteTemplates" :key="template" class="plain-row">{{ template }}</li>
            </ul>
          </div>
        </BrutPanel>

        <BrutPanel title="下一步训练">
          <p class="panel-copy">优先围绕下面的方向生成专项任务，练完后可以回到面试台再来一场。</p>
          <div class="priority-row">
            <BrutChip v-for="tag in priorityWeakTags" :key="tag" tone="info" :label="tag" />
          </div>
          <p v-if="reportStore.trainingGeneratedMessage" class="success-text">
            {{ reportStore.trainingGeneratedMessage }}
          </p>
          <div class="action-row">
            <BrutButton
              data-testid="generate-training-tasks"
              type="button"
              variant="primary"
              :disabled="reportStore.generatingTraining"
              @click="generateAndGoTraining"
            >
              {{ reportStore.generatingTraining ? "正在生成..." : "生成专项训练任务" }}
            </BrutButton>
            <BrutButton type="button" variant="ghost" @click="router.push('/vue/app/training')">进入训练中心</BrutButton>
            <BrutButton
              data-testid="start-another-interview"
              type="button"
              variant="ghost"
              @click="router.push('/vue/app/interview')"
            >
              再来一场
            </BrutButton>
          </div>
        </BrutPanel>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppLayout from "@/layouts/AppLayout.vue";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutChip from "@/components/brut/BrutChip.vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";
import BrutStamp from "@/components/brut/BrutStamp.vue";
import ScoreBlock from "@/components/brut/ScoreBlock.vue";
import { useReportStore } from "@/stores/report";

type ReviewLike = Record<string, unknown>;
type StampVerdict = "pass" | "warn" | "fail";
interface EvidenceSource {
  label: string;
  title: string;
}
interface ReviewStamp {
  text: string;
  verdict: StampVerdict;
}

/* 报告 answerStatus 实际值域见 prompts/interview.py：完整 | 模糊 | 不会 | 跑题（另兼容 良好）。未知值走 neutral。 */
const ANSWER_STATUS_VERDICTS: Record<string, StampVerdict> = {
  完整: "pass",
  良好: "pass",
  模糊: "warn",
  跑题: "warn",
  不会: "fail"
};

const route = useRoute();
const router = useRouter();
const reportStore = useReportStore();
const LOW_VALUE_EVIDENCE = ["本题由当前档案、历史回答和检索上下文共同驱动。"];

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

const scoreValue = computed(() => {
  const value = report.value.score;
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
});

const scoreCaption = computed(() => `总评 · ${levelText.value}`);

const fallbackActive = computed(() => report.value.fallbackUsed === true);

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

const evidenceReasons = computed(() => {
  const reasons = report.value.ragReasons;
  if (!Array.isArray(reasons)) {
    return [];
  }
  return Array.from(new Set(reasons.map(String).map((item) => item.trim()).filter(Boolean))).slice(0, 3);
});

function normalizeEvidenceReason(reason: string): EvidenceSource | null {
  const cleaned = reason
    .replace(/，?命中词包括[:：].*$/u, "")
    .replace(/^命中/u, "")
    .trim()
    .replace(/[。.]$/u, "");
  const match = cleaned.match(/^(岗位知识库|题库|候选人画像)[:：](.+)$/u);
  if (match) {
    return { label: match[1], title: match[2].trim() };
  }
  return null;
}

const evidenceSources = computed(() => {
  const seen = new Set<string>();
  return evidenceReasons.value
    .map((reason) => normalizeEvidenceReason(reason))
    .filter((source): source is EvidenceSource => Boolean(source?.title))
    .filter((source) => {
      const key = `${source.label}:${source.title}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 3);
});

const hasStrongEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return Boolean(summary && !LOW_VALUE_EVIDENCE.includes(summary) && evidenceSources.value.length > 0);
});

const hasWeakEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return Boolean(evidenceReasons.value.length > 0 && !hasStrongEvidence.value && (!summary || LOW_VALUE_EVIDENCE.includes(summary)));
});

const humanizedEvidenceText = computed(() => {
  const summary = evidenceText.value.trim();
  if (hasStrongEvidence.value) {
    const sourceLabels = evidenceSources.value.map((source) => source.label).join("、");
    return `这道题主要围绕岗位 JD 和上一轮回答中的薄弱点展开。${summary} 系统参考了${sourceLabels}中的相关材料，用来检查你能否把概念落到实际排查步骤。`;
  }
  if (summary && !LOW_VALUE_EVIDENCE.includes(summary)) {
    return `这道题主要围绕岗位 JD 和上一轮回答中的薄弱点展开。${summary} 当前知识库命中较弱，因此系统更多依赖面试上下文来追问。`;
  }
  return "这道题主要根据你的投递档案、岗位 JD 和上一轮回答生成。当前知识库命中较弱，因此系统更多依赖面试上下文来追问。";
});

const shouldShowEvidence = computed(() => {
  const summary = evidenceText.value.trim();
  return Boolean(hasStrongEvidence.value || hasWeakEvidence.value || (summary && !LOW_VALUE_EVIDENCE.includes(summary)));
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

function reviewTitle(review: ReviewLike, index: number): string {
  const focus = review.focus;
  const suffix = typeof focus === "string" && focus.trim() ? ` · ${focus.trim()}` : "";
  return `第 ${index + 1} 题${suffix}`;
}

function answerStatusText(review: ReviewLike): string {
  const status = review.answerStatus;
  return typeof status === "string" ? status.trim() : "";
}

function reviewStamp(review: ReviewLike): ReviewStamp | null {
  const status = answerStatusText(review);
  if (!status) {
    return null;
  }
  const verdict = ANSWER_STATUS_VERDICTS[status];
  return verdict ? { text: status, verdict } : null;
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
.report-page {
  display: grid;
  gap: var(--s6);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s5);
}

.eyebrow {
  margin: 0 0 var(--s2);
  color: var(--action);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.page-head h1 {
  margin: 0 0 var(--s2);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.1;
}

.subtitle {
  margin: 0;
  max-width: 56ch;
  color: var(--ink-soft);
  font-size: var(--text-strong);
  font-weight: 700;
  line-height: 1.6;
}

.notice {
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s4);
}

.notice--error {
  background: var(--danger);
  color: var(--action-ink);
}

.report-body {
  display: grid;
  gap: var(--s5);
}

.report-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 400px);
  gap: var(--s5);
  align-items: start;
}

.report-hero__profile {
  display: grid;
  gap: var(--s2);
}

.report-hero__profile h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
}

.report-hero__role {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-strong);
  font-weight: 700;
}

.report-hero__summary {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.report-hero__score {
  display: grid;
  gap: var(--s3);
  justify-items: start;
}

.panel-duo {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s5);
}

.mark-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--s2);
}

.mark-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--s3);
  align-items: start;
  border: 1px solid var(--line-hair);
  background: var(--panel);
  padding: var(--s2) var(--s3);
}

.mark-row__mark {
  width: 10px;
  height: 10px;
  margin-top: 4px;
}

.mark-row__mark--ok {
  background: var(--ok);
}

.mark-row__mark--warn {
  background: var(--warn);
}

.mark-row__text {
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.panel-copy {
  margin: 0 0 var(--s3);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.review-section {
  display: grid;
  gap: var(--s4);
}

.section-title {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
}

.review-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s2);
  margin-bottom: var(--s3);
}

.review-tag {
  border: 1px solid var(--ink);
  background: var(--panel);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 800;
  padding: var(--s1) var(--s2);
}

.review-question {
  margin: 0 0 var(--s3);
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.5;
}

.review-line {
  margin: 0 0 var(--s2);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.review-line strong {
  color: var(--ink);
}

.point-group {
  display: grid;
  gap: var(--s2);
  margin-bottom: var(--s3);
}

.group-label {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.point-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--s2);
}

.point-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--s3);
  align-items: start;
  border: var(--line);
  background: var(--panel);
  padding: var(--s2) var(--s3);
}

.point-row__mark {
  width: 10px;
  height: 10px;
  margin-top: 4px;
  background: var(--danger);
}

.point-row__text {
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.group {
  display: grid;
  gap: var(--s2);
  margin-top: var(--s4);
}

.plain-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--s2);
}

.plain-row {
  border: 1px solid var(--line-hair);
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  padding: var(--s2) var(--s3);
  overflow-wrap: anywhere;
}

.tag-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
}

.tag-button {
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 800;
  padding: var(--s2) var(--s3);
  box-shadow: var(--shadow-2);
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

@media (hover: hover) and (pointer: fine) {
  .tag-button:hover {
    transform: translateY(-1px);
  }
}

.tag-button:active {
  transform: scale(0.97);
}

.topic-rows {
  display: grid;
  gap: var(--s3);
}

.topic-row {
  display: grid;
  gap: var(--s2);
  border: 1px solid var(--line-hair);
  background: var(--panel);
  padding: var(--s3);
}

.topic-row h4 {
  margin: 0;
  font-size: var(--text-strong);
  font-weight: 900;
}

.topic-row p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.topic-row p strong {
  color: var(--ink);
}

.priority-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
  margin-bottom: var(--s3);
}

.success-text {
  margin: 0 0 var(--s3);
  color: var(--ok);
  font-size: var(--text-strong);
  font-weight: 800;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s3);
}

@media (max-width: 760px) {
  .page-head {
    flex-direction: column;
  }

  .report-hero,
  .panel-duo {
    grid-template-columns: 1fr;
  }
}
</style>
