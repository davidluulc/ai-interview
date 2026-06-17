import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TrainingPage from "./TrainingPage.vue";

const pushMock = vi.fn();

const task = {
  id: 3,
  weakTag: "agent_tool_calling",
  weakLabel: "工具调用",
  title: "工具调用专项训练",
  description: "补齐 Agent tool calling 表达。",
  status: "todo",
  priority: "high",
  masteryScore: 45,
  sourceInterviewRecordId: 12
};

const trainingStore = {
  tasks: [task],
  activeTasks: [task],
  todoTasks: [task],
  inProgressTasks: [],
  doneTasks: [],
  completedTasks: [],
  archivedTasks: [],
  averageMastery: 45,
  weakTagGroups: [
    {
      weakTag: "agent_tool_calling",
      weakLabel: "工具调用",
      total: 1,
      todo: 1,
      inProgress: 0,
      done: 0,
      averageMastery: 45,
      highestPriority: "high"
    }
  ],
  statusFilter: "",
  weakTag: "agent_tool_calling",
  selectedTaskId: null,
  practiceLoading: false,
  practiceError: "",
  practiceDetail: {
    weakTag: "agent_tool_calling",
    weakLabel: "工具调用",
    mode: "coach",
    difficulty: "basic",
    question: "ToolCalls 在 Agent 里解决什么问题？",
    answerKeyPoints: ["工具调用", "可观测性"],
    commonMistakes: ["只说调用工具，不说日志"],
    oneMinuteTemplate: "按状态、工具、结果三步回答。",
    relatedTags: [],
    rubric: ["是否覆盖：工具调用"],
    fallbackUsed: false
  },
  practiceAnswerText: "",
  practiceAnswerStatus: "模糊",
  selfRating: null,
  lastPracticeResult: null,
  visibleTasks: [task],
  filterSummary: "正在查看报告 #12 中 agent_tool_calling 的专项训练",
  loading: false,
  error: "",
  loadTasks: vi.fn(),
  setFilters: vi.fn(),
  setStatusFilter: vi.fn(),
  setWeakTagFilter: vi.fn(),
  clearFilters: vi.fn(),
  startTask: vi.fn(),
  completeTask: vi.fn(),
  openPractice: vi.fn(),
  submitPractice: vi.fn(),
  resetPractice: vi.fn(),
  setPracticeAnswerText: vi.fn(),
  setPracticeAnswerStatus: vi.fn(),
  setSelfRating: vi.fn(),
  archiveTask: vi.fn()
};

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: { recordId: "12", weakTag: "agent_tool_calling" } }),
  useRouter: () => ({ push: pushMock })
}));

vi.mock("@/stores/training", () => ({
  useTrainingStore: () => trainingStore
}));

describe("training page", () => {
  beforeEach(() => {
    pushMock.mockReset();
    trainingStore.loadTasks.mockReset();
    trainingStore.setFilters.mockReset();
    trainingStore.setStatusFilter.mockReset();
    trainingStore.setWeakTagFilter.mockReset();
    trainingStore.clearFilters.mockReset();
    trainingStore.startTask.mockReset();
    trainingStore.completeTask.mockReset();
    trainingStore.openPractice.mockReset();
    trainingStore.submitPractice.mockReset();
    trainingStore.resetPractice.mockReset();
    trainingStore.setPracticeAnswerText.mockReset();
    trainingStore.setPracticeAnswerStatus.mockReset();
    trainingStore.setSelfRating.mockReset();
    trainingStore.archiveTask.mockReset();
  });

  it("loads and renders the training center v2 workbench", () => {
    const wrapper = mount(TrainingPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(trainingStore.loadTasks).toHaveBeenCalled();
    expect(trainingStore.setFilters).toHaveBeenCalledWith({
      sourceInterviewRecordId: 12,
      weakTag: "agent_tool_calling"
    });
    expect(wrapper.text()).toContain("训练中心");
    expect(wrapper.text()).toContain("训练概览");
    expect(wrapper.text()).toContain("薄弱点训练地图");
    expect(wrapper.text()).toContain("平均掌握度");
    expect(wrapper.text()).toContain("专项练习");
    expect(wrapper.text()).toContain("正在查看报告 #12 中 agent_tool_calling 的专项训练");
    expect(wrapper.text()).toContain("工具调用专项训练");
    expect(wrapper.text()).toContain("补齐 Agent tool calling 表达");
    expect(wrapper.text()).toContain("待训练");
    expect(wrapper.text()).toContain("45");
  });

  it("filters tasks by status and weak tag", async () => {
    const wrapper = mount(TrainingPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="status-filter-done"]').trigger("click");
    expect(trainingStore.setStatusFilter).toHaveBeenCalledWith("done");

    await wrapper.get('[data-testid="weak-tag-agent_tool_calling"]').trigger("click");
    expect(trainingStore.setWeakTagFilter).toHaveBeenCalledWith("agent_tool_calling");
  });

  it("starts, completes and archives a training task", async () => {
    const wrapper = mount(TrainingPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="start-task-3"]').trigger("click");
    expect(trainingStore.startTask).toHaveBeenCalledWith(3);
    expect(trainingStore.openPractice).toHaveBeenCalledWith(3);

    await wrapper.get('[data-testid="complete-task-3"]').trigger("click");
    expect(trainingStore.completeTask).toHaveBeenCalledWith(3, "完整");

    await wrapper.get('[data-testid="archive-task-3"]').trigger("click");
    expect(trainingStore.archiveTask).toHaveBeenCalledWith(3);
  });

  it("can return to the interview workbench", async () => {
    const wrapper = mount(TrainingPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="return-to-interview"]').trigger("click");

    expect(pushMock).toHaveBeenCalledWith("/vue/app/interview");
  });
});
