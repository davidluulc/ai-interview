import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as trainingApi from "@/api/training";

export interface TrainingTaskFilters {
  sourceInterviewRecordId?: number | null;
  weakTag?: string;
}

export type TrainingStatusFilter = "" | "todo" | "in_progress" | "done" | "archived";

export interface TrainingWeakTagGroup {
  weakTag: string;
  weakLabel: string;
  total: number;
  todo: number;
  inProgress: number;
  done: number;
  averageMastery: number;
  highestPriority: trainingApi.TrainingTaskPriority;
}

function replaceTask(tasks: trainingApi.TrainingTask[], updated: trainingApi.TrainingTask): trainingApi.TrainingTask[] {
  return tasks.map((task) => (task.id === updated.id ? updated : task));
}

function averageScore(tasks: trainingApi.TrainingTask[]): number {
  if (tasks.length === 0) {
    return 0;
  }
  return Math.round(tasks.reduce((total, task) => total + Number(task.masteryScore || 0), 0) / tasks.length);
}

function highestPriorityOf(tasks: trainingApi.TrainingTask[]): trainingApi.TrainingTaskPriority {
  const rank: Record<trainingApi.TrainingTaskPriority, number> = {
    low: 1,
    medium: 2,
    high: 3
  };
  return tasks.reduce<trainingApi.TrainingTaskPriority>((highest, task) => {
    return rank[task.priority] > rank[highest] ? task.priority : highest;
  }, "low");
}

