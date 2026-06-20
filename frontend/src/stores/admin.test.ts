import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as adminApi from "@/api/admin";
import { useAdminStore } from "./admin";

vi.mock("@/api/admin", () => ({
  fetchAdminSummary: vi.fn(),
  fetchAdminUsers: vi.fn(),
  fetchAdminRagDocuments: vi.fn(),
  fetchAdminRagQuality: vi.fn(),
  fetchAdminRagIngestionTasks: vi.fn(),
  fetchAdminAgentLogs: vi.fn(),
  fetchAdminConfig: vi.fn(),
  fetchAdminAiDebugRecent: vi.fn(),
  fetchAdminAiDebugDetail: vi.fn(),
  forceLogoutUser: vi.fn()
}));

describe("admin store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(adminApi.fetchAdminSummary).mockReset();
    vi.mocked(adminApi.fetchAdminUsers).mockReset();
    vi.mocked(adminApi.fetchAdminRagDocuments).mockReset();
    vi.mocked(adminApi.fetchAdminRagQuality).mockReset();
    vi.mocked(adminApi.fetchAdminRagIngestionTasks).mockReset();
    vi.mocked(adminApi.fetchAdminAgentLogs).mockReset();
    vi.mocked(adminApi.fetchAdminConfig).mockReset();
    vi.mocked(adminApi.fetchAdminAiDebugRecent).mockReset();
    vi.mocked(adminApi.fetchAdminAiDebugDetail).mockReset();
    vi.mocked(adminApi.forceLogoutUser).mockReset();
  });

  it("loads the full admin dashboard through read-only endpoints", async () => {
    vi.mocked(adminApi.fetchAdminSummary).mockResolvedValue({
      userCount: 2,
      interviewRecordCount: 3,
      ragDocumentCount: 4,
      ragRetrievalLogCount: 5,
      agentDecisionLogCount: 6
    });
    vi.mocked(adminApi.fetchAdminUsers).mockResolvedValue({
      items: [
        {
          id: 1,
          email: "admin@ai-interview.com",
          username: "admin",
          role: "admin",
          createdAt: "2026-06-12T10:00:00"
        },
        {
          id: 2,
          email: "demo@ai-interview.com",
          username: "demo",
          role: "user",
          createdAt: "2026-06-12T11:00:00"
        }
      ]
    });
    vi.mocked(adminApi.fetchAdminRagDocuments).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagQuality).mockResolvedValue({
      summary: {
        totalLogCount: 2,
        lowQualityCount: 1,
        emptyRecallCount: 1,
        weakRecallCount: 0,
        unusedInPromptCount: 0
      },
      items: []
    });
    vi.mocked(adminApi.fetchAdminRagIngestionTasks).mockResolvedValue({
      summary: {
        totalCount: 2,
        runningCount: 0,
        succeededCount: 1,
        failedCount: 1,
        retryableCount: 1
      },
      items: [
        {
          taskId: "rag_ingestion-failed",
          userEmail: "demo@ai-interview.com",
          title: "失败导入",
          originalFilename: "failed.md",
          knowledgeBase: "role_knowledge",
          status: "failed",
          error: "document create failed",
          retryCount: 0,
          maxRetries: 2,
          canRetry: true
        }
      ]
    });
    vi.mocked(adminApi.fetchAdminAgentLogs).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminConfig).mockResolvedValue({
      modelName: "qwen-plus",
      embeddingModel: "text-embedding-v4",
      rerankModel: "gte-rerank",
      databaseUrl: "sqlite:///./data/app.db"
    });
    vi.mocked(adminApi.fetchAdminAiDebugRecent).mockResolvedValue({
      items: [
        {
          traceId: 1,
          createdAt: "2026-06-13T18:00:00",
          userId: 101,
          applicationProfileId: 201,
          requestType: "next_question",
          agentMode: "coach",
          nextAction: "lower_difficulty",
          nextActionLabel: "降低难度",
          difficulty: "basic",
          fallbackUsed: true,
          totalRagHits: 0,
          threadId: "agent-log-1",
          diagnostics: [
            {
              type: "fallback_used",
              level: "warning",
              title: "兜底规则已启用",
              message: "模型决策输出不稳定。"
            }
          ]
        }
      ]
    });

    const store = useAdminStore();
    await store.loadDashboard();

    expect(store.summary?.userCount).toBe(2);
    expect(store.users).toHaveLength(2);
    expect(store.ragQuality?.summary.emptyRecallCount).toBe(1);
    expect(store.ragIngestionTasks?.summary.failedCount).toBe(1);
    expect(store.ragIngestionTasks?.items[0].canRetry).toBe(true);
    expect(store.config?.modelName).toBe("qwen-plus");
    expect(store.aiDebugRecent).toHaveLength(1);
    expect(store.aiDebugRecent[0].nextActionLabel).toBe("降低难度");
  });

  it("loads selected AI debug detail", async () => {
    vi.mocked(adminApi.fetchAdminAiDebugDetail).mockResolvedValue({
      summary: { traceId: 1, agentMode: "coach", stage: "技术追问" },
      rag: {
        totalHitCount: 0,
        items: [{ retrieverLabel: "岗位知识库", hitCount: 0, qualityLevel: "miss" }]
      },
      agent: { nextActionLabel: "降低难度", fallbackUsed: true, reason: "连续弱回答" },
      langgraph: { exists: false, explanation: "本次请求未启用 LangGraph 旁路。" },
      diagnostics: [
        {
          type: "empty_recall",
          level: "warning",
          title: "岗位知识库空召回",
          message: "建议补充知识库。"
        }
      ]
    });

    const store = useAdminStore();
    await store.loadAiDebugDetail(1);

    expect(adminApi.fetchAdminAiDebugDetail).toHaveBeenCalledWith(1);
    expect(store.selectedAiDebugTraceId).toBe(1);
    expect(store.selectedAiDebugDetail?.diagnostics[0].title).toBe("岗位知识库空召回");
    expect(store.aiDebugLoading).toBe(false);
  });

  it("keeps runtime quality and comparison fields in ai debug detail", async () => {
    vi.mocked(adminApi.fetchAdminAiDebugDetail).mockResolvedValue({
      summary: { traceId: 1, threadId: "debug-runtime-v4" },
      rag: { items: [], totalHitCount: 0 },
      agent: {},
      langgraph: {
        exists: true,
        runtime: "langgraph",
        visibleRuntime: "classic",
        qualityGate: { passed: false, fallbackToClassic: true, reasons: ["LangGraph 没有生成可展示的问题"] },
        comparisonSummary: {
          comparison: {
            actionMatched: false,
            difficultyMatched: false,
            fallbackToClassic: true,
            reasons: ["两条链路的下一步动作不同"]
          }
        }
      },
      diagnostics: []
    });

    const store = useAdminStore();
    await store.loadAiDebugDetail(1);

    expect(store.selectedAiDebugDetail?.langgraph?.qualityGate?.passed).toBe(false);
    expect(store.selectedAiDebugDetail?.langgraph?.comparisonSummary?.comparison?.fallbackToClassic).toBe(true);
  });

  it("keeps replay summary and runtime report fields in ai debug detail", async () => {
    vi.mocked(adminApi.fetchAdminAiDebugDetail).mockResolvedValue({
      summary: { traceId: 1, threadId: "debug-runtime-v6" },
      rag: { items: [], totalHitCount: 0 },
      agent: {},
      langgraph: {
        exists: true,
        replaySummary: {
          status: "interrupted",
          summary: "本轮 LangGraph 在 human_review 节点暂停。",
          timeline: [{ step: 1, node: "human_review", title: "人工复核", detail: "连续弱回答" }],
          risks: ["requires_human_review"],
          nextActions: ["resume", "fallback_classic"]
        },
        runtimeReport: {
          totalRuns: 2,
          fallbackCount: 1,
          humanReviewCount: 1,
          topQualityGateReasons: [{ reason: "需要人工复核", count: 1 }],
          summary: "该线程共 2 次运行，其中 1 次 fallback、1 次触发人工复核，需要继续观察。"
        }
      },
      diagnostics: []
    });

    const store = useAdminStore();
    await store.loadAiDebugDetail(1);

    expect(store.selectedAiDebugDetail?.langgraph?.replaySummary?.timeline?.[0]?.node).toBe("human_review");
    expect(store.selectedAiDebugDetail?.langgraph?.runtimeReport?.fallbackCount).toBe(1);
  });

  it("filters users by search text and role", () => {
    const store = useAdminStore();
    store.users = [
      { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin", createdAt: "" },
      { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "" }
    ];

    store.userSearch = "demo";
    store.roleFilter = "user";

    expect(store.filteredUsers).toEqual([
      { id: 2, email: "demo@ai-interview.com", username: "demo", role: "user", createdAt: "" }
    ]);
  });

  it("forces a user logout through the admin api", async () => {
    vi.mocked(adminApi.forceLogoutUser).mockResolvedValue({
      ok: true,
      revokedSessions: 1,
      revokedRefreshTokens: 1
    });

    const store = useAdminStore();
    await store.forceLogoutUser(2);

    expect(adminApi.forceLogoutUser).toHaveBeenCalledWith(2);
  });

  it("maps 403 errors to a readable permission message", async () => {
    vi.mocked(adminApi.fetchAdminSummary).mockRejectedValue(new Error("Admin privileges required"));
    vi.mocked(adminApi.fetchAdminUsers).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagDocuments).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminRagQuality).mockResolvedValue({
      summary: {
        totalLogCount: 0,
        lowQualityCount: 0,
        emptyRecallCount: 0,
        weakRecallCount: 0,
        unusedInPromptCount: 0
      },
      items: []
    });
    vi.mocked(adminApi.fetchAdminRagIngestionTasks).mockResolvedValue({
      summary: {
        totalCount: 0,
        runningCount: 0,
        succeededCount: 0,
        failedCount: 0,
        retryableCount: 0
      },
      items: []
    });
    vi.mocked(adminApi.fetchAdminAgentLogs).mockResolvedValue({ items: [] });
    vi.mocked(adminApi.fetchAdminConfig).mockResolvedValue({
      modelName: "",
      embeddingModel: "",
      rerankModel: "",
      databaseUrl: ""
    });
    vi.mocked(adminApi.fetchAdminAiDebugRecent).mockResolvedValue({ items: [] });

    const store = useAdminStore();
    await store.loadDashboard();

    expect(store.error).toBe("当前账号没有管理员权限");
  });
});
