<template>
  <AppLayout>
    <div class="training-page">
      <section class="page-head">
        <div>
          <h1>训练中心</h1>
          <p class="subtitle">把面试报告里的薄弱点沉淀成专项任务，练完后再回到面试台验证提升效果。</p>
        </div>
        <div class="head-actions">
          <BrutButton
            variant="primary"
            type="button"
            data-testid="return-to-interview"
            @click="returnToInterview"
          >
            回到面试台
          </BrutButton>
          <BrutButton variant="ghost" type="button" @click="training.clearFilters">清空筛选</BrutButton>
        </div>
      </section>

      <section v-if="training.error" class="notice notice--error">
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
            <BrutPanel title="训练从哪里来">
              <div class="explain-copy">
                <p>完成一次模拟面试后，系统会从报告中提取 weakTag，并生成专项训练任务。</p>
                <p>训练任务会保留来源报告和掌握度，方便你知道自己为什么要练这一项。</p>
              </div>
            </BrutPanel>

            <TrainingWeakTagMap
              :active-weak-tag="training.weakTag"
              :groups="training.weakTagGroups"
              @select="training.setWeakTagFilter"
            />
          </aside>

          <section class="task-panel">
            <div class="task-toolbar">
              <div class="task-filter-heading">
                <p class="toolbar-label">{{ training.hasWeakTagFilter ? "当前薄弱点" : "任务筛选" }}</p>
                <h2>{{ training.taskListTitle }}</h2>
              </div>
              <div class="toolbar-actions">
                <BrutButton
                  v-if="training.hasWeakTagFilter"
                  variant="ghost"
                  type="button"
                  data-testid="clear-weak-tag-filter"
                  @click="training.setWeakTagFilter('')"
                >
                  查看全部
                </BrutButton>
                <TrainingStatusFilter
                  :model-value="training.statusFilter"
                  @update:model-value="training.setStatusFilter"
                />
              </div>
            </div>

            <p v-if="training.loading" class="loading-line">正在加载训练任务...</p>
            <p v-if="training.filterSummary" class="filter-summary">{{ training.filterSummary }}</p>

            <div v-if="training.visibleTasks.length === 0" class="empty-guidance">
              <h3>暂时没有符合筛选条件的训练任务</h3>
              <p>可以清空筛选，或者完成一次新的模拟面试，再从报告页生成专项训练任务。</p>
              <div class="empty-actions">
                <BrutButton variant="primary" type="button" @click="returnToInterview">去开始面试</BrutButton>
                <BrutButton variant="ghost" type="button" @click="openHistory">去历史复盘</BrutButton>
              </div>
            </div>

            <TrainingTaskList
              v-else
              :tasks="training.visibleTasks"
              @archive="training.archiveTask"
              @complete="completeTask"
              @open-report="openReport"
              @start="startPractice"
            />

            <TrainingPracticePanel
              :answer-status="training.practiceAnswerStatus"
              :answer-text="training.practiceAnswerText"
              :error="training.practiceError"
              :loading="training.practiceLoading"
              :practice="training.practiceDetail"
              :practice-submitted="training.practiceSubmitted"
              :practice-submitting="training.practiceSubmitting"
              :result="training.lastPracticeResult"
              :self-rating="training.selfRating"
              @reset="training.resetPractice"
              @submit="training.submitPractice"
              @update:answer-status="training.setPracticeAnswerStatus"
              @update:answer-text="training.setPracticeAnswerText"
              @update:self-rating="training.setSelfRating"
            />
          </section>
        </section>
      </section>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import TrainingOverviewCards from "@/components/training/TrainingOverviewCards.vue";
import TrainingPracticePanel from "@/components/training/TrainingPracticePanel.vue";
import TrainingStatusFilter from "@/components/training/TrainingStatusFilter.vue";
import TrainingTaskList from "@/components/training/TrainingTaskList.vue";
import TrainingWeakTagMap from "@/components/training/TrainingWeakTagMap.vue";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";
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

async function startPractice(id: number): Promise<void> {
  await training.startTask(id);
  await training.openPractice(id);
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
.training-page {
  display: grid;
  gap: var(--s6);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s5);
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

.head-actions,
.toolbar-actions,
.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
}

.head-actions {
  justify-content: flex-end;
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

.training-workbench {
  display: grid;
  gap: var(--s5);
}

.training-grid {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  gap: var(--s5);
  align-items: start;
}

.side-panel,
.task-panel {
  display: grid;
  gap: var(--s4);
}

.explain-copy {
  display: grid;
  gap: var(--s2);
}

.explain-copy p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.task-toolbar {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  align-items: center;
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.task-filter-heading {
  display: grid;
  gap: var(--s1);
}

.toolbar-label {
  margin: 0;
  color: var(--action);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.task-toolbar h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
}

.toolbar-actions {
  align-items: center;
  justify-content: flex-end;
}

.loading-line,
.filter-summary {
  margin: 0;
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 800;
  padding: var(--s3) var(--s4);
}

.loading-line {
  width: fit-content;
  border-style: dashed;
  color: var(--ink-soft);
}

.empty-guidance {
  display: grid;
  gap: var(--s3);
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s5);
}

.empty-guidance h3 {
  margin: 0;
  font-size: var(--text-strong);
  font-weight: 900;
}

.empty-guidance p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .page-head,
  .task-toolbar {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-head {
    flex-direction: column;
  }

  .training-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 520px) {
  .head-actions,
  .toolbar-actions,
  .empty-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
