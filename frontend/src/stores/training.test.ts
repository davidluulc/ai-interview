import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as trainingApi from "@/api/training";
import { useTrainingStore } from "./training";

vi.mock("@/api/training", () => ({
  listTrainingTasks: vi.fn(),
  getTrainingPractice: vi.fn(),
  startTrainingTask: vi.fn(),
  completeTrainingTask: vi.fn(),
  archiveTrainingTask: vi.fn()
}));

const task = {
  id: 3,
  weakTag: "agent_tool_calling",
  weakLabel: "工具调用",
  title: "工具调用专项训练",
  description: "补齐 Agent tool calling 表达。",
  status: "todo" as const,
  priority: "high" as const,
  masteryScore: 45,
  sourceInterviewRecordId: 12
};

describe("training store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(trainingApi.listTrainingTasks).mockReset();
    vi.mocked(trainingApi.getTrainingPractice).mockReset();
    vi.mocked(trainingApi.startTrainingTask).mockReset();
    vi.mocked(trainingApi.completeTrainingTask).mockReset();
    vi.mocked(trainingApi.archiveTrainingTask).mockReset();
  });

  it("loads real training tasks and groups active tasks", async () => {
    vi.mocked(trainingApi.listTrainingTasks).mockResolvedValue({ items: [task] });

    const store = useTrainingStore();
    await store.loadTasks();

    expect(store.tasks).toHaveLength(1);
    expect(store.activeTasks).toHaveLength(1);
    expect(store.completedTasks).toHaveLength(0);
    expect(store.error).toBe("");
  });

  it("filters visible tasks by source report id and weak tag", async () => {
    vi.mocked(trainingApi.listTrainingTasks).mockResolvedValue({
      items: [
        task,
        {
          ...task,
          id: 4,
          weakTag: "rag_quality",
          title: "RAG 质量评估专项训练",
          sourceInterviewRecordId: 12
        },
        {
          ...task,
          id: 5,
          weakTag: "agent_tool_calling",
          sourceInterviewRecordId: 99
        }
      ]
    });

    const store = useTrainingStore();
    await store.loadTasks();
    store.setFilters({ sourceInterviewRecordId: 12, weakTag: "agent_tool_calling" });

    expect(store.visibleTasks).toHaveLength(1);
    expect(store.visibleTasks[0].id).toBe(3);
    expect(store.filterSummary).toBe("正在查看报告 #12 中 agent_tool_calling 的专项训练");
  });

  it("updates a task when starting, completing and archiving it", async () => {
    vi.mocked(trainingApi.listTrainingTasks).mockResolvedValue({ items: [task] });
    vi.mocked(trainingApi.startTrainingTask).mockResolvedValue({ ...task, status: "in_progress" });
    vi.mocked(trainingApi.completeTrainingTask).mockResolvedValue({ ...task, status: "done", masteryScore: 82 });
    vi.mocked(trainingApi.archiveTrainingTask).mockResolvedValue({ ...task, status: "archived" });

    const store = useTrainingStore();
    await store.loadTasks();
    await store.startTask(3);
    expect(store.tasks[0].status).toBe("in_progress");

    await store.completeTask(3, "完整");
    expect(store.tasks[0].status).toBe("done");
    expect(store.tasks[0].masteryScore).toBe(82);

    await store.archiveTask(3);
    expect(store.tasks[0].status).toBe("archived");
  });

  it("computes training overview metrics", () => {
    const store = useTrainingStore();
    store.tasks = [
      {
        id: 1,
        weakTag: "agent_tool_calling",
        title: "A",
        description: "",
        status: "todo",
        priority: "high",
        masteryScore: 40
      },
      {
        id: 2,
        weakTag: "rag_quality",
        title: "B",
        description: "",
        status: "in_progress",
        priority: "medium",
        masteryScore: 60
      },
      {
        id: 3,
        weakTag: "rag_quality",
        title: "C",
        description: "",
        status: "done",
        priority: "low",
        masteryScore: 80
      },
      {
        id: 4,
        weakTag: "behavioral",
        title: "D",
        description: "",
        status: "archived",
        priority: "low",
        masteryScore: 20
      }
    ];

    expect(store.todoTasks).toHaveLength(1);
    expect(store.inProgressTasks).toHaveLength(1);
    expect(store.doneTasks).toHaveLength(1);
    expect(store.archivedTasks).toHaveLength(1);
    expect(store.averageMastery).toBe(50);
  });

  it("groups training tasks by weak tag", () => {
    const store = useTrainingStore();
    store.tasks = [
      {
        id: 1,
        weakTag: "rag_quality",
        weakLabel: "RAG 质量",
        title: "A",
        description: "",
        status: "todo",
        priority: "high",
        masteryScore: 40
      },
      {
        id: 2,
        weakTag: "rag_quality",
        weakLabel: "RAG 质量",
        title: "B",
        description: "",
        status: "done",
        priority: "medium",
        masteryScore: 80
      }
    ];

    expect(store.weakTagGroups).toEqual([
      expect.objectContaining({
        weakTag: "rag_quality",
        weakLabel: "RAG 质量",
        total: 2,
        averageMastery: 60,
        highestPriority: "high"
      })
    ]);
  });

  it("filters visible tasks by status and weak tag", () => {
    const store = useTrainingStore();
    store.tasks = [
      {
        id: 1,
        weakTag: "rag_quality",
        title: "A",
        description: "",
        status: "todo",
        priority: "high",
        masteryScore: 40
      },
      {
        id: 2,
        weakTag: "agent_tool_calling",
        title: "B",
        description: "",
        status: "done",
        priority: "medium",
        masteryScore: 80
      }
    ];

    store.setWeakTagFilter("rag_quality");
    store.setStatusFilter("todo");

    expect(store.visibleTasks.map((item) => item.id)).toEqual([1]);

    store.clearFilters();
    expect(store.visibleTasks).toHaveLength(2);
  });

  it("opens a practice payload for a task", async () => {
    vi.mocked(trainingApi.getTrainingPractice).mockResolvedValueOnce({
      task: { ...task, id: 1, weakTag: "rag_quality" },
      practice: makePractice({ weakTag: "rag_quality", question: "什么是 Hit@K？" })
    });
    const store = useTrainingStore();

    await store.openPractice(1);

    expect(store.selectedTaskId).toBe(1);
    expect(store.practiceDetail?.question).toBe("什么是 Hit@K？");
    expect(store.practiceError).toBe("");
  });

  it("submits practice and updates the task list", async () => {
    const updated = { ...task, id: 1, status: "done" as const, masteryScore: 85, attemptCount: 1 };
    vi.mocked(trainingApi.completeTrainingTask).mockResolvedValueOnce(updated);
    const store = useTrainingStore();
    store.tasks = [{ ...task, id: 1, status: "in_progress", masteryScore: 70, attemptCount: 0 }];
    store.selectedTaskId = 1;
    store.practiceAnswerText = "我的回答";
    store.practiceAnswerStatus = "完整";
    store.selfRating = 4;

    await store.submitPractice();

    expect(store.tasks[0].masteryScore).toBe(85);
    expect(store.lastPracticeResult?.masteryScore).toBe(85);
    expect(trainingApi.completeTrainingTask).toHaveBeenCalledWith(1, {
      answerStatus: "完整",
      answerText: "我的回答",
      selfRating: 4
    });
  });
});

function makePractice(overrides: Partial<trainingApi.TrainingPractice> = {}): trainingApi.TrainingPractice {
  return {
    weakTag: "rag_quality",
    weakLabel: "RAG 质量评估",
    mode: "coach",
    difficulty: "basic",
    question: "什么是 Hit@K？",
    answerKeyPoints: ["Hit@K"],
    commonMistakes: [],
    oneMinuteTemplate: "",
    relatedTags: [],
    rubric: [],
    fallbackUsed: false,
    ...overrides
  };
}
