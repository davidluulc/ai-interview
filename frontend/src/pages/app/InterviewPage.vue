<template>
  <AppLayout>
    <section v-if="!profiles.currentProfile" class="empty-profile">
      <p class="eyebrow">Interview Workspace</p>
      <h1>请先选择或创建投递档案</h1>
      <p>AI 面试官需要结合简历、岗位 JD 和公司信息，才能生成贴近真实场景的问题。</p>
      <button data-testid="go-profiles" type="button" @click="router.push('/vue/app/profiles')">去创建档案</button>
    </section>

    <div v-else class="interview-workbench">
      <section class="workbench-main">
        <div class="toolbar">
          <div>
            <p class="eyebrow">Interview Workspace</p>
            <h1>面试训练台</h1>
          </div>
          <InterviewModeSwitch :model-value="interview.agentMode" @update:model-value="interview.setAgentMode" />
        </div>
        <section v-if="auth.isAdmin" class="runtime-panel" aria-label="实验链路">
          <div>
            <p class="eyebrow">Runtime Canary</p>
            <h2>实验链路</h2>
            <p>仅管理员可见。实验链路会经过质量门禁，异常时自动回退稳定链路。</p>
          </div>
          <div class="runtime-actions">
            <button
              :class="{ active: interview.agentRuntime === 'classic' }"
              data-testid="runtime-classic"
              type="button"
              @click="interview.setAgentRuntime('classic')"
            >
              稳定链路
            </button>
            <button
              :class="{ active: interview.agentRuntime === 'shadow' }"
              data-testid="runtime-shadow"
              type="button"
              @click="interview.setAgentRuntime('shadow')"
            >
              旁路对比
            </button>
            <button
              :class="{ active: interview.agentRuntime === 'langgraph_canary' }"
              data-testid="runtime-langgraph-canary"
              type="button"
              @click="interview.setAgentRuntime('langgraph_canary')"
            >
              LangGraph 灰度
            </button>
          </div>
        </section>
        <CurrentProfileBanner :profile="profiles.currentProfile" />
        <InterviewSessionSetup
          :config="interview.sessionConfig"
          :profile="profiles.currentProfile"
          @update:config="interview.updateSessionConfig"
        />
        <p class="subtitle">围绕当前投递档案，进行可解释的 AI 模拟面试。</p>

        <InterviewProgressStrip
          :complete="interview.isSessionComplete"
          :current-round="interview.currentRound"
          :difficulty="interview.sessionConfig.difficulty"
          :focus-area="interview.sessionConfig.focusArea"
          :mode="interview.agentMode"
          :total-rounds="interview.sessionConfig.totalRounds"
        />
        <section v-if="!interview.hasStarted" class="start-panel">
          <div>
            <p class="eyebrow">Start</p>
            <h2>生成第一道面试题</h2>
            <p>系统会结合当前档案、岗位 JD 和知识库生成开场问题。</p>
          </div>
          <button
            data-testid="start-interview"
            type="button"
            :disabled="interview.loading"
            @click="startInterview"
          >
            {{ interview.loading ? "生成中" : "开始面试" }}
          </button>
        </section>
        <InterviewChatPanel
          v-model:draft="interview.draft"
          :can-submit="interview.canSubmitAnswer"
          :error="interview.error"
          :loading="interview.loading"
          :messages="interview.messages"
          :session-status="interview.sessionStatus"
          @submit="submit"
        />
        <InterviewFinishPanel
          :answered-count="interview.answeredHistory.length"
          :can-finish="interview.canFinish"
          :complete="interview.isSessionComplete"
          :submitting="finishingReport"
          @finish="finishInterview"
        />
      </section>

      <aside class="workbench-side">
        <InterviewEvidencePanel :decision-summary="interview.decisionSummary" :rag-reasons="interview.ragReasons" />
      </aside>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import * as historyApi from "@/api/history";
import * as interviewApi from "@/api/interview";
import * as trainingApi from "@/api/training";
import AppLayout from "@/layouts/AppLayout.vue";
import CurrentProfileBanner from "@/components/interview/CurrentProfileBanner.vue";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import InterviewEvidencePanel from "@/components/interview/InterviewEvidencePanel.vue";
import InterviewFinishPanel from "@/components/interview/InterviewFinishPanel.vue";
import InterviewModeSwitch from "@/components/interview/InterviewModeSwitch.vue";
import InterviewProgressStrip from "@/components/interview/InterviewProgressStrip.vue";
import InterviewSessionSetup from "@/components/interview/InterviewSessionSetup.vue";
import { useInterviewStore } from "@/stores/interview";
import { useProfilesStore } from "@/stores/profiles";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const interview = useInterviewStore();
const profiles = useProfilesStore();
const auth = useAuthStore();
const finishingReport = ref(false);

