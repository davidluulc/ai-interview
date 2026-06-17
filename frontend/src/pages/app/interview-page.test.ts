import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import InterviewChatPanel from "@/components/interview/InterviewChatPanel.vue";
import InterviewPage from "./InterviewPage.vue";

const push = vi.fn();

const interviewStore = {
  messages: [{ role: "interviewer", content: "请先做一个一分钟自我介绍。" }],
  draft: "",
  loading: false,
  error: "",
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
    interviewStore.agentMode = "coach";
    interviewStore.agentRuntime = "langgraph_mainline";
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
