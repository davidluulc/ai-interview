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
          <strong>{{ statusText(task.status) }}</strong>
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
        <button
          type="button"
          :data-testid="`start-task-${task.id}`"
          :disabled="task.status === 'done' || task.status === 'archived'"
          @click="$emit('start', task.id)"
        >
          {{ task.status === "in_progress" ? "继续训练" : "开始训练" }}
        </button>
        <button
          type="button"
          :data-testid="`complete-task-${task.id}`"
          :disabled="task.status === 'done' || task.status === 'archived'"
          @click="$emit('complete', task.id)"
        >
          标记完成
        </button>
        <button
          class="ghost"
          type="button"
          :data-testid="`archive-task-${task.id}`"
          :disabled="task.status === 'archived'"
          @click="$emit('archive', task.id)"
        >
          归档
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { TrainingTaskView } from "./types";

defineProps<{ tasks: TrainingTaskView[] }>();

defineEmits<{
  start: [id: number];
  complete: [id: number];
  archive: [id: number];
  "open-report": [id: number];
}>();

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
  gap: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.list-head,
.task-title,
.task-meta,
.task-actions,
.planning-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.list-head {
  justify-content: space-between;
}

h2,
h3,
p {
  margin: 0;
}

.list-head span,
p,
.task-meta,
.planning-meta {
  color: var(--color-text-muted);
}

.empty-state {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 22px;
}

.task-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  border-top: 1px solid var(--color-border);
  padding-top: 16px;
}

.task-main {
  display: grid;
  min-width: 0;
  gap: 8px;
}

.task-title {
  justify-content: space-between;
}

.tag,
.planning-meta span {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 8px;
}

.tag {
  background: #eef4ff;
  color: #175cd3;
}

.planning-meta {
  flex-wrap: wrap;
  gap: 8px;
}

.planning-meta span {
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}

.task-actions {
  align-items: flex-end;
  flex-direction: column;
  justify-content: center;
}

button {
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  font-weight: 800;
  padding: 9px 14px;
  white-space: nowrap;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.ghost {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.source-link {
  border-radius: 0;
  background: transparent;
  color: var(--color-accent);
  padding: 0;
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
