import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as historyApi from "@/api/history";
import * as interviewApi from "@/api/interview";
import * as trainingApi from "@/api/training";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import InterviewPage from "./InterviewPage.vue";

const push = vi.fn();

const interviewStore = {
  messages: [{ role: "interviewer", content: "请先做一个一分钟自我介绍。" }],
  draft: "",
  loading: false,
  error: "",
  sessionStatus: "idle" as "idle" | "starting" | "ready" | "answering" | "reporting" | "completed",
  decisionSummary: "当前处于学习辅导模式，会先确认基础概念。",
  ragReasons: ["命中岗位知识库：FastAPI"],
  agentMode: "coach" as "coach" | "interview",
  agentRuntime: "langgraph_mainline" as "langgraph_mainline" | "classic" | "shadow" | "langgraph_canary",
  lastRuntimeAudit: null as null | { visibleRuntime?: string; fallbackUsed?: boolean },
  lastWorkflowTrace: [] as Array<{ nodeName?: string; node?: string }>,
  lastCheckpointSummary: null as null | Record<string, unknown>,
  lastFallbackSummary: null as null | { used?: boolean; reason?: string },
  sessionConfig: { totalRounds: 8, difficulty: "standard", focusArea: "mixed" },
  currentRound: 1,
  isSessionComplete: false,
  canFinish: false,
  hasStarted: false,
  canSubmitAnswer: false,
  answeredHistory: [] as Array<{ question: string; answer: string }>,
  setAgentMode: vi.fn((mode: "coach" | "interview") => {
    interviewStore.agentMode = mode;
  }),
  setAgentRuntime: vi.fn((runtime: "langgraph_mainline" | "classic" | "shadow" | "langgraph_canary") => {
    interviewStore.agentRuntime = runtime;
  }),
  updateSessionConfig: vi.fn((config: Record<string, unknown>) => {
    interviewStore.sessionConfig = { ...interviewStore.sessionConfig, ...config };
  }),
  resetSession: vi.fn(),
  startInterview: vi.fn(),
  submitAnswer: vi.fn()
};

const authStore = {
  isAdmin: false
};

const profilesStore = {
  currentProfileId: 3 as number | null,
  currentProfile: {
    id: 3,
    title: "后端实习投递",
    targetRole: "Python 后端开发实习生",
    company: "Example AI"
  } as Record<string, unknown> | null
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/api/interview", () => ({
  generateReport: vi.fn()
}));

vi.mock("@/api/history", () => ({
  createHistory: vi.fn()
}));

vi.mock("@/api/training", () => ({
  generateTrainingTasksFromReport: vi.fn()
}));

vi.mock("@/stores/interview", () => ({
  useInterviewStore: () => interviewStore
}));

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

