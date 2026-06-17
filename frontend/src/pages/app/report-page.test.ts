import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReportPage from "./ReportPage.vue";

const push = vi.fn();

const reportStore = {
  record: {
    id: 12,
    createdAt: "2026-06-12T11:00:00",
    applicationProfile: { id: 2, title: "AI 应用开发投递", targetRole: "Agent 开发实习生" },
    profile: { targetRole: "Agent 开发实习生" },
    answers: [
      {
        question: "Agent 和普通 LLM 有什么区别？",
        answer: "Agent 会观察状态并决策。"
      }
    ],
    report: {
      score: 88,
      level: "良好",
      summary: "表达有结构，但可以补充工具调用细节。",
      strengths: ["能说清状态和决策"],
      risks: ["工具调用细节偏少"],
      actions: ["补充 tool calling 示例"],
      weakTags: ["agent_tool_calling"],
      questionReviews: [
        {
          question: "Agent 和普通 LLM 有什么区别？",
          answer: "Agent 会观察状态并决策。",
          feedback: "方向正确，需要补充工具和记忆。",
          weakTags: ["agent_tool_calling"]
        }
      ],
      decisionSummary: "上一轮提到 Agent 状态，因此追问工具调用。",
      ragReasons: ["命中 Agent 工程化知识库"]
    }
  },
  score: "88",
  weakTags: ["agent_tool_calling"],
  loading: false,
  error: "",
  generatingTraining: false,
  trainingGeneratedMessage: "",
  loadReport: vi.fn(),
  generateTrainingTasks: vi.fn()
};

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { recordId: "12" } }),
  useRouter: () => ({ push })
}));

vi.mock("@/stores/report", () => ({
  useReportStore: () => reportStore
}));

describe("report page", () => {
  beforeEach(() => {
    push.mockReset();
    reportStore.loadReport.mockReset();
    reportStore.generateTrainingTasks.mockReset();
    reportStore.trainingGeneratedMessage = "";
  });

  it("renders interview report summary, reviews, evidence and training entry", async () => {
    const wrapper = mount(ReportPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(reportStore.loadReport).toHaveBeenCalledWith(12);
    expect(wrapper.text()).toContain("面试报告");
    expect(wrapper.text()).toContain("AI 应用开发投递");
    expect(wrapper.text()).toContain("Agent 开发实习生");
    expect(wrapper.text()).toContain("88");
    expect(wrapper.text()).toContain("表达有结构");
    expect(wrapper.text()).toContain("Agent 和普通 LLM 有什么区别");
    expect(wrapper.text()).toContain("agent_tool_calling");
    expect(wrapper.text()).toContain("上一轮提到 Agent 状态");
    expect(wrapper.text()).toContain("建议优先训练");
    expect(wrapper.text()).toContain("再来一场");

    await wrapper.get('[data-testid="go-training-agent_tool_calling"]').trigger("click");
    expect(push).toHaveBeenCalledWith({
      path: "/vue/app/training",
      query: { recordId: "12", weakTag: "agent_tool_calling" }
    });
  });

  it("generates training tasks from the current report before entering training center", async () => {
    reportStore.generateTrainingTasks.mockResolvedValue([
      {
        id: 3,
        weakTag: "agent_tool_calling",
        title: "工具调用专项训练",
        status: "todo"
      }
    ]);

    const wrapper = mount(ReportPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="generate-training-tasks"]').trigger("click");

    expect(reportStore.generateTrainingTasks).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith({
      path: "/vue/app/training",
      query: { recordId: "12", weakTag: "agent_tool_calling" }
    });
  });

  it("returns users to the interview workbench for another session", async () => {
    const wrapper = mount(ReportPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="start-another-interview"]').trigger("click");

    expect(push).toHaveBeenCalledWith("/vue/app/interview");
  });
});
