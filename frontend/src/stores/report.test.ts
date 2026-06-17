import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as historyApi from "@/api/history";
import * as trainingApi from "@/api/training";
import { useReportStore } from "./report";

vi.mock("@/api/history", () => ({
  listHistory: vi.fn()
}));

vi.mock("@/api/training", () => ({
  generateTrainingTasksFromReport: vi.fn()
}));

describe("report store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(historyApi.listHistory).mockReset();
    vi.mocked(trainingApi.generateTrainingTasksFromReport).mockReset();
  });

  it("loads a single interview report by record id", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([
      {
        id: 12,
        createdAt: "2026-06-12T11:00:00",
        applicationProfile: { id: 2, title: "AI 应用开发投递", targetRole: "Agent 开发实习生" },
        profile: { targetRole: "Agent 开发实习生" },
        answers: [{ question: "Agent 和普通 LLM 有什么区别？", answer: "Agent 会观察状态并决策。" }],
        report: {
          score: 88,
          level: "良好",
          summary: "表达有结构，但可以补充工具调用细节。",
          weakTags: ["agent_tool_calling"]
        }
      }
    ]);

    const store = useReportStore();
    await store.loadReport(12);

    expect(store.record?.id).toBe(12);
    expect(store.score).toBe("88");
    expect(store.weakTags).toEqual(["agent_tool_calling"]);
    expect(store.error).toBe("");
  });

  it("sets an error when the report record cannot be found", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([]);

    const store = useReportStore();
    await store.loadReport(99);

    expect(store.record).toBeNull();
    expect(store.error).toBe("没有找到这场面试报告");
  });

  it("generates training tasks from the loaded report", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([
      {
        id: 12,
        createdAt: "2026-06-12T11:00:00",
        applicationProfile: { id: 2, title: "AI 应用开发投递", targetRole: "Agent 开发实习生" },
        profile: { targetRole: "Agent 开发实习生" },
        answers: [],
        report: { score: 88, weakTags: ["agent_tool_calling"] }
      }
    ]);
    vi.mocked(trainingApi.generateTrainingTasksFromReport).mockResolvedValue({
      items: [
        {
          id: 3,
          weakTag: "agent_tool_calling",
          title: "工具调用专项训练",
          description: "补齐工具调用表达。",
          status: "todo",
          priority: "high",
          masteryScore: 45,
          sourceInterviewRecordId: 12
        }
      ]
    });

    const store = useReportStore();
    await store.loadReport(12);
    const tasks = await store.generateTrainingTasks();

    expect(trainingApi.generateTrainingTasksFromReport).toHaveBeenCalledWith({
      applicationProfileId: 2,
      sourceInterviewRecordId: 12,
      report: { score: 88, weakTags: ["agent_tool_calling"] }
    });
    expect(tasks).toHaveLength(1);
    expect(store.trainingGeneratedMessage).toBe("已生成 1 个专项训练任务");
  });
});