describe("interview page", () => {
  beforeEach(() => {
    push.mockReset();
    interviewStore.submitAnswer.mockReset();
    interviewStore.setAgentMode.mockClear();
    interviewStore.setAgentRuntime.mockClear();
    interviewStore.updateSessionConfig.mockClear();
    interviewStore.resetSession.mockClear();
    interviewStore.startInterview.mockReset();
    interviewStore.agentMode = "coach";
    interviewStore.agentRuntime = "langgraph_mainline";
    interviewStore.sessionStatus = "idle";
    interviewStore.hasStarted = false;
    interviewStore.canSubmitAnswer = false;
    interviewStore.lastRuntimeAudit = null;
    interviewStore.lastWorkflowTrace = [];
    interviewStore.lastCheckpointSummary = null;
    interviewStore.lastFallbackSummary = null;
    authStore.isAdmin = false;
    interviewStore.sessionConfig = { totalRounds: 8, difficulty: "standard", focusArea: "mixed" };
    interviewStore.currentRound = 1;
    interviewStore.isSessionComplete = false;
    interviewStore.canFinish = false;
    interviewStore.answeredHistory = [];
    vi.mocked(interviewApi.generateReport).mockReset();
    vi.mocked(historyApi.createHistory).mockReset();
    vi.mocked(trainingApi.generateTrainingTasksFromReport).mockReset();
    vi.mocked(interviewApi.generateReport).mockResolvedValue({
      score: 82,
      strengths: ["表达清楚"],
      risks: ["RAG 质量指标展开不够"],
      actions: ["补充 Hit@K 和 MRR"],
      questionReviews: [{ weakTags: ["rag_quality"] }],
      trainingPlan: { weakTopics: [{ weakTags: ["rag_quality"] }] }
    });
    vi.mocked(historyApi.createHistory).mockResolvedValue({
      id: 55,
      createdAt: "2026-06-19T08:00:00",
      applicationProfile: { id: 3, title: "后端实习投递" },
      profile: {},
      answers: [],
      report: {}
    });
    vi.mocked(trainingApi.generateTrainingTasksFromReport).mockResolvedValue({ items: [] });
    profilesStore.currentProfileId = 3;
    profilesStore.currentProfile = {
      id: 3,
      title: "后端实习投递",
      targetRole: "Python 后端开发实习生",
      company: "Example AI",
      jd: "熟悉 FastAPI、RAG 和 Agent"
    };
  });

  it("shows the current profile and mode switch", () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("当前面试档案");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("学习辅导");
    expect(wrapper.text()).toContain("真实面试");
  });

  it("shows setup progress and finish guidance in the interview workbench", () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("本次面试配置");
    expect(wrapper.text()).toContain("第 1 / 8 题");
    expect(wrapper.text()).toContain("至少完成 1 轮问答后再复盘");
  });

  it("updates interview session config from setup controls", async () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="session-total-rounds"]').setValue("10");

    expect(interviewStore.updateSessionConfig).toHaveBeenCalledWith(expect.objectContaining({ totalRounds: 10 }));
  });

  it("starts the interview with empty backend history from the selected profile", async () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="start-interview"]').trigger("click");

    expect(interviewStore.startInterview).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        agentMode: "coach",
        agentRuntime: "langgraph_mainline",
        profile: expect.objectContaining({
          title: "后端实习投递",
          targetRole: "Python 后端开发实习生",
          sessionConfig: interviewStore.sessionConfig
        })
      })
    );
  });

  it("generates report saves history creates training tasks and opens the report page", async () => {
    interviewStore.canFinish = true;
    interviewStore.answeredHistory = [
      {
        question: "请解释 RAG 命中日志怎么设计。",
        answer: "我会记录 query、知识库、命中结果和是否进入 prompt。"
      }
    ];

    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="finish-interview"]').trigger("click");
    await flushPromises();

    expect(interviewApi.generateReport).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        answers: interviewStore.answeredHistory,
        profile: expect.objectContaining({
          title: "后端实习投递",
          sessionConfig: interviewStore.sessionConfig
        })
      })
    );
    expect(historyApi.createHistory).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        answers: interviewStore.answeredHistory,
        report: expect.objectContaining({ score: 82 })
      })
    );
    expect(trainingApi.generateTrainingTasksFromReport).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        sourceInterviewRecordId: 55,
        report: expect.objectContaining({ score: 82 })
      })
    );
    expect(push).toHaveBeenCalledWith("/vue/app/reports/55");
  });

  it("guides users to create a profile before interviewing", async () => {
    profilesStore.currentProfileId = null;
    profilesStore.currentProfile = null;

    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("请先选择或创建投递档案");
    await wrapper.get('[data-testid="go-profiles"]').trigger("click");
    expect(push).toHaveBeenCalledWith("/vue/app/profiles");
  });

  it("submits answers with the selected mode", async () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="mode-interview"]').trigger("click");
    wrapper.getComponent(InterviewChatPanel).vm.$emit("submit");

    expect(interviewStore.setAgentMode).toHaveBeenCalledWith("interview");
    expect(interviewStore.submitAnswer).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        agentMode: "interview",
        profile: expect.objectContaining({
          sessionConfig: interviewStore.sessionConfig
        })
      })
    );
  });

  it("hides runtime experiment controls from normal users", () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).not.toContain("实验链路");
    expect(wrapper.find('[data-testid="runtime-langgraph-canary"]').exists()).toBe(false);
  });

  it("shows friendly fallback note without raw workflow json", () => {
    interviewStore.decisionSummary = "候选人回答偏弱，先降低难度。";
    interviewStore.lastRuntimeAudit = { visibleRuntime: "classic", fallbackUsed: true };
    interviewStore.lastFallbackSummary = { used: true, reason: "quality gate failed" };
    interviewStore.lastWorkflowTrace = [{ nodeName: "observe_state" }];

    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("为什么这么问");
    expect(wrapper.text()).toContain("系统已使用稳定兜底策略保证面试继续");
    expect(wrapper.text()).not.toContain("quality gate failed");
    expect(wrapper.text()).not.toContain("observe_state");
  });

  it("shows runtime experiment controls for admins and submits selected runtime", async () => {
    authStore.isAdmin = true;

    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("实验链路");

    await wrapper.get('[data-testid="runtime-langgraph-canary"]').trigger("click");
    wrapper.getComponent(InterviewChatPanel).vm.$emit("submit");

    expect(interviewStore.setAgentRuntime).toHaveBeenCalledWith("langgraph_canary");
    expect(interviewStore.submitAnswer).toHaveBeenCalledWith(
      expect.objectContaining({
        agentRuntime: "langgraph_canary"
      })
    );
  });
});
