import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as adminApi from "@/api/admin";

export type AdminAiDebugTab = "overview" | "rag" | "agent" | "langgraph" | "diagnostics" | "raw";

export const useAdminStore = defineStore("admin", () => {
  const summary = ref<adminApi.AdminSummary | null>(null);
  const users = ref<adminApi.AdminUser[]>([]);
  const ragDocuments = ref<adminApi.AdminRagDocument[]>([]);
  const ragQuality = ref<adminApi.AdminRagQuality | null>(null);
  const ragIngestionTasks = ref<adminApi.AdminRagIngestionTasks | null>(null);
  const agentLogs = ref<adminApi.AdminAgentLog[]>([]);
  const aiDebugRecent = ref<adminApi.AdminAiDebugRecentItem[]>([]);
  const selectedAiDebugTraceId = ref<number | null>(null);
  const selectedAiDebugDetail = ref<adminApi.AdminAiDebugDetail | null>(null);
  const selectedAiDebugTab = ref<AdminAiDebugTab>("overview");
  const aiDebugLoading = ref(false);
  const aiDebugError = ref("");
  const config = ref<adminApi.AdminConfig | null>(null);
  const loading = ref(false);
  const error = ref("");
  const userSearch = ref("");
  const roleFilter = ref<"all" | "admin" | "user">("all");
  const forceLogoutPendingUserId = ref<number | null>(null);
  const forceLogoutMessage = ref("");
  const forceLogoutError = ref("");

  const filteredUsers = computed(() => {
    const search = userSearch.value.trim().toLowerCase();
    return users.value.filter((user) => {
      const matchesRole = roleFilter.value === "all" || user.role === roleFilter.value;
      const matchesSearch =
        !search ||
        user.email.toLowerCase().includes(search) ||
        user.username.toLowerCase().includes(search);
      return matchesRole && matchesSearch;
    });
  });

  const agentActionSummary = computed(() => {
    const grouped = new Map<string, number>();
    for (const log of agentLogs.value) {
      const action = log.nextAction || log.next_action || "unknown";
      grouped.set(action, (grouped.get(action) || 0) + 1);
    }
    return Array.from(grouped.entries()).map(([action, count]) => ({ action, count }));
  });

  const agentDashboardSummary = computed(() => ({
    totalCount: agentLogs.value.length,
    fallbackCount: agentLogs.value.filter((log) => Boolean(log.fallbackUsed || log.fallback_used)).length,
    actionSummary: agentActionSummary.value
  }));

  const ragDocumentDashboard = computed(() => {
    const activeDocs = ragDocuments.value.filter((document) => (document.status || "enabled") === "enabled");
    const coverage = new Map<string, { knowledgeBase: string; readyDocumentCount: number; readyChunkCount: number }>();
    for (const document of activeDocs) {
      const knowledgeBase = document.knowledgeBase || document.knowledge_base || "unknown";
      const current = coverage.get(knowledgeBase) || {
        knowledgeBase,
        readyDocumentCount: 0,
        readyChunkCount: 0
      };
      current.readyDocumentCount += 1;
      current.readyChunkCount += document.chunkCount || document.chunk_count || 0;
      coverage.set(knowledgeBase, current);
    }
    return {
      readyDocumentCount: activeDocs.length,
      readyChunkCount: activeDocs.reduce((sum, document) => sum + (document.chunkCount || document.chunk_count || 0), 0),
      knowledgeBaseCoverage: Array.from(coverage.values())
    };
  });

  async function loadDashboard(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const [
        summaryResult,
        usersResult,
        documentsResult,
        qualityResult,
        ingestionTasksResult,
        logsResult,
        aiDebugResult,
        configResult
      ] =
        await Promise.all([
          adminApi.fetchAdminSummary(),
          adminApi.fetchAdminUsers(),
          adminApi.fetchAdminRagDocuments(),
          adminApi.fetchAdminRagQuality(),
          adminApi.fetchAdminRagIngestionTasks(),
          adminApi.fetchAdminAgentLogs(),
          adminApi.fetchAdminAiDebugRecent(),
          adminApi.fetchAdminConfig()
        ]);

      summary.value = summaryResult;
      users.value = usersResult.items;
      ragDocuments.value = documentsResult.items;
      ragQuality.value = qualityResult;
      ragIngestionTasks.value = ingestionTasksResult;
      agentLogs.value = logsResult.items;
      aiDebugRecent.value = aiDebugResult.items;
      config.value = configResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : "管理员后台加载失败";
      error.value =
        message.includes("Admin privileges") || message.includes("403") ? "当前账号没有管理员权限" : message;
    } finally {
      loading.value = false;
    }
  }

  async function loadAiDebugDetail(traceId: number): Promise<void> {
    selectedAiDebugTraceId.value = traceId;
    selectedAiDebugTab.value = "overview";
    aiDebugLoading.value = true;
    aiDebugError.value = "";
    try {
      selectedAiDebugDetail.value = await adminApi.fetchAdminAiDebugDetail(traceId);
    } catch (err) {
      selectedAiDebugDetail.value = null;
      aiDebugError.value = err instanceof Error ? err.message : "AI 调试详情加载失败";
    } finally {
      aiDebugLoading.value = false;
    }
  }

  function setAiDebugTab(tab: AdminAiDebugTab): void {
    selectedAiDebugTab.value = tab;
  }

  async function forceLogoutUser(user: adminApi.AdminUser): Promise<void> {
    forceLogoutPendingUserId.value = user.id;
    forceLogoutMessage.value = "";
    forceLogoutError.value = "";
    try {
      const result = await adminApi.forceLogoutUser(user.id);
      forceLogoutMessage.value = `已下线 ${user.email}，撤销 ${result.revokedSessions} 个会话、${result.revokedRefreshTokens} 个 refresh token。`;
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      forceLogoutError.value = `强制下线失败：${message}`;
    } finally {
      forceLogoutPendingUserId.value = null;
    }
  }

  return {
    summary,
    users,
    ragDocuments,
    ragQuality,
    ragIngestionTasks,
    agentLogs,
    aiDebugRecent,
    selectedAiDebugTraceId,
    selectedAiDebugDetail,
    selectedAiDebugTab,
    aiDebugLoading,
    aiDebugError,
    config,
    loading,
    error,
    userSearch,
    roleFilter,
    forceLogoutPendingUserId,
    forceLogoutMessage,
    forceLogoutError,
    filteredUsers,
    agentActionSummary,
    agentDashboardSummary,
    ragDocumentDashboard,
    loadDashboard,
    loadAiDebugDetail,
    setAiDebugTab,
    forceLogoutUser
  };
});