function buildFallbackReport(answers: Array<{ question: string; answer: string }>): interviewApi.ReportResponse {
  const questionReviews = answers.map((item, index) => {
    const question = item.question || `第 ${index + 1} 题`;
    return {
      index: index + 1,
      focus: "综合能力",
      question,
      answerStatus: item.answer.trim().length >= 24 ? "模糊" : "不会",
      whyAsked: "模型复盘暂时不可用，系统先根据本轮问答生成保守兜底复盘。",
      missingPoints: ["概念解释", "项目例子", "验证方式"],
      referenceDirection: "建议按背景、做法、原因、结果的顺序补充回答。",
      trainingAction: `围绕「${question.slice(0, 18)}」准备一段 1 分钟回答。`,
      weakTags: ["fallback_review"]
    };
  });
  return {
    score: 60,
    strengths: ["已完成一轮真实问答，回答内容已保留。"],
    risks: ["模型复盘暂时不可用，系统已先保存本轮面试记录。"],
    actions: ["先查看逐题记录，补充每题的背景、做法、结果和验证方式。"],
    questionReviews,
    trainingPlan: {
      weakTopics: questionReviews.map((review) => ({
        focus: String(review.focus),
        reason: "兜底复盘标记为需要继续训练。",
        trainingAction: String(review.trainingAction),
        weakTags: review.weakTags
      })),
      nextRoundPriority: questionReviews.map((review) => String(review.focus)),
      practiceQuestions: questionReviews.map((review) => String(review.trainingAction)),
      oneMinuteTemplates: ["背景：面试官追问；做法：解释概念并讲项目实现；结果：补充验证方式和改进点。"],
      shouldRetry: true
    },
    fallbackUsed: true
  };
}

function buildProfilePayload(): Record<string, unknown> {
  return {
    ...((profiles.currentProfile || {}) as Record<string, unknown>),
    sessionConfig: interview.sessionConfig
  };
}

function startInterview(): Promise<void> {
  return interview.startInterview({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: interview.agentMode,
    agentRuntime: interview.agentRuntime,
    profile: buildProfilePayload()
  });
}

function submit(): Promise<void> {
  return interview.submitAnswer({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: interview.agentMode,
    agentRuntime: interview.agentRuntime,
    profile: buildProfilePayload()
  });
}

async function finishInterview(): Promise<void> {
  if (!interview.canFinish || finishingReport.value) {
    return;
  }

  finishingReport.value = true;
  interview.error = "";
  interview.sessionStatus = "reporting";

  try {
    const applicationProfileId = profiles.currentProfileId || undefined;
    const profile = buildProfilePayload();
    const answers = [...interview.answeredHistory];
    let report: interviewApi.ReportResponse;
    try {
      report = await interviewApi.generateReport({
        applicationProfileId,
        profile,
        answers
      });
    } catch {
      report = buildFallbackReport(answers);
    }
    const record = await historyApi.createHistory({
      applicationProfileId,
      profile,
      answers,
      report
    });
    await trainingApi.generateTrainingTasksFromReport({
      applicationProfileId,
      sourceInterviewRecordId: record.id,
      report
    });
    interview.sessionStatus = "completed";
    await router.push(`/vue/app/reports/${record.id}`);
  } catch (err) {
    interview.sessionStatus = interview.answeredHistory.length > 0 ? "ready" : "idle";
    interview.error = err instanceof Error ? err.message : "生成复盘失败，请稍后重试。";
  } finally {
    finishingReport.value = false;
  }
}
</script>

<style scoped>
.empty-profile {
  display: grid;
  gap: 14px;
  max-width: 720px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 28px;
}

.empty-profile button {
  width: fit-content;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  font-weight: 700;
  padding: 11px 18px;
}

.interview-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 22px;
  align-items: start;
}

.workbench-main {
  min-width: 0;
}

.workbench-side {
  display: grid;
  gap: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h1 {
  font-size: 40px;
  margin: 0 0 8px;
}

.subtitle {
  color: var(--color-text-muted);
  margin: 16px 0 22px;
}

.start-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  margin: 0 0 14px;
  padding: 16px;
}

.start-panel h2,
.start-panel p {
  margin: 0;
}

.start-panel h2 {
  font-size: 18px;
}

.start-panel p:not(.eyebrow) {
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: 6px;
}

.start-panel button {
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  flex: 0 0 auto;
  font-weight: 700;
  padding: 11px 17px;
}

.start-panel button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.runtime-panel {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  gap: 16px;
  justify-content: space-between;
  margin: 0 0 16px;
  padding: 16px;
}

.runtime-panel h2 {
  font-size: 18px;
  margin: 0 0 6px;
}

.runtime-panel p {
  color: var(--color-text-muted);
  margin: 0;
}

.runtime-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.runtime-actions button {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  font-weight: 700;
  padding: 9px 13px;
}

.runtime-actions button.active {
  background: var(--color-text);
  border-color: var(--color-text);
  color: var(--color-surface);
}

.runtime-note {
  color: var(--color-text-muted);
  line-height: 1.7;
}

@media (max-width: 1040px) {
  .interview-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .runtime-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .start-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .runtime-actions {
    justify-content: flex-start;
  }
}
</style>
