import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminPage from "./AdminPage.vue";

const authStore: {
  user: { id: number; email: string; username: string; role: string } | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
} = {
  user: { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin" },
  loading: false,
  isAuthenticated: true,
  isAdmin: true
};

const adminStore = {
  summary: {
    userCount: 2,
    interviewRecordCount: 3,
    ragDocumentCount: 4,
    ragRetrievalLogCount: 5,
    agentDecisionLogCount: 6
  },
  filteredUsers: Array.from({ length: 12 }, (_, index) => ({
    id: index + 1,
    email:
      index === 0
        ? "admin@ai-interview.com"
        : index === 1
          ? "demo@ai-interview.com"
          : `user${index + 1}@example.com`,
    username: index === 0 ? "admin" : index === 1 ? "demo" : `user${index + 1}`,
    role: index === 0 ? "admin" : "user",
    createdAt: `2026-06-12T${String(10 + index).padStart(2, "0")}:00:00`
  })),
  ragDocuments: [
    {
      id: 1,
      title: "RAG 日志知识",
      knowledgeBase: "role_knowledge",
      status: "enabled",
      visibility: "public",
      chunkCount: 8,
      duplicateChunkCount: 1,
      userEmail: "admin@ai-interview.com"
    }
  ],
  ragQuality: {
    summary: {
      totalLogCount: 3,
      lowQualityCount: 1,
      emptyRecallCount: 1,
      weakRecallCount: 0,
      unusedInPromptCount: 0
    },
    items: [
      {
        id: 1,
        queryText: "RAG 日志怎么写",
        retrieverName: "role_knowledge",
        hitCount: 0,
        issueType: "empty_recall",
        recommendation: "补充知识库内容"
      }
    ]
  },
  agentLogs: [
    {
      id: 1,
      nextAction: "switch_topic",
      stage: "技术追问",
      difficulty: "basic",
      focus: "RAG",
      reason: "连续弱回答",
      fallbackUsed: true
    },
    {
      id: 2,
      nextAction: "deepen",
      stage: "技术追问",
      difficulty: "medium",
      focus: "RAG 质量评估",
      reason: "用户回答较完整，继续深挖。",
      fallbackUsed: false
    }
  ],
  aiDebugRecent: [
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
  ],
  selectedAiDebugTraceId: 1,
  selectedAiDebugDetail: {
    summary: { traceId: 1, agentMode: "coach", stage: "技术追问", threadId: "agent-log-1" },
    rag: {
      totalHitCount: 0,
      items: [{ retrieverLabel: "岗位知识库", queryText: "RAG 日志 JSON", hitCount: 0, qualityLevel: "miss" }]
    },
    agent: {
      nextActionLabel: "降低难度",
      fallbackUsed: true,
      reason: "连续弱回答",
      focus: "RAG 日志 JSON"
    },
    langgraph: {
      exists: true,
      explanation: "LangGraph checkpoint 已记录本轮旁路状态。",
      runtime: "langgraph",
      visibleRuntime: "classic",
      status: "interrupted",
      currentNode: "human_review",
      threadId: "agent-log-1",
      nodeTraceCount: 1,
      requiresHumanReview: true,
      interrupt: { reason: "连续弱回答", options: ["switch_to_coach"] },
      resumeDecision: "",
      qualityGate: { passed: true, fallbackToClassic: false, reasons: [] as string[] },
      comparisonSummary: {
        comparison: {
          actionMatched: true,
          difficultyMatched: true,
          fallbackToClassic: false,
          reasons: [] as string[]
        }
      },
      runtimeAudit: {
        requestedRuntime: "langgraph_canary",
        allowedRuntime: "langgraph",
        visibleRuntime: "classic",
        fallbackUsed: true,
        policyReasons: ["管理员账号允许使用 LangGraph 灰度链路"],
        qualityGateReasons: ["LangGraph 问题与最近问题重复度过高"]
      }
    },
    diagnostics: [
      {
        type: "empty_recall",
        level: "warning",
        title: "岗位知识库空召回",
        message: "建议补充知识库。"
      },
      {
        type: "missing_checkpoint",
        level: "info",
        title: "未找到 LangGraph checkpoint",
        message: "本次请求可能未启用 LangGraph 旁路。"
      }
    ]
  },
  aiDebugLoading: false,
  aiDebugError: "",
  loadAiDebugDetail: vi.fn(),
  config: {
    modelName: "qwen-plus",
    embeddingModel: "text-embedding-v4",
    rerankModel: "gte-rerank",
    databaseUrl: "sqlite:///./data/app.db"
  },
  loading: false,
  error: "",
  userSearch: "",
  roleFilter: "all",
  loadDashboard: vi.fn()
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

vi.mock("@/stores/admin", () => ({
  useAdminStore: () => adminStore
}));

const globalConfig = {
  stubs: {
    AppLayout: { template: "<main><slot /></main>" }
  }
};

describe("admin page", () => {
  beforeEach(() => {
    authStore.user = { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin" };
    authStore.loading = false;
    authStore.isAuthenticated = true;
    authStore.isAdmin = true;
    adminStore.error = "";
    adminStore.loadDashboard.mockReset();
    adminStore.loadAiDebugDetail.mockReset();
  });

  it("shows a restoring message instead of denying access while auth state is loading", () => {
    authStore.user = null;
    authStore.loading = true;
    authStore.isAdmin = false;

    const wrapper = mount(AdminPage, { global: globalConfig });

    expect(wrapper.text()).toContain("正在恢复登录状态");
    expect(wrapper.text()).not.toContain("当前账号没有管理员权限");
    expect(adminStore.loadDashboard).not.toHaveBeenCalled();
  });

  it("shows a permission message for normal users", () => {
    authStore.isAdmin = false;

    const wrapper = mount(AdminPage, { global: globalConfig });

    expect(wrapper.text()).toContain("当前账号没有管理员权限");
    expect(adminStore.loadDashboard).not.toHaveBeenCalled();
  });

  it("loads and renders the admin dashboard for admin users", () => {
    const wrapper = mount(AdminPage, { global: globalConfig });

    expect(adminStore.loadDashboard).toHaveBeenCalled();
    expect(wrapper.text()).toContain("平台概览");
    expect(wrapper.text()).toContain("用户数");
    expect(wrapper.text()).toContain("账号管理");
    expect(wrapper.text()).toContain("admin@ai-interview.com");
    expect(wrapper.text()).toContain("RAG 质量诊断");
    expect(wrapper.text()).toContain("补充岗位知识库或题库内容");
    expect(wrapper.text()).toContain("Agent 决策日志");
    expect(wrapper.text()).toContain("连续弱回答");
    expect(wrapper.text()).toContain("系统配置");
    expect(wrapper.text()).not.toContain("undefined");
  });

  it("translates raw RAG and Agent logs into readable admin diagnostics", () => {
    const wrapper = mount(AdminPage, { global: globalConfig });
    const text = wrapper.text();

    expect(text).toContain("用于判断 RAG 是不是找到了合适资料");
    expect(text).toContain("空召回：没有找到资料");
    expect(text).toContain("岗位知识库");
    expect(text).toContain("建议动作：补充岗位知识库或题库内容");
    expect(text).toContain("启用中");
    expect(text).toContain("公共资料");
    expect(text).toContain("可能存在重复切片");
    expect(text).toContain("兜底规则已启用");
    expect(text).toContain("下一步动作：切换话题");
    expect(text).toContain("下一步动作：继续深挖");
    expect(text).not.toContain("下一步动作：deepen");
    expect(text).not.toContain("undefined");
  });

  it("renders the AI debug console with RAG Agent and LangGraph traces", () => {
    const wrapper = mount(AdminPage, { global: globalConfig });
    const text = wrapper.text();

    expect(text).toContain("AI 调试控制台");
    expect(text).toContain("最近 AI 请求");
    expect(text).toContain("RAG 召回链路");
    expect(text).toContain("Agent 决策链路");
    expect(text).toContain("LangGraph 执行链路");
    expect(text).toContain("Runtime");
    expect(text).toContain("langgraph");
    expect(text).toContain("interrupted");
    expect(text).toContain("human_review");
    expect(text).toContain("需要人工介入");
    expect(text).toContain("连续弱回答");
    expect(text).toContain("诊断建议");
    expect(text).toContain("兜底规则已启用");
    expect(text).toContain("LangGraph checkpoint 已记录本轮旁路状态");
    expect(text).not.toContain("undefined");
  });

  it("renders langgraph runtime quality gate and comparison summary", () => {
    adminStore.selectedAiDebugDetail = {
      summary: { traceId: 1, agentMode: "coach", stage: "技术追问", threadId: "debug-runtime-v4" },
      rag: { items: [], totalHitCount: 0 },
      agent: {
        nextActionLabel: "降低难度",
        fallbackUsed: true,
        reason: "LangGraph 未通过门禁，回退 classic",
        focus: "runtime quality gate"
      },
      langgraph: {
        exists: true,
        explanation: "LangGraph checkpoint 已记录本轮旁路状态。",
        runtime: "langgraph",
        visibleRuntime: "classic",
        status: "completed",
        currentNode: "generate_question",
        threadId: "debug-runtime-v4",
        nodeTraceCount: 2,
        requiresHumanReview: false,
        interrupt: { reason: "", options: [] },
        resumeDecision: "",
        qualityGate: { passed: false, fallbackToClassic: true, reasons: ["LangGraph 没有生成可展示的问题"] },
        comparisonSummary: {
          comparison: {
            actionMatched: false,
            difficultyMatched: false,
            fallbackToClassic: true,
            reasons: ["两条链路的下一步动作不同"]
          }
        },
        runtimeAudit: {
          requestedRuntime: "langgraph_canary",
          allowedRuntime: "langgraph",
          visibleRuntime: "classic",
          fallbackUsed: true,
          policyReasons: ["管理员账号允许使用 LangGraph 灰度链路"],
          qualityGateReasons: ["LangGraph 没有生成可展示的问题"]
        }
      },
      diagnostics: []
    };

    const wrapper = mount(AdminPage, { global: globalConfig });
    const text = wrapper.text();

    expect(text).toContain("Runtime 对比");
    expect(text).toContain("可见链路：classic");
    expect(text).toContain("Quality Gate：未通过");
    expect(text).toContain("Fallback：已回退 classic");
  });

  it("renders runtime audit summary in AI debug detail", () => {
    adminStore.selectedAiDebugDetail = {
      summary: { traceId: 1, agentMode: "coach", stage: "技术追问", threadId: "debug-runtime-v5" },
      rag: { items: [], totalHitCount: 0 },
      agent: {
        nextActionLabel: "降低难度",
        fallbackUsed: true,
        reason: "LangGraph canary 触发回退",
        focus: "runtime audit"
      },
      langgraph: {
        exists: true,
        explanation: "LangGraph checkpoint 已记录本轮旁路状态。",
        runtime: "langgraph",
        visibleRuntime: "classic",
        status: "completed",
        currentNode: "generate_question",
        threadId: "debug-runtime-v5",
        nodeTraceCount: 2,
        requiresHumanReview: false,
        interrupt: { reason: "", options: [] },
        resumeDecision: "",
        qualityGate: { passed: false, fallbackToClassic: true, reasons: ["LangGraph 问题与最近问题重复度过高"] },
        comparisonSummary: {
          comparison: {
            actionMatched: false,
            difficultyMatched: false,
            fallbackToClassic: true,
            reasons: ["两条链路的下一步动作不同"]
          }
        },
        runtimeAudit: {
          requestedRuntime: "langgraph_canary",
          allowedRuntime: "langgraph",
          visibleRuntime: "classic",
          fallbackUsed: true,
          policyReasons: ["管理员账号允许使用 LangGraph 灰度链路"],
          qualityGateReasons: ["LangGraph 问题与最近问题重复度过高"]
        }
      },
      diagnostics: []
    };

    const wrapper = mount(AdminPage, { global: globalConfig });
    const text = wrapper.text();

    expect(text).toContain("Runtime 审计");
    expect(text).toContain("请求链路：langgraph_canary");
    expect(text).toContain("允许链路：langgraph");
    expect(text).toContain("最终可见：classic");
    expect(text).toContain("回退状态：已回退");
    expect(text).toContain("管理员账号允许使用 LangGraph 灰度链路");
    expect(text).toContain("LangGraph 问题与最近问题重复度过高");
    expect(text).not.toContain("undefined");
  });

  it("paginates account management and supports changing page size", async () => {
    const wrapper = mount(AdminPage, { global: globalConfig });
    const accountTableText = () => wrapper.find("table").text();

    expect(wrapper.text()).toContain("第 1 / 2 页");
    expect(wrapper.text()).toContain("显示 1-10 条，共 12 条");
    expect(accountTableText()).toContain("admin@ai-interview.com");
    expect(accountTableText()).toContain("user10@example.com");
    expect(accountTableText()).not.toContain("user11@example.com");

    await wrapper.get("button[aria-label='下一页账号']").trigger("click");

    expect(wrapper.text()).toContain("第 2 / 2 页");
    expect(wrapper.text()).toContain("显示 11-12 条，共 12 条");
    expect(accountTableText()).toContain("user11@example.com");
    expect(accountTableText()).toContain("user12@example.com");
    expect(accountTableText()).not.toContain("admin@ai-interview.com");

    await wrapper.get("select[aria-label='每页显示账号数量']").setValue("5");
    await nextTick();

    expect(wrapper.text()).toContain("第 1 / 3 页");
    expect(wrapper.text()).toContain("显示 1-5 条，共 12 条");
    expect(accountTableText()).toContain("admin@ai-interview.com");
    expect(accountTableText()).not.toContain("user6@example.com");
  });
});
