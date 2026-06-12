<template>
  <AppLayout>
    <div class="interview-workbench">
      <section class="workbench-main">
        <p class="eyebrow">Interview Workspace</p>
        <h1>面试训练台</h1>
        <p class="subtitle">围绕当前投递档案，进行可解释的 AI 模拟面试。</p>

        <InterviewChatPanel
          v-model:draft="interview.draft"
          :error="interview.error"
          :loading="interview.loading"
          :messages="interview.messages"
          @submit="submit"
        />
      </section>

      <InterviewContextPanel :decision-summary="interview.decisionSummary" :rag-reasons="interview.ragReasons" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import InterviewContextPanel from "@/components/interview/InterviewContextPanel.vue";
import { useInterviewStore } from "@/stores/interview";
import { useProfilesStore } from "@/stores/profiles";

const interview = useInterviewStore();
const profiles = useProfilesStore();

function submit(): Promise<void> {
  return interview.submitAnswer({
    applicationProfileId: profiles.currentProfileId || undefined,
    agentMode: "coach",
    profile: (profiles.currentProfile || {}) as Record<string, unknown>
  });
}
</script>

<style scoped>
.interview-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 22px;
  align-items: start;
}

.workbench-main {
  min-width: 0;
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
  margin: 0 0 22px;
}

@media (max-width: 1040px) {
  .interview-workbench {
    grid-template-columns: 1fr;
  }
}
</style>
