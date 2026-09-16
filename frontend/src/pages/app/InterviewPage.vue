<template>
  <AppLayout>
    <section v-if="!profiles.currentProfile" class="empty-profile">
      <header class="empty-profile__head">
        <span>面试训练台</span>
      </header>
      <div class="empty-profile__body">
        <h1>请先选择或创建投递档案</h1>
        <p>AI 面试官需要结合简历、岗位 JD 和公司信息，才能生成贴近真实场景的问题。</p>
        <BrutButton type="button" variant="primary" data-testid="go-profiles" @click="router.push('/vue/app/profiles')">
          去创建档案
        </BrutButton>
      </div>
    </section>

    <div v-else class="focus-mode">
      <aside class="focus-mode__ledger">
        <RoundLedger :rounds="rounds" />
      </aside>

      <section class="focus-mode__stage">
        <header class="stage-bar">
          <InterviewProgressStrip
            class="stage-bar__meta"
            :complete="interview.isSessionComplete"
            :current-round="interview.currentRound"
            :difficulty="interview.sessionConfig.difficulty"
            :focus-area="interview.sessionConfig.focusArea"
            :runtime-label="auth.isAdmin ? runtimeLabel : ''"
            :total-rounds="interview.sessionConfig.totalRounds"
          />
        </header>

        <div class="stage-head">
          <div>
            <h1>面试训练台</h1>
          </div>
          <InterviewModeSwitch :model-value="interview.agentMode" @update:model-value="interview.setAgentMode" />
        </div>
        <p class="subtitle">围绕当前投递档案，进行可解释的 AI 模拟面试。</p>

        <CurrentProfileBanner :profile="profiles.currentProfile" />
        <InterviewSessionSetup
          :config="interview.sessionConfig"
          :profile="profiles.currentProfile"
          @update:config="interview.updateSessionConfig"
        />

        <section v-if="!interview.hasStarted" class="start-panel">
          <div>
            <h2>生成第一道面试题</h2>
            <p>系统会结合当前档案、岗位 JD 和知识库生成开场问题。</p>
          </div>
          <BrutButton
            type="button"
            variant="primary"
            data-testid="start-interview"
            :disabled="interview.loading"
            @click="startInterview"
          >
            {{ interview.loading ? "生成中" : "开始面试" }}
          </BrutButton>
        </section>
        <InterviewChatPanel
          v-else
          v-model:draft="interview.draft"
          :can-submit="interview.canSubmitAnswer"
          :current-round="interview.currentRound"
          :difficulty="interview.sessionConfig.difficulty"
          :error="interview.error"
          :focus-area="interview.sessionConfig.focusArea"
          :loading="interview.loading"
          :messages="interview.messages"
          :mode="interview.agentMode"
          :session-status="interview.sessionStatus"
          :total-rounds="interview.sessionConfig.totalRounds"
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

      <aside class="focus-mode__evidence">
        <HazardBanner
          v-if="guardrailActive"
          title="链路兜底已触发"
          detail="实验链路未通过质量门禁，已自动回退稳定链路，面试继续。"
        />
        <InterviewEvidencePanel :decision-summary="interview.decisionSummary" :rag-reasons="interview.ragReasons" />
        <section v-if="auth.isAdmin" class="runtime-panel" aria-label="实验链路">
          <div class="runtime-panel__copy">
            <h2>实验链路</h2>
            <p>仅管理员可见。实验链路会经过质量门禁，异常时自动回退稳定链路。</p>
          </div>
          <div class="runtime-actions">
            <button
              :class="{ active: interview.agentRuntime === 'langgraph_agent_v3' }"
              data-testid="runtime-langgraph-agent-v3"
              type="button"
              @click="interview.setAgentRuntime('langgraph_agent_v3')"
            >
              v3 主线
            </button>
            <button
              :class="{ active: interview.agentRuntime === 'langgraph_mainline' }"
              data-testid="runtime-langgraph-mainline"
              type="button"
              @click="interview.setAgentRuntime('langgraph_mainline')"
            >
              v1 主线回退
            </button>
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
      </aside>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import * as historyApi from "@/api/history";
import * as interviewApi from "@/api/interview";
import * as trainingApi from "@/api/training";
import AppLayout from "@/layouts/AppLayout.vue";
import BrutButton from "@/components/brut/BrutButton.vue";
import HazardBanner from "@/components/brut/HazardBanner.vue";
import RoundLedger from "@/components/brut/RoundLedger.vue";
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

