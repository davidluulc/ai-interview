<template>
  <section class="task-list">
    <div class="list-head">
      <h2>训练任务</h2>
      <span>{{ tasks.length }} 个</span>
    </div>

    <div v-if="tasks.length === 0" class="empty-state">
      <h3>暂无训练任务</h3>
      <p>先完成一次模拟面试，系统会根据复盘里的薄弱点生成专项训练建议。</p>
    </div>

    <article v-for="task in tasks" :key="task.id" class="task-card">
      <div class="task-main">
        <div class="task-title">
          <span class="tag">{{ task.weakLabel || task.weakTag }}</span>
          <BrutChip :label="statusText(task.status)" :tone="statusTone(task.status)" />
        </div>
        <h3>{{ task.title }}</h3>
        <p>{{ task.description || "围绕该薄弱点完成一次专项表达训练。" }}</p>

        <div class="planning-meta">
          <span v-if="task.priority">{{ priorityText(task.priority) }}</span>
          <span>掌握度 {{ task.masteryScore ?? 0 }}</span>
          <span v-if="typeof task.attemptCount === 'number'">尝试 {{ task.attemptCount }} 次</span>
          <span v-if="task.nextReviewAt">下次复习 {{ formatDate(task.nextReviewAt) }}</span>
        </div>

        <div class="task-meta">
          <button
            v-if="task.sourceInterviewRecordId"
            class="source-link"
            type="button"
            :data-testid="`open-source-report-${task.sourceInterviewRecordId}`"
            @click="$emit('open-report', task.sourceInterviewRecordId)"
          >
            来源报告 #{{ task.sourceInterviewRecordId }}
          </button>
        </div>
      </div>

      <div class="task-actions">
        <BrutButton
          variant="primary"
          type="button"
          :data-testid="`start-task-${task.id}`"
          :disabled="task.status === 'done' || task.status === 'archived'"
          @click="$emit('start', task.id)"
        >
          {{ task.status === "in_progress" ? "继续训练" : "开始训练" }}
        </BrutButton>
        <BrutButton
          variant="ghost"
          type="button"
          :data-testid="`complete-task-${task.id}`"
          :disabled="task.status === 'done' || task.status === 'archived'"
          @click="$emit('complete', task.id)"
        >
          标记完成
        </BrutButton>
        <BrutButton
          variant="ghost"
          type="button"
          :data-testid="`archive-task-${task.id}`"
          :disabled="task.status === 'archived'"
          @click="$emit('archive', task.id)"
        >
          归档
        </BrutButton>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutChip from "@/components/brut/BrutChip.vue";
import type { TrainingTaskView } from "./types";

defineProps<{ tasks: TrainingTaskView[] }>();

defineEmits<{
  start: [id: number];
  complete: [id: number];
  archive: [id: number];
  "open-report": [id: number];
}>();

/* 状态实际值域见 TrainingTaskView：todo | in_progress | done | archived；未知值走 neutral。 */
function statusTone(status: TrainingTaskView["status"]): "ok" | "warn" | "neutral" {
  const map = {
    todo: "neutral",
    in_progress: "warn",
    done: "ok",
    archived: "neutral"
  } as const;
  return map[status] ?? "neutral";
}

function statusText(status: TrainingTaskView["status"]): string {
  const map = {
    todo: "待训练",
    in_progress: "训练中",
    done: "已完成",
    archived: "已归档"
  };
  return map[status];
}

function priorityText(priority: NonNullable<TrainingTaskView["priority"]>): string {
  const map = {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级"
  };
  return map[priority];
}

function formatDate(value: string): string {
  return value.slice(0, 10);
}
</script>

<style scoped>
.task-list {
  display: grid;
  gap: var(--s3);
}

.list-head,
.task-title,
.task-meta,
.planning-meta {
  display: flex;
  align-items: center;
  gap: var(--s2);
}

.list-head {
  justify-content: space-between;
}

h2,
h3,
p {
  margin: 0;
}

.list-head h2 {
  font-size: var(--text-section);
  font-weight: 900;
}

.list-head span,
p,
.task-meta,
.planning-meta {
  color: var(--ink-soft);
}

.list-head span {
  font-family: var(--font-mono);
  font-size: var(--text-body);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.empty-state {
  display: grid;
  gap: var(--s2);
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s4);
}

.empty-state h3 {
  font-size: var(--text-strong);
  font-weight: 900;
}

.empty-state p {
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.task-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--s4);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  padding: var(--s4);
  box-shadow: var(--shadow-3);
}

.task-main {
  display: grid;
  min-width: 0;
  gap: var(--s2);
}

.task-title {
  justify-content: space-between;
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

.task-main h3 {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.5;
}

.task-main p {
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.planning-meta {
  flex-wrap: wrap;
  gap: var(--s2);
}

.planning-meta span {
  display: inline-flex;
  width: fit-content;
  border: 1px solid var(--line-hair);
  border-radius: 0;
  background: var(--panel);
  font-size: var(--text-data);
  font-weight: 800;
  padding: var(--s1) var(--s2);
}

.task-actions {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  gap: var(--s2);
}

.source-link {
  border: 0;
  border-bottom: 2px solid var(--action);
  border-radius: 0;
  background: transparent;
  color: var(--action);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: var(--text-label);
  font-weight: 800;
  padding: var(--s1) 0;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .task-card,
  .task-title,
  .task-actions {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .task-actions {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