export const useTrainingStore = defineStore("training", () => {
  const tasks = ref<trainingApi.TrainingTask[]>([]);
  const loading = ref(false);
  const error = ref("");
  const sourceInterviewRecordId = ref<number | null>(null);
  const weakTag = ref("");
  const statusFilter = ref<TrainingStatusFilter>("");
  const selectedTaskId = ref<number | null>(null);
  const practiceLoading = ref(false);
  const practiceError = ref("");
  const practiceDetail = ref<trainingApi.TrainingPractice | null>(null);
  const practiceAnswerText = ref("");
  const practiceAnswerStatus = ref<trainingApi.TrainingAnswerStatus>("模糊");
  const selfRating = ref<number | null>(null);
  const lastPracticeResult = ref<trainingApi.TrainingTask | null>(null);

  const activeTasks = computed(() => tasks.value.filter((task) => ["todo", "in_progress"].includes(task.status)));
  const todoTasks = computed(() => tasks.value.filter((task) => task.status === "todo"));
  const inProgressTasks = computed(() => tasks.value.filter((task) => task.status === "in_progress"));
  const doneTasks = computed(() => tasks.value.filter((task) => task.status === "done"));
  const completedTasks = computed(() => tasks.value.filter((task) => task.status === "done"));
  const archivedTasks = computed(() => tasks.value.filter((task) => task.status === "archived"));
  const averageMastery = computed(() => averageScore(tasks.value));
  const weakTagGroups = computed<TrainingWeakTagGroup[]>(() => {
    const grouped = new Map<string, trainingApi.TrainingTask[]>();
    for (const task of tasks.value) {
      const key = task.weakTag || "unknown";
      grouped.set(key, [...(grouped.get(key) || []), task]);
    }

    return [...grouped.entries()]
      .map(([tag, groupTasks]) => ({
        weakTag: tag,
        weakLabel: groupTasks.find((task) => task.weakLabel)?.weakLabel || tag,
        total: groupTasks.length,
        todo: groupTasks.filter((task) => task.status === "todo").length,
        inProgress: groupTasks.filter((task) => task.status === "in_progress").length,
        done: groupTasks.filter((task) => task.status === "done").length,
        averageMastery: averageScore(groupTasks),
        highestPriority: highestPriorityOf(groupTasks)
      }))
      .sort((left, right) => right.total - left.total || left.weakTag.localeCompare(right.weakTag));
  });
  const activeWeakTagGroup = computed(() => {
    return weakTagGroups.value.find((group) => group.weakTag === weakTag.value) || null;
  });
  const visibleTasks = computed(() => {
    return tasks.value.filter((task) => {
      const matchesRecord =
        !sourceInterviewRecordId.value || task.sourceInterviewRecordId === sourceInterviewRecordId.value;
      const matchesWeakTag = !weakTag.value || task.weakTag === weakTag.value;
      const matchesStatus = !statusFilter.value || task.status === statusFilter.value;
      return matchesRecord && matchesWeakTag && matchesStatus;
    });
  });
  const activeWeakTagLabel = computed(() => activeWeakTagGroup.value?.weakLabel || weakTag.value);
  const hasWeakTagFilter = computed(() => Boolean(weakTag.value));
  const taskListTitle = computed(() => {
    const label = activeWeakTagLabel.value || "全部";
    return `训练任务 · ${label}（${visibleTasks.value.length} 个）`;
  });
  const filterSummary = computed(() => {
    if (sourceInterviewRecordId.value && weakTag.value) {
      return `正在查看报告 #${sourceInterviewRecordId.value} 中 ${weakTag.value} 的专项训练`;
    }
    if (sourceInterviewRecordId.value) {
      return `正在查看报告 #${sourceInterviewRecordId.value} 生成的训练任务`;
    }
    if (weakTag.value) {
      return `正在查看 ${weakTag.value} 的专项训练`;
    }
    return "";
  });

  async function loadTasks(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const result = await trainingApi.listTrainingTasks();
      tasks.value = result.items;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "训练任务加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function startTask(taskId: number): Promise<void> {
    const updated = await trainingApi.startTrainingTask(taskId);
    tasks.value = replaceTask(tasks.value, updated);
  }

  async function completeTask(taskId: number, answerStatus = "完整"): Promise<void> {
    const updated = await trainingApi.completeTrainingTask(taskId, answerStatus as trainingApi.TrainingAnswerStatus);
    tasks.value = replaceTask(tasks.value, updated);
  }

  async function archiveTask(taskId: number): Promise<void> {
    const updated = await trainingApi.archiveTrainingTask(taskId);
    tasks.value = replaceTask(tasks.value, updated);
  }

  function setFilters(filters: TrainingTaskFilters): void {
    sourceInterviewRecordId.value = filters.sourceInterviewRecordId || null;
    weakTag.value = filters.weakTag || "";
  }

  function setStatusFilter(status: TrainingStatusFilter): void {
    statusFilter.value = status;
  }

  function setWeakTagFilter(tag: string): void {
    weakTag.value = tag;
  }

  function clearFilters(): void {
    sourceInterviewRecordId.value = null;
    weakTag.value = "";
    statusFilter.value = "";
  }

  async function openPractice(taskId: number): Promise<void> {
    selectedTaskId.value = taskId;
    practiceLoading.value = true;
    practiceError.value = "";
    lastPracticeResult.value = null;
    try {
      const result = await trainingApi.getTrainingPractice(taskId, "coach", "basic");
      practiceDetail.value = result.practice;
      tasks.value = replaceTask(tasks.value, result.task);
    } catch (err) {
      practiceError.value = err instanceof Error ? err.message : "训练练习加载失败";
    } finally {
      practiceLoading.value = false;
    }
  }

  async function submitPractice(): Promise<void> {
    if (!selectedTaskId.value) {
      practiceError.value = "请先选择训练任务";
      return;
    }
    const updated = await trainingApi.completeTrainingTask(selectedTaskId.value, {
      answerStatus: practiceAnswerStatus.value,
      answerText: practiceAnswerText.value,
      selfRating: selfRating.value
    });
    tasks.value = replaceTask(tasks.value, updated);
    lastPracticeResult.value = updated;
  }

  function resetPractice(): void {
    selectedTaskId.value = null;
    practiceError.value = "";
    practiceDetail.value = null;
    practiceAnswerText.value = "";
    practiceAnswerStatus.value = "模糊";
    selfRating.value = null;
    lastPracticeResult.value = null;
  }

  function setPracticeAnswerText(text: string): void {
    practiceAnswerText.value = text;
  }

  function setPracticeAnswerStatus(status: trainingApi.TrainingAnswerStatus): void {
    practiceAnswerStatus.value = status;
  }

  function setSelfRating(rating: number | null): void {
    selfRating.value = rating;
  }

  return {
    tasks,
    activeTasks,
    todoTasks,
    inProgressTasks,
    doneTasks,
    completedTasks,
    archivedTasks,
    averageMastery,
    weakTagGroups,
    activeWeakTagGroup,
    activeWeakTagLabel,
    hasWeakTagFilter,
    sourceInterviewRecordId,
    weakTag,
    statusFilter,
    selectedTaskId,
    practiceLoading,
    practiceError,
    practiceDetail,
    practiceAnswerText,
    practiceAnswerStatus,
    selfRating,
    lastPracticeResult,
    visibleTasks,
    taskListTitle,
    filterSummary,
    loading,
    error,
    loadTasks,
    startTask,
    completeTask,
    archiveTask,
    setFilters,
    setStatusFilter,
    setWeakTagFilter,
    clearFilters,
    openPractice,
    submitPractice,
    resetPractice,
    setPracticeAnswerText,
    setPracticeAnswerStatus,
    setSelfRating
  };
});
