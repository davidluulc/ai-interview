<template>
  <section class="session-setup">
    <div class="setup-header">
      <div>
        <p class="eyebrow">Session Setup</p>
        <h2>本次面试配置</h2>
      </div>
      <span class="focus-pill">{{ focusLabel(config.focusArea) }}</span>
    </div>

    <div class="profile-summary">
      <strong>{{ textOf(profile.title, "未命名档案") }}</strong>
      <p>{{ textOf(profile.targetRole, "未填写岗位") }} · {{ textOf(profile.company, "未填写公司") }}</p>
      <p>{{ shortText(textOf(profile.jd, "暂无 JD 摘要")) }}</p>
    </div>

    <div class="setup-controls">
      <label>
        <span>轮数</span>
        <select data-testid="session-total-rounds" :value="draftConfig.totalRounds" @change="emitNumber('totalRounds', $event)">
          <option value="5">5 题</option>
          <option value="8">8 题</option>
          <option value="10">10 题</option>
        </select>
      </label>

      <label>
        <span>难度</span>
        <select data-testid="session-difficulty" :value="draftConfig.difficulty" @change="emitValue('difficulty', $event)">
          <option value="basic">基础</option>
          <option value="standard">标准</option>
          <option value="pressure">压力</option>
        </select>
      </label>

      <label>
        <span>重点方向</span>
        <select data-testid="session-focus-area" :value="draftConfig.focusArea" @change="emitValue('focusArea', $event)">
          <option value="project_deep_dive">项目深挖</option>
          <option value="technical_basic">技术基础</option>
          <option value="rag_agent">RAG & Agent</option>
          <option value="behavioral">行为面试</option>
          <option value="mixed">综合</option>
        </select>
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";
import type { InterviewDifficulty, InterviewFocusArea, InterviewSessionConfig } from "@/stores/interview";

type ProfileLike = Record<string, unknown>;

const props = defineProps<{
  profile: ProfileLike;
  config: InterviewSessionConfig;
}>();

const emit = defineEmits<{
  "update:config": [config: Partial<InterviewSessionConfig>];
}>();

const draftConfig = reactive<InterviewSessionConfig>({
  ...props.config
});

watch(
  () => props.config,
  (config) => {
    Object.assign(draftConfig, config);
  },
  { deep: true }
);

const focusLabels: Record<InterviewFocusArea, string> = {
  project_deep_dive: "项目深挖",
  technical_basic: "技术基础",
  rag_agent: "RAG & Agent",
  behavioral: "行为面试",
  mixed: "综合"
};

function textOf(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function shortText(value: string): string {
  return value.length > 80 ? `${value.slice(0, 80)}...` : value;
}

function focusLabel(value: InterviewFocusArea): string {
  return focusLabels[value] || "综合";
}

function emitNumber(key: "totalRounds", event: Event): void {
  const value = Number((event.target as HTMLSelectElement).value);
  draftConfig[key] = value;
  emit("update:config", { ...draftConfig });
}

function emitValue(key: "difficulty" | "focusArea", event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (key === "difficulty") {
    draftConfig.difficulty = value as InterviewDifficulty;
  } else {
    draftConfig.focusArea = value as InterviewFocusArea;
  }
  emit("update:config", { ...draftConfig });
}
</script>

<style scoped>
.session-setup {
  display: grid;
  gap: var(--s3);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-3);
  font-family: var(--font-ui);
  padding: var(--s4);
}

.setup-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s3);
}

.eyebrow {
  color: var(--action);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.12em;
  margin: 0 0 var(--s1);
  text-transform: uppercase;
}

h2,
p {
  margin: 0;
}

h2 {
  color: var(--ink);
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.3;
}

.focus-pill {
  border: 2px solid var(--ink);
  border-radius: 0;
  background: var(--panel-warm);
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.04em;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  white-space: nowrap;
}

.profile-summary {
  display: grid;
  gap: var(--s1);
  border: 2px dashed var(--ink);
  border-radius: 0;
  background: var(--paper);
  padding: var(--s3);
}

.profile-summary strong {
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
}

.profile-summary p {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
}

.setup-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--s3);
}

label {
  display: grid;
  gap: var(--s1);
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
}

select {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: var(--text-body);
  font-weight: 800;
  padding: var(--s2) var(--s2);
}

select:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

@media (max-width: 760px) {
  .setup-header {
    align-items: stretch;
    flex-direction: column;
  }

  .focus-pill {
    width: fit-content;
  }

  .setup-controls {
    grid-template-columns: 1fr;
  }
}
</style>
