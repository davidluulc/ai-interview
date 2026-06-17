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
        <InterviewChatPanel
          v-model:draft="interview.draft"
          :error="interview.error"
          :loading="interview.loading"
          :messages="interview.messages"
          @submit="submit"
        />
        <InterviewFinishPanel
          :answered-count="interview.answeredHistory.length"
          :can-finish="interview.canFinish"
          :complete="interview.isSessionComplete"
          @finish="finishInterview"
        />
      </section>

      <InterviewEvidencePanel :decision-summary="interview.decisionSummary" :rag-reasons="interview.ragReasons" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
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

function submit(): Promise<void> {
  return interview.submitAnswer({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: interview.agentMode,
    agentRuntime: interview.agentRuntime,
    profile: {
      ...((profiles.currentProfile || {}) as Record<string, unknown>),
      sessionConfig: interview.sessionConfig
    }
  });
}

function finishInterview(): void {
  void router.push("/vue/app/history");
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

  .runtime-actions {
    justify-content: flex-start;
  }
}
</style>
