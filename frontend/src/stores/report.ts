import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as historyApi from "@/api/history";
import * as trainingApi from "@/api/training";

export const useReportStore = defineStore("report", () => {
  const record = ref<historyApi.HistoryRecord | null>(null);
  const loading = ref(false);
  const error = ref("");
  const generatingTraining = ref(false);
  const trainingGeneratedMessage = ref("");

  const report = computed(() => record.value?.report || {});
  const score = computed(() => {
    const value = report.value.score;
    return typeof value === "number" || typeof value === "string" ? String(value) : "--";
  });
  const weakTags = computed(() => {
    const value = report.value.weakTags;
    return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
  });

  async function loadReport(recordId: number): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const records = await historyApi.listHistory();
      record.value = records.find((item) => item.id === recordId) || null;
      if (!record.value) {
        error.value = "没有找到这场面试报告";
      }
    } catch (err) {
      record.value = null;
      error.value = err instanceof Error ? err.message : "面试报告加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function generateTrainingTasks(): Promise<trainingApi.TrainingTask[]> {
    if (!record.value) {
      error.value = "请先加载面试报告";
      return [];
    }

    generatingTraining.value = true;
    trainingGeneratedMessage.value = "";
    error.value = "";
    try {
      const result = await trainingApi.generateTrainingTasksFromReport({
        applicationProfileId: record.value.applicationProfile?.id ?? null,
        sourceInterviewRecordId: record.value.id,
        report: record.value.report
      });
      trainingGeneratedMessage.value = `已生成 ${result.items.length} 个专项训练任务`;
      return result.items;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "训练任务生成失败";
      return [];
    } finally {
      generatingTraining.value = false;
    }
  }

  return {
    record,
    report,
    score,
    weakTags,
    loading,
    error,
    generatingTraining,
    trainingGeneratedMessage,
    loadReport,
    generateTrainingTasks
  };
});