const RUNTIME_LABELS: Record<interviewApi.AgentRuntime, string> = {
  langgraph_agent_v3: "v3 主线",
  langgraph_mainline: "v1 主线",
  classic: "稳定链路",
  shadow: "旁路对比",
  langgraph_canary: "LangGraph 灰度"
};

const runtimeLabel = computed(() => RUNTIME_LABELS[interview.agentRuntime] || "v3 主线");

const guardrailActive = computed(
  () => interview.lastFallbackSummary?.used === true || interview.lastRuntimeAudit?.fallbackUsed === true
);

function ledgerLabel(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) {
    return "待生成";
  }
  return clean;
}

const rounds = computed(() => {
  const total = interview.sessionConfig.totalRounds;
  const answered = interview.answeredHistory;
  const currentQuestion =
    [...interview.messages].reverse().find((message) => message.role === "interviewer")?.content || "";
  const sessionActive = interview.hasStarted && !interview.isSessionComplete;

  return Array.from({ length: total }, (_, position) => {
    const index = position + 1;
    if (position < answered.length) {
      return { index, label: ledgerLabel(answered[position].question), status: "done" as const };
    }
    if (sessionActive && position === answered.length) {
      return { index, label: ledgerLabel(currentQuestion), status: "current" as const };
    }
    return { index, label: "待生成", status: "todo" as const };
  });
});

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
  max-width: 560px;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-4);
  font-family: var(--font-ui);
}

.empty-profile__head {
  background: var(--ink);
  color: var(--paper);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.12em;
  line-height: 1.2;
  padding: var(--s2) var(--s3);
  text-transform: uppercase;
}

.empty-profile__body {
  display: grid;
  justify-items: start;
  gap: var(--s3);
  padding: var(--s5) var(--s4);
}

.empty-profile__body h1 {
  color: var(--ink);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.25;
  margin: 0;
}

.empty-profile__body p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
  margin: 0;
}

.focus-mode {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr) 268px;
  grid-template-areas: "ledger stage evidence";
  gap: var(--s5);
  align-items: start;
  font-family: var(--font-ui);
}

.focus-mode__ledger {
  grid-area: ledger;
  min-width: 0;
}

.focus-mode__stage {
  grid-area: stage;
  display: grid;
  gap: var(--s4);
  min-width: 0;
}

.focus-mode__evidence {
  grid-area: evidence;
  display: grid;
  gap: var(--s4);
  min-width: 0;
}

.stage-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--s3);
  border: var(--line);
  border-radius: 0;
  background: var(--ink);
  box-shadow: var(--shadow-4);
  padding: var(--s2) var(--s3);
}

.stage-bar__meta {
  margin-left: auto;
}

.stage-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--s3);
}

h1 {
  color: var(--ink);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.2;
  margin: 0;
}

.subtitle {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  margin: 0;
}

.start-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s4);
  border: var(--line);
  border-radius: 0;
  background: var(--panel-warm);
  box-shadow: var(--shadow-5);
  padding: var(--s4);
}

.start-panel h2,
.start-panel p {
  margin: 0;
}

.start-panel h2 {
  color: var(--ink);
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.3;
}

.start-panel p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  margin-top: var(--s1);
}

.runtime-panel {
  display: grid;
  gap: var(--s3);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-4);
  padding: var(--s4);
}

.runtime-panel__copy h2 {
  color: var(--ink);
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.3;
  margin: 0;
}

.runtime-panel__copy p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  margin: var(--s1) 0 0;
}

.runtime-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
}

.runtime-actions button {
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-2);
  color: var(--ink);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.04em;
  line-height: 1.2;
  padding: var(--s2) var(--s3);
}

.runtime-actions button.active {
  background: var(--warn);
}

.runtime-actions button:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

@media (max-width: 1040px) {
  .focus-mode {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "stage"
      "ledger"
      "evidence";
  }

  .focus-mode__ledger :deep(.round-ledger .round-ledger__row) {
    display: flex;
    flex: 0 0 auto;
    max-width: 240px;
    border: var(--line);
    background: var(--panel);
    padding: var(--s1) var(--s2);
  }

  .focus-mode__ledger :deep(.round-ledger) {
    display: flex;
    gap: var(--s2);
    overflow-x: auto;
    padding-bottom: var(--s2);
  }

  .stage-bar__meta {
    margin-left: 0;
    width: 100%;
  }
}

@media (max-width: 760px) {
  .stage-head {
    align-items: stretch;
    flex-direction: column;
  }

  .start-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .start-panel .brut-button {
    width: 100%;
  }

  .runtime-actions {
    justify-content: flex-start;
  }
}
</style>
