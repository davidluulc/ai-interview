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
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  margin: 18px 0;
  padding: 20px;
}

.setup-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
  margin: 0 0 6px;
}

h2,
p {
  margin: 0;
}

h2 {
  font-size: 22px;
}

.focus-pill {
  border-radius: 999px;
  background: #eef4ff;
  color: #175cd3;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  white-space: nowrap;
}

.profile-summary {
  display: grid;
  gap: 6px;
  border-radius: var(--radius-md);
  background: #f8fafc;
  padding: 14px;
}

.profile-summary p {
  color: var(--color-text-muted);
  line-height: 1.6;
}

.setup-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 7px;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 700;
}

select {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
  color: var(--color-text);
  font: inherit;
  padding: 10px 11px;
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
