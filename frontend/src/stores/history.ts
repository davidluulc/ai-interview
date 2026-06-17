import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as historyApi from "@/api/history";

export type HistorySortOrder = "newest" | "oldest";

export interface HistoryFilters {
  applicationProfileId?: number | null;
  roleKeyword?: string;
  sortOrder?: HistorySortOrder;
}

export const useHistoryStore = defineStore("history", () => {
  const items = ref<historyApi.HistoryRecord[]>([]);
  const loading = ref(false);
  const error = ref("");
  const applicationProfileId = ref<number | null>(null);
  const roleKeyword = ref("");
  const sortOrder = ref<HistorySortOrder>("newest");

  const latestItems = computed(() => items.value.slice(0, 20));
  const profileOptions = computed(() => {
    const optionMap = new Map<number, string>();
    for (const item of items.value) {
      if (item.applicationProfile?.id && item.applicationProfile.title) {
        optionMap.set(item.applicationProfile.id, item.applicationProfile.title);
      }
    }
    return Array.from(optionMap.entries()).map(([id, title]) => ({ id, title }));
  });
  const filteredItems = computed(() => {
    const keyword = roleKeyword.value.trim().toLowerCase();
    return [...items.value]
      .filter((item) => {
        const matchesProfile =
          !applicationProfileId.value || item.applicationProfile?.id === applicationProfileId.value;
        const role = `${item.applicationProfile?.targetRole || ""} ${String(item.profile.targetRole || "")}`.toLowerCase();
        const matchesRole = !keyword || role.includes(keyword);
        return matchesProfile && matchesRole;
      })
      .sort((left, right) => {
        const leftTime = new Date(left.createdAt).getTime();
        const rightTime = new Date(right.createdAt).getTime();
        return sortOrder.value === "oldest" ? leftTime - rightTime : rightTime - leftTime;
      });
  });

  async function loadHistory(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      items.value = await historyApi.listHistory();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "历史记录加载失败";
    } finally {
      loading.value = false;
    }
  }

  function findById(id: number): historyApi.HistoryRecord | null {
    return items.value.find((item) => item.id === id) || null;
  }

  function setFilters(filters: HistoryFilters): void {
    applicationProfileId.value = filters.applicationProfileId || null;
    roleKeyword.value = filters.roleKeyword || "";
    sortOrder.value = filters.sortOrder || "newest";
  }

  return {
    items,
    latestItems,
    filteredItems,
    profileOptions,
    applicationProfileId,
    roleKeyword,
    sortOrder,
    loading,
    error,
    loadHistory,
    findById,
    setFilters
  };
});
