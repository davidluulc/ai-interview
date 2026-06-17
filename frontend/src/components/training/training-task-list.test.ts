import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TrainingTaskList from "./TrainingTaskList.vue";

describe("TrainingTaskList", () => {
  it("renders training task planning metadata", () => {
    const wrapper = mount(TrainingTaskList, {
      props: {
        tasks: [
          {
            id: 5,
            weakTag: "rag_quality",
            title: "RAG 质量评估训练",
            description: "补齐命中率和 MRR 表达。",
            status: "in_progress",
            priority: "high",
            masteryScore: 62,
            attemptCount: 2,
            nextReviewAt: "2026-06-14T09:00:00"
          }
        ]
      }
    });

    expect(wrapper.text()).toContain("高优先级");
    expect(wrapper.text()).toContain("尝试 2 次");
    expect(wrapper.text()).toContain("下次复习 2026-06-14");
  });

  it("emits an open-report event from a task source report", async () => {
    const wrapper = mount(TrainingTaskList, {
      props: {
        tasks: [
          {
            id: 3,
            weakTag: "agent_tool_calling",
            title: "工具调用专项训练",
            description: "补齐工具调用表达。",
            status: "todo",
            masteryScore: 45,
            sourceInterviewRecordId: 12
          }
        ]
      }
    });

    await wrapper.get('[data-testid="open-source-report-12"]').trigger("click");

    expect(wrapper.emitted("open-report")).toEqual([[12]]);
  });
});
