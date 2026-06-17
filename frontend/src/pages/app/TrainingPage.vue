<template>
  <AppLayout>
    <section class="page-header">
      <div>
        <p class="eyebrow">Training Center</p>
        <h1>训练中心</h1>
        <p>把面试报告里的薄弱点沉淀成专项任务，练完后再回到面试台验证提升效果。</p>
      </div>
      <div class="header-actions">
        <button type="button" class="primary-action" data-testid="return-to-interview" @click="returnToInterview">
          回到面试台
        </button>
        <button type="button" class="ghost-action" @click="training.clearFilters">清空筛选</button>
      </div>
    </section>

    <section v-if="training.error" class="notice error">
      {{ training.error }}
    </section>

    <section v-else class="training-workbench">
      <TrainingOverviewCards
        :archived-count="training.archivedTasks.length"
        :average-mastery="averageMasteryForView"
        :done-count="training.doneTasks.length"
        :in-progress-count="training.inProgressTasks.length"
        :todo-count="training.todoTasks.length"
      />

      <section class="training-grid">
        <aside class="side-panel">
          <article class="explain-card">
            <h2>训练从哪里来</h2>
            <p>完成一次模拟面试后，系统会从报告中提取 weakTag，并生成专项训练任务。</p>
            <p>训练任务会保留来源报告和掌握度，方便你知道自己为什么要练这一项。</p>
          </article>

          <TrainingWeakTagMap
            :active-weak-tag="training.weakTag"
            :groups="training.weakTagGroups"
            @select="training.setWeakTagFilter"
          />
        </aside>

        <section class="task-panel">
          <div class="task-toolbar">
            <div>
              <p class="toolbar-label">任务筛选</p>
              <h2>专项训练任务</h2>
            </div>
            <TrainingStatusFilter
              :model-value="training.statusFilter"
              @update:model-value="training.setStatusFilter"
            />
          </div>

          <p v-if="training.loading" class="loading-text">正在加载训练任务...</p>
          <p v-if="training.filterSummary" class="filter-summary">{{ training.filterSummary }}</p>

          <div v-if="training.visibleTasks.length === 0" class="empty-guidance">
            <h3>暂时没有符合筛选条件的训练任务</h3>
            <p>可以清空筛选，或者完成一次新的模拟面试，再从报告页生成专项训练任务。</p>
            <div class="empty-actions">
              <button type="button" class="primary-action" @click="returnToInterview">去开始面试</button>
              <button type="button" class="ghost-action" @click="openHistory">去历史复盘</button>
            </div>
          </div>

          <TrainingTaskList
            v-else
            :tasks="training.visibleTasks"
            @archive="training.archiveTask"
            @complete="completeTask"
            @open-report="openReport"
            @start="training.startTask"
          />
        </section>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import TrainingOverviewCards from "@/components/training/TrainingOverviewCards.vue";
import TrainingStatusFilter from "@/components/training/TrainingStatusFilter.vue";
import TrainingTaskList from "@/components/training/TrainingTaskList.vue";
import TrainingWeakTagMap from "@/components/training/TrainingWeakTagMap.vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useTrainingStore } from "@/stores/training";

const route = useRoute();
const router = useRouter();
const training = useTrainingStore();

const averageMasteryForView = computed(() => (training.tasks.length > 0 ? training.averageMastery : null));

onMounted(() => {
  training.setFilters({
    sourceInterviewRecordId: numericQuery(route.query.recordId),
    weakTag: stringQuery(route.query.weakTag)
  });
  void training.loadTasks();
});

function completeTask(id: number): Promise<void> {
  return training.completeTask(id, "完整");
}

function openReport(id: number): void {
  void router.push(`/vue/app/reports/${id}`);
}

function openHistory(): void {
  void router.push("/vue/app/history");
}

function returnToInterview(): void {
  void router.push("/vue/app/interview");
}

function numericQuery(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw || 0);
  return parsed > 0 ? parsed : null;
}

function stringQuery(value: unknown): string {
  const raw = Array.isArray(value) ? value[0] : value;
  return typeof raw === "string" ? raw : "";
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 40px;
  margin-top: 8px;
}

h2 {
  font-size: 20px;
}

.page-header p,
.explain-card p,
.loading-text,
.empty-guidance p {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.header-actions,
.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.primary-action,
.ghost-action {
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 800;
  min-height: 40px;
  padding: 10px 16px;
  white-space: nowrap;
}

.primary-action {
  background: var(--color-accent);
  color: #fff;
}

.ghost-action {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

.training-workbench {
  display: grid;
  gap: 22px;
}

.training-grid {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.side-panel,
.task-panel {
  display: grid;
  gap: 14px;
}

.explain-card,
.notice,
.task-toolbar,
.empty-guidance {
  display: grid;
  gap: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.task-toolbar {
  align-items: center;
  grid-template-columns: minmax(180px, 1fr) auto;
}

.toolbar-label {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
}

.filter-summary {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-weight: 700;
  padding: 12px 14px;
}

.empty-guidance {
  border-style: dashed;
  background: var(--color-surface-muted);
}

.error {
  color: #b42318;
}

@media (max-width: 980px) {
  .page-header,
  .task-toolbar {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .training-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  h1 {
    font-size: 32px;
  }

  .header-actions,
  .empty-actions {
    flex-direction: column;
  }

  .primary-action,
  .ghost-action {
    width: 100%;
  }
}
</style>
