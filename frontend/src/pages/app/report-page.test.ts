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
          whyAsked: "用于确认你是否理解 Agent 和普通 LLM 的边界。",
          missingPoints: ["工具调用", "状态管理"],
          referenceDirection: "按观察状态、选择工具、生成回答的顺序讲。",
          trainingAction: "用 1 分钟讲清楚一次工具调用流程。",
          weakTags: ["agent_tool_calling"]
        }
      ],
      trainingPlan: {
        weakTopics: [
          {
            focus: "Agent 工具调用",
            reason: "工具调用链路解释不完整。",
            trainingAction: "画出 observe、decide、act 三步流程。",
            weakTags: ["agent_tool_calling"]
          }
        ],
        nextRoundPriority: ["Agent 工具调用"],
        practiceQuestions: ["请用 1 分钟说明 Agent 如何决定是否调用工具。"],
        oneMinuteTemplates: ["背景：用户问题需要外部信息；做法：先观察状态再调用工具；结果：把工具结果整合进回答。"],
        shouldRetry: true
      },
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
    reportStore.weakTags = ["agent_tool_calling"];
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
    expect(wrapper.text()).toContain("用于确认你是否理解 Agent 和普通 LLM 的边界。");
    expect(wrapper.text()).toContain("工具调用");
    expect(wrapper.text()).toContain("按观察状态、选择工具、生成回答的顺序讲。");
    expect(wrapper.text()).toContain("用 1 分钟讲清楚一次工具调用流程。");
    expect(wrapper.text()).toContain("Agent 工具调用");
    expect(wrapper.text()).toContain("工具调用链路解释不完整。");
    expect(wrapper.text()).toContain("请用 1 分钟说明 Agent 如何决定是否调用工具。");
    expect(wrapper.text()).toContain("背景：用户问题需要外部信息");
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

  it("derives priority training tags from the report training plan when top-level weak tags are missing", () => {
    reportStore.weakTags = [];

    const wrapper = mount(ReportPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("Agent 工具调用");
    expect(wrapper.text()).not.toContain("待训练");
  });

  it("renders human-readable evidence instead of the old why title", () => {
    const originalSummary = reportStore.record.report.decisionSummary;
    const originalReasons = reportStore.record.report.ragReasons;

    try {
      reportStore.record.report.decisionSummary = "JD 要求 RAG 链路理解，上一轮回答缺少日志字段。";
      reportStore.record.report.ragReasons = [
        "命中岗位知识库：RAG Agent 与 LangGraph 项目知识",
        "命中岗位知识库：RAG Agent 与 LangGraph 项目知识",
        "命中题库：Redis PostgreSQL Celery 生产化职责",
        "命中候选人画像：Python 后端开发实习生"
      ];

      const wrapper = mount(ReportPage, {
        global: {
          stubs: {
            AppLayout: { template: "<main><slot /></main>" }
          }
        }
      });

      expect(wrapper.text()).toContain("出题依据");
      expect(wrapper.text()).not.toContain("为什么这样问");
      expect(wrapper.text()).toContain("JD 要求 RAG 链路理解");
      expect(wrapper.findAll("li").filter((item) => item.text().includes("RAG Agent 与 LangGraph")).length).toBe(1);
    } finally {
      reportStore.record.report.decisionSummary = originalSummary;
      reportStore.record.report.ragReasons = originalReasons;
    }
  });

  it("turns RAG reasons into candidate-facing evidence and secondary sources", () => {
    const originalSummary = reportStore.record.report.decisionSummary;
    const originalReasons = reportStore.record.report.ragReasons;

    try {
      reportStore.record.report.decisionSummary = "JD 要求 RAG 链路理解，上一轮回答缺少日志字段。";
      reportStore.record.report.ragReasons = [
        "命中岗位知识库：RAG Agent 与 LangGraph 项目知识，命中词包括：rag、prompt、langgraph、agent。",
        "命中题库：PostgreSQL、Redis、Celery 在这个项目里分别承担什么职责？",
        "命中候选人画像：Python 后端开发实习生"
      ];

      const wrapper = mount(ReportPage, {
        global: {
          stubs: {
            AppLayout: { template: "<main><slot /></main>" }
          }
        }
      });

      expect(wrapper.text()).toContain("这道题主要围绕");
      expect(wrapper.text()).toContain("岗位 JD");
      expect(wrapper.text()).toContain("上一轮回答");
      expect(wrapper.text()).toContain("参考来源");
      expect(wrapper.text()).toContain("岗位知识库：RAG Agent 与 LangGraph 项目知识");
      expect(wrapper.text()).toContain("题库：PostgreSQL、Redis、Celery 在这个项目里分别承担什么职责？");
      expect(wrapper.text()).not.toContain("命中词包括");
    } finally {
      reportStore.record.report.decisionSummary = originalSummary;
      reportStore.record.report.ragReasons = originalReasons;
    }
  });

  it("does not pretend weak evidence is strong", () => {
    const originalSummary = reportStore.record.report.decisionSummary;
    const originalReasons = reportStore.record.report.ragReasons;

    try {
      reportStore.record.report.decisionSummary = "";
      reportStore.record.report.ragReasons = ["围绕当前档案、历史回答和检索上下文共同驱动。"];

      const wrapper = mount(ReportPage, {
        global: {
          stubs: {
            AppLayout: { template: "<main><slot /></main>" }
          }
        }
      });

      expect(wrapper.text()).toContain("当前知识库命中较弱");
      expect(wrapper.text()).not.toContain("命中岗位知识库");
    } finally {
      reportStore.record.report.decisionSummary = originalSummary;
      reportStore.record.report.ragReasons = originalReasons;
    }
  });

  it("hides low-value fallback evidence copy", () => {
    const originalSummary = reportStore.record.report.decisionSummary;
    const originalReasons = reportStore.record.report.ragReasons;

    try {
      reportStore.record.report.decisionSummary = "本题由当前档案、历史回答和检索上下文共同驱动。";
      reportStore.record.report.ragReasons = [];

      const wrapper = mount(ReportPage, {
        global: {
          stubs: {
            AppLayout: { template: "<main><slot /></main>" }
          }
        }
      });

      expect(wrapper.text()).not.toContain("出题依据");
      expect(wrapper.text()).not.toContain("本题由当前档案、历史回答和检索上下文共同驱动");
    } finally {
      reportStore.record.report.decisionSummary = originalSummary;
      reportStore.record.report.ragReasons = originalReasons;
    }
  });

  it("fills old question reviews from saved answers and review guidance", () => {
    const originalReviews = reportStore.record.report.questionReviews;

    try {
      reportStore.record.report.questionReviews = [
        {
          question: "Agent 和普通 LLM 有什么区别？",
          whyAsked: "用于确认你是否理解 Agent 和普通 LLM 的边界。",
          missingPoints: ["工具调用", "状态管理"],
          referenceDirection: "按观察状态、选择工具、生成回答的顺序讲。",
          trainingAction: "用 1 分钟讲清楚一次工具调用流程。",
          weakTags: ["agent_tool_calling"]
        } as any
      ];

      const wrapper = mount(ReportPage, {
        global: {
          stubs: {
            AppLayout: { template: "<main><slot /></main>" }
          }
        }
      });

      expect(wrapper.text()).toContain("回答：Agent 会观察状态并决策。");
      expect(wrapper.text()).toContain("建议：按观察状态、选择工具、生成回答的顺序讲。");
      expect(wrapper.text()).not.toContain("回答：暂无");
      expect(wrapper.text()).not.toContain("建议：暂无");
    } finally {
      reportStore.record.report.questionReviews = originalReviews;
    }
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
